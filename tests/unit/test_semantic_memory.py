"""Tests for SemanticMemoryStore — Cypher queries with mocked graph engine."""

import pytest
from unittest.mock import AsyncMock
from uuid import UUID

from cortexbrain.memory.semantic import SemanticMemoryStore

NODE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    engine.query.return_value = []
    engine.get_node.return_value = {"id": str(NODE_ID), "name": "Test Node"}
    return engine


@pytest.fixture
def semantic(mock_engine):
    return SemanticMemoryStore(graph_engine=mock_engine)


class TestFindNodesByName:
    async def test_unwraps_cypher_results(self, semantic, mock_engine):
        # Cypher returns [{n: {id: ..., name: ...}}]
        mock_engine.query.return_value = [
            {"n": {"id": str(NODE_ID), "name": "Auth Service"}}
        ]
        results = await semantic.find_nodes_by_name("Auth")
        assert len(results) == 1
        assert results[0]["name"] == "Auth Service"
        assert "n" not in results[0]  # Should be unwrapped

    async def test_handles_flat_dict_results(self, semantic, mock_engine):
        # Some engines return flat dicts directly
        mock_engine.query.return_value = [
            {"id": str(NODE_ID), "name": "Auth Service"}
        ]
        results = await semantic.find_nodes_by_name("Auth")
        assert len(results) == 1
        assert results[0]["name"] == "Auth Service"

    async def test_uses_entity_label(self, semantic, mock_engine):
        mock_engine.query.return_value = []
        await semantic.find_nodes_by_name("anything")
        query_str = mock_engine.query.call_args[0][0]
        assert ":Entity" in query_str
        assert ":KnowledgeNode" not in query_str

    async def test_returns_empty_on_error(self, semantic, mock_engine):
        mock_engine.query.side_effect = Exception("connection lost")
        results = await semantic.find_nodes_by_name("Auth")
        assert results == []


class TestGetNeighbors:
    async def test_returns_neighbor_data(self, semantic, mock_engine):
        mock_engine.query.return_value = [
            {"neighbor": {"id": "b-id", "name": "Neighbor"}, "rel_type": "RELATES_TO", "weight": 0.8}
        ]
        results = await semantic.get_neighbors(NODE_ID)
        assert len(results) == 1
        assert results[0]["name"] == "Neighbor"

    async def test_returns_empty_on_error(self, semantic, mock_engine):
        mock_engine.query.side_effect = Exception("timeout")
        results = await semantic.get_neighbors(NODE_ID)
        assert results == []


class TestGetNeighborsWithWeights:
    async def test_returns_node_weight_tuples(self, semantic, mock_engine):
        mock_engine.query.return_value = [
            {"neighbor": {"id": "b-id", "name": "Neighbor"}, "weight": 0.7}
        ]
        results = await semantic.get_neighbors_with_weights(NODE_ID)
        assert len(results) == 1
        node_data, weight = results[0]
        assert node_data["name"] == "Neighbor"
        assert weight == 0.7

    async def test_default_weight_is_one(self, semantic, mock_engine):
        mock_engine.query.return_value = [
            {"neighbor": {"id": "b-id", "name": "Neighbor"}}
        ]
        results = await semantic.get_neighbors_with_weights(NODE_ID)
        _, weight = results[0]
        assert weight == 1.0

    async def test_returns_empty_on_error(self, semantic, mock_engine):
        mock_engine.query.side_effect = Exception("fail")
        results = await semantic.get_neighbors_with_weights(NODE_ID)
        assert results == []


class TestGetEdgeCount:
    async def test_returns_count(self, semantic, mock_engine):
        mock_engine.query.return_value = [{"cnt": 5}]
        count = await semantic.get_edge_count(NODE_ID)
        assert count == 5

    async def test_returns_zero_on_no_results(self, semantic, mock_engine):
        mock_engine.query.return_value = []
        count = await semantic.get_edge_count(NODE_ID)
        assert count == 0

    async def test_returns_zero_on_error(self, semantic, mock_engine):
        mock_engine.query.side_effect = Exception("fail")
        count = await semantic.get_edge_count(NODE_ID)
        assert count == 0


class TestGetAllEntityIds:
    async def test_returns_id_strings(self, semantic, mock_engine):
        mock_engine.query.return_value = [
            {"id": "aaa"},
            {"id": "bbb"},
        ]
        ids = await semantic.get_all_entity_ids()
        assert ids == ["aaa", "bbb"]

    async def test_skips_null_ids(self, semantic, mock_engine):
        mock_engine.query.return_value = [
            {"id": "aaa"},
            {"id": None},
            {"other": "no-id"},
        ]
        ids = await semantic.get_all_entity_ids()
        assert ids == ["aaa"]

    async def test_returns_empty_on_error(self, semantic, mock_engine):
        mock_engine.query.side_effect = Exception("fail")
        ids = await semantic.get_all_entity_ids()
        assert ids == []
