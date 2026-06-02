"""Shared utilities for Claude Code hooks. Stdlib only — no pip dependencies."""

import collections
import json
import os
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CORTEXBRAIN_URL = os.environ.get("CORTEXBRAIN_URL", "http://127.0.0.1:8000")
CORTEXBRAIN_API_KEY = os.environ.get("CORTEXBRAIN_API_KEY", "test-key")

DEFAULT_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def cortexbrain_post(endpoint: str, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """POST JSON to a CortexBrain API endpoint. Returns parsed response or raises."""
    url = f"{CORTEXBRAIN_URL.rstrip('/')}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CORTEXBRAIN_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cortexbrain_get(endpoint: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """GET from a CortexBrain API endpoint. Returns parsed response or raises."""
    url = f"{CORTEXBRAIN_URL.rstrip('/')}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {CORTEXBRAIN_API_KEY}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Hook I/O
# ---------------------------------------------------------------------------
def read_hook_input() -> dict:
    """Read the JSON object that Claude Code pipes to stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def hook_response(continue_: bool = True, reason: str = "") -> None:
    """Write the hook response JSON to stdout and exit."""
    json.dump({"continue": continue_, "reason": reason}, sys.stdout)
    sys.stdout.flush()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------
def parse_transcript(path: str, max_lines: int = 500) -> list[dict]:
    """Read the last *max_lines* JSONL entries from a transcript file.

    Returns a list of parsed dicts (latest entries last).
    Silently returns [] if the file doesn't exist or is unreadable.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            tail = collections.deque(f, maxlen=max_lines)
    except (OSError, IOError):
        return []

    entries: list[dict] = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def extract_session_knowledge(
    entries: list[dict],
    session_id: str = "",
    cwd: str = "",
    max_turns: int = 10,
    max_chars: int = 4000,
) -> str:
    """Extract the last N user/assistant text turns into a structured summary.

    Skips thinking blocks, tool_use blocks, tool_result blocks, and progress events.
    Returns a string capped at *max_chars*.
    """
    SKIP_TYPES = {"thinking", "tool_use", "tool_result", "progress", "server_tool_use"}

    turns: list[str] = []
    for entry in reversed(entries):
        if len(turns) >= max_turns:
            break

        role = entry.get("role", "")
        if role not in ("user", "assistant"):
            continue

        # entry["content"] can be a string or a list of content blocks
        content = entry.get("content", "")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type", "text") in SKIP_TYPES:
                        continue
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            text = "\n".join(p for p in parts if p).strip()
        else:
            continue

        if not text:
            continue
        turns.append(f"[{role.upper()}]: {text}")

    # Reverse so chronological order is preserved
    turns.reverse()

    header_parts = ["=== Session Context ==="]
    if session_id:
        header_parts.append(f"Session: {session_id}")
    if cwd:
        header_parts.append(f"Working directory: {cwd}")
    header_parts.append(f"Turns captured: {len(turns)}")
    header_parts.append("")

    body = "\n\n".join(turns)
    result = "\n".join(header_parts) + body

    if len(result) > max_chars:
        result = result[: max_chars - 3] + "..."
    return result
