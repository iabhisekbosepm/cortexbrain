/* TypeScript types mirroring backend schemas.py */

export type ConfidenceLevel = "high" | "medium" | "low" | "conflicted";
export type QueryMode = "agent" | "normal";

// --- Request Types ---

export interface QueryRequest {
  query: string;
  session_id?: string;
  user_id: string;
}

export interface CorrectionRequest {
  node_id: string;
  corrected_value: string;
  user_id: string;
  reason?: string;
}

export interface IngestRequest {
  dataset_name?: string;
  source_type?: string;
}

// --- Response Types ---

export interface SourceReference {
  node_id: string;
  source_name: string;
  confidence: number;
  activation_score?: number;
  salience?: number;
  description?: string;
  conflicted?: boolean;
}

export interface QueryInsights {
  total_nodes_activated: number;
  entities_extracted: string[];
  activation_mode: string;
  max_activation_score: number;
  avg_salience: number;
}

export interface TokenUsage {
  input: number;
  output: number;
}

export interface GeneratedImage {
  b64_data: string;
  content_type: string;
  prompt: string;
}

export interface QueryResponse {
  answer: string;
  confidence: ConfidenceLevel;
  confidence_score: number;
  sources: SourceReference[];
  tokens_used: TokenUsage;
  session_id: string;
  fallback: boolean;
  auto_learned?: boolean;
  insights?: QueryInsights;
  images?: GeneratedImage[];
}

export interface CorrectionResponse {
  status: string;
  version: number;
  node_id: string;
  previous_value: string;
  new_value: string;
}

export interface NodeVersion {
  version: number;
  value: string;
  changed_by: string;
  timestamp: string;
  reason: string;
  source: string;
}

export interface NodeHistoryResponse {
  node_id: string;
  current_version: number;
  history: NodeVersion[];
}

export interface ServiceHealth {
  status: string; // "ok" | "error"
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: string; // "healthy" | "degraded" | "unhealthy"
  redis: ServiceHealth;
  neo4j: ServiceHealth;
  qdrant: ServiceHealth;
  postgres: ServiceHealth;
  llm: ServiceHealth;
}

export interface NodeDetailResponse {
  node_id: string;
  name: string;
  description: string;
  confidence: number;
  salience: number;
  conflicted: boolean;
  volatile: boolean;
  access_count: number;
  correction_count: number;
  last_accessed: string | null;
  edge_count: number;
  properties: Record<string, unknown>;
}

export interface ActivationEntry {
  node_id: string;
  score: number;
}

export interface SessionActivationsResponse {
  session_id: string;
  active_node_count: number;
  activations: ActivationEntry[];
}

export interface SalienceRecomputeResponse {
  status: string;
  nodes_updated: number;
}

export interface DebugStatsResponse {
  total_entities: number;
  active_sessions: number;
  total_metadata_rows: number;
  top_accessed_nodes: Record<string, unknown>[];
  top_salient_nodes: Record<string, unknown>[];
}

// --- Ingest Response Types ---

export interface IngestResponse {
  status: string;
  nodes_initialized: number;
  files: string[];
}

export interface BatchIngestResponse {
  status: string;
  task_id: string;
  files: string[];
  dataset: string;
}

export interface BatchStatusResponse {
  task_id: string;
  status: string; // PENDING | STARTED | SUCCESS | FAILURE
  result?: Record<string, unknown>;
  error?: string;
}

export interface TextIngestResponse {
  status: string;
  nodes_initialized: number;
}

export interface TextIngestAsyncResponse {
  status: string;
  task_id: string;
  dataset: string;
}

// --- Timeline / Audit Log Types ---

export interface AuditLogEntry {
  id: string;
  node_id: string;
  action: string;
  changed_by: string;
  previous_value: string;
  new_value: string;
  reason: string;
  version: number;
  timestamp: string;
}

export interface TimelineSummary {
  total_events: number;
  corrections: number;
  ingestions: number;
  decays: number;
  consolidations: number;
  continuous_learning: number;
}

export interface TimelineResponse {
  summary: TimelineSummary;
  events: AuditLogEntry[];
  has_more: boolean;
}

// --- Agent Query Types ---

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AgentStep {
  type: "tool_call" | "tool_result";
  name: string;
  content: string;
  timestamp: Date;
}

export interface AgentAnswerEvent {
  answer: string;
  confidence: string;
  confidence_score: number;
  sources: { node_id: string; source_name: string; confidence: number; activation_score?: number }[];
  session_id: string;
  fallback: boolean;
  auto_learned?: boolean;
}

