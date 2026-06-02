"""Timeline endpoint — chronological view of all Meta Memory (M_meta) activity.

Provides a filterable audit log of all PostgreSQL events: corrections,
ingestions, decay cycles, and consolidation runs.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from cortexbrain.api.deps import get_meta_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.models.database import AuditLog
from cortexbrain.models.schemas import (
    AuditLogEntry,
    TimelineResponse,
    TimelineSummary,
)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    action: Optional[str] = Query(None, description="Filter by action: correction, ingestion, decay, consolidation, continuous_learning"),
    start: Optional[str] = Query(None, description="Start datetime ISO 8601"),
    end: Optional[str] = Query(None, description="End datetime ISO 8601"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Get a chronological timeline of all Meta Memory events.

    Returns summary counts + paginated event list, filterable by action type and date range.
    """
    factory = await meta._get_session_factory()
    async with factory() as session:
        # Base query scoped to default org
        base = select(AuditLog).where(AuditLog.org_id == _DEFAULT_ORG)

        # Parse optional date filters
        start_dt = None
        end_dt = None
        if start:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
            base = base.where(AuditLog.timestamp >= start_dt)
        if end:
            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
            base = base.where(AuditLog.timestamp <= end_dt)

        if action:
            # Support prefix matching for subtypes (e.g. "consolidation" matches
            # "consolidation:merge", "consolidation:summary")
            base = base.where(AuditLog.action.startswith(action))

        # Summary counts (same date filters, but not filtered by action)
        count_stmt = select(func.count(AuditLog.id)).where(AuditLog.org_id == _DEFAULT_ORG)
        if start_dt:
            count_stmt = count_stmt.where(AuditLog.timestamp >= start_dt)
        if end_dt:
            count_stmt = count_stmt.where(AuditLog.timestamp <= end_dt)
        total_result = await session.execute(count_stmt)
        total_events = total_result.scalar() or 0

        # Count per action type
        group_stmt = (
            select(AuditLog.action, func.count(AuditLog.id))
            .where(AuditLog.org_id == _DEFAULT_ORG)
        )
        if start_dt:
            group_stmt = group_stmt.where(AuditLog.timestamp >= start_dt)
        if end_dt:
            group_stmt = group_stmt.where(AuditLog.timestamp <= end_dt)
        group_stmt = group_stmt.group_by(AuditLog.action)
        action_counts_result = await session.execute(group_stmt)
        action_counts = {row[0]: row[1] for row in action_counts_result.all()}

        # Aggregate counts — consolidation subtypes (merge, summary) roll up
        consolidation_total = sum(
            v for k, v in action_counts.items() if k.startswith("consolidation")
        )
        summary = TimelineSummary(
            total_events=total_events,
            corrections=action_counts.get("correction", 0),
            ingestions=action_counts.get("ingestion", 0),
            decays=action_counts.get("decay", 0),
            consolidations=consolidation_total,
            continuous_learning=action_counts.get("continuous_learning", 0),
        )

        # Paginated events
        stmt = base.order_by(AuditLog.timestamp.desc()).limit(limit + 1).offset(offset)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        rows = rows[:limit]

        events = [
            AuditLogEntry(
                id=str(row.id),
                node_id=str(row.node_id),
                action=row.action,
                changed_by=row.changed_by,
                previous_value=row.previous_value or "",
                new_value=row.new_value or "",
                reason=row.reason or "",
                version=row.version,
                timestamp=row.timestamp.isoformat() if row.timestamp else "",
            )
            for row in rows
        ]

    return TimelineResponse(summary=summary, events=events, has_more=has_more)
