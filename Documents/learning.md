# CortexBrain - Comprehensive Codebase Learning

> Generated 2026-02-14 by Claude Code agents exploring every file in the project.
> Also ingested into CortexBrain dataset: `codebase_understanding` (1,728 knowledge nodes).

---

## 1. Project Identity

**CortexBrain** is a B2B AI knowledge system — an auditable, self-correcting "internal brain" for enterprises.

**Core Promise:** An AI assistant that gets smarter every time someone corrects it, with a full audit trail for every answer.

**Author:** Abhisek Bose
**Version:** 0.1.0
**Python:** >=3.12
**Status:** All core phases complete; full Docker deployment working (8 services)
**File Count:** ~150 source files (57 Python backend, 65 TypeScript/TSX frontend, tests, scripts, config)

---

## 2. Architecture Overview

```
CortexBrain Layer (src/cortexbrain/)
├── core/activation/       — Spreading activation + decay (Novel)
├── core/mutation/         — Revision-based corrections (Novel)
├── core/metacognition/    — Confidence gating + salience (Novel)
├── core/consolidation/    — Episodic→semantic compression (Novel)
├── memory/active.py       — M_a: Redis sorted sets
├── memory/semantic.py     — M_s: Wraps Cognee Neo4j
├── memory/raw.py          — M_r: Wraps Cognee LanceDB/Qdrant
├── memory/meta.py         — M_meta: PostgreSQL audit/metadata
├── api/v1/                — FastAPI REST endpoints (27 routes)
├── auth/                  — Bearer token auth
├── workers/               — Celery background tasks (5 tasks)
├── ingestion/             — Document processing + continuous learning
├── services/              — Image generation (Gemini 2.5 Flash)
├── mcp/                   — MCP server for Claude Code (6 tools)
├── pipelines/             — Cognee Task wrappers
├── models/                — Pydantic + SQLAlchemy + Graph models
└── config/                — CortexBrainSettings (Pydantic BaseSettings)
    ▼
Cognee OSS (pip dependency, v0.5.2)
├── add() → cognify() → search()  — ECL pipeline
├── GraphDBInterface (Neo4j)       — Our M_s
├── VectorDBInterface (LanceDB)    — Our M_r
└── LLMGateway (litellm)          — LLM abstraction
```

---

## 3. MFCA Memory Model (Four Substrates)

| Substrate | Store | Class | Key Pattern / Table |
|-----------|-------|-------|---------------------|
| **M_a** (Active) | Redis 7+ | `ActiveMemoryStore` | `cortex:active:{session_id}` sorted set, TTL 600s |
| **M_s** (Semantic) | Neo4j 5.x | `SemanticMemoryStore` | `:Entity` nodes + `:PREVIOUS_VERSION` / `:MERGED_INTO` edges |
| **M_r** (Raw) | LanceDB (via Cognee) | `RawMemoryStore` | `Entity_name` vector collection |
| **M_meta** (Meta) | PostgreSQL 16 | `MetaMemoryStore` | `audit_logs`, `node_metadata`, `organizations`, `api_keys` |

---

## 4. Core Algorithms

### Spreading Activation (core/activation/engine.py)
```
neighbor_activation = source_activation × edge_weight × dampening_factor (0.5)
Initial seed score: 100.0
Threshold: 30 (configurable)
Max context: 2000 tokens
BFS traversal, skips archived nodes
Fallback: vector search (M_r) if no graph matches
```

### Decay Cycle (core/activation/decay.py)
```
Every 30s: score -= decay_rate (10)
Evict at 0 from Redis (Neo4j untouched)
Celery beat task
```

### Salience (core/metacognition/salience.py)
```
S = (access_freq × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)
Normalization caps: access=100, corrections=20, edges=50
Recency: exponential decay over 7-day window
New nodes get default salience 0.5 for 7 days (grace period)
```

### Confidence (core/metacognition/confidence.py)
```
HIGH (≥0.8): No prefix
MEDIUM (0.5-0.8): "I have moderate confidence in this..."
LOW (<0.5): "I have low confidence..."
CONFLICTED: "I have conflicting data..."
Aggregate: weighted average by activation scores
```

### Mutation Pipeline (core/mutation/engine.py)
```
1. Locate: Find node in Neo4j (or create)
2. Version: Create PREVIOUS_VERSION edge archiving current state
3. Mutate: Update description + value, set confidence=0.95, volatile=True
4. Meta-Update: Record in audit log + update PostgreSQL metadata
5. Re-index: Re-embed corrected text in LanceDB Entity_name collection
```

### Consolidation (core/consolidation/engine.py) — Weekly
```
1. Promote: auto-learned (0.6) → validated (0.75) if access≥3 or 2+ high-conf neighbors
2. Archive: bottom 10% salience + 90+ days idle → status='archived'
3. Merge: duplicate entities via normalized name + fuzzy match (threshold 0.85)
4. Compress: version chains > 5 → keep first + last, mark intermediates compressed
5. Report: store ConsolidationReport in audit log
```

### Continuous Learning (ingestion/continuous_learning.py)
```
Trigger: Knowledge base can't answer a query (avg_confidence < 0.9 + "can't answer" phrases)
1. generate_fallback_answer(): Unconstrained LLM call ("Answer using general knowledge")
2. format_qa_for_ingestion(): Structured Q&A format for Cognee
3. ingest_learned_knowledge(): Background task with 80% term overlap dedup
4. Ingests into `auto_learned` dataset at confidence 0.6
5. All auto-learned knowledge tagged in audit log as system:auto_learn
```

