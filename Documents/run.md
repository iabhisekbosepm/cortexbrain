# Running CortexBrain — Full Stack Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | >= 3.12 | `python3 --version` |
| Node.js | >= 18 | `node --version` |
| Docker & Docker Compose | Latest | `docker compose version` |
| pip | Latest | `pip --version` |

---

## 1. Quick Start (TL;DR)

```bash
# 1. Clone & setup
cp .env.example .env              # Configure environment variables
pip install -e ".[dev]"           # Install Python dependencies

# 2. Start infrastructure
docker compose up -d              # Neo4j, Redis, PostgreSQL, Qdrant
sleep 30                          # Wait for services to be healthy

# 3. Start backend (3 terminals)
uvicorn cortexbrain.main:app --reload --port 8000                       # Terminal 1: API
celery -A cortexbrain.workers.celery_app worker --loglevel=info         # Terminal 2: Worker
celery -A cortexbrain.workers.celery_app beat --loglevel=info           # Terminal 3: Scheduler

# 4. Start frontend (1 terminal)
cd frontend && npm install && npm run dev                               # Terminal 4: UI
```

**Access Points:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

---

## 2. Detailed Setup

### 2.1 Environment Variables

Copy the example env file and edit as needed:

```bash
cp .env.example .env
```

Key variables in `.env`:

```bash
# LLM Provider
LLM_API_KEY=<your-api-key>
LLM_MODEL=gemini/gemini-2.0-flash
LLM_PROVIDER=gemini

# Neo4j (Graph Database)
GRAPH_DATABASE_PROVIDER=neo4j
GRAPH_DATABASE_URL=bolt://localhost:7687
GRAPH_DATABASE_USERNAME=neo4j
GRAPH_DATABASE_PASSWORD=cortexbrain_dev

# Vector Database (Qdrant)
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_URL=http://localhost:6333

# PostgreSQL (Cognee metadata)
DB_PROVIDER=postgres
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=cortexbrain
DB_PASSWORD=cortexbrain_dev
DB_NAME=cognee_db

# Redis (Active Memory)
REDIS_URL=redis://localhost:6379/0

# PostgreSQL (CortexBrain metadata)
POSTGRES_URL=postgresql+asyncpg://cortexbrain:cortexbrain_dev@localhost:5432/cortexbrain

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 2.2 Install Python Dependencies

```bash
# Production only
pip install -e .

# With dev tools (pytest, ruff, mypy)
pip install -e ".[dev]"
```

---

## 3. Docker Services

### Start all services

```bash
docker compose up -d
```

### Service Map

| Service | Port(s) | Credentials | Purpose |
|---------|---------|-------------|---------|
| **Neo4j** | `7474` (HTTP), `7687` (Bolt) | `neo4j` / `cortexbrain_dev` | Semantic Memory (M_s) — knowledge graph |
| **Redis** | `6379` | — | Active Memory (M_a) + Celery broker |
| **PostgreSQL** | `5432` | `cortexbrain` / `cortexbrain_dev` | Meta Memory (M_meta) + Cognee DB |
| **Qdrant** | `6333` (REST), `6334` (gRPC) | — | Raw Memory (M_r) — vector embeddings |

### Verify services are healthy

```bash
docker compose ps
```

All containers should show `running` (or `healthy` if health checks are configured).

### PostgreSQL databases

Two databases are created automatically by `scripts/init-db.sh`:
- `cortexbrain` — CortexBrain audit logs, confidence scores, metadata
- `cognee_db` — Cognee's internal entity/relationship storage

---

## 4. Backend

### 4.1 FastAPI Server

```bash
uvicorn cortexbrain.main:app --reload --port 8000
```

On startup the server will:
1. Load `.env` configuration
2. Run Cognee database migrations
3. Initialize CortexBrain's M_meta PostgreSQL tables
4. Register all API v1 routes

**API Base URL:** `http://localhost:8000/api/v1`

### 4.2 Celery Worker

