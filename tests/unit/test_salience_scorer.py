"""Tests for SalienceScorer — salience formula and edge cases."""

import time

import pytest

from cortexbrain.core.metacognition.salience import SalienceScorer


@pytest.fixture
def scorer():
    return SalienceScorer()


class TestCompute:
    def test_zero_everything(self, scorer):
        score = scorer.compute(
            access_count=0,
            last_accessed_ts=0.0,  # Very old
            correction_count=0,
            edge_count=0,
        )
        assert score == 0.0

    def test_max_everything(self, scorer):
        score = scorer.compute(
            access_count=100,
            last_accessed_ts=time.time(),  # Just now
            correction_count=20,
            edge_count=50,
        )
        # All factors maxed → should be close to 1.0
        assert score == pytest.approx(1.0, abs=0.05)

    def test_only_access_freq(self, scorer):
        score = scorer.compute(
            access_count=50,
            last_accessed_ts=0.0,
            correction_count=0,
            edge_count=0,
        )
        # access_freq weight = 0.4, normalized = 50/100 = 0.5
        # score = 0.5 * 0.4 = 0.2
        assert score == pytest.approx(0.2, abs=0.01)

    def test_only_recency(self, scorer):
        score = scorer.compute(
            access_count=0,
            last_accessed_ts=time.time(),  # Just now
            correction_count=0,
            edge_count=0,
        )
        # recency weight = 0.3, normalized ≈ 1.0
        assert score == pytest.approx(0.3, abs=0.01)

    def test_only_corrections(self, scorer):
        score = scorer.compute(
            access_count=0,
            last_accessed_ts=0.0,
            correction_count=10,
            edge_count=0,
        )
        # correction weight = 0.2, normalized = 10/20 = 0.5
        assert score == pytest.approx(0.1, abs=0.01)

    def test_only_edge_count(self, scorer):
        score = scorer.compute(
            access_count=0,
            last_accessed_ts=0.0,
            correction_count=0,
            edge_count=25,
        )
        # edge weight = 0.1, normalized = 25/50 = 0.5
        assert score == pytest.approx(0.05, abs=0.01)

    def test_normalization_caps_at_one(self, scorer):
        score = scorer.compute(
            access_count=500,  # Way over max
            last_accessed_ts=time.time(),
            correction_count=100,
            edge_count=200,
        )
        assert score <= 1.0

    def test_returns_float_with_4_decimals(self, scorer):
        score = scorer.compute(
            access_count=33,
            last_accessed_ts=time.time() - 3600,
            correction_count=7,
            edge_count=12,
        )
        # Should be rounded to 4 decimal places
        assert score == round(score, 4)
