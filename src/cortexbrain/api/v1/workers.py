"""Workers API — Celery worker health, active tasks, and beat schedule."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.models.schemas import (
    ActiveTask,
    BeatScheduleEntry,
    WorkerInfo,
    WorkersStatusResponse,
)
from cortexbrain.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()

INSPECT_TIMEOUT = 2.0

TASK_DESCRIPTIONS = {
    "cortexbrain.workers.tasks.decay_cycle_task": "Decay activation scores in Redis, evict nodes at zero",
    "cortexbrain.workers.tasks.salience_recompute_task": "Recompute salience scores for all entities",
    "cortexbrain.workers.tasks.consolidation_task": "Full consolidation: promote, archive, merge, compress",
    "cortexbrain.workers.tasks.batch_ingestion_task": "Process document batches through Cognee ECL pipeline",
}


def _inspect_with_timeout(method_name: str, timeout: float = INSPECT_TIMEOUT):
    """Run a Celery inspect call in a thread with timeout.

    Celery inspect() is synchronous and hangs if no worker responds.
    """
    inspector = celery_app.control.inspect(timeout=timeout)
    method = getattr(inspector, method_name)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(method)
        try:
            return future.result(timeout=timeout + 0.5)
        except (FuturesTimeoutError, Exception) as e:
            logger.debug("Inspect %s failed: %s", method_name, e)
            return None


def _format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"Every {seconds}s"
    if seconds < 3600:
        return f"Every {seconds // 60}m"
    if seconds < 86400:
        return f"Every {seconds // 3600}h"
    return f"Every {seconds // 86400}d"


def _build_beat_schedule() -> list[BeatScheduleEntry]:
    schedule = celery_app.conf.beat_schedule or {}
    entries = []
    for name, config in schedule.items():
        task = config.get("task", "")
        secs = config.get("schedule", 0)
        if hasattr(secs, "total_seconds"):
            secs = int(secs.total_seconds())
        else:
            secs = int(secs)
        entries.append(BeatScheduleEntry(
            name=name,
            task=task,
            interval_seconds=secs,
            interval_human=_format_interval(secs),
            description=TASK_DESCRIPTIONS.get(task, task.split(".")[-1]),
        ))
    return entries


def _parse_worker_info(
    stats_result: dict | None, ping_result: dict | None, active_result: dict | None
) -> list[WorkerInfo]:
    if not ping_result:
        return []
    workers = []
    for hostname in ping_result:
        worker_stats = (stats_result or {}).get(hostname, {})
        pool = worker_stats.get("pool", {})
        total_dict = worker_stats.get("total", {})
        total_processed = sum(total_dict.values()) if isinstance(total_dict, dict) else 0
        active_count = len((active_result or {}).get(hostname, []))
        workers.append(WorkerInfo(
            hostname=hostname,
            pid=worker_stats.get("pid"),
            pool_size=pool.get("max-concurrency"),
            total_tasks_processed=total_processed,
            active_task_count=active_count,
        ))
    return workers


def _parse_tasks(result: dict | None) -> list[ActiveTask]:
    if not result:
        return []
    tasks = []
    for hostname, task_list in result.items():
        for t in (task_list or []):
            started_at = None
            runtime = None
            time_start = t.get("time_start")
            if time_start:
                started_at = datetime.fromtimestamp(time_start, tz=timezone.utc).isoformat()
                runtime = round(time.time() - time_start, 1)
            tasks.append(ActiveTask(
                task_id=t.get("id", ""),
                task_name=t.get("name", ""),
                worker=hostname,
                started_at=started_at,
                runtime_seconds=runtime,
                args=str(t.get("args")) if t.get("args") else None,
                kwargs=str(t.get("kwargs")) if t.get("kwargs") else None,
            ))
    return tasks


def _parse_registered(result: dict | None) -> list[str]:
    if not result:
        return []
    all_tasks: set[str] = set()
    for task_list in result.values():
        all_tasks.update(task_list or [])
    return sorted(all_tasks)


@router.get("/workers/status", response_model=WorkersStatusResponse)
async def get_workers_status(api_key: str = Depends(verify_api_key)):
    """Comprehensive Celery worker status for the Workers dashboard."""
    start = time.monotonic()

    ping_result = _inspect_with_timeout("ping")
    workers_connected = ping_result is not None and len(ping_result) > 0

    stats_result = None
    active_result = None
    reserved_result = None
    registered_result = None

    if workers_connected:
        # Run remaining inspect calls concurrently to reduce total latency
        with ThreadPoolExecutor(max_workers=4) as pool:
            inspector = celery_app.control.inspect(timeout=INSPECT_TIMEOUT)
            f_stats = pool.submit(inspector.stats)
            f_active = pool.submit(inspector.active)
            f_reserved = pool.submit(inspector.reserved)
            f_registered = pool.submit(inspector.registered)
            try:
                stats_result = f_stats.result(timeout=INSPECT_TIMEOUT + 0.5)
            except Exception:
                pass
            try:
                active_result = f_active.result(timeout=INSPECT_TIMEOUT + 0.5)
            except Exception:
                pass
            try:
                reserved_result = f_reserved.result(timeout=INSPECT_TIMEOUT + 0.5)
            except Exception:
                pass
            try:
                registered_result = f_registered.result(timeout=INSPECT_TIMEOUT + 0.5)
            except Exception:
                pass

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    return WorkersStatusResponse(
        connected=workers_connected,
        latency_ms=latency_ms,
        workers=_parse_worker_info(stats_result, ping_result, active_result),
        active_tasks=_parse_tasks(active_result),
        reserved_tasks=_parse_tasks(reserved_result),
        registered_tasks=_parse_registered(registered_result),
        beat_schedule=_build_beat_schedule(),
    )
