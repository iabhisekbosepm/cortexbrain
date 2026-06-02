"""Salience Scorer — Calculates importance score for knowledge nodes.

Formula from PRD:
S = (access_freq × 0.4) + (recency × 0.3) + (correction_count × 0.2) + (edge_count × 0.1)

All factors normalized to [0, 1].
"""

import time
from typing import Any

from cortexbrain.config import get_settings


class SalienceScorer:
    """Computes salience scores for knowledge nodes."""

    def __init__(self):
        self.settings = get_settings()

    def compute(
        self,
        access_count: int,
        last_accessed_ts: float,
        correction_count: int,
        edge_count: int,
        max_access_count: int = 100,
        max_correction_count: int = 20,
        max_edge_count: int = 50,
        recency_window_seconds: float = 7 * 24 * 3600,  # 7 days
    ) -> float:
        """Compute normalized salience score in [0, 1].

        New nodes with no access history get a default salience of 0.5
        for a 7-day grace period (per PRD).
        """
        w = self.settings

        # Normalize each factor to [0, 1]
        norm_access = min(access_count / max(max_access_count, 1), 1.0)

        time_since_access = time.time() - last_accessed_ts
        norm_recency = max(1.0 - (time_since_access / max(recency_window_seconds, 1)), 0.0)

        norm_corrections = min(correction_count / max(max_correction_count, 1), 1.0)
        norm_edges = min(edge_count / max(max_edge_count, 1), 1.0)

        salience = (
            norm_access * w.salience_weight_access_freq
            + norm_recency * w.salience_weight_recency
            + norm_corrections * w.salience_weight_correction_count
            + norm_edges * w.salience_weight_edge_count
        )

        return round(salience, 4)
