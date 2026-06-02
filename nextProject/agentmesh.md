# AgentMesh Enterprise — Requirements & Phased Implementation Plan

## Project Summary

AgentMesh Enterprise is a modular, secure, scalable multi-agent orchestration platform with runtime tool/skill integration, hybrid LLM routing, governance, and enterprise-grade UI for visualization, monitoring, and management.

**Model Backend:** Gemini 3 Pro (`gemini-3-pro-image-preview`) via `https://generativelanguage.googleapis.com/v1beta/models`

---

## Requirements

### R1. Agent Runtime

| ID | Requirement | Priority |
|----|------------|----------|
| R1.1 | Supervisor Agent receives user input, classifies intent, and routes to the correct downstream agent | Must |
| R1.2 | Planner Agent decomposes complex tasks into ordered sub-tasks with dependencies | Must |
| R1.3 | Executor Agent runs tools in a loop (plan → execute → observe → decide) with retry and exit conditions | Must |
| R1.4 | Vision Agent handles multimodal inputs (text + image) and delegates vision-specific tasks | Must |
| R1.5 | Human-in-the-loop Agent pauses execution and solicits user approval before proceeding | Should |
| R1.6 | Agents share context via a common memory store (short-term per conversation) | Must |
| R1.7 | Support both synchronous (request/response) and asynchronous (event-driven) execution modes | Must |
| R1.8 | Agents publish structured events to a message broker for observability and chaining | Should |

### R2. Model Abstraction Layer (Hybrid LLMs)

| ID | Requirement | Priority |
|----|------------|----------|
| R2.1 | Unified `invoke_model(model_id, inputs, tool_schemas, context)` interface for all LLM calls | Must |
| R2.2 | Cloud LLM integration (Gemini) with native function/tool calling support | Must |
| R2.3 | Local LLM integration via the same standardized interface | Should |
| R2.4 | Model Router selects the best model based on data sensitivity, latency, cost, and offline mode | Should |
| R2.5 | Fallback chain: if primary model fails, route to secondary automatically | Should |

### R3. Tool System

| ID | Requirement | Priority |
|----|------------|----------|
| R3.1 | Tool Registry stores built-in, user-defined, MCP, and API gateway tools with JSON Schema parameters | Must |
| R3.2 | CRUD operations on tools: `register_tool`, `unregister_tool`, `get_tool`, `list_tools` | Must |
| R3.3 | User-defined skills: upload Python code, validate against sandbox restrictions, register as tool | Must |
| R3.4 | Sandbox enforcement: restricted imports, timeouts, resource limits, optional containerization | Must |
| R3.5 | MCP integration: register remote MCP servers, discover tool schemas via `/tools`, generate proxy wrappers | Should |
| R3.6 | API Gateway tools: register REST/GraphQL APIs as tools with automatic auth injection and schema enforcement | Should |

### R4. Guardrails & PII Protection

| ID | Requirement | Priority |
|----|------------|----------|
| R4.1 | Input guardrails: prompt sanitization, safety policy enforcement, prevent system prompt leakage | Must |
| R4.2 | Output guardrails: prevent tool poisoning, block unsafe content in responses | Must |
| R4.3 | Policy engine: rule-based + pattern detection with severity levels (STRICT, MODERATE, OFF) | Must |
| R4.4 | PII detection: emails, phones, IDs, tokens, credentials, enterprise identifiers | Must |
| R4.5 | PII redaction modes: MASK, TOKENIZE, BLOCK — applied before any outbound call | Must |

### R5. Memory System

| ID | Requirement | Priority |
|----|------------|----------|
| R5.1 | Short-term memory: per-conversation context accessible to all agents in the session | Must |
| R5.2 | Long-term memory: persistent KV store or vector index for cross-session knowledge | Should |
| R5.3 | Store tool history, execution traces, agent decisions, and context vectors | Must |

### R6. Execution Backbone

