"""POST /api/v1/query/agent — Agentic AI query with tool-use and SSE streaming.

The LLM decides which CortexBrain tools to call, executes them in sequence,
and streams each step to the frontend as Server-Sent Events. Supports
multi-turn conversation via conversation_history.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

import cognee
import litellm
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from cortexbrain.api.deps import (
    get_activation_engine,
    get_confidence_gate,
    get_meta_memory,
    get_semantic_memory,
)
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.core.activation import ActivationEngine
from cortexbrain.core.metacognition import ConfidenceGate
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.schemas import AgentQueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")
_MAX_TOOL_CALLS = 8
_TOTAL_TIMEOUT = 180.0  # seconds for entire agent run

# Per-tool timeout — batch-optimized operations finish faster now
_TOOL_TIMEOUTS: dict[str, float] = {
    "search_knowledge": 18.0,  # cognee inner timeout 12s + graph search ~2s + margin
    "activate_and_gather": 15.0,  # batch BFS typically <5s
    "search_graph_text": 10.0,
    "find_entity": 10.0,
    "check_confidence": 10.0,
}
_DEFAULT_TOOL_TIMEOUT = 10.0
_MAX_HISTORY_CHARS = 16000
_MAX_TOOL_RESULT_CHARS = 8000

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """\
You are CortexBrain, an enterprise knowledge assistant created by Abhisek Bose.

You answer questions by searching and exploring a knowledge graph. You have tools \
available to search, find entities, traverse the graph, check confidence, and review \
audit history.

CRITICAL: Do NOT answer after just 1-2 tool calls. You MUST explore thoroughly before \
answering. Use at least 3-4 tools to gather comprehensive information. A single search \
result is never enough — always run activate_and_gather to discover related context.

WORKFLOW (follow ALL steps before answering):
1. SEARCH: Start with search_knowledge for broad queries, find_entity for specific names, \
or search_graph_text for keyword search. If one tool returns an error or no results, \
try another search tool before giving up.
2. ACTIVATE (REQUIRED): Always use activate_and_gather on the key entities found in step 1. \
This discovers related nodes through spreading activation and is essential for comprehensive answers.
3. DETAIL: Use get_node_detail or get_neighbors on the most relevant nodes to get full context.
4. ASSESS: Use check_confidence to verify the reliability of your sources.
5. HISTORY (if relevant): If asked about changes/audit, use get_version_history or get_audit_logs.
6. ANSWER: Only after steps 1-4, synthesize your findings into a comprehensive answer.

RULES:
- Always cite which nodes/sources informed your answer.
- If a tool returns an error or times out, try an alternative tool. Do not give up after one failure.
- If the knowledge base truly has no relevant information after trying multiple tools, say so clearly.
- Preserve exact technical terms, abbreviations, and numeric values from sources.
- Do NOT make up information. Only use what you find from tools.
- Keep tool call arguments minimal, but make your FINAL answer comprehensive and detailed.
- Use markdown formatting for readability.

