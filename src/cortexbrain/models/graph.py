"""Graph models that extend Cognee's DataPoint for CortexBrain-specific semantics.

Cognee's DataPoint already provides: id, created_at, updated_at, version, metadata.
We extend it with confidence, salience, volatility, and audit-trail fields.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from cognee.infrastructure.engine.models.DataPoint import DataPoint


class KnowledgeNode(DataPoint):
    """A knowledge node in the semantic memory graph (M_s).

    Extends Cognee's DataPoint with CortexBrain's metacognition fields.
    Stored in Neo4j via Cognee's graph engine.
    """

    # Content
    name: str = ""
    value: str = ""
    source: str = ""  # e.g. "runbook-v2.pdf", "user:priya", "system:ingestion"
    node_type: str = "fact"  # fact, config, procedure, entity, etc.

    # Metacognition (M_meta)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    volatile: bool = False  # True if node has been corrected
    conflicted: bool = False  # True if conflicting corrections exist

    # Embeddable fields for Cognee's vector indexing
    metadata: dict = {"type": "KnowledgeNode", "index_fields": ["name", "value"]}


class VersionEdge(BaseModel):
    """Represents a PREVIOUS_VERSION edge in Neo4j for the mutation audit trail.

    Created by the Mutation Engine when a correction is applied.
    """

    source_node_id: UUID
    target_node_id: UUID  # the archived previous version
    relationship_name: str = "PREVIOUS_VERSION"
    changed_by: str  # "user:priya" or "system:ingestion"
    reason: str = ""
    previous_value: str = ""
    new_value: str = ""


class ActivationState(BaseModel):
    """In-flight activation state for a node in Active Memory (M_a / Redis).

    Not persisted in the graph — lives in Redis with TTL.
    """

    node_id: UUID
    session_id: str
    activation_score: float = Field(default=0.0, ge=0.0)
    activated_at: float  # unix timestamp


class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICTED = "conflicted"
