# CortexBrain — Project Build Task Tracker

> This file tracks the progress of building the CortexBrain project structure from the PRD.
> It persists across sessions so future agents can understand what's been done and what's next.
>
> **Last updated:** 2026-02-10

---

## Legend

- [x] Completed
- [~] In Progress
- [ ] Pending
- ~~Deleted~~ — removed (no longer needed)

---

## Critical Architectural Decision (Session 1)

**CortexBrain extends Cognee OSS — it does NOT build from scratch.**

After cloning and analyzing `https://github.com/topoteretes/cognee.git` (v0.5.2), the project structure was redesigned to properly use Cognee's extension points:

| Cognee Provides | CortexBrain Wraps/Extends |
|---|---|
| `cognee.add()`, `cognee.cognify()`, `cognee.search()` | `ingestion/documents.py` calls these directly |
| `GraphDBInterface` (Neo4j adapter) | `memory/semantic.py` wraps it, adds PREVIOUS_VERSION edges |
| `VectorDBInterface` (Qdrant adapter) | `memory/raw.py` wraps it for fallback retrieval |
| `DataPoint` base class | `models/graph.py::KnowledgeNode` extends it |
| `LLMGateway` (litellm + instructor) | Used directly in API routes — **no separate LLM abstraction** |
| `run_custom_pipeline()` + `Task` | `pipelines/` registers CortexBrain tasks with Cognee's system |
| Cognee's env-based config | `config/settings.py` adds CortexBrain-specific settings |
| Cognee's Alembic migrations | CortexBrain uses its own SQLAlchemy tables (auto-created) |

**Deleted task T8 (LLM provider abstraction)** — Cognee already has LLMGateway.
**Deleted task T12 (Alembic setup)** — Using Cognee's migration system + SQLAlchemy auto-create for MVP.

---

## Phase 0: Project Scaffolding & Infrastructure

### T1: Create Python project scaffolding ✅
- **Status:** COMPLETED
- **Files:**
  - `pyproject.toml` — Depends on `cognee[neo4j,anthropic,redis]>=0.5.0` as foundation
  - `src/cortexbrain/__init__.py` — Root package
  - All sub-package `__init__.py` files
  - `tests/` with `unit/`, `integration/`, `e2e/` sub-dirs

### T2: Create Docker and environment configuration ✅
- **Status:** COMPLETED
- **Files:**
  - `docker-compose.yml` — Neo4j 5, Redis 7, PostgreSQL 16, Qdrant, API, Celery worker/beat
  - `Dockerfile` — Python 3.12-slim
  - `.env.example` — Cognee env vars + CortexBrain-specific settings
  - `.gitignore`

---

## Phase 1: Configuration & Data Models

### T3: Create configuration management module ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/config/settings.py` — `CortexBrainSettings(BaseSettings)` with all PRD params
  - Does NOT replace Cognee's config — sits alongside it

### T7: Create Pydantic schemas and SQLAlchemy/DB models ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/models/schemas.py` — API request/response models
  - `src/cortexbrain/models/database.py` — SQLAlchemy: Organization, APIKey, AuditLog, NodeMetadata
  - `src/cortexbrain/models/graph.py` — `KnowledgeNode(DataPoint)` extending Cognee's base class

---

## Phase 2: Memory Substrates & Core Engines

