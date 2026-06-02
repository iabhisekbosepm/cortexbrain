"""CortexBrain MCP Server — exposes knowledge tools to Claude Code CLI.

Communicates with CortexBrain's REST API over HTTP.
Runs as a stdio-based MCP server spawned by Claude Code.

Usage:
    python -m cortexbrain.mcp

Environment:
    CORTEXBRAIN_URL      — Base URL (default: http://localhost:8000)
    CORTEXBRAIN_API_KEY  — Bearer token (default: test-key)
"""

import logging
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

# --- All logging → stderr (stdout is reserved for JSON-RPC protocol) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("cortexbrain.mcp")

# --- Configuration ---
CORTEXBRAIN_URL = os.environ.get("CORTEXBRAIN_URL", "http://localhost:8000")
CORTEXBRAIN_API_KEY = os.environ.get("CORTEXBRAIN_API_KEY", "test-key")

# --- MCP Server ---
# Host/port only used when running with SSE transport (Docker); ignored for stdio.
mcp = FastMCP(
    "cortexbrain",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "8001")),
)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {CORTEXBRAIN_API_KEY}",
        "Content-Type": "application/json",
    }


def _format_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    lines = ["\n\nSources:"]
    for s in sources[:10]:  # Cap at 10 to keep output readable
        conf = s.get("confidence", 0.0)
        name = s.get("source_name", "unknown")
        node_id = s.get("node_id", "")
        lines.append(f"  - {name} (confidence: {conf:.0%}, node: {node_id})")
    if len(sources) > 10:
        lines.append(f"  ... and {len(sources) - 10} more")
    return "\n".join(lines)


# ─── Tool: Query ────────────────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_query(query: str, user_id: str = "claude-code") -> str:
    """Query the CortexBrain knowledge base.

    Search the enterprise knowledge graph for information. Returns an answer
    with confidence level and source attribution. Use this to check if the
    knowledge base has information about a topic before answering from scratch.

    Args:
        query: Natural language question to ask the knowledge base
        user_id: Identifier for the querying user (default: claude-code)
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{CORTEXBRAIN_URL}/api/v1/query",
                headers=_headers(),
                json={"query": query, "user_id": user_id},
            )
            resp.raise_for_status()
            data = resp.json()

            answer = data.get("answer", "No answer returned")
            confidence = data.get("confidence", "unknown")
            score = data.get("confidence_score", 0.0)
            fallback = data.get("fallback", False)
            auto_learned = data.get("auto_learned", False)
            sources = data.get("sources", [])

            result = f"{answer}\n\n"
            result += f"Confidence: {confidence} ({score:.0%})"
            if fallback:
                result += " | Fallback mode"
            if auto_learned:
                result += " | Auto-learned (saved for future queries)"
            result += _format_sources(sources)

            return result

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running? Start with: "
                "uvicorn cortexbrain.main:app --reload --port 8000"
            )
        except httpx.HTTPStatusError as e:
            return f"Error querying CortexBrain: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error querying CortexBrain: {e}"


# ─── Tool: Remember ─────────────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_remember(
    text: str,
    dataset_name: str = "claude_code_memory",
    source_type: str = "claude_code",
) -> str:
    """Store text as knowledge in CortexBrain for persistent memory.

    Ingests raw text into the knowledge graph via Cognee's ECL pipeline.
    The text is processed into entities and relationships, making it
    searchable via cortexbrain_query in future sessions.

    Use this to remember facts, decisions, architecture choices, debugging
    insights, or any information that should persist across Claude Code sessions.

    Args:
        text: The text content to store in the knowledge base
        dataset_name: Dataset category for organizing knowledge (default: claude_code_memory)
        source_type: Source identifier (default: claude_code)
    """
    if not text.strip():
        return "Error: Cannot remember empty text."

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{CORTEXBRAIN_URL}/api/v1/ingest/text",
                headers=_headers(),
                json={
                    "text": text,
                    "dataset_name": dataset_name,
                    "source_type": source_type,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "unknown")
            nodes = data.get("nodes_initialized", 0)

            return (
                f"Remembered successfully.\n"
                f"Status: {status}\n"
                f"Dataset: {data.get('dataset', dataset_name)}\n"
                f"Knowledge nodes created: {nodes}\n"
                f"Text length: {data.get('text_length', len(text))} chars"
            )

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?"
            )
        except httpx.HTTPStatusError as e:
            return f"Error storing knowledge: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error storing knowledge: {e}"


# ─── Tool: Correct ──────────────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_correct(
    node_id: str,
    corrected_value: str,
    reason: str = "",
    user_id: str = "claude-code",
) -> str:
    """Correct a knowledge node in CortexBrain.

    Submit a versioned correction to an existing knowledge node. The old value
    is preserved in the audit trail (PREVIOUS_VERSION edges in Neo4j).

    Args:
        node_id: UUID of the node to correct (from cortexbrain_query sources)
        corrected_value: The new/correct value for the node
        reason: Why this correction is being made
        user_id: Who is making the correction (default: claude-code)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{CORTEXBRAIN_URL}/api/v1/correct",
                headers=_headers(),
                json={
                    "node_id": node_id,
                    "corrected_value": corrected_value,
                    "user_id": user_id,
                    "reason": reason or "Corrected via Claude Code MCP",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return (
                f"Correction applied.\n"
                f"Node: {data.get('node_id')}\n"
                f"Version: {data.get('version')}\n"
                f"Previous: {data.get('previous_value')}\n"
                f"New: {data.get('new_value')}"
            )

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?"
            )
        except httpx.HTTPStatusError as e:
            return f"Error applying correction: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error applying correction: {e}"