| ID | Requirement | Priority |
|----|------------|----------|
| R6.1 | Event mesh via message broker (Redis Streams / Kafka / NATS) with pub/sub and command/event patterns | Must |
| R6.2 | Structured event schema: `{ event_type, timestamp, agent_id, payload }` | Must |
| R6.3 | Async task queues for long-running agent operations | Must |
| R6.4 | Horizontal scaling and fault tolerance for agent workers | Should |
| R6.5 | Leader election for critical orchestration components | Could |

### R7. Visual Orchestration UI & Dashboards

| ID | Requirement | Priority |
|----|------------|----------|
| R7.1 | Workflow Designer: drag-and-drop builder, visual agent graphs, tool binding editor, save/export templates | Should |
| R7.2 | Execution Trace Viewer: step-by-step logs, timing breakdowns, visual sequence diagrams | Must |
| R7.3 | Metrics Dashboards: latency, throughput, agent/tool usage, success/failure rates, guardrail triggers, PII events | Must |
| R7.4 | Policy & Guardrail UI: edit rules, assign policies to tenants/workflows, visual compliance feedback | Should |
| R7.5 | Debugging Tools: breakpoints, visual context inspector, re-run with modified data | Could |
| R7.6 | Role-Based Access: admin dashboard, developer IDE view, analyst insights panel | Should |

### R8. Security & Compliance

| ID | Requirement | Priority |
|----|------------|----------|
| R8.1 | RBAC for all APIs and UI endpoints | Must |
| R8.2 | Tenant isolation: data, policies, and agent configurations scoped per tenant | Must |
| R8.3 | Encryption in transit (TLS) and at rest | Must |
| R8.4 | Audit logs retained per tenant with configurable retention policies | Must |

### R9. API Surface

| ID | Requirement | Priority |
|----|------------|----------|
| R9.1 | `POST /chat` — Primary chat endpoint (agent orchestration) | Must |
| R9.2 | `POST /register-tool`, `GET /tools`, `DELETE /tool/{name}` — Tool management | Must |
| R9.3 | `POST /register-mcp`, `GET /mcp`, `DELETE /mcp/{name}` — MCP server management | Should |
| R9.4 | `POST /register-gateway`, `GET /gateway`, `DELETE /gateway/{name}` — API gateway management | Should |
| R9.5 | `GET /ui/workflows`, `POST /ui/workflows`, `GET /ui/execution/{id}` — UI workflow routes | Should |

---

## Phased Implementation Plan

---

### Phase 1 — Foundation (Week 1, Days 1-4)

**Goal:** Project scaffolding, core agent loop, single-model LLM integration, and basic chat endpoint.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 1.1 | **Project setup** — Init Python project (FastAPI), Docker Compose (Redis, Postgres), CI pipeline, linting (ruff), testing (pytest) | — | Runnable empty API at `localhost:8000` |
| 1.2 | **Define data models** — Agent, Tool, Event, Memory, Execution Trace schemas (Pydantic + SQLAlchemy) | 1.1 | `models/` package |
| 1.3 | **Model Abstraction Layer (Gemini)** — Implement `invoke_model()` with Gemini function-calling support (R2.1, R2.2) | 1.1 | `core/llm/` module |
| 1.4 | **Supervisor Agent** — Intent classification, route to planner or direct executor (R1.1) | 1.2, 1.3 | `agents/supervisor.py` |
| 1.5 | **Planner Agent** — Task decomposition into ordered sub-tasks (R1.2) | 1.3 | `agents/planner.py` |
| 1.6 | **Executor Agent** — Tool execution loop: plan → execute → observe → decide (R1.3) | 1.3 | `agents/executor.py` |
| 1.7 | **Short-term memory** — In-memory per-conversation context store (R5.1) | 1.2 | `memory/short_term.py` |
| 1.8 | **`POST /chat` endpoint** — Receives user input, runs supervisor → planner → executor pipeline, returns response (R9.1) | 1.4-1.7 | Working chat API |
| 1.9 | **Unit tests** — Agent routing, planner decomposition, executor loop, model invocation | 1.4-1.8 | >80% coverage on core |

