"""SQLAlchemy models for CortexBrain's PostgreSQL meta store (M_meta).

These tables are CortexBrain-specific and live alongside Cognee's own
relational tables (Cognee uses SQLite by default, or Postgres with its own schema).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt hash
    label: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """Every mutation (correction, ingestion, decay) is recorded here."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # "correction", "ingestion", "decay", "consolidation"
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)  # "user:priya", "system:ingestion"
    previous_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class NodeMetadata(Base):
    """Metacognition metadata stored in PostgreSQL for analytics and querying.

    The authoritative confidence/salience values also live on the Neo4j node,
    but this table enables SQL-based analytics, dashboards, and audit exports.
    """

    __tablename__ = "node_metadata"

    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    salience: Mapped[float] = mapped_column(Float, default=0.5)
    volatile: Mapped[bool] = mapped_column(Boolean, default=False)
    conflicted: Mapped[bool] = mapped_column(Boolean, default=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    correction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
