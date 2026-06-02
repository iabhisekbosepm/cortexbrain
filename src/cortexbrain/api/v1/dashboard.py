"""Dashboard stats endpoint — confidence distribution, low-confidence nodes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select

from cortexbrain.api.deps import get_meta_memory, get_semantic_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.database import NodeMetadata
from cortexbrain.models.schemas import (
    ConfidenceBucket,
    DashboardStatsResponse,
    LowConfidenceNode,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
):
    """Aggregated confidence stats for the dashboard."""
    factory = await meta._get_session_factory()
    async with factory() as session:
        # Total nodes and average confidence
        result = await session.execute(
            select(
                func.count(NodeMetadata.node_id),
                func.avg(NodeMetadata.confidence),
            )
        )
        row = result.one()
        total_nodes = row[0] or 0
        avg_confidence = float(row[1] or 0)

        # Confidence distribution buckets
        bucket_label = case(
            (NodeMetadata.confidence < 0.3, "0.0-0.3"),
            (NodeMetadata.confidence < 0.5, "0.3-0.5"),
            (NodeMetadata.confidence < 0.8, "0.5-0.8"),
            else_="0.8-1.0",
        ).label("bucket")

        bucket_result = await session.execute(
            select(bucket_label, func.count().label("count")).group_by(bucket_label)
        )
        buckets = [
            ConfidenceBucket(range=r.bucket, count=r.count)
            for r in bucket_result.all()
        ]

        # Low-confidence nodes (< 0.5), sorted by confidence ASC, limit 20
        low_conf_result = await session.execute(
            select(NodeMetadata)
            .where(NodeMetadata.confidence < 0.5)
            .order_by(NodeMetadata.confidence.asc())
            .limit(20)
        )
        low_confidence_nodes = []
        for meta_row in low_conf_result.scalars().all():
            node = await semantic.get_node(meta_row.node_id)
            low_confidence_nodes.append(
                LowConfidenceNode(
                    node_id=str(meta_row.node_id),
                    name=node.get("name", "") if node else "",
                    confidence=meta_row.confidence,
                    salience=meta_row.salience,
                    access_count=meta_row.access_count,
                    last_accessed=(
                        meta_row.last_accessed.isoformat()
                        if meta_row.last_accessed
                        else None
                    ),
                )
            )

    return DashboardStatsResponse(
        total_nodes=total_nodes,
        avg_confidence=round(avg_confidence, 4),
        distribution=buckets,
        low_confidence_nodes=low_confidence_nodes,
    )