**Phase 1 Exit Criteria:**
- User can send a text message to `/chat` and receive an LLM-generated response
- Supervisor correctly routes simple vs complex tasks
- Planner produces a valid sub-task list
- Executor runs a dummy built-in tool and returns results
- All unit tests pass

---

### Phase 2 — Tool System & Sandbox (Week 1, Days 5-7)

**Goal:** Full tool registry, built-in tools, user-defined skill upload with sandboxed execution.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 2.1 | **Tool Registry** — In-memory + DB-backed registry with JSON Schema validation (R3.1, R3.2) | Phase 1 | `tools/registry.py` |
| 2.2 | **Built-in tools** — Web search, calculator, code interpreter, file reader (minimum 4 tools) | 2.1 | `tools/builtin/` |
| 2.3 | **Tool API endpoints** — `POST /register-tool`, `GET /tools`, `DELETE /tool/{name}` (R9.2) | 2.1 | API routes |
| 2.4 | **User-defined skills** — Upload Python code, define input schema, validate, register (R3.3) | 2.1 | `tools/user_skills.py` |
| 2.5 | **Sandbox execution** — Restricted imports, timeouts, resource limits via `subprocess` + `seccomp` or container (R3.4) | 2.4 | `tools/sandbox.py` |
| 2.6 | **Wire tools into Executor** — Executor resolves tool names from registry, passes params, handles output | 2.1, 2.2 | Updated `agents/executor.py` |
| 2.7 | **Integration tests** — End-to-end: chat → plan → tool call → response with real Gemini calls | 2.6 | Test suite |

**Phase 2 Exit Criteria:**
- Tools can be registered, listed, and deleted via API
- User can upload a Python skill and invoke it through chat
- Sandboxed code cannot import `os`, `subprocess`, or access the network
- Built-in tools work end-to-end through the agent pipeline

---

### Phase 3 — Guardrails, PII & Security (Week 2, Days 1-3)

**Goal:** Input/output guardrails, PII detection and redaction, RBAC, tenant isolation.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 3.1 | **Input guardrails** — Prompt sanitization, system prompt leakage prevention (R4.1) | Phase 2 | `guardrails/input.py` |
| 3.2 | **Output guardrails** — Tool poisoning detection, unsafe content blocking (R4.2) | Phase 2 | `guardrails/output.py` |
| 3.3 | **Policy engine** — Rule-based + regex pattern detection, severity levels (STRICT/MODERATE/OFF) (R4.3) | 3.1, 3.2 | `guardrails/policy.py` |
| 3.4 | **PII detector** — Regex + NER-based detection for emails, phones, IDs, tokens, credentials (R4.4) | Phase 2 | `guardrails/pii_detector.py` |
| 3.5 | **PII redaction** — MASK, TOKENIZE, BLOCK modes applied pre-outbound (R4.5) | 3.4 | `guardrails/pii_redactor.py` |
| 3.6 | **RBAC middleware** — Role-based access control for all API endpoints (R8.1) | Phase 1 | `auth/rbac.py` |
| 3.7 | **Tenant isolation** — Scoped data, policies, agent configs per tenant (R8.2) | 3.6 | `auth/tenants.py` |
| 3.8 | **Audit logging** — Structured logs per tenant, retained with configurable policies (R8.4) | 3.7 | `audit/logger.py` |
| 3.9 | **Guardrail tests** — Injection attempts, PII samples, policy enforcement edge cases | 3.1-3.5 | Test suite |

**Phase 3 Exit Criteria:**
- Prompt injection attempts are blocked or sanitized
- PII in user input is detected and redacted before reaching the LLM
- API endpoints enforce role-based access (admin, developer, analyst)
- Tenant A cannot access Tenant B's tools, memory, or logs
- Audit log captures all mutations with tenant attribution