### Image Generation (services/image_gen.py)
```
Model: Gemini 2.5 Flash (native image generation)
Trigger: Query contains action words (generate, create, draw...) + visual nouns (image, diagram...)
Returns: Combined text + base64 image in single API call
Non-blocking: Falls back gracefully if image gen fails
```

---

## 5. REST API Endpoints (27 Routes)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/query` | Query with activation-based context selection + image generation |
| POST | `/api/v1/query/agent` | **Agentic query — SSE streaming with multi-step reasoning** |
| POST | `/api/v1/correct` | Submit versioned correction |
| GET | `/api/v1/nodes/{node_id}` | Node detail (Neo4j + PostgreSQL combined) |
| GET | `/api/v1/nodes/{node_id}/history` | Full audit trail |
| GET | `/api/v1/health` | All service health checks (Redis, Neo4j, Qdrant, PostgreSQL, LLM) |
| POST | `/api/v1/ingest` | File upload via Cognee ECL |
| POST | `/api/v1/ingest/batch` | Async file ingestion (Celery) |
| POST | `/api/v1/ingest/text` | Direct text ingestion |
| POST | `/api/v1/ingest/text/async` | Fire-and-forget text ingestion |
| GET | `/api/v1/datasets` | List all datasets |
| GET | `/api/v1/datasets/{name}/data` | List data items in dataset |
| POST | `/api/v1/consolidation/run` | Trigger consolidation cycle |
| GET | `/api/v1/consolidation/status/{task_id}` | Poll consolidation progress |
| GET | `/api/v1/consolidation/last-report` | Last consolidation summary |
| GET | `/api/v1/timeline` | **Meta memory timeline — audit logs with filters + summary** |
| GET | `/api/v1/workers/status` | Celery worker dashboard |
| GET | `/api/v1/sessions/{session_id}/activations` | View activation scores |
| POST | `/api/v1/debug/salience-recompute` | Manual salience recompute |
| GET | `/api/v1/debug/stats` | System-wide stats |
| GET | `/api/v1/graph/overview` | **Knowledge graph visualization — top-salient nodes + edges** |
| GET | `/api/v1/graph/subgraph` | **BFS subgraph from a center node** |
| GET | `/api/v1/dashboard/stats` | **Confidence dashboard — distribution buckets, low-confidence nodes** |
| GET | `/api/v1/review/queue` | **Validation queue — auto-learned nodes pending review** |
| POST | `/api/v1/review/approve/{node_id}` | **Approve auto-learned node (confidence → 0.8)** |
| POST | `/api/v1/review/reject/{node_id}` | **Reject auto-learned node (archive)** |

All endpoints require Bearer token auth (currently placeholder — accepts any non-empty token).

---

## 6. Query Pipeline (Full Flow)

```
User Query
    ↓
1. Cognee search (vector + graph) → entity extraction
2. Neo4j text search (direct graph for corrected nodes)
3. Entity extraction from results (capped at 20, deduped case-insensitive)
4. Spreading activation (BFS through Neo4j graph)
5. Enrich with M_meta (confidence, salience, conflicted)
6. Confidence gate (weighted average by activation scores)
7. Access tracking (record access for each activated node)
8. Image check → if visual query, call Gemini 2.5 Flash for text+image
9. LLM generation (activated nodes as context + confidence prefix)
10. Continuous learning fallback (if KB fails → unconstrained LLM + background ingestion)
```

**Fallback cascade:** Spreading activation → Graph text search → Raw Cognee results → Continuous learning (unconstrained LLM)

### Agentic Query Pipeline (api/v1/agent_query.py)
```
User Query + Conversation History (last 10 turns)
    ↓
1. Build system prompt + conversation context (capped at 16000 chars)
2. LLM call with 9 agent tools (tool_choice="auto")
3. Agent loop (max 5 tool calls):
   a. If LLM returns tool_calls → execute them, yield SSE "step" events
   b. If LLM returns text → yield SSE "answer" event + "done"
   c. If max calls reached → force final answer
4. Per-tool timeout: 15s, total timeout: 60s
5. Errors returned as tool results so LLM can adapt
```

**9 Agent Tools:**
| Tool | Backend Call | Purpose |
|------|-------------|---------|
| `search_knowledge` | `cognee.search()` | Vector+graph search |
| `find_entity` | `semantic.find_nodes_by_name()` | Entity lookup by name |
| `search_graph_text` | `semantic.search_nodes_by_text()` | Text search in graph |
| `get_node_detail` | `semantic.get_node()` + `meta.get_or_create_metadata()` | Full node info |
| `get_neighbors` | `semantic.get_neighbors_with_weights()` | Graph traversal |
| `get_version_history` | `semantic.get_version_history()` | Audit trail |
| `activate_and_gather` | `activation_engine.activate_for_query()` | Spreading activation |
| `check_confidence` | `confidence_gate.compute_aggregate_confidence()` | Confidence scoring |
| `get_audit_logs` | `meta.get_audit_logs()` | Meta memory audit logs |

**SSE Event Types:** `step` (tool_call/tool_result), `answer`, `error`, `done`

---

## 7. Frontend (Next.js 16)

