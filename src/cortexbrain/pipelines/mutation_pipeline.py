"""Mutation pipeline — Cognee Task for applying corrections.

Wraps the MutationEngine in a Cognee-compatible task for composability.
"""

from typing import Any
from uuid import UUID

from cognee.modules.pipelines.tasks.task import Task

from cortexbrain.core.mutation import MutationEngine
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore


async def apply_correction(
    node_id: UUID,
    corrected_value: str,
    user_id: str,
    org_id: UUID,
    reason: str = "",
) -> dict[str, Any]:
    """Cognee-compatible task function for the Mutation Engine."""
    engine = MutationEngine(
        semantic_memory=SemanticMemoryStore(),
        meta_memory=MetaMemoryStore(),
    )
    return await engine.apply_correction(node_id, corrected_value, user_id, org_id, reason)


def get_mutation_task() -> Task:
    """Factory to create a Cognee Task wrapping the mutation engine."""
    return Task(apply_correction)
