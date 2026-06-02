"""Tests for the query pipeline — entity extraction and response wiring."""

import pytest

from cortexbrain.api.v1.query import _extract_entity_names, _node_text


class TestExtractEntityNames:
    def test_extracts_from_dict_with_name(self):
        results = [{"name": "Auth Service"}, {"name": "User DB"}]
        names = _extract_entity_names(results)
        assert "Auth Service" in names
        assert "User DB" in names

    def test_extracts_from_dict_with_entity_name(self):
        results = [{"entity_name": "Neo4j Database"}]
        names = _extract_entity_names(results)
        assert "Neo4j Database" in names

    def test_extracts_capitalized_phrases_from_strings(self):
        results = ["The Activation Engine handles spreading activation over the Knowledge Graph"]
        names = _extract_entity_names(results)
        # Should find capitalized multi-word phrases
        assert any("Activation Engine" in n for n in names)
        assert any("Knowledge Graph" in n for n in names)

    def test_deduplicates_case_insensitive(self):
        results = [{"name": "Auth"}, {"name": "auth"}, {"name": "AUTH"}]
        names = _extract_entity_names(results)
        # Should keep only one
        auth_names = [n for n in names if n.lower() == "auth"]
        assert len(auth_names) == 1

    def test_caps_at_30(self):
        results = [{"name": f"Entity{i}"} for i in range(40)]
        names = _extract_entity_names(results)
        assert len(names) <= 30

    def test_empty_results(self):
        assert _extract_entity_names([]) == []

    def test_short_strings_used_as_entity(self):
        results = ["Redis Cache"]
        names = _extract_entity_names(results)
        assert "Redis Cache" in names

    def test_long_strings_not_used_as_entity(self):
        long_text = "x" * 150
        results = [long_text]
        names = _extract_entity_names(results)
        assert long_text not in names


class TestNodeText:
    def test_prefers_description(self):
        node = {"description": "A database", "value": "db", "name": "DB"}
        assert _node_text(node) == "A database"

    def test_falls_back_to_value(self):
        node = {"description": "", "value": "db-value", "name": "DB"}
        assert _node_text(node) == "db-value"

    def test_falls_back_to_name(self):
        node = {"description": "", "value": "", "name": "My Node"}
        assert _node_text(node) == "My Node"

    def test_empty_node(self):
        node = {}
        assert _node_text(node) == ""