**Stack:** Next.js 16.1.6, React 19.2.3, TypeScript 5, Tailwind CSS v4
**Location:** `frontend/`
**Dependencies:** react-markdown 10.1.0, @tailwindcss/typography 0.5.19

### Pages
| Route | Purpose |
|-------|---------|
| `/` | Redirects to `/query` |
| `/query` | **Agentic chat** — multi-step reasoning with live thinking trace, multi-turn conversation, confidence badges, inline corrections, source attribution, image display |
| `/ingest` | Drag-and-drop file upload, sync/batch modes, pipeline visualization (4 steps) |
| `/nodes` | Node browser with UUID search, top accessed/salient tables |
| `/nodes/[nodeId]` | Node detail with version history timeline, correction dialog |
| `/timeline` | **Meta memory timeline** — audit log visualization with action filters, date range, summary cards, grouped events |
| `/graph` | **Knowledge graph visualization** — force-directed canvas, click-to-expand subgraph, search highlight, node detail sidebar |
| `/dashboard` | **Confidence dashboard** — stat cards, confidence distribution chart, low-confidence node table |
| `/review` | **Validation queue** — approve/reject auto-learned nodes, inline correction, confidence bars |
| `/debug` | Stats overview, activation viewer, salience recompute |
| `/workers` | Celery worker monitoring, active/queued tasks, beat schedule |
| `/health` | Auto-refreshing service health (10s), health history timeline |
| `/settings` | API URL, key, user ID (localStorage), test connection |

### Key Components (60+ files)
- **UI Library (13):** Card, Badge, Button, Input, Textarea, DataTable, Dialog, StatusDot, Spinner, ProgressBar, CodeBlock, EmptyState, Toast
- **Layout (3):** PageShell, Header, Sidebar
- **Query (7):** QueryInput, QueryResult, QueryDetailPanel, QueryHistory, SourceList, ThinkingTrace, ActivationReplay
- **Graph (2):** GraphCanvas (react-force-graph-2d + dynamic import), GraphNodePanel (sidebar detail)
- **Dashboard (3):** DashboardOverview (stat cards), ConfidenceChart (CSS bar chart), LowConfidenceTable
- **Review (1):** ReviewQueue (approve/reject/edit cards with CorrectionForm dialog)
- **Timeline (4):** TimelineSummary, TimelineFilters, TimelineEventList, TimelinePage
- **Ingest (4):** IngestForm, FileUploadZone, PipelinePanel, BatchStatusCard, IngestHistory
- **Nodes (4):** NodeSearch, NodeDetailCard, NodeHistoryTimeline, CorrectionForm
- **Health (2):** HealthGrid (5 services + overall), HealthHistory timeline
- **Debug (4):** StatsOverview, TopNodesTable, ActivationViewer, SalienceRecomputeButton
- **Workers (4):** WorkerStatusCard, WorkerStats, BeatScheduleTable, ActiveTasksList

### Hooks
- `useApiKey`: localStorage API credentials
- `useSession`: UUID-based query sessions
- `useHealth`: Auto-refresh every 10s, maintains 20-entry history
- `useBatchStatus`: Polls every 3s until SUCCESS/FAILURE

### API Integration
- Base URL proxied through Next.js rewrites → `http://localhost:8000`
- `experimental.proxyTimeout: 300000` (5 min for long cognify operations)
- Bearer token from localStorage
- API client modules: query, correct, nodes, health, ingest, debug, workers, timeline, agent-query, graph, dashboard, review

---

## 8. Backend Models

### Pydantic Schemas (models/schemas.py) — 44 Models
- **Enums:** ConfidenceLevel (HIGH/MEDIUM/LOW/CONFLICTED)
- **Requests:** QueryRequest, CorrectionRequest, IngestRequest, TextIngestRequest, AgentQueryRequest
- **Responses:** QueryResponse (answer, confidence, confidence_score, sources, tokens_used, fallback, auto_learned, insights, images), CorrectionResponse, NodeHistoryResponse, NodeDetailResponse, HealthResponse, WorkersStatusResponse, ConsolidationReportResponse, TimelineResponse, GraphOverviewResponse, GraphSubgraphResponse, DashboardStatsResponse, ReviewQueueResponse, ReviewActionResponse
- **Graph models:** GraphNode, GraphEdge
- **Dashboard models:** ConfidenceBucket, LowConfidenceNode
- **Review models:** ReviewNodeEntry
- **Sub-models:** SourceReference, QueryInsights, TokenUsage, GeneratedImage, NodeVersion, ServiceHealth, WorkerInfo, BeatScheduleEntry, ActiveTask, ActivationEntry, SessionActivationsResponse, SalienceRecomputeResponse, DebugStatsResponse, ConsolidationTriggerResponse, ConversationMessage, AuditLogEntry, TimelineSummary

### SQLAlchemy (models/database.py)
- **Organization:** id, name, created_at
- **APIKey:** id, org_id, key_hash (bcrypt), label, revoked
- **AuditLog:** id, org_id, node_id, action, changed_by, previous_value, new_value, reason, version, timestamp
- **NodeMetadata:** node_id (PK), org_id, confidence, salience, volatile, conflicted, access_count, correction_count, last_accessed

### Graph (models/graph.py)
- **KnowledgeNode:** Extends Cognee DataPoint with confidence, salience, volatile, conflicted
- **VersionEdge:** PREVIOUS_VERSION relationship (changed_by, reason, previous_value, new_value)
- **ActivationState:** In-flight Redis state (node_id, session_id, activation_score)

