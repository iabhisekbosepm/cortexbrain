"""Tests for ActivationEngine — spreading activation with mocked graph."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID

import fakeredis.aioredis

from cortexbrain.core.activation.engine import ActivationEngine
from cortexbrain.memory.active import ActiveMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.memory.raw import RawMemoryStore

NODE_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NODE_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
NODE_C_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


@pytest.fixture
async def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def active_memory(fake_redis):
    return ActiveMemoryStore(redis_client=fake_redis)


@pytest.fixture
def mock_semantic():
    semantic = AsyncMock(spec=SemanticMemoryStore)
    # find_nodes_by_name returns one match for "Auth"
    semantic.find_nodes_by_name.return_value = [
        {"id": NODE_A_ID, "name": "Auth Service", "description": "Handles authentication"}
    ]
    # get_neighbors_with_weights: A → B with weight 1.0
    async def neighbors_side_effect(node_id):
        if str(node_id) == NODE_A_ID:
            return [
                ({"id": NODE_B_ID, "name": "User DB", "description": "User database"}, 1.0)
            ]
        return []

    semantic.get_neighbors_with_weights.side_effect = neighbors_side_effect

    # get_node returns node data
    async def get_node_side_effect(node_id):
        nodes = {
            NODE_A_ID: {"id": NODE_A_ID, "name": "Auth Service", "description": "Handles authentication"},
            NODE_B_ID: {"id": NODE_B_ID, "name": "User DB", "description": "User database"},
        }
        return nodes.get(str(node_id))

    semantic.get_node.side_effect = get_node_side_effect
    return semantic


@pytest.fixture
def mock_raw():
    raw = AsyncMock(spec=RawMemoryStore)
    raw.search.return_value = []
    return raw


@pytest.fixture
async def engine(active_memory, mock_semantic, mock_raw):
    return ActivationEngine(
        active_memory=active_memory,
        semantic_memory=mock_semantic,
        raw_memory=mock_raw,
    )


class TestActivateForQuery:
    async def test_seed_node_gets_initial_score(self, engine, active_memory):
        results = await engine.activate_for_query("sess-1", ["Auth"])
        # Should find Auth Service as seed node
        assert len(results) >= 1
        seed = next(r for r in results if r["name"] == "Auth Service")
        assert seed["activation_score"] == 100.0

    async def test_neighbor_gets_dampened_score(self, engine):
        results = await engine.activate_for_query("sess-1", ["Auth"])
        names = {r["name"] for r in results}
        assert "Auth Service" in names
        assert "User DB" in names
        # Neighbor score = 100 * 1.0 * 0.5 = 50 (above threshold of 30)
        neighbor = next(r for r in results if r["name"] == "User DB")
        assert neighbor["activation_score"] == 50.0

    async def test_scores_persisted_to_redis(self, engine, active_memory):
        await engine.activate_for_query("sess-1", ["Auth"])
        score_a = await active_memory.get_score("sess-1", UUID(NODE_A_ID))
        score_b = await active_memory.get_score("sess-1", UUID(NODE_B_ID))
        assert score_a == 100.0
        assert score_b == 50.0

    async def test_fallback_to_vector_when_no_match(self, engine, mock_semantic, mock_raw):
        mock_semantic.find_nodes_by_name.return_value = []
        mock_raw.search.return_value = [{"text": "fallback result"}]
        results = await engine.activate_for_query("sess-1", ["NonExistent"])
        mock_raw.search.assert_called_once()

    async def test_below_threshold_not_activated(self, engine, mock_semantic):
        # Make neighbor weight very low so score < threshold (30)
        async def low_weight_neighbors(node_id):
            if str(node_id) == NODE_A_ID:
                return [
                    ({"id": NODE_B_ID, "name": "User DB", "description": "User database"}, 0.1)
                ]
            return []

        mock_semantic.get_neighbors_with_weights.side_effect = low_weight_neighbors

        results = await engine.activate_for_query("sess-1", ["Auth"])
        # 100 * 0.1 * 0.5 = 5.0 — below threshold of 30
        names = {r["name"] for r in results}
        assert "User DB" not in names

    async def test_token_budget_limits_results(self, engine, mock_semantic):
        # First node has huge description that exhausts the 2000-token budget.
        # Second node (neighbor) won't fit.
        async def get_node_side_effect(node_id):
            if str(node_id) == NODE_A_ID:
                return {
                    "id": NODE_A_ID,
                    "name": "Auth Service",
                    # 7600 chars → ~1900 tokens, leaving no room for the neighbor
                    "description": "x" * 7600,
                }
            if str(node_id) == NODE_B_ID:
                return {
                    "id": NODE_B_ID,
                    "name": "User DB",
                    # 1000 chars → ~250 tokens, won't fit in remaining budget
                    "description": "y" * 1000,
                }
            return None

        mock_semantic.get_node.side_effect = get_node_side_effect

        results = await engine.activate_for_query("sess-1", ["Auth"])
        # Seed (A, score=100) is sorted first, exhausts budget; neighbor B is cut
        assert len(results) == 1
        assert results[0]["name"] == "Auth Service"
