"""Meta Memory (M_meta) — PostgreSQL-backed audit logs, confidence, salience.

CortexBrain-specific store. Cognee's relational engine is separate (SQLite/Postgres).
This manages the audit trail and analytics that the PRD requires for enterprise compliance.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cortexbrain.config import get_settings
from cortexbrain.models.database import AuditLog, Base, NodeMetadata


class MetaMemoryStore:
    """Manages audit logs and node metadata in PostgreSQL."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory

    async def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            settings = get_settings()
            engine = create_async_engine(settings.postgres_url)
            # Create tables on first access (replaced by Alembic in production)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return self._session_factory

    # --- Audit Logs ---

    async def record_mutation(
        self,
        org_id: UUID,
        node_id: UUID,
        action: str,
        changed_by: str,
        previous_value: str = "",
        new_value: str = "",
        reason: str = "",
        version: int = 1,
    ) -> AuditLog:
        factory = await self._get_session_factory()
        log = AuditLog(
            org_id=org_id,
            node_id=node_id,
            action=action,
            changed_by=changed_by,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            version=version,
        )
        async with factory() as session:
            session.add(log)
            await session.commit()
            await session.refresh(log)
        return log

    async def get_node_history(self, node_id: UUID) -> list[AuditLog]:
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(AuditLog)
                .where(AuditLog.node_id == node_id)
                .order_by(AuditLog.timestamp.desc())
            )
            return list(result.scalars().all())

    async def get_audit_logs(
        self,
        org_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        factory = await self._get_session_factory()
        async with factory() as session:
            stmt = select(AuditLog).where(AuditLog.org_id == org_id)
            if start_date:
                stmt = stmt.where(AuditLog.timestamp >= start_date)
            if end_date:
                stmt = stmt.where(AuditLog.timestamp <= end_date)
            stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # --- Node Metadata ---

    async def get_or_create_metadata(self, node_id: UUID, org_id: UUID) -> NodeMetadata:
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(NodeMetadata).where(NodeMetadata.node_id == node_id)
            )
            meta = result.scalar_one_or_none()
            if meta is None:
                meta = NodeMetadata(node_id=node_id, org_id=org_id)
                session.add(meta)
                await session.commit()
                await session.refresh(meta)
            return meta

    async def update_metadata(self, node_id: UUID, **kwargs: Any) -> None:
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(NodeMetadata).where(NodeMetadata.node_id == node_id)
            )
            meta = result.scalar_one_or_none()
            if meta:
                for key, value in kwargs.items():
                    if hasattr(meta, key):
                        setattr(meta, key, value)
                await session.commit()

    async def record_access(self, node_id: UUID) -> None:
        """Increment access count and update last_accessed (for salience scoring)."""
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(NodeMetadata).where(NodeMetadata.node_id == node_id)
            )
            meta = result.scalar_one_or_none()
            if meta:
                meta.access_count += 1
                meta.last_accessed = datetime.now(timezone.utc)
                await session.commit()

    # --- Consolidation Queries ---

    async def get_nodes_by_confidence_range(
        self, min_conf: float, max_conf: float
    ) -> list[NodeMetadata]:
        """Get all nodes with confidence in [min_conf, max_conf]."""
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(NodeMetadata)
                .where(NodeMetadata.confidence >= min_conf)
                .where(NodeMetadata.confidence <= max_conf)
            )
            return list(result.scalars().all())

    async def get_stale_low_salience_nodes(
        self, salience_threshold: float, stale_days: int
    ) -> list[NodeMetadata]:
        """Nodes with salience <= threshold AND last_accessed > stale_days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        factory = await self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(NodeMetadata)
                .where(NodeMetadata.salience <= salience_threshold)
                .where(NodeMetadata.last_accessed < cutoff)
            )
            return list(result.scalars().all())

    async def compute_salience_percentile(self, percentile: float) -> float:
        """Compute the salience score at the given percentile (0.0-1.0).

        Returns the salience value below which `percentile` fraction of nodes fall.
        """
        factory = await self._get_session_factory()
        async with factory() as session:
            count_result = await session.execute(
                select(func.count(NodeMetadata.node_id))
            )
            total = count_result.scalar() or 0
            if total == 0:
                return 0.0

            offset = max(int(total * percentile) - 1, 0)
            result = await session.execute(
                select(NodeMetadata.salience)
                .order_by(NodeMetadata.salience.asc())
                .offset(offset)
                .limit(1)
            )
            val = result.scalar()
            return float(val) if val is not None else 0.0