---

## 9. Workers (Celery)

**Broker:** Redis DB 1 | **Backend:** Redis DB 2

### Tasks
| Task | Schedule | Purpose |
|------|----------|---------|
| `decay_cycle_task` | Every 30s | Decrement activation scores, evict at 0 |
| `salience_recompute_task` | Every 1 hour | Recompute salience for all Entity nodes |
| `consolidation_task` | Every 7 days | Promote, archive, merge, compress |
| `batch_ingestion_task` | On demand | Process document batches via Cognee |
| `text_ingestion_task` | On demand | Async text ingestion |

**Important:** All tasks use `asyncio.run()` not `new_event_loop()` to avoid future loop mismatch.

---

## 10. MCP Server (mcp/server.py)

FastMCP server with 6 tools, runs via stdio: `python -m cortexbrain.mcp`

| Tool | Endpoint | Purpose |
|------|----------|---------|
| `cortexbrain_query` | POST /query | Query with confidence scoring |
| `cortexbrain_remember` | POST /ingest/text | Ingest text (default dataset: claude_code_memory) |
| `cortexbrain_correct` | POST /correct | Versioned correction |
| `cortexbrain_search_sources` | GET /datasets | List datasets |
| `cortexbrain_consolidate` | POST /consolidation/run | Trigger consolidation |
| `cortexbrain_health` | GET /health | Service health |

---

## 11. Services

### Image Generation (services/image_gen.py)
- **Model:** Gemini 2.5 Flash (native image generation)
- **Detection:** Word-level matching — action words (generate, create, draw, make, show) + visual nouns (image, diagram, chart, flowchart, etc.)
- **Standalone triggers:** "visualize", "visualise", "draw me", "show me"
- **API:** Google Generative Language API with `responseModalities: ["TEXT", "IMAGE"]`
- **Returns:** `ImageAnswerResult` (text + base64 image) or None on failure
- **Non-blocking:** Failure returns None, text-only path continues unaffected
- **Key env var:** `GEMINI_API_KEY` or `LLM_API_KEY`

---

## 12. Hooks (scripts/hooks/)

| Hook | Trigger | Action |
|------|---------|--------|
| `pre_compact_save.py` | Before /compact | Extract last 10 turns, ingest to CortexBrain (dataset: session_context) |
| `session_start_restore.py` | Session start (source=compact) | Query CortexBrain for recent context, restore via reason field |
| `_shared.py` | Imported by hooks | Transcript parsing, CortexBrain API calls (stdlib only) |

Both: stdlib only, non-blocking, 30s timeout, graceful fallback.

---

## 13. Docker Deployment

Full stack runs with `docker compose up -d` — all 8 services containerized.

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| neo4j | neo4j:5-community | 7474, 7687 | M_s (Semantic Memory) |
| redis | redis:7-alpine | 6379 | M_a (Active Memory) + Celery broker/backend |
| postgres | postgres:16-alpine | 5432 | M_meta + Cognee metadata (`init-db.sh` creates `cognee_db`) |
| qdrant | qdrant/qdrant | 6333, 6334 | M_r (Raw Memory) |
| cortexbrain | python:3.12-slim-bookworm | 8000 | FastAPI app (healthcheck via `/api/v1/health`) |
| celery-worker | python:3.12-slim-bookworm | - | Decay, salience, consolidation, ingestion tasks |
| celery-beat | python:3.12-slim-bookworm | - | Scheduled task runner |
| frontend | node:20-alpine | 3005→3000 | Next.js 16 production build |

### Docker Files
| File | Purpose |
|------|---------|
| `Dockerfile` | Backend — Python 3.12, gcc/g++/libpq-dev/git/curl, editable install |
| `frontend/Dockerfile` | Frontend — Node 20, `npm ci` + `npm run build` + `npm start` |
| `.env.docker` | Docker env — all connection strings use service names (`neo4j`, `redis`, `postgres`, `qdrant`) |
| `.dockerignore` | Excludes `.git`, `node_modules`, `.next`, `tests/`, `Documents/`, `website/` |
| `frontend/.dockerignore` | Excludes `node_modules`, `.next`, `.env.local` |
| `scripts/init-db.sh` | PostgreSQL init — creates `cognee_db` database for Cognee |

### Docker Networking
- **Backend services** use Docker service names: `bolt://neo4j:7687`, `redis://redis:6379`, `postgresql+asyncpg://...@postgres:5432`
- **Frontend proxy** uses `API_INTERNAL_URL=http://cortexbrain:8000` (baked at build time for Next.js server-side rewrites)
- **Browser SSE** uses `NEXT_PUBLIC_API_URL=http://localhost:8000` (exposed port, bypasses Next.js proxy for streaming)
- **`next.config.ts`** reads `API_INTERNAL_URL` first, falls back to `NEXT_PUBLIC_API_URL` — backward-compatible with local dev

### Running
```bash
docker compose build              # Build all images
docker compose up -d              # Start all 8 services
docker compose ps                 # Verify healthy status
docker compose logs -f cortexbrain frontend  # Watch logs
# Backend: http://localhost:8000  |  Frontend: http://localhost:3005
docker compose down               # Tear down
```

**Hybrid mode (alternative):** Start only infra (`docker compose up -d neo4j redis postgres qdrant`), run app locally.