ANSWER FORMAT (when giving your final answer):
- Provide a thorough, detailed answer that covers ALL relevant information found.
- CRITICAL: Preserve exact technical terms, abbreviations, and numeric values \
(e.g., write 'BFS' not 'breadth-first', '0.5' not 'half', 'PREVIOUS_VERSION' not 'prior version').
- Include specific thresholds, formulas, weights, and configuration values when present.
- Use clear paragraphs and structure. Use bullet points or numbered lists for multiple items.
- Synthesize information from multiple tool results into a coherent narrative.
- Write as if explaining to a knowledgeable colleague who wants the full technical picture.
- Do NOT list raw tool outputs back. Synthesize them into flowing text.
"""

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the knowledge base using vector + graph search. Use this first for any factual question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "The search query"},
                },
                "required": ["query_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_entity",
            "description": "Find specific entity nodes by name in the knowledge graph. Case-insensitive substring match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Entity name to search for"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_graph_text",
            "description": "Text search across entity names and descriptions in the graph. Good for finding corrected or recently updated nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search terms",
                    },
                },
                "required": ["terms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node_detail",
            "description": "Get full details of a specific node by UUID, including metadata (confidence, salience, access count).",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "UUID of the node"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_neighbors",
            "description": "Get neighboring nodes connected to a given node in the knowledge graph. Use for exploring related concepts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "UUID of the node"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_version_history",
            "description": "Get the correction/version history of a node. Use when asked about changes, audit trail, or who modified what.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "UUID of the node"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "activate_and_gather",
            "description": "Run spreading activation from entity names to find the most relevant connected knowledge. Returns ranked nodes with activation scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Entity names to seed activation from",
                    },
                },
                "required": ["entity_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_confidence",
            "description": "Compute aggregate confidence score for a set of nodes. Returns confidence level (high/medium/low/conflicted) and numeric score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "UUIDs of nodes to evaluate",
                    },
                },
                "required": ["node_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_audit_logs",
            "description": "Retrieve recent audit logs from meta memory. Use when asked about what changed, when, or by whom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "ISO date string (optional)"},
                    "end_date": {"type": "string", "description": "ISO date string (optional)"},
                },
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Human-readable step labels
# ---------------------------------------------------------------------------

_STEP_LABELS = {
    "search_knowledge": "Searching knowledge base",
    "find_entity": "Finding entity",
    "search_graph_text": "Searching graph by text",
    "get_node_detail": "Getting node details",
    "get_neighbors": "Exploring connected nodes",
    "get_version_history": "Checking version history",
    "activate_and_gather": "Running spreading activation",
    "check_confidence": "Evaluating confidence",
    "get_audit_logs": "Retrieving audit logs",
}


def _human_readable_step(tool_name: str, arguments: dict) -> str:
    label = _STEP_LABELS.get(tool_name, tool_name)
    if tool_name == "search_knowledge":
        return f'{label} for "{arguments.get("query_text", "")}"'
    if tool_name == "find_entity":
        return f'{label} "{arguments.get("name", "")}"'
    if tool_name == "search_graph_text":
        terms = arguments.get("terms", [])
        return f'{label}: {", ".join(terms[:5])}'
    if tool_name == "activate_and_gather":
        entities = arguments.get("entity_names", [])
        return f'{label} on {len(entities)} entities'
    if tool_name == "check_confidence":
        node_ids = arguments.get("node_ids", [])
        return f'{label} for {len(node_ids)} nodes'
    if tool_name in ("get_node_detail", "get_neighbors", "get_version_history"):
        nid = arguments.get("node_id", "")
        return f'{label}: {nid[:8]}...'
    return label


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# ---------------------------------------------------------------------------
# SSE formatting
# ---------------------------------------------------------------------------


def _sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _node_text(node: dict[str, Any]) -> str:
    return str(node.get("description", "") or node.get("value", "") or node.get("name", ""))


def _format_node(node: dict[str, Any]) -> dict:
    return {
        "id": str(node.get("id", "")),
        "name": str(node.get("name", "")),
        "description": _truncate(_node_text(node), 1000),
    }


async def _dispatch_tool(
    tool_name: str,
    arguments: dict,
    *,
    semantic: SemanticMemoryStore,
    activation: ActivationEngine,
    confidence_gate: ConfidenceGate,
    meta: MetaMemoryStore,
    session_id: str,
) -> str:
    """Execute a tool call and return a JSON string result."""

    if tool_name == "search_knowledge":
        query_text = arguments["query_text"]

        # Run Cognee search + graph text search in parallel, each with its own
        # timeout so one slow path doesn't block the other.
        async def _cognee_search():
            try:
                return await asyncio.wait_for(
                    cognee.search(query_text=query_text), timeout=12.0
                )
            except asyncio.TimeoutError:
                logger.warning("Cognee vector search timed out after 12s, using graph results only")
                return []
            except Exception as e:
                logger.warning("Cognee search failed: %s", e)
                return []

        async def _graph_search():
            try:
                terms = [w for w in query_text.split() if len(w) > 2][:6]
                return await semantic.search_nodes_by_text(terms) if terms else []
            except Exception as e:
                logger.warning("Graph text search failed: %s", e)
                return []

        cognee_results, graph_nodes = await asyncio.gather(
            _cognee_search(), _graph_search()
        )

        # Merge: graph nodes (structured with IDs) take priority
        formatted = []
        seen_ids: set[str] = set()

        # Add graph nodes first (they have proper id, name, description)
        for n in graph_nodes[:10]:
            node_data = _format_node(n)
            nid = node_data["id"]
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                formatted.append(node_data)

        # Add Cognee results (may be dicts or raw strings)
        for r in cognee_results[:10]:
            if isinstance(r, dict):
                nid = str(r.get("id", ""))
                if nid and nid in seen_ids:
                    continue
                if nid:
                    seen_ids.add(nid)
                formatted.append({
                    "name": str(r.get("name", r.get("entity_name", ""))),
                    "description": _truncate(str(r.get("description", "")), 200),
                    "id": nid,
                })
            else:
                formatted.append({"text": _truncate(str(r), 200)})

        if not formatted:
            return json.dumps({"results": [], "message": "No results found"})
        return json.dumps({"results": formatted[:15], "count": len(formatted)})

    if tool_name == "find_entity":
        nodes = await semantic.find_nodes_by_name(arguments["name"])
        formatted = [_format_node(n) for n in nodes[:10]]
        return json.dumps({"nodes": formatted, "count": len(nodes)})

    if tool_name == "search_graph_text":
        nodes = await semantic.search_nodes_by_text(arguments["terms"])
        formatted = [_format_node(n) for n in nodes[:10]]
        return json.dumps({"nodes": formatted, "count": len(nodes)})

    if tool_name == "get_node_detail":
        node = await semantic.get_node(UUID(arguments["node_id"]))
        if node is None:
            return json.dumps({"error": "Node not found"})
        metadata = await meta.get_or_create_metadata(
            node_id=UUID(arguments["node_id"]), org_id=_DEFAULT_ORG
        )
        edge_count = await semantic.get_edge_count(UUID(arguments["node_id"]))
        return json.dumps({
            "id": str(node.get("id", "")),
            "name": str(node.get("name", "")),
            "description": _truncate(_node_text(node), 1000),
            "confidence": metadata.confidence,
            "salience": metadata.salience,
            "conflicted": metadata.conflicted,
            "access_count": metadata.access_count,
            "correction_count": metadata.correction_count,
            "edge_count": edge_count,
        })

    if tool_name == "get_neighbors":
        neighbors = await semantic.get_neighbors_with_weights(UUID(arguments["node_id"]))
        formatted = []
        for node, weight in neighbors[:15]:
            formatted.append({
                **_format_node(node),
                "edge_weight": weight,
            })
        return json.dumps({"neighbors": formatted, "count": len(neighbors)})

    if tool_name == "get_version_history":
        history = await semantic.get_version_history(UUID(arguments["node_id"]))
        versions = []
        for v in history[:10]:
            versions.append({
                "version": v.get("version", 0),
                "value": _truncate(str(v.get("value", "")), 200),
                "changed_by": str(v.get("changed_by", "")),
                "timestamp": str(v.get("timestamp", "")),
                "reason": str(v.get("reason", "")),
            })
        return json.dumps({"versions": versions, "count": len(history)})

    if tool_name == "activate_and_gather":
        nodes = await activation.activate_for_query(
            session_id=session_id,
            entities=arguments["entity_names"],
        )
        formatted = []
        for node in nodes[:30]:
            formatted.append({
                **_format_node(node),
                "activation_score": node.get("activation_score", 0),
            })
        return json.dumps({"activated_nodes": formatted, "count": len(nodes)})

    if tool_name == "check_confidence":
        nodes_data: list[dict[str, Any]] = []
        for nid_str in arguments["node_ids"][:20]:
            try:
                nid = UUID(nid_str)
                node = await semantic.get_node(nid)
                if node:
                    m = await meta.get_or_create_metadata(node_id=nid, org_id=_DEFAULT_ORG)
                    node["confidence"] = m.confidence
                    node["salience"] = m.salience
                    node["conflicted"] = m.conflicted
                    nodes_data.append(node)
            except Exception:
                pass
        if not nodes_data:
            return json.dumps({"confidence_level": "unknown", "score": 0.0, "evaluated": 0})
        avg, tier = confidence_gate.compute_aggregate_confidence(nodes_data)
        return json.dumps({
            "confidence_level": tier.value,
            "score": round(avg, 4),
            "evaluated": len(nodes_data),
        })

    if tool_name == "get_audit_logs":
        start_dt = None
        end_dt = None
        if arguments.get("start_date"):
            start_dt = datetime.fromisoformat(arguments["start_date"]).replace(tzinfo=timezone.utc)
        if arguments.get("end_date"):
            end_dt = datetime.fromisoformat(arguments["end_date"]).replace(tzinfo=timezone.utc)
        logs = await meta.get_audit_logs(
            org_id=_DEFAULT_ORG,
            start_date=start_dt,
            end_date=end_dt,
            limit=20,
        )
        entries = []
        for log in logs:
            entries.append({
                "action": log.action,
                "node_id": str(log.node_id),
                "changed_by": log.changed_by,
                "reason": _truncate(log.reason or "", 100),
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "version": log.version,
            })
        return json.dumps({"logs": entries, "count": len(logs)})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------


def _compute_answer_confidence(
    collected_sources: list[dict],
    confidence_gate: ConfidenceGate,
) -> tuple[float, str, bool]:
    """Compute confidence from collected source nodes.

    Returns (score, level_string, is_fallback).
    """
    if not collected_sources:
        return 0.3, "low", True

    confidences = [s.get("confidence", 0.5) for s in collected_sources]
    avg = sum(confidences) / len(confidences)

    if avg >= 0.8:
        level = "high"
    elif avg >= 0.5:
        level = "medium"
    else:
        level = "low"

    return round(avg, 4), level, False


# ---------------------------------------------------------------------------
# Synthesis — build rich context from collected sources and generate answer
# ---------------------------------------------------------------------------

_SYNTHESIS_SYSTEM_PROMPT = (
    "You are CortexBrain created by Abhisek Bose, an enterprise knowledge assistant. "
    "Answer based ONLY on the provided context. "
    "If the context doesn't contain the answer, say so.\n\n"
    "Guidelines:\n"
    "- Provide a thorough, detailed answer that covers all relevant information from the context.\n"
    "- CRITICAL: Preserve exact technical terms, abbreviations, and numeric values from the context "
    "(e.g., write 'BFS' not 'breadth-first', '0.5' not 'half', 'PREVIOUS_VERSION' not 'prior version').\n"
    "- Include specific thresholds, formulas, weights, and configuration values when present in context.\n"
    "- Use clear paragraphs and structure. Use bullet points or numbered lists when listing multiple items.\n"
    "- Synthesize information from multiple context sources into a coherent narrative.\n"
    "- Do NOT list raw context items back. Do NOT include bracketed source names or metadata.\n"
    "- Write as if explaining to a knowledgeable colleague who wants the full technical picture."
)

_MAX_SYNTHESIS_CONTEXT_CHARS = 20000


async def _synthesize_answer(
    query: str,
    collected_sources: list[dict],
    semantic: SemanticMemoryStore,
    meta: MetaMemoryStore,
    confidence_gate: ConfidenceGate,
    activation: ActivationEngine | None = None,
    session_id: str = "",
) -> str:
    """Build a rich context from collected sources and generate a comprehensive answer.

    Expands the agent's collected sources via a quick activation pass (now
    batch-optimized, typically <3s) to match the context richness of the
    normal /query endpoint.
    """
    # --- Step 1: Run activation on entity names from collected sources ---
    entity_names: list[str] = []
    seen_names: set[str] = set()
    for src in collected_sources:
        name = src.get("source_name", "")
        if name and name != "unknown" and name not in seen_names and len(name) > 1:
            seen_names.add(name)
            entity_names.append(name)
    entity_names = entity_names[:5]

    activated_nodes: list[dict[str, Any]] = []
    if activation and entity_names:
        try:
            activated_nodes = await asyncio.wait_for(
                activation.activate_for_query(
                    session_id=session_id or "synthesis",
                    entities=entity_names,
                ),
                timeout=8.0,  # batch BFS is fast now (~2s)
            )
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("Synthesis activation failed: %s", e)

    # --- Step 2: Merge activated nodes with collected sources ---
    seen_ids: set[str] = set()
    enriched_nodes: list[dict[str, Any]] = []

    # Add activated nodes first (they have full data + activation_score)
    for node in activated_nodes:
        nid = str(node.get("id", ""))
        if nid and nid not in seen_ids:
            seen_ids.add(nid)
            try:
                m = await meta.get_or_create_metadata(node_id=UUID(nid), org_id=_DEFAULT_ORG)
                node["confidence"] = m.confidence
                node["salience"] = m.salience
            except Exception:
                pass
            enriched_nodes.append(node)

    # Add any collected sources not already in activated set
    missing_ids = [
        src.get("node_id", "") for src in collected_sources
        if src.get("node_id") and src["node_id"] not in seen_ids
    ]
    if missing_ids:
        nodes_map = await semantic.get_nodes_batch([UUID(nid) for nid in missing_ids])
        for nid in missing_ids:
            node = nodes_map.get(nid)
            if not node:
                continue
            seen_ids.add(nid)
            try:
                m = await meta.get_or_create_metadata(node_id=UUID(nid), org_id=_DEFAULT_ORG)
                node["confidence"] = m.confidence
                node["salience"] = m.salience
            except Exception:
                pass
            enriched_nodes.append(node)

    if not enriched_nodes:
        return "I was unable to gather enough context from the knowledge base to provide a detailed answer."

    # Sort by activation score + salience (same as /query endpoint)
    ranked = sorted(
        enriched_nodes,
        key=lambda n: (n.get("activation_score", 0), n.get("salience", 0)),
        reverse=True,
    )

    # Build context string with token budget
    context_parts: list[str] = []
    context_chars = 0
    for node in ranked:
        text = str(node.get("description", "") or node.get("value", "") or node.get("name", ""))
        name = str(node.get("name", "unknown"))
        if not text or text == name or len(text) < 2:
            continue
        part = f"[{name}]: {text}"
        if context_chars + len(part) > _MAX_SYNTHESIS_CONTEXT_CHARS:
            break
        context_parts.append(part)
        context_chars += len(part)

    context = "\n".join(f"- {part}" for part in context_parts)

    # Generate answer with same quality prompt as /query endpoint
    llm_model = os.environ.get("LLM_MODEL", "gemini/gemini-2.0-flash")
    try:
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Synthesis LLM call failed: %s", e)
        return "I encountered an error generating the final answer. Please check the reasoning steps above."


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


async def _run_agent_loop(
    query: str,
    conversation_history: list[dict[str, str]],
    session_id: str,
    *,
    semantic: SemanticMemoryStore,
    activation: ActivationEngine,
    confidence_gate: ConfidenceGate,
    meta: MetaMemoryStore,
) -> AsyncGenerator[str, None]:
    """SSE generator that streams agent steps and final answer."""

    start_time = time.monotonic()

    # Build messages: system + conversation history + current query
    messages: list[dict[str, Any]] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

    # Append conversation history (capped by chars)
    chars_used = 0
    for msg in conversation_history[-10:]:
        msg_chars = len(msg.get("content", ""))
        if chars_used + msg_chars > _MAX_HISTORY_CHARS:
            break
        messages.append({"role": msg["role"], "content": msg["content"]})
        chars_used += msg_chars

    messages.append({"role": "user", "content": query})

    tool_call_count = 0
    collected_sources: list[dict] = []
    tools_used: set[str] = set()
    nudge_count = 0
    _MAX_NUDGES = 2
    llm_model = os.environ.get("LLM_MODEL", "gemini/gemini-2.0-flash")

    while tool_call_count < _MAX_TOOL_CALLS:
        # Check total timeout
        elapsed = time.monotonic() - start_time
        if elapsed > _TOTAL_TIMEOUT:
            break

        # Call LLM with tools
        try:
            response = await litellm.acompletion(
                model=llm_model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.error("LLM call failed in agent loop: %s", e)
            yield _sse_event("error", {"message": f"LLM call failed: {e}"})
            yield _sse_event("done", {})
            return

        choice = response.choices[0]
        message = choice.message

        # If no tool calls, check if the agent explored enough before answering
        if not message.tool_calls:
            # Nudge the LLM to keep exploring if it hasn't used activate_and_gather
            has_searched = tools_used & {"search_knowledge", "find_entity", "search_graph_text"}
            has_activated = "activate_and_gather" in tools_used
            if has_searched and not has_activated and nudge_count < _MAX_NUDGES:
                nudge_count += 1
                messages.append({"role": "assistant", "content": message.content or ""})
                messages.append({
                    "role": "user",
                    "content": (
                        "You found search results but haven't used activate_and_gather yet. "
                        "Please run activate_and_gather on the key entity names from your "
                        "search results to discover related context via spreading activation, "
                        "then provide a comprehensive answer."
                    ),
                })
                yield _sse_event("step", {
                    "type": "tool_call",
                    "name": "system",
                    "content": "Requesting deeper exploration via spreading activation...",
                })
                continue

            # Synthesis: build rich context from all collected sources and generate
            yield _sse_event("step", {
                "type": "tool_call",
                "name": "system",
                "content": "Synthesizing comprehensive answer from all gathered context...",
            })
            answer_text = await _synthesize_answer(
                query, collected_sources, semantic, meta, confidence_gate,
                activation=activation, session_id=session_id,
            )
            conf_score, conf_level, is_fallback = _compute_answer_confidence(
                collected_sources, confidence_gate
            )
            yield _sse_event("answer", {
                "answer": answer_text,
                "confidence": conf_level,
                "confidence_score": conf_score,
                "sources": collected_sources,
                "session_id": session_id,
                "fallback": is_fallback,
                "auto_learned": is_fallback and len(collected_sources) == 0,
            })
            yield _sse_event("done", {})
            return

        # Add assistant message with tool_calls to conversation
        messages.append(message.model_dump(exclude_none=True))

        # Process each tool call
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            tool_call_count += 1
            tools_used.add(tool_name)

            # Stream step: tool being called
            yield _sse_event("step", {
                "type": "tool_call",
                "name": tool_name,
                "content": _human_readable_step(tool_name, arguments),
            })

            # Execute the tool with per-tool timeout
            tool_timeout = _TOOL_TIMEOUTS.get(tool_name, _DEFAULT_TOOL_TIMEOUT)
            try:
                result = await asyncio.wait_for(
                    _dispatch_tool(
                        tool_name,
                        arguments,
                        semantic=semantic,
                        activation=activation,
                        confidence_gate=confidence_gate,
                        meta=meta,
                        session_id=session_id,
                    ),
                    timeout=tool_timeout,
                )
            except asyncio.TimeoutError:
                result = json.dumps({"error": f"Tool {tool_name} timed out after {tool_timeout}s"})
            except Exception as e:
                logger.warning("Tool %s failed: %s", tool_name, e)
                result = json.dumps({"error": str(e)})

            # Truncate tool result for messages
            truncated_result = _truncate(result, _MAX_TOOL_RESULT_CHARS)

            # Stream step: tool result (display-friendly truncation)
            yield _sse_event("step", {
                "type": "tool_result",
                "name": tool_name,
                "content": _truncate(result, 500),
            })

            # Track source nodes from tool results
            try:
                parsed = json.loads(result)
                for key in ("nodes", "results", "activated_nodes"):
                    for item in parsed.get(key, []):
                        if isinstance(item, dict) and item.get("id"):
                            collected_sources.append({
                                "node_id": item["id"],
                                "source_name": item.get("name", "unknown"),
                                "confidence": item.get("confidence", 0.7),
                                "activation_score": item.get("activation_score"),
                            })
            except (json.JSONDecodeError, TypeError):
                pass

            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": truncated_result,
            })

    # Max tool calls or timeout reached — use synthesis for comprehensive answer
    yield _sse_event("step", {
        "type": "tool_call",
        "name": "system",
        "content": "Synthesizing comprehensive answer from all gathered context...",
    })
    answer_text = await _synthesize_answer(
        query, collected_sources, semantic, meta, confidence_gate,
        activation=activation, session_id=session_id,
    )
    conf_score, conf_level, is_fallback = _compute_answer_confidence(
        collected_sources, confidence_gate
    )
    yield _sse_event("answer", {
        "answer": answer_text,
        "confidence": conf_level,
        "confidence_score": conf_score,
        "sources": collected_sources,
        "session_id": session_id,
        "fallback": is_fallback,
        "auto_learned": is_fallback and len(collected_sources) == 0,
    })
    yield _sse_event("done", {})


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/query/agent")
async def agent_query(
    request: AgentQueryRequest,
    api_key: str = Depends(verify_api_key),
    activation_engine: ActivationEngine = Depends(get_activation_engine),
    confidence_gate: ConfidenceGate = Depends(get_confidence_gate),
    meta_memory: MetaMemoryStore = Depends(get_meta_memory),
    semantic_memory: SemanticMemoryStore = Depends(get_semantic_memory),
):
    """Agentic query with tool-use and SSE streaming.

    The LLM autonomously decides which tools to call, streams each step,
    and synthesizes a final answer. Supports multi-turn conversation
    via the conversation_history field.
    """
    session_id = request.session_id or str(uuid.uuid4())

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.conversation_history
    ]

    async def event_stream():
        try:
            async for event in _run_agent_loop(
                query=request.query,
                conversation_history=conversation_history,
                session_id=session_id,
                semantic=semantic_memory,
                activation=activation_engine,
                confidence_gate=confidence_gate,
                meta=meta_memory,
            ):
                yield event
        except Exception as e:
            logger.error("Agent query failed: %s", e, exc_info=True)
            yield _sse_event("error", {"message": str(e)})
            yield _sse_event("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
