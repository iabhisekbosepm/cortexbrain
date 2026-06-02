"""Review queue endpoints — validate auto-learned knowledge nodes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from cortexbrain.api.deps import get_meta_memory, get_semantic_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.schemas import (
    ReviewActionResponse,
    ReviewNodeEntry,
    ReviewQueueResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")
_NULL_NODE = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/review/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
):
    """Get auto-learned nodes pending review (confidence 0.5-0.7)."""
    nodes = await meta.get_nodes_by_confidence_range(0.5, 0.7)
    entries = []
    for m in nodes:
        node = await semantic.get_node(m.node_id)
        entries.append(
            ReviewNodeEntry(
                node_id=str(m.node_id),
                name=node.get("name", "") if node else "",
                description=str(node.get("description", "") or "") if node else "",
                confidence=m.confidence,
                salience=m.salience,
                access_count=m.access_count,
                created_at=m.created_at.isoformat() if hasattr(m, "created_at") and m.created_at else None,
                last_accessed=m.last_accessed.isoformat() if m.last_accessed else None,
            )
        )
    return ReviewQueueResponse(total=len(entries), nodes=entries)


@router.post("/review/approve/{node_id}", response_model=ReviewActionResponse)
async def approve_node(
    node_id: UUID,
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Approve auto-learned node — bump confidence to 0.8."""
    metadata = await meta.get_or_create_metadata(node_id=node_id, org_id=_DEFAULT_ORG)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    await meta.update_metadata(node_id, confidence=0.8)
    await meta.record_mutation(
        org_id=_DEFAULT_ORG,
        node_id=node_id,
        action="review_approve",
        changed_by="system:review",
        previous_value=f"confidence={metadata.confidence}",
        new_value="confidence=0.8",
        reason="Approved by human reviewer",
    )
    return ReviewActionResponse(status="approved", node_id=str(node_id), new_confidence=0.8)


@router.post("/review/reject/{node_id}", response_model=ReviewActionResponse)
async def reject_node(
    node_id: UUID,
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
):
    """Reject auto-learned node — set confidence to 0 and archive."""
    metadata = await meta.get_or_create_metadata(node_id=node_id, org_id=_DEFAULT_ORG)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    await meta.update_metadata(node_id, confidence=0.0, volatile=True)
    try:
        await semantic.update_node_properties(node_id, {"status": "archived"})
    except Exception as e:
        logger.warning("Failed to archive node %s in Neo4j: %s", node_id, e)

    await meta.record_mutation(
        org_id=_DEFAULT_ORG,
        node_id=node_id,
        action="review_reject",
        changed_by="system:review",
        previous_value=f"confidence={metadata.confidence}",
        new_value="confidence=0.0, status=archived",
        reason="Rejected by human reviewer",
    )
    return ReviewActionResponse(status="rejected", node_id=str(node_id), new_confidence=0.0)