The worker processes background tasks (decay cycles, salience recomputation, consolidation):

```bash
celery -A cortexbrain.workers.celery_app worker --loglevel=info
```

### 4.3 Celery Beat (Scheduler)

Beat triggers scheduled tasks on a timer:

```bash
celery -A cortexbrain.workers.celery_app beat --loglevel=info
```

**Scheduled Tasks:**

| Task | Interval | What It Does |
|------|----------|--------------|
| `decay_cycle_task` | Every 30s | Decrements activation scores in Redis, evicts at 0 |
| `salience_recompute_task` | Every 1 hour | Recalculates node importance scores |
| `consolidation_task` | Every 7 days | Promotes validated knowledge, archives stale nodes |

> **Dev shortcut:** Run worker + beat in one process:
> ```bash
> celery -A cortexbrain.workers.celery_app worker --beat --loglevel=info
> ```

---

## 5. Frontend

### 5.1 Setup

```bash
cd frontend
npm install
```

### 5.2 Environment

Create `frontend/.env.local` (if it doesn't already exist):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The Next.js config proxies all `/api/*` requests to the backend, so the frontend and backend work together seamlessly on different ports.

### 5.3 Run

```bash
# Development (hot reload)
npm run dev        # http://localhost:3000

# Production build
npm run build
npm start
```

---

## 6. API Endpoints

All endpoints require a Bearer token: `Authorization: Bearer <token>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | Query knowledge with activation-based context |
| `POST` | `/api/v1/correct` | Submit a correction (versioned mutation) |
| `POST` | `/api/v1/ingest` | Upload documents via Cognee's ECL pipeline |
| `GET` | `/api/v1/nodes/{node_id}/history` | View full audit trail for a node |
| `GET` | `/api/v1/health` | Check all service health |
| `GET` | `/api/v1/datasets` | List datasets |
| `POST` | `/api/v1/consolidation` | Trigger memory consolidation |

### Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is compliance?", "max_tokens": 500}'
```

---

## 7. Testing

```bash
# All tests
pytest

# Unit tests (no Docker needed)
pytest tests/unit/

# Integration tests (requires Docker services running)
pytest tests/integration/

# Single test
pytest tests/unit/test_file.py::test_name

# With coverage report
pytest --cov=cortexbrain
```

---

## 8. Linting & Formatting

```bash
ruff format .              # Auto-format code
ruff check .               # Lint check
mypy src/cortexbrain/      # Type checking
```

---

## 9. Stopping Everything

```bash
# Stop backend processes
pkill -f uvicorn
pkill -f "celery.*worker"
pkill -f "celery.*beat"

# Stop Docker services
docker compose down

# Stop Docker services AND remove volumes (fresh start)
docker compose down -v
```

---

## 10. Troubleshooting

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3` on macOS |
| Neo4j won't connect | Wait 30s after `docker compose up` — Neo4j is slow to start |
| Celery tasks not found | Ensure `include=["cortexbrain.workers.tasks"]` is in celery config |
| Frontend API timeout on ingestion | `proxyTimeout: 300_000` is set in `next.config.ts` — cognify can take minutes |
| Cognee dataset name errors | Dataset names must NOT contain spaces or dots — use hyphens/underscores |
| Celery `Future` loop mismatch | Use `asyncio.run()` not `asyncio.new_event_loop()` inside Celery tasks |
| Port already in use | `lsof -i :<port>` to find the process, then `kill <pid>` |

### Inspect Services

```bash
# Neo4j Browser
open http://localhost:7474/browser/
# Login: neo4j / cortexbrain_dev

# PostgreSQL
psql -h localhost -U cortexbrain -d cortexbrain
# Password: cortexbrain_dev

# Redis
redis-cli -p 6379
> DBSIZE              # Active Memory entries
> SELECT 1
> DBSIZE              # Celery broker queue

# Docker logs
docker compose logs -f neo4j
docker compose logs -f redis
docker compose logs -f postgres
```