---

## 14. Configuration (.env)

| Variable | Value | Purpose |
|----------|-------|---------|
| LLM_MODEL | gemini/gemini-2.0-flash | LLM via litellm |
| GEMINI_API_KEY | (secret) | Gemini 2.5 Flash image generation |
| GRAPH_DATABASE_URL | bolt://localhost:7687 | Neo4j |
| GRAPH_DATABASE_PASSWORD | cortexbrain_dev | Neo4j auth |
| VECTOR_DB_URL | http://localhost:6333 | Qdrant |
| REDIS_URL | redis://localhost:6379/0 | Active memory |
| POSTGRES_URL | postgresql+asyncpg://cortexbrain:cortexbrain_dev@localhost:5432/cortexbrain | Meta memory |
| CELERY_BROKER_URL | redis://localhost:6379/1 | Celery broker |
| CELERY_RESULT_BACKEND | redis://localhost:6379/2 | Celery results |
| ACTIVATION_THRESHOLD | 30 | Min activation score |
| DAMPENING_FACTOR | 0.5 | BFS dampening |
| MAX_CONTEXT_TOKENS | 2000 | Token budget |
| DECAY_RATE | 10 | Score decrement per cycle |
| DECAY_INTERVAL_SECONDS | 30 | Decay frequency |

---

## 15. Test Suite

**Run:** `pytest tests/unit/` (no Docker needed)

| Test File | Coverage |
|-----------|----------|
| test_activation_engine.py | Spreading activation, BFS, dampening, threshold, token budget, vector fallback |
| test_confidence_gate.py | Classification, weighted aggregation, response formatting |
| test_salience_scorer.py | Formula, normalization, individual weights, caps |
| test_semantic_memory.py | Cypher queries, result unwrapping, :Entity label, error handling |
| test_query_pipeline.py | Entity extraction, _node_text fallback (description→value→name) |

**Patterns:** AsyncMock, fakeredis, pytest fixtures, no parameterization

---

## 16. Critical Gotchas

1. **Cognee v0.5.2 uses LanceDB** (NOT Qdrant) internally for vector storage
2. **Entity nodes use `description` field** (NOT `value`) — critical for _node_text fallback
3. **Neo4j label is `:Entity`** not `:KnowledgeNode` — all Cypher queries must use this
4. **Cognee's `get_neighbours()` doesn't exist** — must use raw Cypher queries
5. **Celery tasks need `asyncio.run()`** not `new_event_loop()` (future loop mismatch)
6. **`python3` not `python`** on macOS
7. **Neo4j container name:** `compliancebrain-neo4j-1`, password: `cortexbrain_dev`
8. **Cognee dataset names:** NO spaces or dots (use hyphens/underscores)
9. **Next.js proxy timeout:** Set `experimental.proxyTimeout` for long ingestion requests
10. **Celery app discovery:** Needs `include=["cortexbrain.workers.tasks"]`
11. **Auth is placeholder:** Currently accepts any non-empty Bearer token
12. **Next.js rewrites are build-time:** `NEXT_PUBLIC_*` and rewrite destinations are baked at `npm run build`, not re-evaluated at runtime — must pass `API_INTERNAL_URL` as a Docker build arg
13. **Image gen non-blocking:** `should_generate_image()` uses word-level matching, not exact phrases
14. **Continuous learning dedup:** 80% term overlap threshold prevents learning loops

---

## 17. Design Patterns

1. **Extension over Fork** — CortexBrain wraps Cognee, never reimplements
2. **Idempotent Operations** — Consolidation, metadata init safe to re-run
3. **Non-Destructive Corrections** — PREVIOUS_VERSION edges, never delete
4. **Token-Bounded Context** — Activation engine respects max_context_tokens
5. **Graceful Degradation** — Graph text search → Cognee results → Unconstrained LLM
6. **Audit Everything** — Every mutation recorded in PostgreSQL
7. **Fire-and-Forget** — Background tasks for continuous learning, batch ingestion
8. **Dependency Injection** — FastAPI Depends for clean testing
9. **Async-First** — All I/O async (Redis, Neo4j, PostgreSQL, LLM)
10. **Event Loop Safety** — `asyncio.run()` in Celery tasks
11. **Non-Blocking Image Gen** — Image generation never affects text-only fallback path
12. **Self-Improving System** — Continuous learning auto-ingests from LLM fallback answers
13. **SSE Streaming** — Server-Sent Events for real-time agent step visibility (FastAPI StreamingResponse)
14. **Agentic Tool-Use** — LLM autonomously selects tools via function calling, max 5 iterations with timeout guards
15. **Multi-Turn Conversation** — Conversation history passed in request, capped at 16000 chars

---

## 18. What Cognee Provides vs What CortexBrain Adds