---

### Phase 4 — Event Mesh & Async Execution (Week 2, Days 4-5)

**Goal:** Event-driven backbone, async task queues, agent pub/sub communication.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 4.1 | **Event schema** — Define `{ event_type, timestamp, agent_id, payload }` (R6.2) | Phase 1 | `events/schema.py` |
| 4.2 | **Message broker integration** — Redis Streams (primary) with abstract interface for Kafka/NATS swap (R6.1) | 4.1 | `events/broker.py` |
| 4.3 | **Agent event publishing** — Agents emit events on task start, tool call, completion, failure (R1.8) | 4.1, 4.2 | Updated agent base class |
| 4.4 | **Async task queue** — Celery or custom worker for long-running agent operations (R6.3) | 4.2 | `workers/` package |
| 4.5 | **Execution trace store** — Persist full execution traces (R5.3) | 4.1 | `memory/traces.py` |
| 4.6 | **Integration tests** — Async workflows, event ordering, failure recovery | 4.1-4.5 | Test suite |

**Phase 4 Exit Criteria:**
- Agent actions produce structured events on the message broker
- Long-running tasks execute asynchronously without blocking the chat API
- Execution traces are persisted and queryable
- System recovers gracefully from worker failures

---

### Phase 5 — MCP & API Gateway Integration (Week 3, Days 1-2)

**Goal:** External tool sources — MCP server registration and API gateway tools.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 5.1 | **MCP server registration** — Register remote MCP servers with auth config (R3.5) | Phase 2 | `tools/mcp/registry.py` |
| 5.2 | **MCP tool discovery** — Fetch tool schemas from remote `/tools` endpoint, generate proxy wrappers | 5.1 | `tools/mcp/discovery.py` |
| 5.3 | **MCP proxy execution** — Route tool calls to remote MCP server, handle errors/timeouts | 5.2 | `tools/mcp/proxy.py` |
| 5.4 | **MCP API endpoints** — `POST /register-mcp`, `GET /mcp`, `DELETE /mcp/{name}` (R9.3) | 5.1 | API routes |
| 5.5 | **API Gateway registration** — Register REST/GraphQL APIs as tools with auth injection (R3.6) | Phase 2 | `tools/gateway/registry.py` |
| 5.6 | **API Gateway execution** — HTTP client with schema enforcement, auth header injection, error mapping | 5.5 | `tools/gateway/executor.py` |
| 5.7 | **Gateway API endpoints** — `POST /register-gateway`, `GET /gateway`, `DELETE /gateway/{name}` (R9.4) | 5.5 | API routes |
| 5.8 | **Integration tests** — Mock MCP server, mock external API, auth flow, timeout handling | 5.1-5.7 | Test suite |

**Phase 5 Exit Criteria:**
- MCP tools discovered from a remote server appear in the tool registry
- API gateway tools execute with correct auth headers
- Tool calls to external sources have timeout and error handling
- All CRUD endpoints work for MCP and gateway management

---

### Phase 6 — Vision, Memory & Model Router (Week 3, Days 3-5)

**Goal:** Multimodal support, long-term memory, hybrid model routing.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 6.1 | **Vision Agent** — Accept image + text input, route to Gemini vision endpoint (R1.4) | Phase 1 | `agents/vision.py` |
| 6.2 | **Multimodal `/chat`** — Accept `multipart/form-data` with image attachments | 6.1 | Updated chat endpoint |
| 6.3 | **Long-term memory** — Vector store (Qdrant or pgvector) for cross-session knowledge retrieval (R5.2) | Phase 4 | `memory/long_term.py` |
| 6.4 | **Model Router** — Route based on data sensitivity, latency, cost, offline mode (R2.4) | Phase 1 | `core/llm/router.py` |
| 6.5 | **Local LLM support** — Integrate local model (Ollama) via same `invoke_model` interface (R2.3) | 6.4 | `core/llm/local.py` |
| 6.6 | **Fallback chain** — If primary model fails, auto-route to secondary (R2.5) | 6.4 | Updated router |
| 6.7 | **Human-in-the-loop Agent** — Pause execution, request user approval, resume (R1.5) | Phase 4 | `agents/human_loop.py` |

