"""Pipeline Monitor — SSE stream for real-time pipeline stage events.

GET /api/v1/pipeline/stream  — SSE endpoint (long-lived connection)
GET /api/v1/pipeline/status  — Snapshot of last known pipeline states
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.config import get_settings
from cortexbrain.workers.pipeline_events import PIPELINE_CHANNEL

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory cache of last-seen pipeline state (populated by active SSE connections)
_last_pipeline_state: dict[str, dict] = {}


def _sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event — same pattern as agent_query.py."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _pipeline_event_generator() -> AsyncGenerator[str, None]:
    """Subscribe to Redis pub/sub and yield SSE events."""
    settings = get_settings()

    redis_client = aioredis.from_url(
        settings.celery_broker_url,
        decode_responses=True,
    )

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(PIPELINE_CHANNEL)

    # Send initial heartbeat
    yield _sse_event("heartbeat", {
        "connected": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                # 30s heartbeat to keep connection alive through proxies
                yield _sse_event("heartbeat", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            if message and message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    pipeline = event_data.get("pipeline", "unknown")
                    _last_pipeline_state[pipeline] = event_data
                    yield _sse_event("pipeline_event", event_data)
                except json.JSONDecodeError:
                    pass

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(PIPELINE_CHANNEL)
        await pubsub.close()
        await redis_client.close()


@router.get("/pipeline/stream")
async def pipeline_stream(api_key: str = Depends(verify_api_key)):
    """SSE stream of real-time pipeline stage events.

    Connects to Redis pub/sub and relays pipeline events to the frontend.
    Sends heartbeat every 30s to keep the connection alive.
    """
    async def event_stream():
        try:
            async for event in _pipeline_event_generator():
                yield event
        except Exception as e:
            logger.error("Pipeline stream error: %s", e)
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/pipeline/status")
async def pipeline_status(api_key: str = Depends(verify_api_key)):
    """Snapshot of last-seen state for each pipeline.

    Returns whatever was last cached from the pub/sub stream.
    Useful for initial page load before SSE connection is established.
    """
    return {
        "pipelines": _last_pipeline_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
