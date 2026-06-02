# CortexBrain — Project Idea

**Auditable AI Knowledge System for Enterprise**
**Codename:** CortexBrain
**Foundation:** Extends [Cognee](https://github.com/topoteretes/cognee) Open Source
**Date:** February 2026
**CortexBrain Dataset:** `projectidea` (ID: `55cac41b-4591-5dc0-8ad6-b70e91b1fea4`)

---

## Core Promise

> "An AI assistant for your organization that gets smarter every time someone corrects it — and you can audit every answer it gives."

CortexBrain is a B2B AI knowledge system that gives organizations a persistent, self-correcting "internal brain." It targets engineering/DevOps teams initially, with expansion into regulated verticals (healthcare, legal, finance) where auditability is a hard requirement.

---

## Problem Statement

Enterprise teams using LLMs for internal knowledge retrieval face three compounding failures:

1. **Statelessness Tax** — Every conversation starts from zero. Corrections are lost between sessions. Teams re-correct AI assistants 15-30 times per week on the same facts.

2. **Context Cost Explosion** — Large knowledge bases stuffed into LLM prompts create linear cost scaling. At enterprise scale (50,000+ daily queries, ~3,150 input tokens/call), this creates significant cost and accuracy degradation ("Lost in the Middle" phenomenon).

3. **Accountability Gap** — No audit trail when AI gives wrong answers causing outages, bad deployments, or compliance violations. Nobody can answer: "What data did the AI use? How confident was it? Who corrected it last?"

---

## Three Novel Engines (Not in Cognee)

### 1. Activation-Decay Engine
Intelligent context selection that bounds token costs. Selects only the most relevant subgraph for LLM context, achieving **O(1) context cost** regardless of graph size.

- **Spreading Activation:** `neighbor_activation = source_activation x edge_weight x 0.5`
- **Threshold:** 30 (configurable), Max context: 2,000 tokens
- **Decay Cycle:** Every 30s, decrement by DECAY_RATE (10). Evict at 0 from Redis.
- **Session-aware:** Previously activated nodes retain partial activation across queries.

### 2. Revision-Based Mutation Engine
Corrections become permanent with full audit trail. Every fact change is versioned.

- **Pipeline:** Locate -> Version -> Mutate -> Meta-Update
- **Versioning:** Creates `PREVIOUS_VERSION` edges in Neo4j
- **Conflict Detection:** Flags conflicting corrections from different users
- **Audit Trail:** Complete history via `GET /api/v1/nodes/{node_id}/history`

### 3. Metacognition Layer
Confidence scoring and hallucination guardrails.

- **Confidence Gating:** High (>= 0.8), Medium (>= 0.5), Low (< 0.5), Conflicted (flagged)
- **Salience Scoring:** `S = (access_freq x 0.4) + (recency x 0.3) + (correction_count x 0.2) + (edge_count x 0.1)`
- **Guardrails:** System says "I don't know" instead of hallucinating when no matching nodes exist

---

## MFCA Memory Model — Four Substrates

| Substrate | Store | Purpose |
|-----------|-------|---------|
| **M_a** (Active) | Redis 7+ | Session-scoped activation scores with TTL and decay |
| **M_s** (Semantic) | Neo4j 5.x | Knowledge graph with version history edges |
| **M_r** (Raw) | LanceDB (via Cognee) | Vector embeddings for fallback retrieval |
| **M_meta** (Meta) | PostgreSQL 16 | Audit logs, confidence, salience, volatility |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Foundation | Cognee OSS (pip dependency, NOT a fork) |
| Language | Python 3.12 |
| API | FastAPI (async, typed, OpenAPI) |
| Active Memory | Redis 7+ (sorted sets, TTL) |
| Semantic Graph | Neo4j 5.x (Cypher traversal) |
| Vector Store | LanceDB (via Cognee) |
| Meta Store | PostgreSQL 16 |
| Embeddings | OpenAI text-embedding-3-small |
| Entity Extraction | GLiNER (lightweight, no GPU) |
| LLM | Gemini 2.0 Flash (primary), Claude Sonnet 4.5, GPT-4o |
| Background Jobs | Celery + Redis |
| Frontend | Next.js 16 + Tailwind v4 |
| Auth | API keys (MVP), JWT planned |

---

## REST API

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/query` | Natural language query with activation-based context |
| `POST /api/v1/correct` | Submit versioned correction |
| `GET /api/v1/nodes/{id}/history` | Full audit trail |
| `GET /api/v1/health` | All service health checks |
| `POST /api/v1/ingest` | Document upload via Cognee ECL |
| `POST /api/v1/ingest/text` | Text ingestion for MCP/CLI |
| `GET /api/v1/datasets` | List all knowledge sources |
| `GET /api/v1/datasets/{name}/data` | Browse data items in a dataset |

## MCP Tools (Claude Code Integration)

| Tool | Purpose |
|------|---------|
| `cortexbrain_query` | Semantic search with confidence scoring |
| `cortexbrain_remember` | Store knowledge persistently |
| `cortexbrain_correct` | Versioned corrections |
| `cortexbrain_search_sources` | Browse datasets and data items |
| `cortexbrain_health` | System health check |

---

## User Personas

**Priya** (Senior DevOps Engineer) — Needs accurate answers from runbooks, wants corrections to stick, worried about junior engineers getting wrong info during incidents.

**Marcus** (VP Engineering) — Needs to reduce onboarding time, preserve institutional knowledge when senior engineers leave, justify AI spend with ROI metrics.

**Compliance Officer** (Future) — Needs full audit trail, data residency, access controls for SOC 2/HIPAA compliance.

---

## Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| Context token reduction vs naive RAG | >= 50% |
| Correction persistence across sessions | 100% |
| Retrieval accuracy | >= 85% (vs Cognee baseline ~70-75%) |
| Audit trail completeness | 100% |
| Query latency (p95) | <= 3 seconds |
| Correction application (p95) | <= 1 second |
| Design partner adoption | 10 organizations |

**North Star Metric:** Correction Retention Rate — the percentage of human corrections that persist and improve future queries. Target: 100%.

---

## Competitive Differentiation

| Competitor | Their Strength | CortexBrain Edge |
|------------|---------------|-----------------|
| Cognee OSS | Best open-source memory engine | We extend it with activation, mutation, metacognition |
| Mem0 | Production SaaS, low latency | No audit trail, no confidence scoring, no versioned corrections |
| Zep / Graphiti | Temporal knowledge graphs | Research-led, immature SaaS, no self-correction |
| Letta (MemGPT) | Open-source agent memory | Agent-focused, not knowledge-base-focused, no enterprise features |

---

## Pricing (Draft)

| Tier | Nodes | Seats | API Calls/mo | Price |
|------|-------|-------|-------------|-------|
| Starter | 10,000 | 5 | 50,000 | $500/mo |
| Team | 100,000 | 25 | 500,000 | $2,500/mo |
| Enterprise | Unlimited | Unlimited | Unlimited | $10,000+/mo |

---

## Phase 2 Roadmap

- Real-time Slack/Teams bot integration
- Consolidation batch job (episodic -> semantic memory)
- On-prem deployment with Helm charts
- SOC 2 Type II certification
- Multi-modal ingestion (images, audio, video)
- Conflict resolution workflows
- SSO/SAML authentication
- Fine-tuned entity extraction model
- ColPali for image/diagram understanding
- Custom LLM model support

---

*This document is stored in CortexBrain's knowledge graph under dataset `projectidea` with 299 knowledge nodes and 2,132 tokens. Query it anytime via `cortexbrain_query` or browse via `cortexbrain_search_sources(dataset_name="projectidea")`.*
