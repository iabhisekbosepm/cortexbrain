"""Node endpoints — detail view, metadata, and version history."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from cortexbrain.api.deps import get_meta_memory, get_mutation_engine, get_semantic_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.core.mutation import MutationEngine
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.schemas import NodeDetailResponse, NodeHistoryResponse

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/nodes/{node_id}", response_model=NodeDetailResponse)
async def get_node_detail(
    node_id: UUID,
    api_key: str = Depends(verify_api_key),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Get full node detail: Neo4j properties + PostgreSQL metadata + edge count.

    Combines data from M_s (graph) and M_meta (PostgreSQL) into a single view.
    """
    node = await semantic.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in graph")

    edge_count = await semantic.get_edge_count(node_id)

    # Get or create M_meta entry
    metadata = await meta.get_or_create_metadata(node_id=node_id, org_id=_DEFAULT_ORG)

    return NodeDetailResponse(
        node_id=str(node.get("id", node_id)),
        name=str(node.get("name", "")),
        description=str(node.get("description", "") or node.get("value", "")),
        confidence=metadata.confidence,
        salience=metadata.salience,
        conflicted=metadata.conflicted,
        volatile=metadata.volatile,
        access_count=metadata.access_count,
        correction_count=metadata.correction_count,
        last_accessed=metadata.last_accessed.isoformat() if metadata.last_accessed else None,
        edge_count=edge_count,
        properties={k: v for k, v in node.items() if k not in ("id", "name", "description", "value")},
    )


@router.get("/nodes/{node_id}/history", response_model=NodeHistoryResponse)
async def get_node_history(
    node_id: UUID,
    api_key: str = Depends(verify_api_key),
    mutation: MutationEngine = Depends(get_mutation_engine),
):
    """Get complete version history for a knowledge node.

    Returns ordered list of all versions with who changed what, when, and why.
    Used for audit trail compliance.
    """
    history = await mutation.get_version_history(node_id)

    return NodeHistoryResponse(
        node_id=node_id,
        current_version=history[0]["version"] if history else 0,
        history=history,
    )