**Phase 6 Exit Criteria:**
- User can send images through chat and receive vision-based responses
- Long-term memory stores and retrieves facts across sessions
- Model router correctly selects cloud vs local based on sensitivity rules
- Fallback chain activates when primary model returns an error
- Human-in-the-loop agent pauses and resumes correctly

---

### Phase 7 — Frontend: Dashboards & Execution Viewer (Weeks 4-5)

**Goal:** Enterprise UI — execution traces, metrics dashboards, policy management.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 7.1 | **Frontend scaffolding** — Next.js project, Tailwind, layout, auth pages, sidebar navigation | — | `frontend/` runnable |
| 7.2 | **Chat interface** — Real-time chat with streaming responses, image upload, tool call display | Phase 1 | Chat page |
| 7.3 | **Execution Trace Viewer** — Step-by-step logs, timing breakdowns, sequence diagrams (R7.2) | Phase 4 | Trace page |
| 7.4 | **Metrics Dashboard** — Latency, throughput, agent/tool usage charts, guardrail triggers, PII events (R7.3) | Phase 4 | Dashboard page |
| 7.5 | **Tool Management UI** — List, register, delete tools; view tool schemas; test tool execution | Phase 2 | Tools page |
| 7.6 | **Policy & Guardrail UI** — Edit rules, assign to tenants/workflows, compliance view (R7.4) | Phase 3 | Policy page |
| 7.7 | **Role-based views** — Admin dashboard, developer IDE view, analyst insights panel (R7.6) | 7.1 | Role-specific layouts |
| 7.8 | **UI integration tests** — Playwright or Cypress e2e tests for critical flows | 7.2-7.7 | Test suite |

**Phase 7 Exit Criteria:**
- Chat interface works end-to-end with streaming and tool call visualization
- Execution traces render with timing and sequence diagrams
- Metrics dashboard shows live data from the event mesh
- Policy UI allows editing and assigning guardrail rules
- Role-based access restricts UI panels appropriately

---

### Phase 8 — Workflow Designer & Debugging (Week 5-6)

**Goal:** Visual workflow builder, debugging tools, advanced UI features.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 8.1 | **Workflow Designer** — Drag-and-drop builder using React Flow, visual agent graph editor (R7.1) | Phase 7 | Designer page |
| 8.2 | **Tool binding editor** — Bind tools to workflow nodes, configure parameters visually | 8.1 | Integrated in designer |
| 8.3 | **Workflow templates** — Save, export, import workflow configurations | 8.1 | Template CRUD |
| 8.4 | **Workflow API** — `GET /ui/workflows`, `POST /ui/workflows`, `GET /ui/execution/{id}` (R9.5) | 8.1 | API routes |
| 8.5 | **Debugging: breakpoints** — Pause execution at specific agent/tool nodes (R7.5) | Phase 4, 8.1 | Debug mode |
| 8.6 | **Debugging: context inspector** — View agent memory and context at any execution step | 8.5 | Inspector panel |
| 8.7 | **Debugging: re-run** — Re-execute workflow from a specific step with modified data | 8.5 | Re-run feature |

**Phase 8 Exit Criteria:**
- Users can visually build agent workflows with drag-and-drop
- Workflows can be saved, exported, and imported
- Breakpoints pause execution and allow inspection
- Re-run from a specific step works with modified inputs

---

### Phase 9 — Hardening & Scale (Week 6-7)

