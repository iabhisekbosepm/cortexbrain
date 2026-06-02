# PRD: CortexBrain — Auditable AI Knowledge System for Enterprise

**Author:** Product Team  
**Date:** February 10, 2026  
**Status:** Draft  
**Version:** 1.0  
**Codename:** CortexBrain  
**Foundation:** Extends [Cognee](https://github.com/topoteretes/cognee) Open Source

---

## 1. Executive Summary

CortexBrain is a B2B AI knowledge system that gives organizations a persistent, self-correcting "internal brain." Built as an extension layer on top of Cognee's open-source memory engine, CortexBrain adds three novel capabilities that Cognee and competitors lack: an **Activation-Decay Engine** (intelligent context selection that bounds token costs), a **Revision-Based Mutation Engine** (corrections become permanent with full audit trail), and a **Metacognition Layer** (confidence scoring and hallucination guardrails). The product is positioned for engineering/DevOps teams initially, with expansion into regulated verticals (healthcare, legal, finance) where auditability is a hard requirement.

**Core Promise:** *"An AI assistant for your organization that gets smarter every time someone corrects it — and you can audit every answer it gives."*

---

## 2. Problem Statement

### The Problem

Enterprise teams using LLMs for internal knowledge retrieval face three compounding failures:

1. **Statelessness Tax:** Every conversation starts from zero. When a DevOps engineer corrects the AI ("the port is 3000, not 8080"), that correction is lost the moment the session ends. The next engineer who asks the same question gets the same wrong answer. Teams report re-correcting AI assistants 15–30 times per week on the same facts.

2. **Context Cost Explosion:** Organizations with large knowledge bases (runbooks, internal docs, Slack history, code repos) resort to stuffing entire documents into LLM prompts. At enterprise scale — 50,000+ daily queries with an average of 3,150 input tokens per call — this creates a direct, linear cost problem. For a mid-size team on GPT-4o ($2.50/M input tokens), that's ~$400/month just on input tokens, scaling linearly with team size and document growth. More critically, retrieval accuracy degrades as context grows (the "Lost in the Middle" phenomenon).

3. **Accountability Gap:** When the AI gives a wrong answer that causes an outage, a bad deployment, or a compliance violation, there is no audit trail. Nobody can answer: "What data did the AI use? How confident was it? Who corrected it last?" In regulated industries, this is not just inconvenient — it's a liability.

### Evidence

- RAG systems fail in approximately 40% of cases, far below the 95%+ reliability expected in production environments (Source: Cognee/Memgraph community research, 2025).
- LLM inference costs have declined 10x annually since 2022, meaning "token savings" alone is a weakening value proposition — the differentiation must come from quality, not just cost (Source: Epoch AI, Introl 2026 analysis).
- The AI memory tools market (Mem0, Cognee, Zep/Graphiti, Letta) is growing rapidly but no player has shipped enterprise-grade auditability, confidence scoring, or permanent self-correction with version history.
- Enterprise knowledge management is a $40B+ market, with "AI-powered knowledge bases" identified as the fastest-growing sub-segment by Gartner (2025 Hype Cycle).

---

## 3. Goals & Success Metrics

### MVP Goals (Phase 1 — 6 months)

| Goal | Metric | Target | Measurement Method |
|------|--------|--------|-------------------|
| Reduce context tokens per query | Avg. input tokens per LLM call vs. naive RAG baseline | ≥50% reduction | Instrumented token counter on every API call |
| Persistent corrections work | % of corrections that persist across sessions and users | 100% (no correction loss) | Automated regression test: correct fact → new session → verify |
| Retrieval accuracy | Answer correctness on internal knowledge benchmarks (HotPotQA-style, custom) | ≥85% (vs. Cognee baseline ~70–75%) | Bi-weekly eval suite with 200+ Q&A pairs per customer |
| Audit trail completeness | % of answers that have traceable evidence chain | 100% | Every answer links to source nodes, confidence score, and version history |
| Customer adoption | Paying design partners | 10 organizations | Signed contracts / active usage |
| Time to first value | Time from deployment to first correction-that-persists | < 30 minutes | Onboarding instrumentation |

### North Star Metric

**Correction Retention Rate:** The percentage of human corrections that the system successfully applies, versions, and uses in future queries. Target: 100%.

This metric uniquely captures our differentiation: the system learns from every interaction.

---

## 4. User Personas

### Primary Persona: "Priya" — Senior DevOps Engineer

- **Role:** Lead SRE at a 200-person SaaS company. Maintains 50+ internal runbooks, incident postmortems, and infrastructure docs.
- **Goals:** Get accurate, up-to-date answers about internal systems without reading 20-page runbooks. Ensure junior engineers get correct information even when she's offline.
- **Pain Points:**
  - Corrects the AI assistant multiple times a week on the same facts (ports, configs, deployment procedures) — corrections never stick.
  - Spends 30 min/day re-explaining context that the AI should already know.
  - Worried that a junior engineer will follow wrong AI guidance and cause an outage.
- **Context of Use:** Slack integration, CLI tool, or web chat during incident response and daily operations.

### Secondary Persona: "Marcus" — VP of Engineering

- **Role:** Engineering leader responsible for 8 teams, 60 engineers. Evaluates and procures developer tools.
- **Goals:** Reduce onboarding time for new engineers. Ensure institutional knowledge doesn't leave when senior engineers do. Justify AI tool spend to CFO.
- **Pain Points:**
  - Lost 2 senior engineers last quarter — their tribal knowledge vanished overnight.
  - Current AI tools can't prove they're giving accurate answers. Concerned about liability.
  - Needs measurable ROI to justify the budget.
- **Context of Use:** Admin dashboard, usage analytics, ROI reports.

### Tertiary Persona: "Compliance Officer / CISO" (Future — Phase 2)

- **Role:** Ensures AI tools meet regulatory requirements (SOC 2, HIPAA, etc.)
- **Goals:** Full audit trail of AI decisions. Data residency compliance. Access controls.
- **Pain Points:** "I can't approve an AI tool that can't tell me where it got its answers."

---

## 5. User Stories & Requirements

### Epic 1: Knowledge Ingestion (Extending Cognee's ECL Pipeline)

#### Story 1.1: Ingest Internal Documents
**ID:** US-101  
**Priority:** Must Have

As Priya, I want to upload our internal runbooks, markdown docs, and PDFs so that the system can learn our organization's knowledge.

**Acceptance Criteria:**
- Given a set of PDF, Markdown, or plain text files, when I upload them via the API or web UI, then the system processes them through Cognee's ECL (Extract, Cognify, Load) pipeline and creates graph nodes in the Semantic Memory store.
- Given a 50-page PDF runbook, when ingestion completes, then I can query specific facts from any section within 60 seconds of upload completion.
- Given a document with conflicting information to an existing node, when ingested, then the system flags the conflict in M_meta (confidence reduced) rather than silently overwriting.

**Edge Cases:**
- Duplicate document upload: System deduplicates at the entity level, not file level. Same facts from different sources increase confidence, not node count.
- Corrupted PDF: System returns clear error with partial ingestion status (e.g., "Processed 42 of 50 pages. Pages 43–50 failed: encoding error").
- Empty or non-text file: System rejects with descriptive error.

**Dependencies:** Cognee's existing `cognee.add()` and `cognee.cognify()` pipeline.

---

#### Story 1.2: Ingest Slack/Chat Exports
**ID:** US-102  
**Priority:** Should Have

As Priya, I want to import our Slack channel exports so that tribal knowledge from conversations becomes queryable.

**Acceptance Criteria:**
- Given a Slack JSON export, when I import it, then messages are parsed into Episodic Memory (M_e) with timestamps, authors, and thread context preserved.
- Given a Slack thread where someone corrects a previous message ("Actually, the DB is on port 5433 not 5432"), when ingested, then the system treats this as a correction event and applies it to Semantic Memory.

**Edge Cases:**
- Slack messages with only emojis or reactions: Skip, do not create nodes.
- Messages with file attachments: Index the text content of supported attachments (PDF, text, code); log unsupported types.
- Private DMs included in export: Respect a configurable filter that excludes DM channels by default.

**Dependencies:** Slack export format parser (custom module). Cognee's pipeline for downstream processing.

---

#### Story 1.3: Ingest Code Repositories
**ID:** US-103  
**Priority:** Should Have

As Priya, I want to connect a Git repository so that the system understands our codebase structure, configs, and documentation comments.

**Acceptance Criteria:**
- Given a Git repo URL and access token, when I connect it, then the system parses code files using Tree-sitter into AST-based graph nodes, and indexes README/doc files through the standard text pipeline.
- Given a config file (YAML, JSON, .env), when parsed, then key-value pairs become queryable Semantic Memory nodes (e.g., `DATABASE_PORT = 5432` becomes a node).
- Given a repo update (new commit), when a webhook fires or manual sync is triggered, then only changed files are re-processed (incremental ingestion).

**Edge Cases:**
- Binary files (images, compiled assets): Skipped with log entry.
- Monorepo with 10,000+ files: Ingestion is batched with progress reporting; timeout set at 30 minutes with resumability.
- Private repo with expired token: Clear error message with re-auth instructions.

**Dependencies:** Tree-sitter parsers, Git integration module, Cognee pipeline.

---

### Epic 2: Activation-Decay Engine (Novel — Not in Cognee)

#### Story 2.1: Spreading Activation on Query
**ID:** US-201  
**Priority:** Must Have

As the system, when a user submits a query, I want to activate only the most relevant subgraph of knowledge so that the LLM receives a bounded, high-signal context window instead of a raw document dump.

**Acceptance Criteria:**
- Given a user query "What port does the auth service run on?", when the Activation Engine processes it, then it performs entity extraction → graph lookup → spreading activation (weighted BFS with dampening factor 0.5) → returns only nodes with activation score > THRESHOLD (configurable, default 30).
- Given a knowledge graph with 100,000 nodes, when a query is processed, then the active context serialized to the LLM prompt contains ≤ 2,000 tokens (regardless of total graph size), achieving O(1) context cost.
- Given two queries in the same session ("What port does auth use?" followed by "What about the database?"), when the second query fires, then previously activated nodes from the first query retain partial activation (session-aware priming), and new related nodes are also activated.

**Edge Cases:**
- Query with no matching entities in the graph: Fall back to Cognee's default vector search over M_r (Raw Memory). Log the miss for coverage analysis.
- Query that activates > 3,000 tokens of nodes: Apply top-k truncation by activation score, keeping the highest-scoring nodes within the 2,000 token budget.
- Ambiguous entity ("service" matches 15 different nodes): Use query context and session history to disambiguate; if still ambiguous, activate top 3 by confidence score and include a disambiguation prompt to the LLM.

**Dependencies:** Redis (for activation scores and TTL), Cognee's Neo4j graph (for traversal), GLiNER or equivalent for entity extraction.

---

#### Story 2.2: Decay Cycle
**ID:** US-202  
**Priority:** Must Have

As the system, I want to periodically decay activation scores so that the active context stays fresh and relevant, and old activations don't pollute future queries.

**Acceptance Criteria:**
- Given active nodes in Redis, when the decay cycle runs (every 30 seconds, configurable), then each node's activation score is decremented by DECAY_RATE (configurable, default 10 per cycle).
- Given a node whose activation score reaches 0, when the decay cycle runs, then the node is evicted from Active Memory (Redis) but remains in Passive Memory (Neo4j). No data is lost.
- Given a session that has been idle for > 5 minutes, when a new query arrives, then all session-specific activations have fully decayed, and the query starts with a clean active memory.

**Edge Cases:**
- Node is re-activated during decay: Re-activation resets the activation score to the new value; decay timer restarts.
- Redis is temporarily unavailable: Queries fall back to Cognee's standard retrieval. System logs the Redis failure and auto-reconnects.

**Dependencies:** Redis, Celery or APScheduler for background decay task.

---

### Epic 3: Revision-Based Mutation Engine (Novel — Not in Cognee)

#### Story 3.1: User Correction Persists
**ID:** US-301  
**Priority:** Must Have (Core differentiator)

As Priya, I want to correct the AI's answer ("The port is 3000, not 8080") and have that correction permanently update the knowledge base so that no one ever gets the wrong answer again.

**Acceptance Criteria:**
- Given the AI answers "The auth service runs on port 8080" and Priya responds "No, it's port 3000", when the Mutation Engine processes this correction, then:
  1. **Locate:** The node `AuthService.port = 8080` is identified in M_s.
  2. **Version:** The current state `{port: 8080, source: "runbook-v2.pdf", confidence: 0.85}` is archived as a history edge: `(N_port)-[:PREVIOUS_VERSION]->(N_port_v1)`.
  3. **Mutate:** The node is updated in-place: `{port: 3000, source: "user:priya", confidence: 0.95}`.
  4. **Meta-Update:** The confidence of the original source ("runbook-v2.pdf") is downgraded by 0.1 for future retrievals from that source. The node is flagged as `volatile: true` (has been corrected).
- Given the correction has been applied, when any user asks "What port does auth run on?" in a new session, then the system answers "3000" with a confidence score visible in the response.

**Edge Cases:**
- Conflicting corrections: User A says "port is 3000", User B says "port is 4000". System creates a conflict record, flags the node as `conflicted: true`, and surfaces both versions to the next querier with a note: "There are conflicting corrections for this fact."
- Correction to a non-existent node: System creates a new node from the correction, with source tagged as the correcting user, and confidence set to 0.7 (lower than document-sourced nodes).
- Correction via natural language that is ambiguous ("No, that's wrong"): System asks a clarifying follow-up: "What specifically should I update? Please provide the correct information."
- Rapid sequential corrections to the same node (user refining): Each creates a version entry, but only the latest is active. Version history is fully traversable.

**Dependencies:** Neo4j (versioning via history edges), M_meta store, correction detection classifier (LLM-based intent detection).

---

#### Story 3.2: Audit Trail for Every Mutation
**ID:** US-302  
**Priority:** Must Have

As Marcus, I want to see a complete history of every change to every fact in the system so that I can audit what changed, when, and who changed it.

**Acceptance Criteria:**
- Given any node in M_s, when I query its history via the API (`GET /api/v1/nodes/{node_id}/history`), then I receive an ordered list of all versions: `[{version: 2, value: "3000", changed_by: "user:priya", timestamp: "2026-03-15T14:32:00Z", reason: "user_correction"}, {version: 1, value: "8080", changed_by: "system:ingestion", timestamp: "2026-03-01T09:00:00Z", source: "runbook-v2.pdf"}]`.
- Given the admin dashboard, when Marcus views the "Recent Mutations" feed, then he sees a reverse-chronological list of all corrections and ingestion events with filters by user, date range, and node type.
- Given a compliance export request, when Marcus triggers an audit export, then the system generates a CSV/JSON of all mutations within a specified date range, suitable for SOC 2 or internal audit review.

**Edge Cases:**
- Node with 1000+ versions (very frequently corrected): Paginated API response. Dashboard shows latest 50 with "load more."
- Deleted node: Soft-delete only. Node marked as `status: archived` but version history is fully retained.
- System-generated mutations (e.g., confidence decay from consolidation): Tagged as `changed_by: "system:consolidation"` to distinguish from human corrections.

**Dependencies:** Neo4j history edges, PostgreSQL for audit log indexing, Admin API.

---

### Epic 4: Metacognition Layer (Novel — Not in Cognee)

#### Story 4.1: Confidence-Gated Responses
**ID:** US-401  
**Priority:** Must Have

As Priya, I want the AI to tell me when it's not sure about an answer so that I don't blindly trust a wrong response during an incident.

**Acceptance Criteria:**
- Given a query where the best matching node has a confidence score C ≥ 0.8, when the system responds, then it returns the answer normally with a confidence indicator (e.g., `confidence: high`).
- Given a query where the best matching node has 0.5 ≤ C < 0.8, when the system responds, then it prepends a qualifier: "I have moderate confidence in this — the information may need verification." and includes the source(s).
- Given a query where the best matching node has C < 0.5 or the node is flagged `conflicted: true`, when the system responds, then it explicitly says: "I have conflicting or low-confidence data about this. Here's what I have from different sources: [source A says X, source B says Y]. You may want to verify."
- Given a query with no matching nodes at all, when the system responds, then it says: "I don't have information about this in our knowledge base" rather than hallucinating.

**Edge Cases:**
- Multiple nodes match with varying confidence: Weighted average of confidence scores for the response, but individual source confidences are available via API.
- User asks a question that mixes high-confidence and low-confidence facts: Response segments are independently confidence-tagged.
- Confidence threshold is configurable per organization (some teams want stricter guardrails).

**Dependencies:** M_meta confidence scores, LLM prompt engineering for response formatting.

---

#### Story 4.2: Salience Scoring
**ID:** US-402  
**Priority:** Should Have

As the system, I want to calculate a salience score for every knowledge node so that the most important and frequently-used facts are prioritized during activation and consolidation.

**Acceptance Criteria:**
- Given a knowledge node, when its salience is calculated, then the score is: `Salience = (access_frequency × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)`, where each factor is normalized to [0, 1].
- Given two nodes activated for the same query, when the token budget forces truncation, then the higher-salience node is retained.
- Given the weekly consolidation job, when it runs, then low-salience nodes (bottom 10%) that haven't been accessed in 90+ days are candidates for archival (moved from Semantic to Raw memory).

**Edge Cases:**
- Brand new node with no access history: Default salience of 0.5 for 7 days (grace period), then calculated normally.
- Node with extremely high correction count: Salience is high (it's important), but confidence may be low (it's contentious). These two signals are independent.

**Dependencies:** Access logging, M_meta, Celery batch job.

---

### Epic 5: Query & Response Interface

#### Story 5.1: Natural Language Query with Source Attribution
**ID:** US-501  
**Priority:** Must Have

As Priya, I want to ask a question in natural language and get an answer that cites its sources so that I can verify the information if needed.

**Acceptance Criteria:**
- Given a query "How do I restart the payment service?", when the system responds, then the answer includes inline source references: "According to [runbook-payments-v3.pdf, section 4.2] and a correction by @priya on March 15, you should..."
- Given the response, when I click/expand a source reference, then I see the original text chunk from M_r and the node details from M_s including confidence and version count.
- Given a query, when the full pipeline executes (entity extraction → activation → serialization → LLM call → response formatting), then end-to-end latency is ≤ 3 seconds for p95.

**Edge Cases:**
- Answer synthesized from 5+ sources: Top 3 most relevant sources cited inline; remaining available via "more sources" expansion.
- Source document has been updated since the node was created: Source reference includes a staleness warning if the source file's hash has changed.

**Dependencies:** Activation Engine, LLM API (Claude Sonnet / GPT-4o), response formatter.

---

#### Story 5.2: REST API for Integration
**ID:** US-502  
**Priority:** Must Have

As a developer integrating CortexBrain into our Slack bot, I want a clean REST API so that I can send queries and receive structured responses programmatically.

**Acceptance Criteria:**
- `POST /api/v1/query` accepts `{query: string, session_id?: string, user_id: string}` and returns `{answer: string, confidence: float, sources: [{node_id, source_name, confidence}], tokens_used: {input: int, output: int}}`.
- `POST /api/v1/correct` accepts `{node_id: string, corrected_value: any, user_id: string, reason?: string}` and returns `{status: "applied", version: int, previous_value: any}`.
- `GET /api/v1/nodes/{node_id}/history` returns the full version history.
- `GET /api/v1/health` returns system status including Redis, Neo4j, Qdrant, and LLM API connectivity.
- All endpoints require Bearer token authentication.
- All endpoints return responses within SLA (query: ≤3s p95, correct: ≤1s p95, history: ≤500ms p95).

**Edge Cases:**
- Invalid session_id: Create new session silently, log warning.
- Rate limiting: 100 queries/minute per organization (configurable). Return 429 with retry-after header.
- LLM API timeout: Return partial response from memory with `{fallback: true}` flag, or 503 with clear error.

**Dependencies:** FastAPI, Auth middleware, all backend services.

---

### Epic 6: Admin Dashboard

#### Story 6.1: Organization Knowledge Health Dashboard
**ID:** US-601  
**Priority:** Should Have

As Marcus, I want a dashboard showing the health and usage of our organizational brain so that I can justify the investment and identify gaps.

**Acceptance Criteria:**
- Dashboard shows: total knowledge nodes, nodes by source type (document, user correction, code), total queries this period, average confidence of responses, top 10 most-queried topics, top 10 lowest-confidence topics (knowledge gaps), correction activity (who, what, when), token usage and estimated cost savings vs. naive RAG.
- Given the cost savings widget, when Marcus views it, then it shows: "This month: 145,000 queries. Avg tokens/query with CortexBrain: 1,200. Estimated tokens/query with standard RAG: 3,500. Estimated savings: $X."
- Dashboard updates in real-time (WebSocket) or near-real-time (30s polling).

**Edge Cases:**
- Organization with < 100 queries: Show "not enough data yet" for statistical widgets.
- Dashboard for multiple teams within one org: Filterable by team/project.

**Dependencies:** PostgreSQL analytics tables, React frontend, WebSocket or polling.

---

## 6. Scope

### In Scope (MVP — Phase 1)

- Document ingestion (PDF, Markdown, plain text) via Cognee's ECL pipeline
- Slack export ingestion (JSON format)
- Git repository ingestion (with Tree-sitter for code, standard pipeline for docs)
- Semantic Memory (M_s) in Neo4j — extended with version history edges
- Active Memory (M_a) in Redis — with activation scores and TTL
- Raw Memory (M_r) in Qdrant — via Cognee's existing vector store
- Meta Memory (M_meta) — confidence, salience, volatility as node properties + PostgreSQL
- Spreading Activation algorithm (weighted BFS with configurable threshold and dampening)
- Decay Cycle (background worker, configurable rate)
- Revision-Based Mutation (Locate → Version → Mutate → Meta-Update)
- Confidence-gated responses (high/medium/low/conflict)
- Source attribution in every response
- Full audit trail for all mutations
- REST API (query, correct, history, health)
- Admin dashboard (usage, health, cost savings, mutation log)
- Multi-tenant architecture (organization isolation)
- Bearer token authentication

### Out of Scope (MVP)

- Real-time Slack/Teams integration (Phase 2 — requires bot framework and OAuth)
- Audio/video ingestion via Whisper (Phase 2 — adds infra complexity without core value)
- Image/diagram understanding via ColPali (Phase 2)
- On-premise / VPC deployment (Phase 2 — required for regulated verticals)
- Episodic Memory as a separate time-series graph (MVP uses simplified timestamp properties on M_s nodes)
- Consolidation "Sleep" cycle (Phase 2 — requires usage data to calibrate)
- SSO / SAML (Phase 2 — required for enterprise)
- Role-based access control within organizations (Phase 2 — MVP has org-level access only)
- Custom LLM model support (MVP supports Claude Sonnet + GPT-4o; extensible later)
- Web UI for querying (MVP is API-first; web UI is Phase 2)

### Future Considerations (Phase 2+)

- Slack/Teams real-time bot integration
- "Consolidation" batch job (compress episodic → semantic memory)
- On-prem deployment with Helm charts for regulated industries
- SOC 2 Type II certification
- Fine-tuned small model for entity extraction (replace GLiNER for domain-specific accuracy)
- Multi-modal ingestion (images, audio, video)
- Conflict resolution workflows (assign conflicting facts to a human reviewer)

---

## 7. Technical Considerations

### Architecture Overview

CortexBrain is an **extension layer** on top of Cognee, not a fork. We contribute upstream where possible and maintain our proprietary modules as separate packages.

```
┌─────────────────────────────────────────────────────┐
│                  CortexBrain Layer                   │
│  ┌──────────────┬──────────────┬──────────────────┐  │
│  │  Activation   │   Mutation   │  Metacognition   │  │
│  │  Engine       │   Engine     │  Layer           │  │
│  └──────┬───────┴──────┬───────┴────────┬─────────┘  │
│         │              │                │            │
│  ┌──────▼──────────────▼────────────────▼─────────┐  │
│  │            Orchestrator (FastAPI)               │  │
│  └──────────────────┬──────────────────────────────┘  │
│                     │                                │
├─────────────────────▼────────────────────────────────┤
│                  Cognee OSS Layer                     │
│  ┌──────────────┬──────────────┬──────────────────┐  │
│  │  ECL Pipeline │  Graph Store │  Vector Store    │  │
│  │  (Ingestion)  │  (Neo4j)     │  (Qdrant)        │  │
│  └──────────────┴──────────────┴──────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Foundation | Cognee OSS (latest stable) | Proven ECL pipeline, graph + vector store integration, active community |
| Language | Python 3.12 | Cognee is Python; ecosystem fit for ML/graph |
| API Framework | FastAPI | Async, typed, OpenAPI spec auto-generated |
| Active Memory | Redis 7+ | TTL, sorted sets for activation scores, sub-ms reads |
| Semantic Graph | Neo4j 5.x (via Cognee) | Already Cognee's default; Cypher for traversal |
| Vector Store | Qdrant (via Cognee) | Already Cognee's default; embeddings for fallback retrieval |
| Meta Store | PostgreSQL 16 | Audit logs, analytics, structured metadata |
| Embeddings | OpenAI text-embedding-3-small | Cognee default; proven reliable, cost-effective |
| Entity Extraction | GLiNER | Lightweight SLM, no GPU required, fast |
| LLM (Reasoning) | Claude Sonnet 4.5 (primary), GPT-4o (fallback) | Abstraction layer allows swapping |
| Background Jobs | Celery + Redis | Decay cycles, consolidation, batch ingestion |
| Containerization | Docker Compose (dev), Docker (prod) | Standard; K8s Helm charts in Phase 2 |
| Admin Frontend | React + Tailwind | Dashboard only; lightweight |
| Auth | API keys (MVP), JWT | SSO/SAML in Phase 2 |

### Dependencies

| Dependency | Type | Owner | Status |
|------------|------|-------|--------|
| Cognee OSS (v0.x) | Hard | Cognee / topoteretes | Active, MIT licensed |
| Neo4j 5.x | Hard | Neo4j Inc. | Stable, Community Edition (free) for MVP |
| Redis 7+ | Hard | Redis Ltd. | Stable, open source |
| Qdrant | Hard | Qdrant | Stable, open source |
| PostgreSQL 16 | Hard | PostgreSQL Global Dev Group | Stable |
| OpenAI Embedding API | Soft | OpenAI | Can swap to local model |
| Claude API / GPT-4o API | Hard | Anthropic / OpenAI | Abstracted behind provider interface |
| GLiNER | Soft | GLiNER project | Can swap to spaCy NER or fine-tuned model |

### Performance Requirements

- Query end-to-end latency: ≤ 3 seconds (p95)
- Correction application: ≤ 1 second (p95)
- Ingestion throughput: ≥ 100 pages/minute for document ingestion
- Activation engine: Subgraph selection ≤ 200ms (p95) for graphs up to 500k nodes
- Decay cycle: Processes all active nodes in ≤ 100ms per cycle
- API availability: 99.5% uptime (MVP SLA)
- Concurrent users per org: ≥ 50 simultaneous queries

### Security Considerations

- All data is tenant-isolated (org-level). No cross-tenant data access is possible at the database level (separate Neo4j databases or label-based isolation).
- API keys are hashed (bcrypt) at rest. Never logged or exposed in error messages.
- All external API calls (LLM providers) use TLS 1.3.
- User-submitted corrections are sanitized for injection attacks (Cypher injection, prompt injection).
- Prompt injection defense: User input is wrapped in clear delimiters in the LLM prompt; system prompt includes instruction to ignore conflicting instructions from context.
- PII detection: Optional module (Phase 2) scans ingested content for PII and flags for review before graph storage.

---

## 8. Timeline & Milestones

| Milestone | Target Date | Dependencies | Deliverable |
|-----------|-------------|--------------|-------------|
| M0: Cognee integration validated | Week 2 | Cognee OSS stable release | Fork/extend running locally, ECL pipeline ingesting docs into Neo4j + Qdrant |
| M1: Memory Substrate operational | Week 4 | Neo4j, Redis, PostgreSQL provisioned | All 4 memory stores (M_a, M_s, M_r, M_meta) with CRUD APIs |
| M2: Activation Engine v1 | Week 6 | M1 complete | Spreading activation + decay cycle working; queries return bounded context |
| M3: Mutation Engine v1 | Week 8 | M1, M2 complete | Corrections persist with version history; audit trail API functional |
| M4: Metacognition Layer v1 | Week 10 | M1, M3 complete | Confidence-gated responses; source attribution in every answer |
| M5: API & Integration complete | Week 12 | M2, M3, M4 complete | Full REST API (query, correct, history, health) with auth |
| M6: Admin Dashboard v1 | Week 14 | M5, PostgreSQL analytics | Dashboard with usage, health, cost savings, mutation log |
| M7: Internal dogfood | Week 16 | M6 complete | Team uses CortexBrain on our own docs for 2 weeks |
| M8: Design Partner Alpha | Week 18 | M7 complete, bugs fixed | 3 design partner organizations onboarded |
| M9: Beta launch | Week 24 | Alpha feedback incorporated | 10 paying organizations, public API docs |

---

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cognee OSS introduces breaking changes | Medium | High | Pin to specific version. Maintain thin abstraction layer. Contribute fixes upstream. Have fallback plan to fork if necessary. |
| Activation-Decay thresholds are wrong (too aggressive = missing context; too conservative = no savings) | High | Medium | Ship with configurable thresholds per org. Run A/B tests in alpha. Default to conservative (higher token budget) and tighten over time. |
| Correction detection is inaccurate (false positives mutate good data; false negatives miss corrections) | Medium | High | Require explicit confirmation for mutations in v1 ("Did you mean to correct this fact? [Yes/No]"). Log all attempted corrections for analysis. Build confidence in the classifier before enabling auto-correction. |
| Entity resolution / deduplication fails (duplicate nodes for same concept) | High | Medium | Use Cognee's existing dedup + add fuzzy matching layer. Accept some duplication in MVP; build merge tooling in Phase 2. |
| LLM API cost for mutation detection + response generation exceeds budget | Medium | Medium | Use GLiNER (free, local) for entity extraction. Use smaller/cheaper LLM for correction classification. Reserve expensive model (Claude Sonnet) for final response generation only. |
| Neo4j Community Edition limitations at scale | Low | High | Community Edition supports up to ~34B nodes (sufficient for MVP). Monitor graph size. Plan Neo4j Enterprise or AuraDB migration path for Phase 2. |
| Competitor (Cognee, Mem0) ships audit trail and metacognition features | Medium | High | Speed. Ship MVP in 24 weeks. Our advantage is focus: we're not building a general memory framework, we're building an auditable enterprise brain. Vertical focus beats horizontal breadth. |
| Prompt injection via ingested documents or user corrections | Medium | High | Sanitize all user input. Use delimited context injection in LLM prompts. Add prompt injection detection classifier (Phase 2). In MVP, log all LLM inputs for manual review. |

---

## 10. Open Questions

| # | Question | Owner | Due Date | Status |
|---|----------|-------|----------|--------|
| 1 | What is the optimal activation threshold and decay rate? Need empirical data from real usage. | Engineering | M7 (Dogfood) | Open |
| 2 | Should corrections require explicit confirmation in v1, or can we auto-detect with high-enough precision? | Product + Engineering | M3 | Open |
| 3 | What is Cognee's roadmap for features that overlap with ours (audit trail, confidence)? Should we co-develop or differentiate? | Product | Week 4 | Open |
| 4 | Which LLM should be default? Claude Sonnet is higher quality but Anthropic's API has different caching semantics vs. OpenAI. Need latency + cost comparison for our specific prompt patterns. | Engineering | M2 | Open |
| 5 | Multi-tenant isolation strategy: separate Neo4j databases per org, or label-based isolation in a shared instance? Former is safer, latter is cheaper. | Engineering + Security | M1 | Open |
| 6 | Pricing model validation: $500/$2,500/$10k tiers based on nodes + seats. Need customer development interviews to validate willingness-to-pay. | Product + Business | M8 (Alpha) | Open |
| 7 | Do we need SOC 2 Type I before selling to enterprise design partners, or can we start with a security questionnaire? | Business + Legal | Week 6 | Open |
| 8 | How do we handle the "bootstrapping problem" — new org with empty brain? Pre-loaded templates? Guided onboarding? | Product + Design | M6 | Open |
| 9 | What happens when Cognee's default embedding model (OpenAI) is unavailable? Do we need a local fallback? | Engineering | M5 | Open |
| 10 | Legal review: Can we use Cognee OSS (MIT license) in a commercial B2B product without restriction? | Legal | Week 2 | Open |

---

## Appendix

### A. Key Equations (from MFCA Paper)

**Core function:** `y = f(x, Mₐ)` — LLM is stateless; Active Memory is the input.

**Learning definition:** `Learning ⟺ S(t₁) ≠ S(t₂)` — The system has learned if its memory substrate has changed.

**Activation spread:** `neighbor_activation = source_activation × edge_weight × 0.5`

**Salience:** `S = (access_freq × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)`

**Confidence thresholds:** High ≥ 0.8, Medium ≥ 0.5, Low < 0.5

### B. Competitive Landscape Summary

| Competitor | Strength | Our Differentiation |
|------------|----------|---------------------|
| Cognee OSS | Best open-source memory engine; graph + vector; ECL pipeline | We extend it. Our novel layers (activation, mutation, metacognition) sit on top. |
| Mem0 | Production SaaS; low latency (1.44s); graph memory option | No audit trail. No confidence scoring. No persistent corrections with versioning. |
| Zep / Graphiti | Temporal knowledge graphs; enterprise focus | Research-led, immature SaaS. No self-correction mechanism. |
| Letta (MemGPT) | Open-source agent memory; active community | Agent-focused, not knowledge-base-focused. No enterprise features. |

### C. Pricing Model (Draft — Requires Validation)

| Tier | Knowledge Nodes | Seats | API Calls/month | Price |
|------|----------------|-------|-----------------|-------|
| Starter | Up to 10,000 | 5 | 50,000 | $500/mo |
| Team | Up to 100,000 | 25 | 500,000 | $2,500/mo |
| Enterprise | Unlimited | Unlimited | Unlimited | $10,000+/mo (custom) |

Enterprise tier includes: dedicated instance, audit export, priority support, custom SLA, on-prem option (Phase 2).

### D. Token Savings Model (ROI Calculator Input)

Assumptions for a mid-size engineering team (30 engineers, 5,000 queries/month):

| Metric | Standard RAG | CortexBrain (Projected) |
|--------|-------------|------------------------|
| Avg. input tokens/query | 3,500 | 1,200 |
| Monthly input tokens | 17.5M | 6M |
| Cost at GPT-4o ($2.50/M) | $43.75/mo | $15.00/mo |
| Cost at Claude Sonnet ($3/M) | $52.50/mo | $18.00/mo |
| Token savings | — | ~65% |
| Accuracy (est.) | 60–70% | 85%+ |
| Correction persistence | None | Permanent |
| Audit trail | None | Full |

**Note:** Token savings alone are modest in dollar terms at this scale. The primary value drivers are accuracy improvement, correction persistence, and auditability — which prevent costly incidents, reduce repeated work, and enable compliance. The token savings narrative is a supporting proof point, not the lead pitch.
