"""FastAPI dependency injection for CortexBrain services.

Provides configured instances of memory stores and engines to API routes.
Uses Cognee's existing engine factories where possible.
"""

from cortexbrain.config import get_settings, CortexBrainSettings
from cortexbrain.core.activation import ActivationEngine
from cortexbrain.core.metacognition import ConfidenceGate
from cortexbrain.core.mutation import MutationEngine
from cortexbrain.memory.active import ActiveMemoryStore
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.raw import RawMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore


def get_active_memory() -> ActiveMemoryStore:
    return ActiveMemoryStore()


def get_semantic_memory() -> SemanticMemoryStore:
    return SemanticMemoryStore()


def get_raw_memory() -> RawMemoryStore:
    return RawMemoryStore()


def get_meta_memory() -> MetaMemoryStore:
    return MetaMemoryStore()


def get_activation_engine() -> ActivationEngine:
    return ActivationEngine(
        active_memory=ActiveMemoryStore(),
        semantic_memory=SemanticMemoryStore(),
        raw_memory=RawMemoryStore(),
    )


def get_mutation_engine() -> MutationEngine:
    return MutationEngine(
        semantic_memory=SemanticMemoryStore(),
        meta_memory=MetaMemoryStore(),
    )


def get_confidence_gate() -> ConfidenceGate:
    return ConfidenceGate()


def get_consolidation_engine():
    from cortexbrain.core.consolidation import ConsolidationEngine

    return ConsolidationEngine(
        semantic_memory=SemanticMemoryStore(),
        meta_memory=MetaMemoryStore(),
    )
