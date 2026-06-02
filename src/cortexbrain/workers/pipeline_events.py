"""Pipeline event emitter — publishes stage transitions to Redis pub/sub.

Celery tasks call emit() at each stage boundary. The FastAPI SSE endpoint
subscribes to the same channel and relays events to the frontend.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from cortexbrain.config import get_settings

logger = logging.getLogger(__name__)

PIPELINE_CHANNEL = "cortex:pipeline:events"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineEventEmitter:
    """Publishes pipeline stage events to Redis pub/sub.

    Uses synchronous redis.Redis because Celery tasks run in sync workers.
    All publish calls are wrapped in try/except so they never break task execution.

    Usage in Celery tasks:
        emitter = PipelineEventEmitter("decay", 3, task_id=self.request.id)
        emitter.pipeline_started()
        emitter.stage_started(0, "scan_sessions")
        # ... do work ...
        emitter.stage_completed(0, "scan_sessions", {"sessions_found": 5})
        emitter.pipeline_completed({"total_evicted": 2})
    """

    def __init__(
        self,
        pipeline: str,
        total_stages: int,
        task_id: Optional[str] = None,
    ):
        self.pipeline = pipeline
        self.total_stages = total_stages
        self.task_id = task_id
        self._redis: Optional[redis.Redis] = None
        self._stage_start_times: dict[int, float] = {}

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.celery_broker_url,
                decode_responses=True,
            )
        return self._redis

    def _publish(self, event: dict[str, Any]) -> None:
        try:
            r = self._get_redis()
            r.publish(PIPELINE_CHANNEL, json.dumps(event, default=str))
        except Exception as e:
            logger.debug("Pipeline event publish failed (non-fatal): %s", e)

    def pipeline_started(self) -> None:
        self._publish({
            "event_id": str(uuid.uuid4()),
            "pipeline": self.pipeline,
            "task_id": self.task_id,
            "stage": "__pipeline__",
            "stage_index": -1,
            "total_stages": self.total_stages,
            "status": "started",
            "metrics": {},
            "error": None,
            "timestamp": _iso_now(),
            "duration_ms": None,
        })

    def pipeline_completed(self, metrics: Optional[dict[str, Any]] = None) -> None:
        self._publish({
            "event_id": str(uuid.uuid4()),
            "pipeline": self.pipeline,
            "task_id": self.task_id,
            "stage": "__pipeline__",
            "stage_index": -1,
            "total_stages": self.total_stages,
            "status": "completed",
            "metrics": metrics or {},
            "error": None,
            "timestamp": _iso_now(),
            "duration_ms": None,
        })

    def stage_started(self, stage_index: int, stage_name: str) -> None:
        self._stage_start_times[stage_index] = time.monotonic()
        self._publish({
            "event_id": str(uuid.uuid4()),
            "pipeline": self.pipeline,
            "task_id": self.task_id,
            "stage": stage_name,
            "stage_index": stage_index,
            "total_stages": self.total_stages,
            "status": "running",
            "metrics": {},
            "error": None,
            "timestamp": _iso_now(),
            "duration_ms": None,
        })

    def stage_completed(
        self,
        stage_index: int,
        stage_name: str,
        metrics: Optional[dict[str, Any]] = None,
    ) -> None:
        start = self._stage_start_times.get(stage_index)
        duration_ms = round((time.monotonic() - start) * 1000) if start else None
        self._publish({
            "event_id": str(uuid.uuid4()),
            "pipeline": self.pipeline,
            "task_id": self.task_id,
            "stage": stage_name,
            "stage_index": stage_index,
            "total_stages": self.total_stages,
            "status": "completed",
            "metrics": metrics or {},
            "error": None,
            "timestamp": _iso_now(),
            "duration_ms": duration_ms,
        })

    def stage_failed(
        self,
        stage_index: int,
        stage_name: str,
        error: str,
    ) -> None:
        start = self._stage_start_times.get(stage_index)
        duration_ms = round((time.monotonic() - start) * 1000) if start else None
        self._publish({
            "event_id": str(uuid.uuid4()),
            "pipeline": self.pipeline,
            "task_id": self.task_id,
            "stage": stage_name,
            "stage_index": stage_index,
            "total_stages": self.total_stages,
            "status": "failed",
            "metrics": {},
            "error": error,
            "timestamp": _iso_now(),
            "duration_ms": duration_ms,
        })
