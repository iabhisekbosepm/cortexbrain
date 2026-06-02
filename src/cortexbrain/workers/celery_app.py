"""Celery application for CortexBrain background tasks.

Uses Redis as broker (same Redis instance as Active Memory, different DB).
"""

from celery import Celery

from cortexbrain.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cortexbrain",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["cortexbrain.workers.tasks"],
)

celery_app.conf.update(
    include=["cortexbrain.workers.tasks"],
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "decay-cycle": {
            "task": "cortexbrain.workers.tasks.decay_cycle_task",
            "schedule": settings.decay_interval_seconds,
        },
        "salience-recompute": {
            "task": "cortexbrain.workers.tasks.salience_recompute_task",
            "schedule": 3600,  # Every 1 hour
        },
        "consolidation-cycle": {
            "task": "cortexbrain.workers.tasks.consolidation_task",
            "schedule": settings.consolidation_schedule_seconds,  # Weekly
        },
    },
)
