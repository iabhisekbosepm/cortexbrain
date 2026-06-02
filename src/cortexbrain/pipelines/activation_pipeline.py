"""Activation pipeline — Cognee Task that runs spreading activation on a query.

Registered as a custom Cognee pipeline task so it can be composed with
other Cognee tasks (e.g., entity extraction, graph search).
"""

from typing import Any

from cognee.modules.pipelines.tasks.task import Task

from cortexbrain.core.activation import ActivationEngine
from cortexbrain.memory.active import ActiveMemoryStore
from cortexbrain.memory.raw import RawMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore


async def run_activation(
    entities: list[str],
    session_id: str = "default",
    initial_score: float = 100.0,
) -> list[dict[str, Any]]:
    """Cognee-compatible task function for spreading activation.

    Usage with Cognee's custom pipeline:
        tasks = [
            Task(extract_entities, ...),
            Task(run_activation, session_id="abc"),
        ]
        await cognee.run_custom_pipeline(tasks=tasks, data=query_text)
    """
    engine = ActivationEngine(
        active_memory=ActiveMemoryStore(),
        semantic_memory=SemanticMemoryStore(),
        raw_memory=RawMemoryStore(),
    )
    return await engine.activate_for_query(session_id, entities, initial_score)


def get_activation_task(session_id: str = "default") -> Task:
    """Factory to create a Cognee Task wrapping the activation engine."""
    return Task(run_activation, session_id=session_id)
