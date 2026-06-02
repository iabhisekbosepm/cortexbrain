"""Confidence Gate — Confidence-gated response formatting.

Novel CortexBrain layer. Gates responses based on node confidence scores:
- High (>= 0.8): Normal response
- Medium (0.5 - 0.8): Response with verification qualifier
- Low (< 0.5): Explicit low-confidence warning with sources
- Conflicted: Surfaces all conflicting sources
"""

from typing import Any

from cortexbrain.config import get_settings
from cortexbrain.models.schemas import ConfidenceLevel


class ConfidenceGate:
    """Evaluates confidence of activated nodes and determines response framing."""

    def __init__(self):
        self.settings = get_settings()

    def classify(self, confidence_score: float, is_conflicted: bool = False) -> ConfidenceLevel:
        """Classify a confidence score into a tier."""
        if is_conflicted:
            return ConfidenceLevel.CONFLICTED
        if confidence_score >= self.settings.confidence_high:
            return ConfidenceLevel.HIGH
        if confidence_score >= self.settings.confidence_medium:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def compute_aggregate_confidence(
        self, nodes: list[dict[str, Any]]
    ) -> tuple[float, ConfidenceLevel]:
        """Compute weighted average confidence across activated nodes.

        Returns (score, tier).
        """
        if not nodes:
            return 0.0, ConfidenceLevel.LOW

        any_conflicted = any(n.get("conflicted", False) for n in nodes)

        total_weight = 0.0
        weighted_sum = 0.0
        for node in nodes:
            score = float(node.get("confidence", 0.5))
            activation = float(node.get("activation_score", 1.0))
            weighted_sum += score * activation
            total_weight += activation

        avg_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        tier = self.classify(avg_confidence, any_conflicted)

        return avg_confidence, tier

    def format_confidence_prefix(self, tier: ConfidenceLevel) -> str:
        """Return the response prefix based on confidence tier (per PRD spec)."""
        if tier == ConfidenceLevel.HIGH:
            return ""
        if tier == ConfidenceLevel.MEDIUM:
            return (
                "I have moderate confidence in this — "
                "the information may need verification. "
            )
        if tier == ConfidenceLevel.LOW:
            return (
                "I have low confidence in this answer. "
                "The information may be outdated or incomplete. "
            )
        # CONFLICTED
        return (
            "I have conflicting or low-confidence data about this. "
            "Here's what I have from different sources: "
        )
