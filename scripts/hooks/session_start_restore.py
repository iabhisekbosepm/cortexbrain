#!/usr/bin/env python3
"""SessionStart hook: restore session context from CortexBrain after compaction.

Only activates when source == "compact". Uses the dataset API to directly fetch
the most recent session_context data item, falling back to RAG query if needed.

Always returns {"continue": true} — never blocks session start.
"""

import sys
import os

# Ensure the hooks package is importable
sys.path.insert(0, os.path.dirname(__file__))

from _shared import cortexbrain_get, cortexbrain_post, hook_response, read_hook_input

MAX_RESTORE_CHARS = 10000
MIN_CONFIDENCE = 0.3


def _restore_via_dataset() -> str | None:
    """Fetch the latest session_context data item directly via dataset API."""
    try:
        ds_resp = cortexbrain_get("/api/v1/datasets/session_context/data", timeout=10)
    except Exception:
        return None

    items = ds_resp.get("data", [])
    if not items:
        return None

    # Sort by created_at descending to get the most recent item
    items_sorted = sorted(
        items,
        key=lambda x: x.get("created_at") or "",
        reverse=True,
    )
    latest = items_sorted[0]
    data_id = latest.get("id", "")
    if not data_id:
        return None

    # Fetch the actual content
    try:
        content_resp = cortexbrain_get(
            f"/api/v1/data/{data_id}/content?max_chars={MAX_RESTORE_CHARS}",
            timeout=15,
        )
    except Exception:
        return None

    content = content_resp.get("content", "")
    return content if content else None


def _restore_via_query() -> tuple[str, str] | None:
    """Fallback: RAG query for session context."""
    try:
        result = cortexbrain_post(
            "/api/v1/query",
            {
                "query": "What was the most recent session context? Include key decisions, tasks in progress, and debugging insights.",
                "user_id": "claude-code-hook",
            },
            timeout=30,
        )
    except Exception:
        return None

    confidence_score = result.get("confidence_score", 0.0)
    answer = result.get("answer", "")
    confidence_label = result.get("confidence", "unknown")

    if not answer or confidence_score < MIN_CONFIDENCE:
        return None

    return answer, confidence_label


def main() -> None:
    hook_input = read_hook_input()
    source = hook_input.get("source", "")

    # --- Only activate after compaction ---
    if source != "compact":
        hook_response(True, "")
        return

    # --- Try direct dataset retrieval first (faster, more reliable) ---
    content = _restore_via_dataset()
    if content:
        if len(content) > MAX_RESTORE_CHARS:
            content = content[: MAX_RESTORE_CHARS - 3] + "..."
        hook_response(True, f"[Restored from CortexBrain (dataset: session_context)] {content}")
        return

    # --- Fallback to RAG query ---
    rag_result = _restore_via_query()
    if rag_result:
        answer, confidence_label = rag_result
        if len(answer) > MAX_RESTORE_CHARS:
            answer = answer[: MAX_RESTORE_CHARS - 3] + "..."
        hook_response(True, f"[Restored from CortexBrain (confidence: {confidence_label})] {answer}")
        return

    hook_response(True, "SessionStart: no recent session context found in CortexBrain")


if __name__ == "__main__":
    main()
