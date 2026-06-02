"""Shared test fixtures for CortexBrain tests.

Uses fakeredis for Active Memory tests (no real Redis needed for unit tests).
Mocks Cognee's graph/vector engines for isolation.
"""

import pytest
from unittest.mock import AsyncMock

import fakeredis.aioredis

from cortexbrain.config import CortexBrainSettings
from cortexbrain.memory.active import ActiveMemoryStore


@pytest.fixture
def settings():
    """Test settings with defaults."""
    return CortexBrainSettings(
        redis_url="redis://localhost:6379/15",  # Test DB
        postgres_url="sqlite+aiosqlite:///test.db",  # SQLite for fast unit tests
    )


@pytest.fixture
async def fake_redis():
    """Fake Redis for unit tests (no real Redis needed)."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def active_memory(fake_redis):
    """ActiveMemoryStore backed by fakeredis."""
    return ActiveMemoryStore(redis_client=fake_redis)


@pytest.fixture
def mock_graph_engine():
    """Mock of Cognee's GraphDBInterface for unit tests."""
    engine = AsyncMock()
    engine.get_node.return_value = {
        "id": "test-node-id",
        "name": "auth_service_port",
        "value": "8080",
        "confidence": 0.85,
        "version": 1,
    }
    engine.get_neighbors.return_value = []
    engine.query.return_value = []
    engine.is_empty.return_value = False
    return engine


@pytest.fixture
def mock_vector_engine():
    """Mock of Cognee's VectorDBInterface for unit tests."""
    engine = AsyncMock()
    engine.search.return_value = []
    return engine
