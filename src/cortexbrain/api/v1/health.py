"""GET /api/v1/health — System health check for all backing services."""

import time

import redis.asyncio as aioredis
from fastapi import APIRouter

from cognee.infrastructure.databases.graph import get_graph_engine

from cortexbrain.config import get_settings
from cortexbrain.models.schemas import HealthResponse, ServiceHealth

router = APIRouter()


async def _check_redis() -> ServiceHealth:
    settings = get_settings()
    try:
        start = time.monotonic()
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        return ServiceHealth(status="ok", latency_ms=round((time.monotonic() - start) * 1000, 2))
    except Exception as e:
        return ServiceHealth(status="error", error=str(e))


async def _check_neo4j() -> ServiceHealth:
    try:
        start = time.monotonic()
        engine = await get_graph_engine()
        is_empty = await engine.is_empty()  # lightweight check
        return ServiceHealth(status="ok", latency_ms=round((time.monotonic() - start) * 1000, 2))
    except Exception as e:
        return ServiceHealth(status="error", error=str(e))


async def _check_qdrant() -> ServiceHealth:
    try:
        from qdrant_client import QdrantClient

        settings = get_settings()
        start = time.monotonic()
        # Parse URL to extract host/port for Qdrant client
        url = settings.qdrant_url
        client = QdrantClient(url=url, timeout=5)
        client.get_collections()  # lightweight check
        client.close()
        return ServiceHealth(status="ok", latency_ms=round((time.monotonic() - start) * 1000, 2))
    except Exception as e:
        return ServiceHealth(status="error", error=str(e))


async def _check_postgres() -> ServiceHealth:
    settings = get_settings()
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        start = time.monotonic()
        engine = create_async_engine(settings.postgres_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return ServiceHealth(status="ok", latency_ms=round((time.monotonic() - start) * 1000, 2))
    except Exception as e:
        return ServiceHealth(status="error", error=str(e))


async def _check_llm() -> ServiceHealth:
    try:
        from cognee.infrastructure.llm.structured_output_framework.litellm_instructor.llm.get_llm_client import get_llm_client

        start = time.monotonic()
        client = get_llm_client()
        # Just verify the client can be instantiated (no actual LLM call)
        return ServiceHealth(status="ok", latency_ms=round((time.monotonic() - start) * 1000, 2))
    except Exception as e:
        return ServiceHealth(status="error", error=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check connectivity to all backing services."""
    redis_health = await _check_redis()
    neo4j_health = await _check_neo4j()
    qdrant_health = await _check_qdrant()
    postgres_health = await _check_postgres()
    llm_health = await _check_llm()

    services = [redis_health, neo4j_health, qdrant_health, postgres_health, llm_health]
    errors = sum(1 for s in services if s.status == "error")

    if errors == 0:
        overall = "healthy"
    elif errors <= 2:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        redis=redis_health,
        neo4j=neo4j_health,
        qdrant=qdrant_health,
        postgres=postgres_health,
        llm=llm_health,
    )