**Goal:** Production readiness — horizontal scaling, fault tolerance, encryption, load testing.

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 9.1 | **Horizontal scaling** — Stateless API workers behind load balancer, scaled agent workers (R6.4) | Phase 4 | Kubernetes manifests or Docker Swarm config |
| 9.2 | **Fault tolerance** — Worker health checks, automatic restart, dead letter queues | 9.1 | Updated worker config |
| 9.3 | **Leader election** — For critical orchestration components (R6.5) | 9.1 | `cluster/leader.py` |
| 9.4 | **Encryption** — TLS for all connections, at-rest encryption for sensitive data (R8.3) | Phase 3 | Updated configs |
| 9.5 | **Load testing** — Locust or k6 benchmarks: 100 concurrent users, p99 < 5s for chat | All phases | Benchmark results |
| 9.6 | **Observability** — Structured logging with workflow ID correlation, OpenTelemetry traces (R9 section) | Phase 4 | `observability/` package |
| 9.7 | **End-to-end acceptance tests** — Full suite covering all 10 acceptance criteria from the PRD | All phases | Final test suite |

**Phase 9 Exit Criteria:**
- System handles 100 concurrent chat sessions without degradation
- Worker failures are auto-recovered within 30 seconds
- All data in transit and at rest is encrypted
- OpenTelemetry traces correlate across agents, tools, and services
- All 10 acceptance criteria from the PRD pass

---

## Tech Stack — Detailed Breakdown

### Backend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API Framework | **FastAPI** (Python 3.12) | Native async/await, auto OpenAPI docs, Pydantic validation — ideal for agent orchestration with streaming responses |
| Task Queue | **Celery + Redis** | Battle-tested for async agent workloads, built-in retries, scheduling (beat), and dead letter queues |
| Database | **PostgreSQL 16** | RBAC, tenant isolation, audit logs, tool registry, workflow storage — relational model fits structured enterprise data |
| Vector Store | **Qdrant** | Dedicated vector DB for long-term memory and semantic search over context vectors; outperforms pgvector at scale with filtering and payload indexing |
| Message Broker | **Redis Streams** | Event mesh (pub/sub + consumer groups), lightweight — already required for Celery, avoids adding Kafka complexity in early phases |
| Sandbox | **Docker containers** (ephemeral, per skill execution) | Safest isolation for user-uploaded Python code — restricted imports alone are bypassable; containers provide network isolation, CPU/memory caps, and auto-kill timeouts |

### AI / LLM

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Primary LLM | **Gemini 3 Pro** (`gemini-3-pro-image-preview`) | PRD-specified — native function/tool calling + multimodal (text + image) support in a single model |
| Local LLM | **Ollama** | Simple local model serving with OpenAI-compatible API; handles offline mode and sensitive data routing without cloud egress |
| LLM Abstraction | **LiteLLM** | Unified `invoke_model()` across Gemini, Ollama, and 100+ providers — eliminates writing per-provider adapters; supports function calling passthrough |
| PII Detection | **Presidio** (Microsoft OSS) | Production-grade NER + regex PII detection with 20+ built-in recognizers; supports custom entity types for enterprise identifiers; MASK/TOKENIZE/BLOCK modes |

### Frontend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | **Next.js 15** + **TypeScript** | SSR for dashboard SEO/performance, API routes for backend proxy, App Router for layout composition |
| Styling | **Tailwind CSS v4** | Utility-first for rapid UI development, consistent design tokens, zero-runtime CSS |
| Workflow Designer | **React Flow** | Purpose-built library for node-based visual editors — handles drag-and-drop, edge routing, zoom/pan, and custom node rendering out of the box |
| Charts / Metrics | **Tremor** | Built on top of Recharts + Tailwind — provides pre-built dashboard components (area charts, bar charts, KPI cards) matching enterprise aesthetic |
| Real-time Streaming | **SSE** (Server-Sent Events) | Streaming chat responses + live execution traces — simpler than WebSockets for unidirectional server-to-client data; native browser `EventSource` API |
| State Management | **Zustand** | Lightweight global state for agent session, tool registry cache, and UI preferences — avoids Redux boilerplate |
| E2E Testing | **Playwright** | Cross-browser testing, better async handling than Cypress, native support for SSE and streaming assertions |

