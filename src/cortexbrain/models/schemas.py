"""Pydantic request/response schemas for the CortexBrain REST API."""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Enums ---

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICTED = "conflicted"


# --- API Request Models ---

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: str


class CorrectionRequest(BaseModel):
    node_id: UUID
    corrected_value: str
    user_id: str
    reason: Optional[str] = None


class IngestRequest(BaseModel):
    dataset_name: str = "default"
    source_type: str = "document"  # document, slack, git


class TextIngestRequest(BaseModel):
    """Request body for text-based ingestion (MCP, CLI, programmatic use)."""
    text: str = Field(..., min_length=1)
    dataset_name: str = Field(default="default")
    source_type: str = Field(default="text")


# --- API Response Models ---

class SourceReference(BaseModel):
    node_id: UUID
    source_name: str
    confidence: float
    activation_score: Optional[float] = None
    salience: Optional[float] = None
    description: Optional[str] = None
    conflicted: bool = False


class QueryInsights(BaseModel):
    total_nodes_activated: int = 0
    entities_extracted: list[str] = []
    activation_mode: str = "none"  # "spreading" | "graph_text" | "vector" | "continuous_learning"
    max_activation_score: float = 0.0
    avg_salience: float = 0.0


class TokenUsage(BaseModel):
    input: int
    output: int


class GeneratedImage(BaseModel):
    b64_data: str
    content_type: str = "image/png"
    prompt: str


class QueryResponse(BaseModel):
    answer: str
    confidence: ConfidenceLevel
    confidence_score: float
    sources: list[SourceReference]
    tokens_used: TokenUsage
    session_id: str
    fallback: bool = False
    auto_learned: bool = False
    insights: Optional[QueryInsights] = None
    images: list[GeneratedImage] = []


class CorrectionResponse(BaseModel):
    status: str = "applied"
    version: int
    node_id: UUID
    previous_value: str
    new_value: str


class NodeVersion(BaseModel):
    version: int
    value: str
    changed_by: str
    timestamp: str
    reason: str = ""
    source: str = ""


class NodeHistoryResponse(BaseModel):
    node_id: UUID
    current_version: int
    history: list[NodeVersion]


class ServiceHealth(BaseModel):
    status: str  # "ok" or "error"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    redis: ServiceHealth
    neo4j: ServiceHealth
    qdrant: ServiceHealth
    postgres: ServiceHealth
    llm: ServiceHealth


# --- Debug / Introspection Response Models ---


class NodeDetailResponse(BaseModel):
    node_id: str
    name: str = ""
    description: str = ""
    # M_meta fields (from PostgreSQL)
    confidence: float = 0.7
    salience: float = 0.5
    conflicted: bool = False
    volatile: bool = False
    access_count: int = 0
    correction_count: int = 0
    last_accessed: Optional[str] = None
    # Graph fields
    edge_count: int = 0
    # Raw Neo4j properties (everything else)
    properties: dict = {}


class ActivationEntry(BaseModel):
    node_id: str
    score: float


class SessionActivationsResponse(BaseModel):
    session_id: str
    active_node_count: int
    activations: list[ActivationEntry]


class SalienceRecomputeResponse(BaseModel):
    status: str = "completed"
    nodes_updated: int


class DebugStatsResponse(BaseModel):
    total_entities: int
    active_sessions: int
    total_metadata_rows: int
    top_accessed_nodes: list[dict]
    top_salient_nodes: list[dict]


# --- Consolidation Response Models ---


class ConsolidationTriggerResponse(BaseModel):
    status: str  # "queued"
    task_id: str


class ConsolidationReportResponse(BaseModel):
    started_at: str
    completed_at: str
    nodes_promoted: int = 0
    nodes_archived: int = 0
    nodes_merged: int = 0
    merge_nodes_deprecated: int = 0
    version_chains_compressed: int = 0
    errors: list[str] = []


# --- Workers Dashboard Response Models ---


class WorkerInfo(BaseModel):
    hostname: str
    pid: Optional[int] = None
    pool_size: Optional[int] = None
    total_tasks_processed: int = 0
    active_task_count: int = 0


class BeatScheduleEntry(BaseModel):
    name: str
    task: str
    interval_seconds: int
    interval_human: str
    description: str


class ActiveTask(BaseModel):
    task_id: str
    task_name: str
    worker: Optional[str] = None
    started_at: Optional[str] = None
    runtime_seconds: Optional[float] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None


class WorkersStatusResponse(BaseModel):
    connected: bool
    latency_ms: float
    workers: list[WorkerInfo]
    active_tasks: list[ActiveTask]
    reserved_tasks: list[ActiveTask]
    registered_tasks: list[str]
    beat_schedule: list[BeatScheduleEntry]


# --- Timeline / Audit Log Response Models ---


class AuditLogEntry(BaseModel):
    id: str
    node_id: str
    action: str  # "correction", "ingestion", "decay", "consolidation"
    changed_by: str
    previous_value: str = ""
    new_value: str = ""
    reason: str = ""
    version: int = 1
    timestamp: str


class TimelineSummary(BaseModel):
    total_events: int
    corrections: int = 0
    ingestions: int = 0
    decays: int = 0
    consolidations: int = 0
    continuous_learning: int = 0


class TimelineResponse(BaseModel):
    summary: TimelineSummary
    events: list[AuditLogEntry]
    has_more: bool = False


# --- Agent Query Models ---


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AgentQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: str
    conversation_history: list[ConversationMessage] = []


# --- Graph Visualization Models ---


class GraphNode(BaseModel):
    id: str
    name: str
    description: str = ""
    confidence: float = 0.7
    salience: float = 0.5
    edge_count: int = 0
    access_count: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    rel_type: str = ""
    weight: float = 1.0


class GraphOverviewResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphSubgraphResponse(BaseModel):
    center: str
    depth: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# --- Dashboard Models ---


class ConfidenceBucket(BaseModel):
    range: str  # "0.0-0.3", "0.3-0.5", "0.5-0.8", "0.8-1.0"
    count: int


class LowConfidenceNode(BaseModel):
    node_id: str
    name: str = ""
    confidence: float
    salience: float = 0.0
    access_count: int = 0
    last_accessed: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    total_nodes: int
    avg_confidence: float
    distribution: list[ConfidenceBucket]
    low_confidence_nodes: list[LowConfidenceNode]


# --- Review Queue Models ---


class ReviewNodeEntry(BaseModel):
    node_id: str
    name: str = ""
    description: str = ""
    confidence: float
    salience: float = 0.0
    access_count: int = 0
    created_at: Optional[str] = None
    last_accessed: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    total: int
    nodes: list[ReviewNodeEntry]


class ReviewActionResponse(BaseModel):
    status: str  # "approved" | "rejected"
    node_id: str
    new_confidence: float
