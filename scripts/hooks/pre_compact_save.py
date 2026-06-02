#!/usr/bin/env python3
"""PreCompact hook: save session knowledge to CortexBrain before compaction.

Reads the conversation transcript, extracts the last N user/assistant turns,
and ingests them into CortexBrain so they survive context compression.

Always returns {"continue": true} — never blocks compaction.
"""

import sys
import os

# Ensure the hooks package is importable
sys.path.insert(0, os.path.dirname(__file__))

from _shared import (
    cortexbrain_get,
    cortexbrain_post,
    extract_session_knowledge,
    hook_response,
    parse_transcript,
    read_hook_input,
)


def main() -> None:
    hook_input = read_hook_input()
    session_id = hook_input.get("session_id", "unknown")
    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")

    # --- Guard: no transcript path ---
    if not transcript_path:
        hook_response(True, "PreCompact: no transcript path provided")
        return

    # --- Parse transcript ---
    entries = parse_transcript(transcript_path)
    if not entries:
        hook_response(True, "PreCompact: no transcript file found")
        return

    # --- Extract knowledge ---
    knowledge = extract_session_knowledge(entries, session_id=session_id, cwd=cwd)
    if not knowledge or len(knowledge) < 50:
        hook_response(True, "PreCompact: not enough session content to save")
        return

    # --- Check existing session_context items for reporting ---
    existing_count = 0
    try:
        ds_resp = cortexbrain_get("/api/v1/datasets/session_context/data", timeout=5)
        existing_count = ds_resp.get("total", 0)
    except Exception:
        pass  # Non-fatal — proceed with save regardless

    # --- Ingest into CortexBrain (async endpoint — returns immediately) ---
    try:
        result = cortexbrain_post(
            "/api/v1/ingest/text/async",
            {
                "text": knowledge,
                "dataset_name": "session_context",
                "source_type": "claude_code_session",
            },
            timeout=10,
        )
        task_id = result.get("task_id", "?")
        hook_response(
            True,
            f"PreCompact: queued {len(knowledge)} chars (task {task_id}), "
            f"dataset has {existing_count + 1} session snapshots",
        )
    except Exception as exc:
        # Never block compaction — log the error in the reason field
        hook_response(True, f"PreCompact: CortexBrain save failed ({type(exc).__name__}: {exc})")


if __name__ == "__main__":
    main()
