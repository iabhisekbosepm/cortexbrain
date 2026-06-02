"""POST /api/v1/ingest — Document upload and ingestion via Cognee's ECL pipeline."""

import logging
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Form, UploadFile

from cortexbrain.api.deps import get_meta_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.ingestion.documents import ingest_documents
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.models.schemas import TextIngestRequest
from cortexbrain.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")
_NULL_NODE = UUID("00000000-0000-0000-0000-000000000000")


@router.post("/ingest")
async def ingest(
    files: list[UploadFile],
    dataset_name: str = Form(default="default"),
    source_type: str = Form(default="document"),
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Ingest documents via Cognee's ECL pipeline (synchronous).

    Accepts PDF, Markdown, text, and image files via multipart upload.
    Files are saved to a temp directory so Cognee can auto-detect types
    (including images routed to ImageDocument for vision transcription).
    """
    if not files:
        return {"status": "error", "detail": "No files provided"}

    tmp_dir = tempfile.mkdtemp(prefix="cortexbrain_sync_")
    filenames = []
    try:
        for file in files:
            content = await file.read()
            safe_name = Path(file.filename).name if file.filename else "upload.txt"
            file_path = Path(tmp_dir) / safe_name
            file_path.write_bytes(content)
            filenames.append(safe_name)

        logger.info("Ingesting %d file(s): %s into dataset=%s", len(files), filenames, dataset_name)

        result = await ingest_documents(
            data=tmp_dir,
            dataset_name=dataset_name,
        )

        await meta.record_mutation(
            org_id=_DEFAULT_ORG,
            node_id=_NULL_NODE,
            action="ingestion",
            changed_by=f"api:{source_type}",
            new_value=f"{len(filenames)} file(s): {', '.join(filenames[:5])}",
            reason=f"Document ingestion into dataset={dataset_name}",
        )

        return {**result, "files": filenames}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/ingest/batch")
async def ingest_batch(
    files: list[UploadFile],
    dataset_name: str = Form(default="default"),
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Batch ingestion — saves files to temp dir, dispatches Celery task, returns task_id.

    Use GET /ingest/batch/{task_id} to poll for status.
    """
    if not files:
        return {"status": "error", "detail": "No files provided"}

    # Save uploaded files to a temp directory for the Celery worker to read
    tmp_dir = tempfile.mkdtemp(prefix="cortexbrain_batch_")
    filenames = []
    for file in files:
        content = await file.read()
        safe_name = Path(file.filename).name if file.filename else "upload.txt"
        file_path = Path(tmp_dir) / safe_name
        file_path.write_bytes(content)
        filenames.append(safe_name)

    logger.info(
        "Batch ingestion queued: %d file(s) → %s, dataset=%s",
        len(files),
        tmp_dir,
        dataset_name,
    )

    # Dispatch Celery task
    from cortexbrain.workers.tasks import batch_ingestion_task

    task = batch_ingestion_task.delay(data_path=tmp_dir, dataset_name=dataset_name)

    await meta.record_mutation(
        org_id=_DEFAULT_ORG,
        node_id=_NULL_NODE,
        action="ingestion",
        changed_by="api:batch",
        new_value=f"{len(filenames)} file(s): {', '.join(filenames[:5])}",
        reason=f"Batch ingestion queued into dataset={dataset_name} (task={task.id})",
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "files": filenames,
        "dataset": dataset_name,
    }


@router.get("/ingest/batch/{task_id}")
async def ingest_batch_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Poll batch ingestion task status."""
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,  # PENDING, STARTED, SUCCESS, FAILURE
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)

    return response


@router.post("/ingest/text")
async def ingest_text(
    request: TextIngestRequest,
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Ingest raw text via Cognee's ECL pipeline.

    Accepts JSON with a text field. Designed for programmatic ingestion
    from MCP clients, CLIs, and other tools that don't have files to upload.
    """
    logger.info(
        "Text ingestion: %d chars into dataset=%s (source_type=%s)",
        len(request.text),
        request.dataset_name,
        request.source_type,
    )

    result = await ingest_documents(
        data=request.text,
        dataset_name=request.dataset_name,
    )

    await meta.record_mutation(
        org_id=_DEFAULT_ORG,
        node_id=_NULL_NODE,
        action="ingestion",
        changed_by=f"api:{request.source_type}",
        new_value=f"Text: {len(request.text)} chars",
        reason=f"Text ingestion into dataset={request.dataset_name}",
    )

    return {**result, "source_type": request.source_type, "text_length": len(request.text)}


@router.post("/ingest/text/async")
async def ingest_text_async(
    request: TextIngestRequest,
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Queue text ingestion as a Celery task — returns immediately.

    Same as /ingest/text but non-blocking. Designed for hooks and
    automation that need fire-and-forget semantics.
    Use GET /ingest/batch/{task_id} to poll for status.
    """
    from cortexbrain.workers.tasks import text_ingestion_task

    logger.info(
        "Async text ingestion queued: %d chars into dataset=%s",
        len(request.text),
        request.dataset_name,
    )

    task = text_ingestion_task.delay(
        text=request.text,
        dataset_name=request.dataset_name,
    )

    await meta.record_mutation(
        org_id=_DEFAULT_ORG,
        node_id=_NULL_NODE,
        action="ingestion",
        changed_by=f"api:{request.source_type}",
        new_value=f"Text: {len(request.text)} chars",
        reason=f"Async text ingestion queued into dataset={request.dataset_name} (task={task.id})",
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "dataset": request.dataset_name,
        "text_length": len(request.text),
    }