| Cognee Provides (DO NOT rebuild) | CortexBrain Adds (Novel) |
|----------------------------------|--------------------------|
| `cognee.add()`, `cognee.cognify()`, `cognee.search()` | ActivationEngine (spreading activation) |
| GraphDBInterface (Neo4j adapter) | SemanticMemoryStore (version history edges) |
| VectorDBInterface (LanceDB) | ActiveMemoryStore (Redis activation scores) |
| DataPoint base class | KnowledgeNode (confidence, salience, volatile) |
| LLMGateway (litellm + instructor) | ConfidenceGate (confidence-gated responses) |
| ECL pipeline (Extract, Cognify, Load) | MutationEngine (revision-based corrections) |
| Env-based config | SalienceScorer (importance scoring) |
| Alembic migrations | ConsolidationEngine (episodic→semantic compression) |
| | ContinuousLearning (auto-ingest from LLM fallback) |
| | ImageGeneration (Gemini 2.5 Flash visual answers) |
| | MetaMemoryStore (PostgreSQL audit + metadata) |
| | MCP Server (Claude Code integration, 6 tools) |
| | Hooks (pre-compact save, session-start restore) |
| | Admin Dashboard (Next.js 16, 13 pages, 60+ components) |
| | Agentic Query (SSE streaming, 9 tools, multi-turn) |
| | Meta Memory Timeline (audit log visualization) |
| | Knowledge Graph Visualization (force-directed canvas) |
| | Confidence Dashboard (stats, distribution, low-confidence) |
| | Auto-Learning Validation Queue (approve/reject/edit) |
| | Activation Replay (session activation flow viewer) |

---

## 19. Key Files Quick Reference

| File | Purpose |
|------|---------|
| `src/cortexbrain/main.py` | FastAPI app entry point |
| `src/cortexbrain/config/settings.py` | All configuration (Pydantic BaseSettings) |
| `src/cortexbrain/api/v1/query.py` | Query pipeline (fixed pipeline endpoint) |
| `src/cortexbrain/api/v1/agent_query.py` | **Agentic query** — SSE streaming, 9 tools, agent loop |
| `src/cortexbrain/api/v1/timeline.py` | **Timeline** — Meta memory audit log visualization |
| `src/cortexbrain/api/v1/correct.py` | Correction endpoint |
| `src/cortexbrain/api/v1/ingest.py` | Ingestion endpoints (sync, batch, text) |
| `src/cortexbrain/api/v1/datasets.py` | Dataset browsing API |
| `src/cortexbrain/api/v1/consolidation.py` | Consolidation control endpoints |
| `src/cortexbrain/api/v1/workers.py` | Celery worker dashboard API |
| `src/cortexbrain/api/v1/graph.py` | **Knowledge graph visualization** — overview + subgraph endpoints |
| `src/cortexbrain/api/v1/dashboard.py` | **Confidence dashboard** — stats + distribution + low-confidence |
| `src/cortexbrain/api/v1/review.py` | **Validation queue** — queue/approve/reject endpoints |
| `src/cortexbrain/api/v1/debug.py` | Debug/introspection endpoints |
| `src/cortexbrain/core/activation/engine.py` | Spreading activation algorithm |
| `src/cortexbrain/core/activation/decay.py` | Decay cycle |
| `src/cortexbrain/core/mutation/engine.py` | Mutation pipeline |
| `src/cortexbrain/core/metacognition/confidence.py` | Confidence gating |
| `src/cortexbrain/core/metacognition/salience.py` | Salience scoring |
| `src/cortexbrain/core/consolidation/engine.py` | Weekly consolidation |
| `src/cortexbrain/memory/active.py` | Redis M_a |
| `src/cortexbrain/memory/semantic.py` | Neo4j M_s wrapper |
| `src/cortexbrain/memory/raw.py` | Vector M_r wrapper |
| `src/cortexbrain/memory/meta.py` | PostgreSQL M_meta |
| `src/cortexbrain/ingestion/documents.py` | Cognee pipeline wrapper |
| `src/cortexbrain/ingestion/continuous_learning.py` | Auto-learning system |
| `src/cortexbrain/services/image_gen.py` | Gemini 2.5 Flash image generation |
| `src/cortexbrain/workers/tasks.py` | Celery background tasks |
| `src/cortexbrain/workers/celery_app.py` | Celery config + beat schedule |
| `src/cortexbrain/mcp/server.py` | MCP server for Claude Code |
| `src/cortexbrain/models/schemas.py` | 44 Pydantic API models |
| `src/cortexbrain/models/database.py` | SQLAlchemy tables |
| `src/cortexbrain/models/graph.py` | KnowledgeNode + VersionEdge |
| `frontend/src/app/query/page.tsx` | **Agentic query page** — SSE streaming, multi-turn conversation |
| `frontend/src/app/timeline/page.tsx` | **Timeline page** — audit log visualization |
| `frontend/src/lib/api/agent-query.ts` | SSE consumer for agentic query |
| `frontend/src/lib/api/timeline.ts` | Timeline API client |
| `frontend/src/lib/api/graph.ts` | Graph visualization API client |
| `frontend/src/lib/api/dashboard.ts` | Dashboard stats API client |
| `frontend/src/lib/api/review.ts` | Validation queue API client |
| `frontend/src/app/graph/page.tsx` | **Knowledge graph page** — force-directed canvas + node sidebar |
| `frontend/src/app/dashboard/page.tsx` | **Confidence dashboard page** — stats, chart, table |
| `frontend/src/app/review/page.tsx` | **Validation queue page** — approve/reject auto-learned nodes |
| `frontend/src/components/graph/graph-canvas.tsx` | ForceGraph2D wrapper (dynamic import, ssr: false) |
| `frontend/src/components/graph/graph-node-panel.tsx` | Node detail sidebar panel |
| `frontend/src/components/dashboard/dashboard-overview.tsx` | Stat cards (total, avg confidence, low count) |
| `frontend/src/components/dashboard/confidence-chart.tsx` | Pure CSS horizontal bar chart |
| `frontend/src/components/dashboard/low-confidence-table.tsx` | DataTable with confidence bars |
| `frontend/src/components/query/activation-replay.tsx` | Lazy-loaded activation flow viewer |
| `frontend/src/components/review/review-queue.tsx` | Approve/reject/edit card list |
| `frontend/src/components/query/thinking-trace.tsx` | Collapsible agent reasoning trace |
| `frontend/src/lib/api-client.ts` | API client with Bearer auth |
| `frontend/src/lib/types.ts` | TypeScript types (mirrors Pydantic schemas) |
| `scripts/hooks/_shared.py` | Hook utilities (stdlib only) |
| `scripts/hooks/pre_compact_save.py` | PreCompact hook |
| `scripts/hooks/session_start_restore.py` | SessionStart hook |
| `Dockerfile` | Backend Docker image (Python 3.12, gcc/g++/libpq-dev/git/curl) |
| `frontend/Dockerfile` | Frontend Docker image (Node 20, build + serve) |
| `.env.docker` | Docker-specific env (service names instead of localhost) |
| `.dockerignore` | Docker build context exclusions |
| `docker-compose.yml` | 8 services (full stack) |
| `pyproject.toml` | Dependencies + build config |
| `TASKLIST.md` | Implementation progress |
| `prd-mfca-compliance-brain-mvp.md` | Product requirements |

