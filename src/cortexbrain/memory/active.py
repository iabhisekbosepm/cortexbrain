"""Active Memory (M_a) — Redis-backed activation scores and session context.

This is CortexBrain-specific (Cognee has no activation concept).
Uses Redis sorted sets for O(log N) activation score management.
"""

from uuid import UUID

import redis.asyncio as aioredis

from cortexbrain.config import get_settings
from cortexbrain.models.graph import ActivationState


def _session_key(session_id: str) -> str:
    return f"cortex:active:{session_id}"


def _node_detail_key(session_id: str, node_id: UUID) -> str:
    return f"cortex:active:{session_id}:detail:{node_id}"


class ActiveMemoryStore:
    """Manages activation scores in Redis for the Activation-Decay Engine."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self._redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def activate(self, session_id: str, node_id: UUID, score: float) -> None:
        """Set or update activation score for a node in a session."""
        r = await self._get_redis()
        key = _session_key(session_id)
        await r.zadd(key, {str(node_id): score})
        # Session TTL: auto-expire after 10 minutes of no writes
        await r.expire(key, 600)

    async def activate_batch(
        self, session_id: str, scores: dict[str, float]
    ) -> None:
        """Batch-activate multiple nodes in a single Redis pipeline round-trip."""
        if not scores:
            return
        r = await self._get_redis()
        key = _session_key(session_id)
        pipe = r.pipeline()
        pipe.zadd(key, scores)
        pipe.expire(key, 600)
        await pipe.execute()

    async def get_active_nodes(
        self, session_id: str, min_score: float = 0.0
    ) -> list[tuple[str, float]]:
        """Return all active nodes above min_score, sorted descending by score."""
        r = await self._get_redis()
        key = _session_key(session_id)
        # ZRANGEBYSCORE returns ascending; we reverse for descending
        results = await r.zrangebyscore(key, min_score, "+inf", withscores=True)
        return sorted(results, key=lambda x: x[1], reverse=True)

    async def get_score(self, session_id: str, node_id: UUID) -> float | None:
        """Get activation score for a specific node."""
        r = await self._get_redis()
        score = await r.zscore(_session_key(session_id), str(node_id))
        return score

    async def decay_all(self, session_id: str, decay_amount: int) -> list[str]:
        """Decrement all scores by decay_amount. Returns node_ids evicted (score <= 0)."""
        r = await self._get_redis()
        key = _session_key(session_id)

        # Get all members
        members = await r.zrangebyscore(key, "-inf", "+inf", withscores=True)
        evicted: list[str] = []

        pipe = r.pipeline()
        for node_id_str, current_score in members:
            new_score = current_score - decay_amount
            if new_score <= 0:
                pipe.zrem(key, node_id_str)
                evicted.append(node_id_str)
            else:
                pipe.zadd(key, {node_id_str: new_score})
        await pipe.execute()

        return evicted

    async def clear_session(self, session_id: str) -> None:
        """Remove all activation state for a session."""
        r = await self._get_redis()
        key = _session_key(session_id)
        await r.delete(key)

    async def get_all_session_keys(self) -> list[str]:
        """List all active session keys (for decay cycle worker)."""
        r = await self._get_redis()
        keys = []
        async for key in r.scan_iter(match="cortex:active:*", count=100):
            # Only top-level session keys, not detail sub-keys
            if ":detail:" not in key:
                keys.append(key.replace("cortex:active:", ""))
        return keys
