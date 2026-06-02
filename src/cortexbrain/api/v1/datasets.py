"""GET /api/v1/datasets — List and search datasets (sources) in CortexBrain.

Wraps Cognee's dataset storage to expose source-level browsing via REST API
and MCP tools. Allows searching ingested knowledge by dataset name, source type,
and creation date.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from cognee.api.v1.datasets.datasets import datasets as cognee_datasets
from cognee.modules.users.methods import get_default_user
from cognee.infrastructure.databases.relational import get_relational_engine
from cognee.infrastructure.files.storage import get_storage_config
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cortexbrain.auth.middleware import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/datasets")
async def list_datasets(
    name: Optional[str] = Query(None, description="Filter by dataset name (substring match)"),
    api_key: str = Depends(verify_api_key),
):
    """List all datasets (knowledge sources) in the system.

    Each dataset corresponds to a source of ingested knowledge (e.g. "context_memory",
    "claude_code_memory", "slack_export"). Optionally filter by name.

    Returns dataset name, ID, creation date, and data item count.
    """
    try:
        all_datasets = await cognee_datasets.list_datasets()
    except Exception as e:
        logger.error("Failed to list datasets: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {e}")

    results = []
    for ds in all_datasets:
        ds_name = ds.name if hasattr(ds, "name") else str(ds)
        ds_id = str(ds.id) if hasattr(ds, "id") else ""
        created = ds.created_at.isoformat() if hasattr(ds, "created_at") and ds.created_at else None
        updated = ds.updated_at.isoformat() if hasattr(ds, "updated_at") and ds.updated_at else None

        # Apply name filter if provided
        if name and name.lower() not in ds_name.lower():
            continue

        results.append({
            "id": ds_id,
            "name": ds_name,
            "created_at": created,
            "updated_at": updated,
        })

    return {"datasets": results, "total": len(results)}


@router.get("/datasets/{dataset_name}/data")
async def get_dataset_data(
    dataset_name: str,
    api_key: str = Depends(verify_api_key),
):
    """List all data items within a specific dataset.

    Shows the individual ingested documents/texts within a dataset,
    including their name, creation date, extension, and size.

    The dataset_name is matched case-insensitively against Cognee's dataset names.
    """
    try:
        all_datasets = await cognee_datasets.list_datasets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {e}")

    # Find the dataset by name (case-insensitive)
    target_ds = None
    for ds in all_datasets:
        if hasattr(ds, "name") and ds.name.lower() == dataset_name.lower():
            target_ds = ds
            break

    if target_ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_name}' not found")

    # Fetch data items for this dataset
    try:
        data_items = await cognee_datasets.list_data(str(target_ds.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list data: {e}")

    results = []
    for item in (data_items or []):
        results.append({
            "id": str(item.id) if hasattr(item, "id") else "",
            "name": item.name if hasattr(item, "name") else str(item),
            "label": getattr(item, "label", None),
            "extension": getattr(item, "extension", ""),
            "mime_type": getattr(item, "mime_type", ""),
            "token_count": getattr(item, "token_count", None),
            "data_size": getattr(item, "data_size", None),
            "created_at": item.created_at.isoformat() if hasattr(item, "created_at") and item.created_at else None,
            "updated_at": item.updated_at.isoformat() if hasattr(item, "updated_at") and item.updated_at else None,
        })

    return {
        "dataset": {
            "id": str(target_ds.id),
            "name": target_ds.name,
            "created_at": target_ds.created_at.isoformat() if target_ds.created_at else None,
        },
        "data": results,
        "total": len(results),
    }


@router.get("/data/{data_id}/content")
async def get_data_content(
    data_id: str,
    max_chars: int = Query(50000, description="Max characters to return (0 = unlimited)"),
    api_key: str = Depends(verify_api_key),
):
    """Read the actual text content of a data item.

    Returns the raw text stored on disk for a given data item ID.
    Content is truncated to max_chars (default 50,000) for safety.
    """
    # Find the data item across all datasets
    try:
        all_datasets = await cognee_datasets.list_datasets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {e}")

    target_item = None
    for ds in all_datasets:
        try:
            items = await cognee_datasets.list_data(str(ds.id))
            for item in (items or []):
                if str(item.id) == data_id:
                    target_item = item
                    break
        except Exception:
            continue
        if target_item:
            break

    if target_item is None:
        raise HTTPException(status_code=404, detail=f"Data item '{data_id}' not found")

    raw_location = getattr(target_item, "raw_data_location", None)
    if not raw_location:
        raise HTTPException(status_code=404, detail="No raw data location for this item")

    # Resolve the file path — data may have been ingested from different environments
    # (local venv, Docker container, system Python) so we try multiple locations
    storage_config = get_storage_config()
    data_root = storage_config.get("data_root_directory", "")

    file_name = unquote(raw_location.split("/")[-1])

    # Build list of candidate paths to check
    candidates = [
        Path(data_root) / file_name,                          # Current storage root
        Path(raw_location.replace("file://", "")),             # Original absolute path
    ]
    # Also scan common .data_storage dirs (Docker paths mapped to local)
    for parent in Path(data_root).parents:
        alt = parent / ".data_storage" / file_name
        if alt not in candidates:
            candidates.append(alt)

    file_path = None
    for candidate in candidates:
        if candidate.exists():
            file_path = candidate
            break

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found on disk: {file_name} (ingested from a different environment)",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    truncated = False
    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars]
        truncated = True

    return {
        "data_id": data_id,
        "name": getattr(target_item, "name", ""),
        "content": content,
        "content_length": len(content),
        "truncated": truncated,
        "max_chars": max_chars,
    }