---

## 20. Dependencies

### Backend (Python)
| Package | Version | Purpose |
|---------|---------|---------|
| cognee[neo4j,anthropic,redis] | >=0.5.0 | Foundation — ECL pipeline, graph, vector, LLM |
| redis | >=5.2.0 | M_a active memory |
| asyncpg | >=0.30.0 | PostgreSQL async driver |
| sqlalchemy[asyncio] | >=2.0.36 | ORM for M_meta |
| mcp | >=1.2.0 | Claude Code MCP integration |
| httpx | >=0.28.0 | Async HTTP (image gen, MCP) |
| celery[redis] | >=5.4.0 | Background task queue |
| gliner | >=0.2.0 | Entity extraction |
| python-jose[cryptography] | >=3.3.0 | JWT auth (future) |
| bcrypt | >=4.2.0 | API key hashing |
| tree-sitter | >=0.23.0 | Code repo ingestion |
| qdrant-client | >=1.12.0 | Vector DB direct client |

### Frontend (Node.js)
| Package | Version | Purpose |
|---------|---------|---------|
| next | 16.1.6 | React framework with App Router |
| react | 19.2.3 | UI library |
| tailwindcss | ^4 | Utility-first CSS |
| typescript | ^5 | Type safety |
| react-markdown | ^10.1.0 | Markdown rendering |
| react-force-graph-2d | ^1.x | Canvas-based force-directed graph (knowledge graph viz) |
| @tailwindcss/typography | ^0.5.19 | Typography plugin |

