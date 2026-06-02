"""Consolidation API — manual trigger, status polling, and last report."""

import json
import logging
from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.models.schemas import ConsolidationTriggerResponse
from cortexbrain.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.post("/consolidation/run", response_model=ConsolidationTriggerResponse)
async def trigger_consolidation(
    api_key: str = Depends(verify_api_key),
):
    """Manually trigger a consolidation cycle. Returns task_id for polling."""
    from cortexbrain.workers.tasks import consolidation_task

    task = consolidation_task.delay()
    return ConsolidationTriggerResponse(status="queued", task_id=task.id)


@router.get("/consolidation/status/{task_id}")
async def consolidation_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Poll consolidation task status (PENDING, STARTED, SUCCESS, FAILURE)."""
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        if result.successful():
            response["report"] = result.result
        else:
            response["error"] = str(result.result)
    return response


@router.get("/consolidation/last-report")
async def last_consolidation_report(
    api_key: str = Depends(verify_api_key),
):
    """Get the most recent consolidation summary from audit logs."""
    meta = MetaMemoryStore()
    logs = await meta.get_audit_logs(org_id=_DEFAULT_ORG, limit=50)
    for log in logs:
        if log.action == "consolidation:summary":
            try:
                report_data = json.loads(log.new_value)
                return {
                    "status": "found",
                    "report": report_data,
                    "timestamp": log.timestamp.isoformat(),
                }
            except json.JSONDecodeError:
                return {
                    "status": "found",
                    "report_raw": log.new_value,
                    "timestamp": log.timestamp.isoformat(),
                }
    return {"status": "no_report", "message": "No consolidation has been run yet."}
