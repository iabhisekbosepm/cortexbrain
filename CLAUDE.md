# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CortexBrain** is a B2B AI knowledge system — an auditable, self-correcting "internal brain" for enterprises. It is built as an **extension layer on top of [Cognee](https://github.com/topoteretes/cognee) OSS** (not a fork). The PRD is in `prd-mfca-compliance-brain-mvp.md`.

Core promise: An AI assistant that gets smarter every time someone corrects it, with a full audit trail for every answer.

## Relationship to Cognee

CortexBrain **extends** Cognee — it does NOT reimplement what Cognee provides. Specifically:

| What Cognee Provides (DO NOT rebuild) | How CortexBrain Uses It |
|---|---|
| `cognee.add()`, `cognee.cognify()`, `cognee.search()` | Called directly for ingestion & graph building |
| `cognee.run_custom_pipeline()` + `Task` | CortexBrain registers custom pipeline tasks |
| `GraphDBInterface` + Neo4j adapter | Wraps it in `SemanticMemoryStore` for version-history edges |
| `VectorDBInterface` + Qdrant adapter | Wraps it in `RawMemoryStore` for fallback retrieval |
| `DataPoint` base class | Extended by `KnowledgeNode` with confidence/salience fields |
| `LLMGateway` (litellm + instructor) | Used directly for LLM calls — no separate LLM abstraction |
| Cognee's env-based config | CortexBrain settings layer on top via `CortexBrainSettings` |
| Cognee's Alembic migrations | CortexBrain uses Cognee's migrations + its own SQLAlchemy tables |

## Development Commands

```bash
# === Full Docker (recommended) ===
docker compose build           # Build all images (backend, frontend, workers)
docker compose up -d           # Start all 8 services
docker compose ps              # Verify all healthy
docker compose logs -f cortexbrain frontend  # Watch logs
# Backend: http://localhost:8000  |  Frontend: http://localhost:3005

# === Hybrid mode (infra in Docker, app local) ===
docker compose up -d neo4j redis postgres qdrant  # Start infra only
pip install -e ".[dev]"        # Install CortexBrain + Cognee + dev tools
uvicorn cortexbrain.main:app --reload --port 8000
cd frontend && npm run dev     # Next.js dev server on :3000

# Run Celery worker (decay cycle, batch ingestion)
celery -A cortexbrain.workers.celery_app worker --loglevel=info
celery -A cortexbrain.workers.celery_app beat --loglevel=info

# Testing
pytest                         # All tests
pytest tests/unit/             # Unit tests only (no Docker needed)
pytest tests/integration/      # Integration tests (requires Docker services)
pytest tests/unit/test_file.py::test_name  # Single test
pytest --cov=cortexbrain       # With coverage

# Linting & formatting
ruff check .                   # Lint
ruff format .                  # Format
mypy src/cortexbrain/          # Type check

# RAG Benchmarks (requires running API + ingested data)
python3 tests/benchmarks/eval_rag.py                      # Accuracy: Recall@K, Precision@K, MRR, keyword match
python3 tests/benchmarks/eval_rag.py --skip-faithfulness   # Skip LLM-as-judge (faster)
python3 tests/benchmarks/bench_speed.py                    # Speed: p50/p95/p99 latency
python3 tests/benchmarks/bench_speed.py --component        # Include component-level timing
```

## Architecture

```
CortexBrain Layer (src/cortexbrain/)
├── core/activation/    — Spreading activation + decay (Novel)
├── core/mutation/      — Revision-based corrections (Novel)
├── core/metacognition/ — Confidence gating + salience (Novel)
├── pipelines/          — Cognee Task wrappers for our engines
├── api/v1/             — FastAPI routes (query, agent-query, correct, nodes, health, ingest, timeline, graph, dashboard, review)
│   ▼
Cognee OSS (pip dependency)
├── add() → cognify() → search()  — ECL pipeline
├── GraphDBInterface (Neo4j)       — Our M_s (Semantic Memory)
├── VectorDBInterface (Qdrant)     — Our M_r (Raw Memory)
└── LLMGateway (litellm)          — LLM abstraction
```

## MFCA Memory Model — Four Substrates

| Substrate | Store | CortexBrain Module | Owner |
|-----------|-------|--------------------|-------|
| **M_a** (Active) | Redis 7+ | `memory/active.py` | CortexBrain-only (Cognee has no activation) |
| **M_s** (Semantic) | Neo4j 5.x | `memory/semantic.py` | Wraps Cognee's `GraphDBInterface` |
| **M_r** (Raw) | Qdrant | `memory/raw.py` | Wraps Cognee's `VectorDBInterface` |
| **M_meta** (Meta) | PostgreSQL 16 | `memory/meta.py` | CortexBrain-only (audit logs, confidence) |

## Key Algorithms

**Spreading Activation:** `neighbor_activation = source_activation × edge_weight × 0.5`
- Threshold: 30 (configurable), Max context: ≤2,000 tokens, BFS with dampening

**Decay Cycle:** Every 30s, decrement by DECAY_RATE (10). Evict at 0 from Redis; Neo4j untouched.

**Salience:** `S = (access_freq × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)`

**Confidence:** High ≥ 0.8, Medium ≥ 0.5, Low < 0.5, Conflicted = flagged

**Mutation Pipeline:** Locate → Version → Mutate → Meta-Update (PREVIOUS_VERSION edges in Neo4j)

## REST API