### Infrastructure
| Service | Version | Purpose |
|---------|---------|---------|
| Neo4j | 5 Community | Graph database (M_s) |
| Redis | 7 Alpine | Cache + message broker (M_a + Celery) |
| PostgreSQL | 16 Alpine | Relational database (M_meta) |
| Qdrant | latest | Vector database (backup to Cognee's LanceDB) |

---

## 21. Changelog vs Previous learning.md

### Added since last version (2026-02-15):
1. **Full Docker Deployment** — All 8 services containerized: backend (`Dockerfile`), frontend (`frontend/Dockerfile`), Celery workers, + 4 infrastructure services. Docker-specific env file (`.env.docker`), healthcheck on cortexbrain, `API_INTERNAL_URL` for Docker proxy networking.
2. **Knowledge Graph Visualization** (`/graph`) — Force-directed canvas via react-force-graph-2d, confidence-based coloring, click-to-expand subgraph, search highlight, node detail sidebar with correction support
3. **Confidence Dashboard** (`/dashboard`) — 3 stat cards (total nodes, avg confidence, low-confidence count), pure CSS confidence distribution chart, low-confidence DataTable with links
3. **Auto-Learning Validation Queue** (`/review`) — Card-based queue for auto-learned nodes (confidence 0.5–0.7), approve (→0.8), reject (→archive), inline edit via CorrectionForm
4. **Activation Replay** — Lazy-loaded component in query detail panel, shows session activation flow with scored node list
5. **Corrected Badge** — SourceCard shows green "Corrected" badge after successful inline correction
6. **6 new backend endpoints** — graph/overview, graph/subgraph, dashboard/stats, review/queue, review/approve, review/reject
7. **10 new Pydantic schemas** — GraphNode, GraphEdge, GraphOverviewResponse, GraphSubgraphResponse, ConfidenceBucket, LowConfidenceNode, DashboardStatsResponse, ReviewNodeEntry, ReviewQueueResponse, ReviewActionResponse
8. **3 new frontend API clients** — graph.ts, dashboard.ts, review.ts
9. **3 new sidebar nav items** — Graph, Dashboard, Review (with SVG icons)
10. **Frontend page count** increased to 13 routes with 60+ TypeScript/TSX files
11. **API route count** increased to 27 endpoints

### Added in version (2026-02-14):
1. **Agentic Query System** (`api/v1/agent_query.py`) — SSE streaming endpoint with LLM function calling, 9 tools, max 5 iterations, multi-turn conversation (last 10 turns, 16000 char cap)
2. **Meta Memory Timeline** (`api/v1/timeline.py`) — Audit log visualization endpoint with action/date filters, summary counts, pagination
3. **ThinkingTrace component** (`components/query/thinking-trace.tsx`) — Collapsible agent step trace with paired tool_call/tool_result display, action-specific icons
4. **SSE consumer** (`lib/api/agent-query.ts`) — Frontend ReadableStream parser for SSE events with abort support
5. **Timeline frontend** (`app/timeline/page.tsx` + 3 components) — Summary cards, action chip filters, date range pickers, grouped event list
6. **5 new Pydantic schemas** — ConversationMessage, AgentQueryRequest, AuditLogEntry, TimelineSummary, TimelineResponse
7. **Frontend page count** increased to 10 routes with 50+ TypeScript/TSX files
8. **API route count** increased to 16+ endpoints

### Added in previous version (2026-02-11):
1. **Image Generation Service** (`services/image_gen.py`) — Gemini 2.5 Flash native image generation with word-level intent detection
2. **GeneratedImage schema** in Pydantic models — base64 image response support
3. **QueryInsights model** — activation mode, entities extracted, max activation score, avg salience
4. **Image display** in query responses — `images: list[GeneratedImage]` field
5. **Updated query pipeline** — Step 8 now includes image generation check before LLM call
6. **Continuous learning integration** into query pipeline — two trigger points (no-activation and post-LLM)
7. **Frontend page count** verified at 8 routes with 40 TypeScript/TSX files
8. **API route count** verified at 14+ endpoints (up from documented 10)
9. **Pydantic model count** verified at 29 models
10. **Celery task count** verified at 5 scheduled/on-demand tasks
11. **Dependency versions** updated to match current pyproject.toml and package.json
12. **RAG Benchmark Suite** — Golden dataset (20 Q&A pairs), accuracy evaluator (Recall@K, Precision@K, MRR, keyword match, faithfulness), speed benchmark (p50/p95/p99 latency)

---

## 22. RAG Benchmark Suite

**Location:** `tests/benchmarks/`

### Files
| File | Purpose |
|------|---------|
| `golden_dataset.jsonl` | 20 Q&A pairs with expected sources and keywords, 7 categories, 3 difficulty levels |
| `eval_rag.py` | Accuracy evaluation: Recall@K, Precision@K, MRR, keyword match, LLM-as-judge faithfulness |
| `bench_speed.py` | Speed benchmark: p50/p95/p99 latency per query type, activation mode distribution |
| `eval_results.json` | Auto-generated accuracy results (JSON) |
| `speed_results.json` | Auto-generated speed results (JSON) |

### Running Benchmarks
```bash
# RAG accuracy (requires running CortexBrain API + ingested data)
python3 tests/benchmarks/eval_rag.py                      # Full eval (20 queries)
python3 tests/benchmarks/eval_rag.py --skip-faithfulness   # Skip LLM judge (faster)
python3 tests/benchmarks/eval_rag.py --category algorithm  # Filter by category
python3 tests/benchmarks/eval_rag.py --ids q01,q05         # Specific queries
python3 tests/benchmarks/eval_rag.py --k 5                 # Recall/Precision@5

# Speed benchmark
python3 tests/benchmarks/bench_speed.py                    # Default (8 queries x 3 iters)
python3 tests/benchmarks/bench_speed.py --iterations 10    # More iterations
python3 tests/benchmarks/bench_speed.py --threshold 30000  # Custom p95 threshold (ms)
python3 tests/benchmarks/bench_speed.py --component        # Include component-level timing
```

### Accuracy Metrics
| Metric | What It Measures | Formula |
|--------|-----------------|---------|
| **Recall@K** | % of expected sources found in top K | matched / expected |
| **Precision@K** | % of top K results that are relevant | relevant_in_K / K |
| **MRR** | How early first relevant result appears | 1 / rank_of_first_match |
| **Keyword Score** | % of expected keywords in answer | found / expected |
| **Faithfulness** | Does answer only use context info? | LLM-as-judge (0.0-1.0) |

### Speed Metrics
- **p50/p95/p99** latency per query type
- **Activation mode distribution** (spreading vs continuous_learning vs fallback)
- **Fallback rate** (% of queries that fell back from activation)

### Golden Dataset Categories
| Category | Count | Examples |
|----------|-------|---------|
| architecture | 6 | Memory substrates, activation, Cognee extension |
| algorithm | 5 | Salience, decay, confidence, token budget, fallback cascade |
| feature | 3 | Continuous learning, correction versioning, image generation |
| api | 2 | REST endpoints, correction endpoint |
| infrastructure | 2 | Celery tasks, vector DB |
| integration | 1 | MCP server |
| security | 1 | Authentication |

### Baseline Results (Feb 14, 2026)
| Metric | Value |
|--------|-------|
| Avg Recall@10 | 55.0% |
| Avg Precision@10 | 40.0% |
| MRR | 0.372 |
| Avg Keyword Match | 53.4% |
| Avg Latency | 22,859ms |
| Fallback Rate | 15% |
| p50 Latency | 22,362ms |
| p95 Latency | 33,874ms |

### Pass/Fail Thresholds
- **Accuracy:** Fails if avg Recall@K < 30% OR avg keyword match < 30%
- **Speed:** Fails if p95 > 45,000ms (configurable via `--threshold`)
