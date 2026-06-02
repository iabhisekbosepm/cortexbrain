"""Debug / introspection endpoints for testing CortexBrain subsystems.

These endpoints expose internal state that is normally invisible:
- Session activation scores (Redis)
- Salience recompute trigger
- System-wide stats (entity count, active sessions, top nodes)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from cortexbrain.api.deps import get_active_memory, get_meta_memory, get_semantic_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.core.metacognition import SalienceScorer
from cortexbrain.memory.active import ActiveMemoryStore
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.database import NodeMetadata
from cortexbrain.models.schemas import (
    ActivationEntry,
    DebugStatsResponse,
    SalienceRecomputeResponse,
    SessionActivationsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/sessions/{session_id}/activations", response_model=SessionActivationsResponse)
async def get_session_activations(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    active: ActiveMemoryStore = Depends(get_active_memory),
):
    """View all activation scores for a session (from Redis).

    Shows which nodes are currently active and their scores.
    Useful for verifying that spreading activation populated Redis after a query.
    """
    nodes = await active.get_active_nodes(session_id, min_score=0.0)

    return SessionActivationsResponse(
        session_id=session_id,
        active_node_count=len(nodes),
        activations=[
            ActivationEntry(node_id=node_id, score=score)
            for node_id, score in nodes
        ],
    )


@router.post("/debug/salience-recompute", response_model=SalienceRecomputeResponse)
async def trigger_salience_recompute(
    api_key: str = Depends(verify_api_key),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Manually trigger salience recomputation for all Entity nodes.

    Same logic as the hourly Celery beat task, but on-demand.
    Iterates all entities, fetches metadata, counts edges, recomputes salience.
    """
    entity_ids = await semantic.get_all_entity_ids()
    scorer = SalienceScorer()
    updated = 0

    for eid_str in entity_ids:
        try:
            node_id = UUID(eid_str)
            metadata = await meta.get_or_create_metadata(node_id=node_id, org_id=_DEFAULT_ORG)
            edge_count = await semantic.get_edge_count(node_id)
            salience = scorer.compute(
                access_count=metadata.access_count,
                last_accessed_ts=metadata.last_accessed.timestamp(),
                correction_count=metadata.correction_count,
                edge_count=edge_count,
            )
            await meta.update_metadata(node_id, salience=salience)
            updated += 1
        except Exception as e:
            logger.debug("Salience recompute skipped for %s: %s", eid_str, e)

    return SalienceRecomputeResponse(status="completed", nodes_updated=updated)


@router.get("/debug/stats", response_model=DebugStatsResponse)
async def get_debug_stats(
    api_key: str = Depends(verify_api_key),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
    active: ActiveMemoryStore = Depends(get_active_memory),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """System-wide debug stats across all subsystems.

    Shows: total entities in Neo4j, active Redis sessions, top accessed/salient nodes.
    """
    # Entity count from Neo4j
    entity_ids = await semantic.get_all_entity_ids()
    total_entities = len(entity_ids)

    # Active sessions from Redis
    session_keys = await active.get_all_session_keys()
    active_sessions = len(session_keys)

    # PostgreSQL metadata stats
    factory = await meta._get_session_factory()
    async with factory() as session:
        # Total metadata rows
        count_result = await session.execute(select(func.count(NodeMetadata.node_id)))
        total_metadata = count_result.scalar() or 0

        # Top 5 by access_count
        top_accessed_result = await session.execute(
            select(NodeMetadata)
            .order_by(NodeMetadata.access_count.desc())
            .limit(5)
        )
        top_accessed = [
            {
                "node_id": str(row.node_id),
                "access_count": row.access_count,
                "confidence": row.confidence,
                "salience": row.salience,
            }
            for row in top_accessed_result.scalars().all()
        ]

        # Top 5 by salience
        top_salient_result = await session.execute(
            select(NodeMetadata)
            .order_by(NodeMetadata.salience.desc())
            .limit(5)
        )
        top_salient = [
            {
                "node_id": str(row.node_id),
                "salience": row.salience,
                "access_count": row.access_count,
                "confidence": row.confidence,
            }
            for row in top_salient_result.scalars().all()
        ]

    return DebugStatsResponse(
        total_entities=total_entities,
        active_sessions=active_sessions,
        total_metadata_rows=total_metadata,
        top_accessed_nodes=top_accessed,
        top_salient_nodes=top_salient,
    )
