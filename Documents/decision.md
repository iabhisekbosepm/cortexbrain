# CortexBrain — Resume Guide

> **Last session:** 2026-02-10
> **Paused reason:** Docker build blocked by network (deb.debian.org returns 403 Forbidden)

---

## Current State

### What's Running (Docker)
All 4 infrastructure services are up and healthy:

| Service | Container | Ports | Status |
|---------|-----------|-------|--------|
| Neo4j 5 | `compliancebrain-neo4j-1` | `7474` (browser), `7687` (bolt) | Healthy |
| Redis 7 | `compliancebrain-redis-1` | `6379` | Healthy |
| PostgreSQL 16 | `compliancebrain-postgres-1` | `5432` | Healthy |
| Qdrant | `compliancebrain-qdrant-1` | `6333` (REST), `6334` (gRPC) | Healthy |

### What's NOT Running
- **CortexBrain API** (`cortexbrain` service) — Docker image build fails
- **Celery Worker** (`celery-worker` service) — depends on same image
- **Celery Beat** (`celery-beat` service) — depends on same image

---

## The Problem

Docker build fails at `apt-get update` inside any Debian-based Python image:
```
Err:1 http://deb.debian.org/debian bookworm InRelease
  403  Forbidden [IP: 151.101.2.132 80]
```

This is a **network/firewall/proxy issue** — the Docker daemon can't reach Debian repos.

### What We Tried
1. `python:3.12-slim` (trixie) — 403 on apt-get
2. `python:3.12-slim-bookworm` — 403 on apt-get
3. `python:3.12-alpine` — apk works, but `cognee` depends on `lancedb` which only ships glibc wheels (Alpine uses musl → incompatible)
4. Skip `apt-get` entirely on bookworm — user interrupted before seeing result

---

## How to Resume

### Option A: Once VPN/Proxy is Fixed (Full Docker)

```bash
cd "/Users/codeclouds-abhisekbose/Documents/Compliance Brain"

# Verify network is unblocked
docker run --rm python:3.12-slim-bookworm apt-get update

# If that works, rebuild and start everything
docker compose up -d --build
```

The Dockerfile is ready at `./Dockerfile`. It should build once `deb.debian.org` is reachable.

### Option B: Run App Locally (Services Stay in Docker)

No VPN fix needed — infrastructure runs in Docker, Python app runs natively on Mac:

```bash
cd "/Users/codeclouds-abhisekbose/Documents/Compliance Brain"

# 1. Start infrastructure (if stopped)
docker compose up -d neo4j redis postgres qdrant

# 2. Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install CortexBrain + Cognee
pip install -e ".[dev]"

# 4. Update .env to use localhost (not Docker service names)
#    Change these in .env:
#      GRAPH_DATABASE_URL=bolt://localhost:7687  (not neo4j:7687)
#      VECTOR_DB_URL=http://localhost:6333       (not qdrant:6333)
#      DB_HOST=localhost                          (not postgres)
#      REDIS_URL=redis://localhost:6379/0        (not redis:6379)
#      POSTGRES_URL=postgresql+asyncpg://cortexbrain:cortexbrain_dev@localhost:5432/cortexbrain
#      CELERY_BROKER_URL=redis://localhost:6379/1
#      CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 5. Run the API
uvicorn cortexbrain.main:app --reload --port 8000

# 6. (Optional) Run Celery worker for decay cycle
celery -A cortexbrain.workers.celery_app worker --loglevel=info
celery -A cortexbrain.workers.celery_app beat --loglevel=info
```

### Option C: Docker with Pre-Built Wheels (No apt-get needed)

If VPN stays blocked but you want full Docker, try this Dockerfile approach:

```dockerfile
FROM python:3.12-slim-bookworm
WORKDIR /app
# Skip apt-get — rely on pre-built pip wheels
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "cortexbrain.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This *might* work if all Cognee deps have pre-built wheels for `linux/amd64`. We didn't finish testing this — it was the last attempt before pausing.

---

## Important: .env File Differences

The `.env` file currently has **Docker service names** (for containers to talk to each other):

| Setting | Docker Value | Localhost Value (Option B) |
|---------|-------------|---------------------------|
| `GRAPH_DATABASE_URL` | `bolt://neo4j:7687` | `bolt://localhost:7687` |
| `VECTOR_DB_URL` | `http://qdrant:6333` | `http://localhost:6333` |
| `DB_HOST` | `postgres` | `localhost` |
| `REDIS_URL` | `redis://redis:6379/0` | `redis://localhost:6379/0` |
| `POSTGRES_URL` | `...@postgres:5432/...` | `...@localhost:5432/...` |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | `redis://localhost:6379/2` |

Switch these based on which option you choose.

---

## What's Already Built (No Changes Needed)

All 40 source files are complete. See `TASKLIST.md` for full details.

- `pyproject.toml` — depends on `cognee[neo4j,anthropic,redis]>=0.5.0`
- `docker-compose.yml` — 7 services (4 infra + app + celery worker + beat)
- `src/cortexbrain/` — full project structure (config, models, memory, core engines, API, workers)
- `tests/` — test infrastructure with fakeredis fixtures
- `.env` — configured for Docker networking
- `.env.example` — template with all settings documented

---

## Verify Services After Resume

```bash
# Check infrastructure health
docker compose ps

# Quick connectivity test
docker exec compliancebrain-redis-1 redis-cli ping          # → PONG
docker exec compliancebrain-postgres-1 pg_isready -U cortexbrain  # → accepting connections

# Neo4j browser
open http://localhost:7474   # Login: neo4j / cortexbrain_dev

# Qdrant dashboard
open http://localhost:6333/dashboard

# CortexBrain API (once running)
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/docs   # Swagger UI
```