// --- UI Types ---

export interface QueryHistoryEntry {
  id: string;
  query: string;
  answer: string;
  confidence: ConfidenceLevel;
  confidence_score: number;
  sources: SourceReference[];
  tokens_used: TokenUsage;
  fallback: boolean;
  auto_learned?: boolean;
  insights?: QueryInsights;
  images?: GeneratedImage[];
  timestamp: Date;
  session_id: string;
  steps?: AgentStep[];
  mode?: QueryMode;
}

export interface HealthHistoryEntry {
  timestamp: Date;
  status: string;
  services: Record<string, string>;
}

// --- Graph Visualization Types ---

export interface GraphNode {
  id: string;
  name: string;
  description: string;
  confidence: number;
  salience: number;
  edge_count: number;
  access_count: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  rel_type: string;
  weight: number;
}

export interface GraphOverviewResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphSubgraphResponse {
  center: string;
  depth: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// --- Dashboard Types ---

export interface ConfidenceBucket {
  range: string;
  count: number;
}

export interface LowConfidenceNode {
  node_id: string;
  name: string;
  confidence: number;
  salience: number;
  access_count: number;
  last_accessed: string | null;
}

export interface DashboardStatsResponse {
  total_nodes: number;
  avg_confidence: number;
  distribution: ConfidenceBucket[];
  low_confidence_nodes: LowConfidenceNode[];
}

// --- Review Queue Types ---

export interface ReviewNodeEntry {
  node_id: string;
  name: string;
  description: string;
  confidence: number;
  salience: number;
  access_count: number;
  created_at: string | null;
  last_accessed: string | null;
}

export interface ReviewQueueResponse {
  total: number;
  nodes: ReviewNodeEntry[];
}

export interface ReviewActionResponse {
  status: string;
  node_id: string;
  new_confidence: number;
}

// --- Dataset Types ---

export interface DatasetEntry {
  id: string;
  name: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface DatasetsResponse {
  datasets: DatasetEntry[];
  total: number;
}

export interface DatasetDataItem {
  id: string;
  name: string;
  label: string | null;
  extension: string;
  mime_type: string;
  token_count: number | null;
  data_size: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DatasetDataResponse {
  dataset: { id: string; name: string; created_at: string | null };
  data: DatasetDataItem[];
  total: number;
}

export interface DataItemContentResponse {
  data_id: string;
  name: string;
  content: string;
  content_length: number;
  truncated: boolean;
  max_chars: number;
}

// --- Workers Dashboard Types ---

export interface WorkerInfo {
  hostname: string;
  pid: number | null;
  pool_size: number | null;
  total_tasks_processed: number;
  active_task_count: number;
}

export interface BeatScheduleEntry {
  name: string;
  task: string;
  interval_seconds: number;
  interval_human: string;
  description: string;
}

export interface ActiveTask {
  task_id: string;
  task_name: string;
  worker: string | null;
  started_at: string | null;
  runtime_seconds: number | null;
  args: string | null;
  kwargs: string | null;
}

export interface WorkersStatusResponse {
  connected: boolean;
  latency_ms: number;
  workers: WorkerInfo[];
  active_tasks: ActiveTask[];
  reserved_tasks: ActiveTask[];
  registered_tasks: string[];
  beat_schedule: BeatScheduleEntry[];
}

// --- Pipeline Monitor Types ---

export type PipelineType = "decay" | "salience" | "consolidation" | "ingestion";
export type PipelineStageStatus = "idle" | "running" | "completed" | "failed";

export interface PipelineEvent {
  event_id: string;
  pipeline: PipelineType;
  task_id: string | null;
  stage: string;
  stage_index: number;
  total_stages: number;
  status: "started" | "running" | "completed" | "failed";
  metrics: Record<string, number>;
  error: string | null;
  timestamp: string;
  duration_ms: number | null;
}

export interface PipelineStageState {
  name: string;
  label: string;
  description: string;
  status: PipelineStageStatus;
  metrics: Record<string, number>;
  duration_ms: number | null;
  error: string | null;
}

export interface PipelineState {
  type: PipelineType;
  label: string;
  description: string;
  schedule: string;
  stages: PipelineStageState[];
  lastRunTime: string | null;
  lastRunResult: Record<string, number>;
  isRunning: boolean;
}

export interface PipelineStatusResponse {
  pipelines: Record<string, PipelineEvent>;
  timestamp: string;
}