### Infrastructure & DevOps

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Dev Environment | **Docker Compose** | All 7+ services (API, workers, Redis, Postgres, Qdrant, frontend, beat) in one `docker compose up` |
| Production | **Kubernetes** (Phase 9) | Horizontal pod autoscaling, rolling deploys, health checks, leader election via lease API |
| Observability | **OpenTelemetry** + **structured JSON logging** | Distributed tracing across agents → tools → LLM calls; workflow ID correlation; exportable to Jaeger/Grafana |
| Load Testing | **Locust** (Python) | Stays in Python ecosystem, scriptable agent-workflow scenarios, real-time web UI for monitoring |
| CI/CD | **GitHub Actions** | Lint (ruff) → type check (mypy) → test (pytest) → build (Docker) → deploy pipeline |
| Linting | **Ruff** | Fast Python linter + formatter (replaces flake8 + black + isort), single tool |
| Type Checking | **mypy** | Static type analysis to catch bugs before runtime, especially important for complex agent pipelines |

### Key Architectural Decisions

1. **Redis does triple duty** — Message broker (Streams for event mesh), task queue backend (Celery), and short-term memory store (per-conversation context with TTL). This avoids introducing Kafka/NATS until Phase 9 scaling demands it. The broker interface is abstract so swapping is a config change.

2. **LiteLLM as the model abstraction** — Instead of writing custom Gemini/Ollama adapters, LiteLLM provides the unified `invoke_model(model_id, inputs, tool_schemas, context)` interface the PRD requires. It handles function calling schema translation, streaming, retries, and fallback chains natively.

3. **Docker-based sandbox over seccomp/subprocess** — User-uploaded Python running in a restricted subprocess is inherently leaky (`ctypes`, `importlib` bypasses). Ephemeral Docker containers with `--network=none`, `--memory=256m`, `--cpus=0.5`, and `--timeout=30s` provide real isolation. Containers are pre-pulled and warm-started for <500ms overhead.

4. **Qdrant over pgvector** — While pgvector is simpler (no extra service), Qdrant provides: payload filtering (essential for tenant-scoped memory queries), built-in HNSW with quantization, and dedicated resource management. The memory system's context vectors and cross-session retrieval benefit from a purpose-built vector DB.

5. **SSE over WebSockets** — The PRD's real-time needs (streaming chat, live traces) are unidirectional (server → client). SSE is simpler to implement, auto-reconnects, works through HTTP/2 proxies, and requires no upgrade handshake. WebSockets would only be needed if we add collaborative editing (not in scope).

6. **Presidio for PII over custom regex** — Custom regex PII detection is fragile and requires constant maintenance. Presidio combines regex + spaCy NER models, handles 20+ entity types out of the box, and supports custom recognizers for enterprise-specific identifiers. The TOKENIZE mode enables reversible redaction for audit trails.

---

## Timeline: Before vs After (Claude Code)

| Phase | Focus | Manual (Before) | AI-Assisted (After) |
|-------|-------|-----------------|---------------------|
| Phase 1 | Foundation: agents, LLM, chat API | 3 weeks | **4 days** |
| Phase 2 | Tool system & sandbox | 3 weeks | **3 days** |
| Phase 3 | Guardrails, PII, security | 3 weeks | **3 days** |
| Phase 4 | Event mesh & async execution | 2 weeks | **2 days** |
| Phase 5 | MCP & API gateway integration | 2 weeks | **2 days** |
| Phase 6 | Vision, memory, model router | 2 weeks | **3 days** |
| Phase 7 | Frontend: dashboards & viewer | 4 weeks | **5 days** |
| Phase 8 | Workflow designer & debugging | 3 weeks | **4 days** |
| Phase 9 | Hardening, scale, acceptance | 3 weeks | **5 days** |
| | | | |
| **Total** | | **25 weeks (6 months)** | **~7 weeks (1.5 months)** |
| **Speedup** | | — | **3.5x faster** |

