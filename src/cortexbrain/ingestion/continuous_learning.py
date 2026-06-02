"""Continuous Learning — auto-ingest Q&A from LLM fallback answers.

When CortexBrain cannot answer a query from its knowledge base, it calls an
unconstrained LLM for a general-knowledge answer. The Q&A pair is then ingested
as new knowledge so future queries can find it.

Design:
- The LLM call is unconstrained (no "answer only from context" constraint)
- Ingestion runs in the background via asyncio.create_task()
- Dedup check prevents learning loops
- Auto-learned knowledge gets lower confidence (0.6) than document-sourced (0.7)
- All auto-learned knowledge is tagged in the audit log for traceability
"""

import logging
import os
from typing import Any
from uuid import UUID

import litellm

from cortexbrain.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


async def generate_fallback_answer(query: str) -> tuple[str, dict[str, int]]:
    """Call an unconstrained LLM to answer a query the knowledge base cannot.

    The system prompt is intentionally general — no "answer only from context"
    constraint. This is the key difference from the normal query pipeline's LLM call.

    Returns (answer_text, {"input": token_count, "output": token_count}).
    """
    model = os.environ.get("LLM_MODEL", "gemini/gemini-2.0-flash")

    response = await litellm.acompletion(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are CortexBrain, an enterprise knowledge assistant. "
                    "Answer the following question using your general knowledge. "
                    "Be accurate, concise, and factual. If you are uncertain "
                    "about something, say so."
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )

    answer = response.choices[0].message.content
    usage = {
        "input": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
        "output": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
    }

    return answer, usage


def format_qa_for_ingestion(query: str, answer: str) -> str:
    """Format a Q&A pair as a structured text document for Cognee ingestion.

    The format is designed to be entity-extractable by Cognee's cognify() pipeline.
    """
    return (
        f"Question: {query}\n\n"
        f"Answer: {answer}\n\n"
        f"Source: Auto-learned from LLM general knowledge. "
        f"This knowledge was generated because no existing knowledge "
        f"was found in the CortexBrain knowledge base for this query."
    )


async def ingest_learned_knowledge(
    query: str, answer: str, session_id: str
) -> None:
    """Background task: ingest a Q&A pair as new knowledge.

    Called via asyncio.create_task() from the query pipeline.
    Failures are logged but never surface to the user.
    """
    try:
        settings = get_settings()

        # Step 1: Dedup check — skip if similar knowledge already exists
        from cortexbrain.memory.semantic import SemanticMemoryStore

        semantic = SemanticMemoryStore()
        search_terms = [w for w in query.split() if len(w) > 3]
        if search_terms:
            existing = await semantic.search_nodes_by_text(search_terms)
            if existing:
                # Check if any existing node's text closely matches the query
                query_lower = {t.lower() for t in search_terms}
                for node in existing:
                    node_text = (
                        str(node.get("description", ""))
                        + " "
                        + str(node.get("name", ""))
                    ).lower()
                    matching = sum(1 for t in query_lower if t in node_text)
                    if matching / len(query_lower) >= 0.8:
                        logger.info(
                            "Continuous learning skipped (similar knowledge exists): query='%s'",
                            query[:80],
                        )
                        return

        # Step 2: Format Q&A for ingestion
        document_text = format_qa_for_ingestion(query, answer)

        # Step 3: Ingest via Cognee pipeline
        from cortexbrain.ingestion.documents import ingest_documents

        result = await ingest_documents(
            data=document_text,
            dataset_name=settings.continuous_learning_dataset,
            org_id=_DEFAULT_ORG,
        )

        # Step 4: Record in audit log
        from cortexbrain.memory.meta import MetaMemoryStore

        meta = MetaMemoryStore()
        await meta.record_mutation(
            org_id=_DEFAULT_ORG,
            node_id=_DEFAULT_ORG,  # System-level action, not tied to a specific node
            action="continuous_learning",
            changed_by="system:auto_learn",
            previous_value="",
            new_value=f"Q: {query[:200]}",
            reason=f"Auto-learned from LLM fallback (session={session_id})",
        )

        logger.info(
            "Continuous learning complete: session=%s, query='%s', result=%s",
            session_id,
            query[:80],
            result,
        )

    except Exception as e:
        logger.warning("Continuous learning ingestion failed: %s", e)