- `POST /api/v1/query` — Query with activation-based context selection (fixed pipeline)
- `POST /api/v1/query/agent` — **Agentic query** — SSE streaming with multi-step LLM reasoning, 9 tools, multi-turn conversation
- `POST /api/v1/correct` — Submit correction (versioned mutation)
- `GET /api/v1/nodes/{node_id}/history` — Full audit trail
- `GET /api/v1/health` — All service health checks
- `POST /api/v1/ingest` — Document upload via Cognee's ECL
- `GET /api/v1/timeline` — Meta memory timeline (audit logs with action/date filters, summary)
- `GET /api/v1/graph/overview` — Knowledge graph visualization (top-salient nodes + edges)
- `GET /api/v1/graph/subgraph` — BFS subgraph from a center node
- `GET /api/v1/dashboard/stats` — Confidence distribution, low-confidence nodes, aggregated stats
- `GET /api/v1/review/queue` — Auto-learned nodes pending human review (confidence 0.5-0.7)
- `POST /api/v1/review/approve/{node_id}` — Approve auto-learned node (confidence → 0.8)
- `POST /api/v1/review/reject/{node_id}` — Reject auto-learned node (archive)

All endpoints require Bearer token auth.

## Configuration

- **Local dev:** `.env` — all connection strings use `localhost`
- **Full Docker:** `.env.docker` — connection strings use Docker service names (`neo4j`, `redis`, `postgres`, `qdrant`)
- **CortexBrain settings:** `src/cortexbrain/config/settings.py` (Pydantic BaseSettings)
- **Frontend proxy:** `next.config.ts` uses `API_INTERNAL_URL` (server-only, Docker: `http://cortexbrain:8000`) with fallback to `NEXT_PUBLIC_API_URL` (client-side: `http://localhost:8000`)

## Docker

Full stack runs with `docker compose up -d` (8 services):

| Service | Image | Ports | Config |
|---------|-------|-------|--------|
| neo4j | neo4j:5-community | 7474, 7687 | Healthcheck via cypher-shell |
| redis | redis:7-alpine | 6379 | 256MB maxmemory, allkeys-lru |
| postgres | postgres:16-alpine | 5432 | `init-db.sh` creates `cognee_db` |
| qdrant | qdrant/qdrant | 6333, 6334 | Vector DB |
| cortexbrain | python:3.12-slim | 8000 | FastAPI + healthcheck, volume-mounts `./src` |
| celery-worker | python:3.12-slim | - | Decay, salience, consolidation, ingestion |
| celery-beat | python:3.12-slim | - | Scheduled task runner |
| frontend | node:20-alpine | 3005→3000 | Next.js production build |

**Key files:** `Dockerfile` (backend), `frontend/Dockerfile`, `.env.docker`, `docker-compose.yml`, `.dockerignore`

**Networking:** Backend uses Docker service names for inter-service calls. Frontend bakes `API_INTERNAL_URL=http://cortexbrain:8000` at build time for server-side proxy rewrites, and `NEXT_PUBLIC_API_URL=http://localhost:8000` for browser-facing SSE.

## CortexBrain as Knowledge Source (MCP Integration)

This project has a running CortexBrain instance with MCP tools available. **Use CortexBrain to reduce token waste from re-exploration.**

### When to query CortexBrain (`cortexbrain_query`):
- **Architecture questions** — "How does activation work?", "Where is the mutation engine?"
- **Past decisions** — "Why did we choose X?", "What was the fix for Y?"
- **Project knowledge** — "What datasets exist?", "What are the API endpoints?"
- **Before exploring** — If unsure where something lives, query CortexBrain first. It's cheaper than 10 file reads.

### When NOT to query (just code directly):
- Direct coding tasks — "fix this typo", "add a field to this model"
- When the user gives specific file paths
- Simple git/npm/build commands

### When to remember (`cortexbrain_remember`):
- After discovering non-obvious patterns (e.g., "Cognee uses LanceDB not Qdrant")
- After debugging sessions — store the root cause and fix
- Architecture decisions made during implementation
- **Do NOT duplicate what's already in CLAUDE.md** — CortexBrain is for dynamic knowledge

### Token savings strategy:
- Keep MEMORY.md minimal (just pointers). Detailed knowledge lives in CortexBrain.
- One `cortexbrain_query` call (~300 tokens) replaces 5-10 file reads (~2000+ tokens).
- Use `cortexbrain_search_sources` to find what datasets/knowledge exist before exploring the filesystem.

## Automated Context Persistence (Hooks)

CortexBrain hooks automatically save session knowledge before `/compact` and restore it after, preventing context loss during compaction.

**How it works:**
1. **PreCompact hook** (`scripts/hooks/pre_compact_save.py`) — Extracts the last 10 user/assistant turns from the transcript and ingests them into CortexBrain via `POST /api/v1/ingest/text` (dataset: `session_context`)
2. **SessionStart hook** (`scripts/hooks/session_start_restore.py`) — When `source == "compact"`, queries CortexBrain for recent session context and surfaces it via the hook reason field

**Environment variables** (optional — defaults work for local dev):
- `CORTEXBRAIN_URL` — API base URL (default: `http://localhost:8000`)
- `CORTEXBRAIN_API_KEY` — Bearer token (default: `test-key`)

**Key properties:**
- Hooks never block — always return `{"continue": true}`
- Stdlib only (no pip dependencies in hook scripts)
- 30s API timeout with graceful fallback if CortexBrain is down
- Knowledge extraction: last 10 turns, capped at 4000 chars
- Restore output: capped at 2000 chars

**Testing:**
```bash
# Test PreCompact with missing transcript
echo '{"session_id":"test","transcript_path":"/nonexistent","cwd":"/tmp"}' | python3 scripts/hooks/pre_compact_save.py

# Test SessionStart skips non-compact sources
echo '{"session_id":"test","source":"startup"}' | python3 scripts/hooks/session_start_restore.py
```

## Project Tracking

See `TASKLIST.md` for implementation progress, task dependencies, and learnings.