---

## Timeline Overview (AI-Assisted with Claude Code)

> **Assumption:** 1 developer + Claude Code writing all implementation code.
> Human time is spent on: design decisions, code review, integration debugging, environment setup, and testing validation.

| Phase | AI-Assisted | Traditional | Focus | Why Faster |
|-------|-------------|-------------|-------|------------|
| Phase 1 | **4 days** | 3 weeks | Foundation: agents, LLM, chat API | Scaffolding, models, FastAPI routes, agent skeletons — all boilerplate that Claude Code generates in minutes |
| Phase 2 | **3 days** | 3 weeks | Tool system & sandbox | Registry CRUD, JSON Schema validation, built-in tools — highly structured code |
| Phase 3 | **3 days** | 3 weeks | Guardrails, PII, security | Regex patterns, middleware, RBAC — well-documented patterns Claude Code handles precisely |
| Phase 4 | **2 days** | 2 weeks | Event mesh & async execution | Redis Streams integration, Celery setup, event schemas — infrastructure glue code |
| Phase 5 | **2 days** | 2 weeks | MCP & API gateway integration | HTTP clients, proxy wrappers, CRUD endpoints — repetitive integration code |
| Phase 6 | **3 days** | 2 weeks | Vision, memory, model router | LiteLLM wiring, Qdrant integration, router logic — library integration work |
| Phase 7 | **5 days** | 4 weeks | Frontend: dashboards & viewer | Next.js pages, Tailwind components, charts — Claude Code is fast at UI generation |
| Phase 8 | **4 days** | 3 weeks | Workflow designer & debugging | React Flow integration, state management — component-heavy but pattern-based |
| Phase 9 | **5 days** | 3 weeks | Hardening, scale, acceptance | **Slowest AI speedup** — load testing, K8s tuning, and debugging need real runtime |

### Summary

| Metric | Traditional (manual) | AI-Assisted (Claude Code) |
|--------|---------------------|--------------------------|
| **Total Duration** | ~25 weeks (6 months) | **~6-7 weeks (1.5 months)** |
| **Speedup** | — | **~3.5x faster** |
| **Where AI saves the most** | — | Boilerplate, CRUD, UI components, integration glue, test generation |
| **Where human time still dominates** | — | Architecture decisions, environment debugging, load testing, security review, UX polish |

### Realistic Weekly Breakdown

```
Week 1  ░░░░░░░░░░  Phase 1 (Foundation) + Phase 2 (Tools)
Week 2  ░░░░░░░░░░  Phase 3 (Guardrails/PII) + Phase 4 (Event Mesh)
Week 3  ░░░░░░░░░░  Phase 5 (MCP/Gateway) + Phase 6 (Vision/Memory/Router)
Week 4  ░░░░░░░░░░  Phase 7 — Frontend (Chat, Traces, Dashboard)
Week 5  ░░░░░░░░░░  Phase 7 contd. (Policy UI, Role views) + Phase 8 (Workflow Designer)
Week 6  ░░░░░░░░░░  Phase 8 contd. (Debugging tools) + Phase 9 (Hardening begins)
Week 7  ░░░░░░░░░░  Phase 9 contd. (Load testing, K8s, acceptance tests, final polish)
```

### Caveats

- **+1-2 weeks buffer** for: unexpected integration issues, API rate limits, Docker/K8s environment problems
- **Design review gates** between phases still recommended — AI writes fast but wrong architecture is expensive to fix
- **Security audit** (Phase 3, 9) should involve human review even if Claude Code generates the code
- Timeline assumes single developer working full-time; parallel developers could compress further