# ─── Tool: Search Sources ───────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_search_sources(
    dataset_name: str = "",
    include_data: bool = False,
) -> str:
    """Search and list knowledge sources (datasets) stored in CortexBrain.

    Lists all datasets/sources that have been ingested into the knowledge base.
    Use this to find what sources exist (e.g. "context_memory", "claude_code_memory",
    "auto_learned") and optionally see the data items within a specific dataset.

    Examples:
        - cortexbrain_search_sources() → list all datasets
        - cortexbrain_search_sources(dataset_name="context") → filter by name
        - cortexbrain_search_sources(dataset_name="context_memory", include_data=True) → show data items

    Args:
        dataset_name: Filter datasets by name (substring match). Empty = list all.
        include_data: If True and dataset_name matches exactly one dataset, also list its data items.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: List datasets (with optional name filter)
            params = {}
            if dataset_name:
                params["name"] = dataset_name

            resp = await client.get(
                f"{CORTEXBRAIN_URL}/api/v1/datasets",
                headers=_headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            datasets = data.get("datasets", [])
            total = data.get("total", 0)

            if total == 0:
                return f"No datasets found{' matching \"' + dataset_name + '\"' if dataset_name else ''}."

            lines = [f"Found {total} dataset(s):\n"]
            for ds in datasets:
                name = ds.get("name", "unknown")
                ds_id = ds.get("id", "")
                created = ds.get("created_at", "")
                updated = ds.get("updated_at", "")
                line = f"  - Dataset: {name}"
                if created:
                    line += f"\n    Source: {name} {created}"
                if updated:
                    line += f"\n    Updated: {updated}"
                line += f"\n    ID: {ds_id}"
                lines.append(line)

            # Step 2: If include_data and exactly one match, fetch data items
            if include_data and total == 1:
                ds_name = datasets[0].get("name", "")
                if ds_name:
                    data_resp = await client.get(
                        f"{CORTEXBRAIN_URL}/api/v1/datasets/{ds_name}/data",
                        headers=_headers(),
                    )
                    if data_resp.status_code == 200:
                        data_result = data_resp.json()
                        items = data_result.get("data", [])
                        lines.append(f"\nData items in '{ds_name}' ({len(items)} total):")
                        for item in items[:20]:  # Cap display at 20
                            item_name = item.get("name", "unknown")
                            item_ext = item.get("extension", "")
                            item_size = item.get("data_size")
                            item_tokens = item.get("token_count")
                            item_created = item.get("created_at", "")
                            detail = f"  - {item_name}"
                            if item_ext:
                                detail += f" ({item_ext})"
                            if item_tokens:
                                detail += f" [{item_tokens} tokens]"
                            if item_size:
                                detail += f" [{item_size} bytes]"
                            if item_created:
                                detail += f" — {item_created}"
                            lines.append(detail)
                        if len(items) > 20:
                            lines.append(f"  ... and {len(items) - 20} more")

            return "\n".join(lines)

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?"
            )
        except httpx.HTTPStatusError as e:
            return f"Error searching sources: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error searching sources: {e}"


# ─── Tool: Query Dataset ───────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_query_dataset(
    dataset_name: str,
    search_filter: str = "",
) -> str:
    """Query what data has been ingested into a specific dataset.

    Returns the dataset metadata and all data items within it. Use this to
    inspect what documents or texts were ingested into a named dataset.

    Examples:
        - cortexbrain_query_dataset(dataset_name="claude_code_memory")
        - cortexbrain_query_dataset(dataset_name="auto_learned", search_filter="docker")

    Args:
        dataset_name: Exact name of the dataset to inspect
        search_filter: Optional substring to filter data item names within the dataset
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(
                f"{CORTEXBRAIN_URL}/api/v1/datasets/{dataset_name}/data",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            ds_info = data.get("dataset", {})
            items = data.get("data", [])
            total = data.get("total", 0)

            # Apply optional search filter on item names
            if search_filter:
                items = [
                    i for i in items
                    if search_filter.lower() in (i.get("name", "")).lower()
                ]

            lines = [
                f"Dataset: {ds_info.get('name', dataset_name)}",
                f"ID: {ds_info.get('id', 'unknown')}",
                f"Created: {ds_info.get('created_at', 'unknown')}",
                f"Total items: {total}",
            ]

            if search_filter:
                lines.append(f"Filtered to: {len(items)} items matching \"{search_filter}\"")

            if not items:
                lines.append("\nNo data items found.")
                return "\n".join(lines)

            # Fetch actual text content for each item (cap at 10 items, 5000 chars each)
            lines.append(f"\nData items ({len(items)}):")
            display_items = items[:10]
            for item in display_items:
                name = item.get("name", "unknown")
                data_id = item.get("id", "")
                ext = item.get("extension", "")
                tokens = item.get("token_count")
                size = item.get("data_size")
                created = item.get("created_at", "")

                header = f"\n--- {name}"
                if ext:
                    header += f" ({ext})"
                if tokens:
                    header += f" [{tokens} tokens]"
                if size:
                    header += f" [{size} bytes]"
                if created:
                    header += f" — {created}"
                lines.append(header)

                # Fetch content
                if data_id:
                    try:
                        content_resp = await client.get(
                            f"{CORTEXBRAIN_URL}/api/v1/data/{data_id}/content",
                            headers=_headers(),
                            params={"max_chars": 5000},
                        )
                        if content_resp.status_code == 200:
                            content_data = content_resp.json()
                            text = content_data.get("content", "")
                            truncated = content_data.get("truncated", False)
                            lines.append(text)
                            if truncated:
                                lines.append("... [truncated to 5000 chars]")
                        else:
                            lines.append("[Content not available — file from different environment]")
                    except Exception:
                        lines.append("[Content not available]")

            if len(items) > 10:
                lines.append(f"\n... and {len(items) - 10} more items (not shown)")

            return "\n".join(lines)

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Dataset '{dataset_name}' not found. Use cortexbrain_search_sources() to list available datasets."
            return f"Error querying dataset: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error querying dataset: {e}"


# ─── Tool: Consolidation ───────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_consolidate() -> str:
    """Trigger a consolidation cycle in CortexBrain.

    Runs the episodic-to-semantic memory consolidation job which:
    - Promotes validated auto-learned knowledge (confidence 0.6 → 0.75)
    - Archives stale low-salience nodes
    - Merges duplicate entities
    - Compresses long version chains

    Returns a task_id that can be polled for status.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{CORTEXBRAIN_URL}/api/v1/consolidation/run",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("task_id", "unknown")
            status = data.get("status", "unknown")

            return (
                f"Consolidation {status}.\n"
                f"Task ID: {task_id}\n"
                f"Poll status: GET /api/v1/consolidation/status/{task_id}"
            )

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?"
            )
        except httpx.HTTPStatusError as e:
            return f"Error triggering consolidation: HTTP {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"Error triggering consolidation: {e}"


# ─── Tool: Health ────────────────────────────────────────────────────────────


@mcp.tool()
async def cortexbrain_health() -> str:
    """Check CortexBrain system health.

    Returns the status of all backing services: Redis, Neo4j, Qdrant,
    PostgreSQL, and LLM gateway.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{CORTEXBRAIN_URL}/api/v1/health")
            resp.raise_for_status()
            data = resp.json()

            overall = data.get("status", "unknown")
            lines = [f"CortexBrain Status: {overall.upper()}"]

            for service in ["redis", "neo4j", "qdrant", "postgres", "llm"]:
                svc = data.get(service, {})
                status = svc.get("status", "unknown")
                latency = svc.get("latency_ms")
                error = svc.get("error")

                line = f"  {service}: {status}"
                if latency is not None:
                    line += f" ({latency:.0f}ms)"
                if error:
                    line += f" — {error}"
                lines.append(line)

            return "\n".join(lines)

        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to CortexBrain at {CORTEXBRAIN_URL}. "
                "Is the server running?\n"
                "Start with: uvicorn cortexbrain.main:app --reload --port 8000"
            )
        except Exception as e:
            return f"Error checking health: {e}"


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
