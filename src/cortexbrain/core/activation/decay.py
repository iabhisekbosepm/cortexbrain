"""Decay Cycle — Background process that decrements activation scores.

Runs every DECAY_INTERVAL_SECONDS (default 30s). Nodes reaching 0 are evicted
from Active Memory (Redis) but remain in Passive Memory (Neo4j). No data is lost.
"""

import logging

from cortexbrain.config import get_settings
from cortexbrain.memory.active import ActiveMemoryStore

logger = logging.getLogger(__name__)


class DecayCycle:
    """Periodically decays activation scores across all sessions."""

    def __init__(self, active_memory: ActiveMemoryStore):
        self.active = active_memory
        self.settings = get_settings()

    async def run_cycle(self) -> dict[str, list[str]]:
        """Execute one decay cycle across all active sessions.

        Returns dict of {session_id: [evicted_node_ids]}.
        """
        decay_rate = self.settings.decay_rate
        session_keys = await self.active.get_all_session_keys()
        eviction_report: dict[str, list[str]] = {}

        for session_id in session_keys:
            evicted = await self.active.decay_all(session_id, decay_rate)
            if evicted:
                eviction_report[session_id] = evicted
                logger.debug(
                    "Decay cycle evicted %d nodes from session %s",
                    len(evicted),
                    session_id,
                )

        return eviction_report
