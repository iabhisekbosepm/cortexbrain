"""Tests for ConfidenceGate — confidence classification and aggregation."""

import pytest

from cortexbrain.core.metacognition.confidence import ConfidenceGate
from cortexbrain.models.schemas import ConfidenceLevel


@pytest.fixture
def gate():
    return ConfidenceGate()


class TestClassify:
    def test_high_confidence(self, gate):
        assert gate.classify(0.9) == ConfidenceLevel.HIGH
        assert gate.classify(0.8) == ConfidenceLevel.HIGH

    def test_medium_confidence(self, gate):
        assert gate.classify(0.7) == ConfidenceLevel.MEDIUM
        assert gate.classify(0.5) == ConfidenceLevel.MEDIUM

    def test_low_confidence(self, gate):
        assert gate.classify(0.3) == ConfidenceLevel.LOW
        assert gate.classify(0.0) == ConfidenceLevel.LOW

    def test_conflicted_overrides_score(self, gate):
        assert gate.classify(0.95, is_conflicted=True) == ConfidenceLevel.CONFLICTED
        assert gate.classify(0.1, is_conflicted=True) == ConfidenceLevel.CONFLICTED


class TestComputeAggregateConfidence:
    def test_empty_nodes_returns_low(self, gate):
        score, tier = gate.compute_aggregate_confidence([])
        assert score == 0.0
        assert tier == ConfidenceLevel.LOW

    def test_single_high_confidence_node(self, gate):
        nodes = [{"confidence": 0.9, "activation_score": 100.0}]
        score, tier = gate.compute_aggregate_confidence(nodes)
        assert score == 0.9
        assert tier == ConfidenceLevel.HIGH

    def test_weighted_average_by_activation(self, gate):
        nodes = [
            {"confidence": 1.0, "activation_score": 100.0},
            {"confidence": 0.0, "activation_score": 100.0},
        ]
        score, tier = gate.compute_aggregate_confidence(nodes)
        assert score == pytest.approx(0.5, abs=0.01)
        assert tier == ConfidenceLevel.MEDIUM

    def test_activation_weights_matter(self, gate):
        # High-activation node with high confidence should dominate
        nodes = [
            {"confidence": 0.9, "activation_score": 100.0},
            {"confidence": 0.1, "activation_score": 10.0},
        ]
        score, tier = gate.compute_aggregate_confidence(nodes)
        # weighted = (0.9*100 + 0.1*10) / (100+10) = 91/110 ≈ 0.827
        assert score == pytest.approx(0.827, abs=0.01)
        assert tier == ConfidenceLevel.HIGH

    def test_conflicted_node_sets_conflicted_tier(self, gate):
        nodes = [
            {"confidence": 0.9, "activation_score": 100.0, "conflicted": True},
        ]
        score, tier = gate.compute_aggregate_confidence(nodes)
        assert tier == ConfidenceLevel.CONFLICTED

    def test_default_confidence_when_missing(self, gate):
        nodes = [{"activation_score": 50.0}]  # no "confidence" key
        score, tier = gate.compute_aggregate_confidence(nodes)
        assert score == pytest.approx(0.5, abs=0.01)


class TestFormatConfidencePrefix:
    def test_high_has_no_prefix(self, gate):
        assert gate.format_confidence_prefix(ConfidenceLevel.HIGH) == ""

    def test_medium_has_qualifier(self, gate):
        prefix = gate.format_confidence_prefix(ConfidenceLevel.MEDIUM)
        assert "moderate confidence" in prefix

    def test_low_has_warning(self, gate):
        prefix = gate.format_confidence_prefix(ConfidenceLevel.LOW)
        assert "low confidence" in prefix

    def test_conflicted_mentions_sources(self, gate):
        prefix = gate.format_confidence_prefix(ConfidenceLevel.CONFLICTED)
        assert "conflicting" in prefix