### T4: Create memory substrate interfaces ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/memory/active.py` — `ActiveMemoryStore` (Redis sorted sets, CortexBrain-only)
  - `src/cortexbrain/memory/semantic.py` — `SemanticMemoryStore` (wraps Cognee's GraphDBInterface)
  - `src/cortexbrain/memory/raw.py` — `RawMemoryStore` (wraps Cognee's VectorDBInterface)
  - `src/cortexbrain/memory/meta.py` — `MetaMemoryStore` (PostgreSQL, CortexBrain-only)

### T5: Create core engine modules ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/core/activation/engine.py` — Spreading activation (BFS + dampening)
  - `src/cortexbrain/core/activation/decay.py` — DecayCycle (periodic score decrement)
  - `src/cortexbrain/core/mutation/engine.py` — Locate → Version → Mutate → Meta-Update
  - `src/cortexbrain/core/metacognition/confidence.py` — ConfidenceGate (high/med/low/conflicted)
  - `src/cortexbrain/core/metacognition/salience.py` — SalienceScorer (weighted formula)

### ~~T8: Create LLM provider abstraction layer~~ ❌ DELETED
- **Reason:** Cognee already provides `LLMGateway` via litellm. No need to rebuild.

---

## Phase 3: API, Ingestion & Pipelines

### T6: Create FastAPI application and API v1 routes ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/main.py` — FastAPI app with Cognee migration on startup
  - `src/cortexbrain/api/deps.py` — DI for all engines and memory stores
  - `src/cortexbrain/api/v1/query.py` — POST /api/v1/query (activation → LLM → confidence gate)
  - `src/cortexbrain/api/v1/correct.py` — POST /api/v1/correct (mutation pipeline)
  - `src/cortexbrain/api/v1/nodes.py` — GET /api/v1/nodes/{node_id}/history
  - `src/cortexbrain/api/v1/health.py` — GET /api/v1/health (all 5 services)
  - `src/cortexbrain/api/v1/ingest.py` — POST /api/v1/ingest
  - `src/cortexbrain/auth/middleware.py` — Bearer token auth

### T9: Create ingestion pipeline modules ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/ingestion/documents.py` — Wraps `cognee.add()` + `cognee.cognify()`
  - `src/cortexbrain/pipelines/activation_pipeline.py` — Cognee `Task` wrapper for activation
  - `src/cortexbrain/pipelines/mutation_pipeline.py` — Cognee `Task` wrapper for mutations

---

## Phase 4: Background Jobs & Tests

### T10: Create Celery worker and background tasks ✅
- **Status:** COMPLETED
- **Files:**
  - `src/cortexbrain/workers/celery_app.py` — Celery config with beat schedule (30s decay)
  - `src/cortexbrain/workers/tasks.py` — `decay_cycle_task`, `batch_ingestion_task`

### T11: Create test infrastructure ✅
- **Status:** COMPLETED
- **Files:**
  - `tests/conftest.py` — fakeredis fixtures, mock Cognee engines, test settings

### ~~T12: Create Alembic migration setup~~ ❌ DELETED
- **Reason:** Using Cognee's migration system + SQLAlchemy `Base.metadata.create_all()` for MVP.

---

## Phase 5: Finalize

### T13: Update CLAUDE.md ✅
- **Status:** COMPLETED
- **Files:** `CLAUDE.md` rewritten with Cognee extension architecture, dev commands, project structure

---

## Phase 6: Subsystem Wiring (All 6 subsystems live)

### T14: Wire up all 6 CortexBrain subsystems ✅
- **Status:** COMPLETED
- **What was done:** Connected all implemented-but-disconnected subsystems so they are live and user-facing.
- **Files modified:**
  - `src/cortexbrain/memory/semantic.py` — Fixed `find_nodes_by_name` (`:KnowledgeNode`→`:Entity`), rewrote `get_neighbors` with raw Cypher (Cognee's `get_neighbours` is broken), added `get_neighbors_with_weights`, `get_edge_count`, `get_all_entity_ids`
  - `src/cortexbrain/core/activation/engine.py` — Uses `get_neighbors_with_weights()` for proper edge weights, fixed `_apply_token_budget` to read `description` field (Cognee Entity nodes use `description`, not `value`)
  - `src/cortexbrain/api/v1/query.py` — Full hybrid pipeline: Cognee search → entity extraction → spreading activation → M_meta enrichment → confidence gate → access tracking → LLM generation → source attribution. Fallback to raw Cognee results if activation finds nothing.
  - `src/cortexbrain/ingestion/documents.py` — Post-ingestion M_meta initialization: creates `NodeMetadata` entries and computes initial salience for all new Entity nodes
  - `src/cortexbrain/workers/tasks.py` — Added `salience_recompute_task` (iterates all entities, recomputes salience from access_count/recency/corrections/edge_count)
  - `src/cortexbrain/workers/celery_app.py` — Added `salience-recompute` to beat schedule (every 1 hour)
  - `src/cortexbrain/api/v1/ingest.py` — Added `POST /ingest/batch` (async Celery dispatch) and `GET /ingest/batch/{task_id}` (status polling)
  - `sample-queries.md` — Updated with batch ingestion examples, activation-aware response format

### Critical fixes applied:
1. **Neo4j label mismatch:** Cognee creates `:Entity` nodes, not `:KnowledgeNode` — all Cypher queries updated
2. **Broken `get_neighbors`:** Cognee's `Neo4jAdapter.get_neighbours()` doesn't exist — replaced with raw Cypher
3. **Entity field mismatch:** Cognee entities use `description` not `value` — `_apply_token_budget` and `_node_text` updated
4. **Cypher result unwrapping:** `engine.query("RETURN n")` returns `[{"n": {...}}]` — unwrap logic added

---

## All Tasks Complete ✅

**Final project structure:**
```
src/cortexbrain/
├── __init__.py
├── main.py                     # FastAPI app (extends Cognee)
├── config/settings.py          # CortexBrain-specific settings
├── models/
│   ├── graph.py                # KnowledgeNode(DataPoint) — extends Cognee
│   ├── schemas.py              # API request/response models
│   └── database.py             # SQLAlchemy (Organization, AuditLog, etc.)
├── memory/
│   ├── active.py               # M_a — Redis (CortexBrain-only)
│   ├── semantic.py             # M_s — wraps Cognee's GraphDBInterface
│   ├── raw.py                  # M_r — wraps Cognee's VectorDBInterface
│   └── meta.py                 # M_meta — PostgreSQL (CortexBrain-only)
├── core/
│   ├── activation/engine.py    # Spreading activation (Novel)
│   ├── activation/decay.py     # Decay cycle (Novel)
│   ├── mutation/engine.py      # Locate→Version→Mutate→Meta-Update (Novel)
│   ├── metacognition/confidence.py  # Confidence gating (Novel)
│   └── metacognition/salience.py    # Salience scoring (Novel)
├── pipelines/
│   ├── activation_pipeline.py  # Cognee Task wrapper
│   └── mutation_pipeline.py    # Cognee Task wrapper
├── ingestion/documents.py      # Wraps cognee.add() + cognee.cognify()
├── api/
│   ├── deps.py                 # Dependency injection
│   └── v1/                     # query, correct, nodes, health, ingest
├── auth/middleware.py           # Bearer token auth
└── workers/
    ├── celery_app.py           # Celery config + beat schedule
    └── tasks.py                # decay_cycle_task, batch_ingestion_task
```

---

## Notes & Learnings

- **Extension, not fork:** CortexBrain depends on `cognee[neo4j,anthropic,redis]>=0.5.0` as a pip package. Never modify Cognee internals.
- **Use Cognee's LLM gateway:** Cognee uses litellm + instructor for structured output. No need for a separate LLM abstraction.
- **Use Cognee's pipeline system:** `cognee.run_custom_pipeline()` + `Task` is how to add custom processing steps.
- **KnowledgeNode extends DataPoint:** Cognee's `DataPoint` already has `id`, `version`, `created_at`, `updated_at`, `metadata`. We add `confidence`, `salience`, `volatile`, `conflicted`.
- **Memory stores wrap, not replace:** `SemanticMemoryStore` wraps `get_graph_engine()`. `RawMemoryStore` wraps `get_vector_engine()`. Only `ActiveMemoryStore` (Redis) and `MetaMemoryStore` (PostgreSQL) are fully CortexBrain-owned.
- **Cognee env vars pass through:** Set `GRAPH_DATABASE_PROVIDER=neo4j`, `VECTOR_DB_PROVIDER=qdrant`, `LLM_PROVIDER=anthropic` etc. in `.env` — Cognee reads these automatically.
