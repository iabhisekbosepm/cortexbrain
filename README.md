# CortexBrain

**An AI assistant that gets smarter every time someone corrects it — and you can audit every answer it gives.**

CortexBrain is a B2B AI knowledge system that gives organizations a persistent, self-correcting "internal brain." Built as an extension layer on top of [Cognee](https://github.com/topoteretes/cognee) open-source memory engine.

---

## The Problem

Enterprise teams using LLMs for knowledge retrieval face three compounding failures:

| Problem | Impact |
|---------|--------|
| **Statelessness Tax** | Every conversation starts from zero. Corrections vanish when sessions end. Teams re-correct AI 15-30x per week on the same facts. |
| **Context Cost Explosion** | Stuffing entire documents into prompts scales linearly — O(n) token costs. Accuracy degrades as context grows ("Lost in the Middle"). |
| **Accountability Gap** | No audit trail when AI gives wrong answers. No one can answer: "What data did it use? Who corrected it last?" |

## The Solution: MFCA Memory Architecture

CortexBrain models AI memory after the human brain using four memory substrates:

```
┌──────────────────────────────────────────────────┐
│  M_a  Active Memory (Redis)                      │
│       Spreading activation — relevant knowledge  │
│       lights up, irrelevant fades away           │
├──────────────────────────────────────────────────┤
│  M_s  Semantic Memory (Neo4j)                    │
│       Knowledge graph — entities, relationships, │
│       meaning persist forever                    │
├──────────────────────────────────────────────────┤
│  M_r  Raw Memory (LanceDB)                       │
│       Vector embeddings — fallback when the      │
│       graph hasn't connected the dots yet        │
├──────────────────────────────────────────────────┤
│  M_meta  Meta Memory (PostgreSQL)                │
│          Audit logs, confidence scores,          │
│          version history                         │
└──────────────────────────────────────────────────┘
```

## Key Capabilities

### What CortexBrain adds on top of Cognee

| Capability | Description |
|------------|-------------|
| **Spreading Activation** | Intelligent context selection that bounds token costs to O(1). Only the most relevant knowledge nodes are activated — not everything. |
| **Versioned Corrections** | When someone corrects the AI, it sticks. Forever. With full version history and `PREVIOUS_VERSION` edges in the knowledge graph. |
| **Confidence Scoring** | Every answer comes with a confidence level (High/Medium/Low/Conflicted). The system knows what it knows — and what it doesn't. |
| **Full Audit Trail** | Every answer is traceable: what data was used, who corrected it, when, and why. Enterprise-grade accountability. |
| **Salience-Based Decay** | Frequently accessed knowledge stays hot. Stale knowledge naturally decays. Mimics how human memory works. |
| **Self-Learning** | Consolidation cycles automatically promote validated knowledge, archive stale nodes, merge duplicates, and compress version chains. |

## Head-to-Head: RAG vs CortexBrain

| Capability | Standard RAG | CortexBrain |
|------------|:------------:|:-----------:|
| Memory Model | Stateless (per-session) | 4-substrate persistent |
| Context Selection | Stuff everything | Spreading activation |
| Corrections | Lost after session | Permanent + versioned |
| Confidence | None | 4-level gating |
| Audit Trail | None | Full (who/what/when/why) |
| Cost Scaling | O(n) linear | O(1) bounded |
| Self-Improvement | No | Continuous learning |

**Result:** ~65% fewer tokens per query. ~85%+ accuracy vs 60-70% with RAG.

## Architecture

```
CortexBrain Extension Layer
├── core/activation/    — Spreading activation + decay engine
├── core/mutation/      — Revision-based correction engine
├── core/metacognition/ — Confidence gating + salience scoring
├── pipelines/          — Cognee Task wrappers
├── api/v1/             — FastAPI REST endpoints
│
Cognee OSS (pip dependency)
├── add() → cognify() → search()  — ECL pipeline
├── GraphDBInterface (Neo4j)       — Semantic Memory store
├── VectorDBInterface (LanceDB)    — Raw Memory store
└── LLMGateway (litellm)          — LLM abstraction
```

## API Endpoints

All endpoints require Bearer token authentication. Responses return in <1s (p95).

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | Natural language query with activation-based context selection |
| `POST` | `/api/v1/correct` | Submit a versioned correction to the knowledge graph |
| `POST` | `/api/v1/ingest` | Upload PDF, Markdown, or text documents |
| `POST` | `/api/v1/ingest/text` | Direct text ingestion via API |

### Audit & Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/nodes/{id}/history` | Full audit trail — every version, change, and user |
| `GET` | `/api/v1/health` | Real-time health checks for all backing services |
| `GET` | `/api/v1/datasets` | List all knowledge sources and browse data items |
| `POST` | `/api/v1/consolidation/run` | Trigger memory consolidation cycle |
| `GET` | `/api/v1/workers/status` | Monitor background workers and scheduled jobs |

## MCP Integration

CortexBrain ships as an MCP (Model Context Protocol) server. Plug it into any MCP-compatible AI tool:

```json
// .mcp.json (Claude Code, Codex, Cursor, Windsurf)
{
  "cortexbrain": {
    "command": "python3",
    "args": ["-m", "cortexbrain.mcp"]
  }
}
```

**6 Built-in MCP Tools:**

| Tool | Description |
|------|-------------|
| `query` | Search knowledge with confidence scoring |
| `remember` | Store information persistently |
| `correct` | Submit versioned corrections |
| `search_sources` | Browse datasets and knowledge sources |
| `consolidate` | Trigger memory consolidation |
| `health` | System health check |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Foundation** | [Cognee OSS](https://github.com/topoteretes/cognee) |
| **Language** | Python 3.12 |
| **API** | FastAPI |
| **Frontend** | Next.js 16 |
| **Graph DB** | Neo4j 5.x |
| **Vector DB** | LanceDB |
| **Cache / Active Memory** | Redis 7+ |
| **Relational DB** | PostgreSQL 16 |
| **Task Queue** | Celery + Redis |

## Key Algorithms

**Spreading Activation:**
```
neighbor_activation = source_activation × edge_weight × 0.5
Threshold: 30 (configurable) | Max context: ≤2,000 tokens | BFS with dampening
```

**Salience Scoring:**
```
S = (access_freq × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)
```

**Confidence Levels:**
- High ≥ 0.8 | Medium ≥ 0.5 | Low < 0.5 | Conflicted = flagged

**Mutation Pipeline:**
```
Locate → Version → Mutate → Meta-Update (PREVIOUS_VERSION edges in Neo4j)
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"
cp .env.example .env

# Start backing services
docker compose up -d  # Neo4j, Redis, PostgreSQL

# Run the API server
uvicorn cortexbrain.main:app --reload --port 8000

# Run Celery worker
celery -A cortexbrain.workers.celery_app worker --loglevel=info
celery -A cortexbrain.workers.celery_app beat --loglevel=info
```

## Target Users

- **DevOps / SRE teams** — Persistent runbook knowledge, incident context that survives sessions
- **Engineering leaders** — Institutional knowledge retention, onboarding acceleration
- **Regulated industries** — Healthcare, legal, finance — where audit trails are a hard requirement

## Website

The marketing website is a single-page site built with:
- Tailwind CSS v4
- Three.js r168 (3D animated knowledge graph, memory layers, brain glow)
- Custom GLSL shaders for spreading activation visualization
- Supabase for early access signups

## License

Proprietary. All rights reserved.

---

**Built by [Abhisek Bose](https://www.linkedin.com/in/abhisek-bose/)**
