"""POST /api/v1/query — Natural language query with activation-based context selection."""

import asyncio
import logging
import os
import re
import uuid
from typing import Any

import cognee
import litellm
from fastapi import APIRouter, Depends

from cortexbrain.api.deps import (
    get_activation_engine,
    get_confidence_gate,
    get_meta_memory,
    get_semantic_memory,
)
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.config import get_settings
from cortexbrain.core.activation import ActivationEngine
from cortexbrain.core.metacognition import ConfidenceGate
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.schemas import (
    ConfidenceLevel,
    GeneratedImage,
    QueryInsights,
    QueryRequest,
    QueryResponse,
    SourceReference,
    TokenUsage,
)
from cortexbrain.services.image_gen import generate_image_answer, should_generate_image

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_entity_names(search_results: list[Any]) -> list[str]:
    """Extract entity names from Cognee search results.

    Cognee search returns varied formats — strings, dicts, or objects.
    We parse out candidate entity names for activation seeding.
    """
    names: list[str] = []
    for r in search_results:
        if isinstance(r, dict):
            name = r.get("name") or r.get("entity_name") or r.get("label", "")
            if name:
                names.append(str(name))
            # Also grab description keywords for broader seeding
            desc = r.get("description", "")
            if desc and len(str(desc)) < 200:
                names.append(str(desc))
            continue
        # String results: extract capitalized phrases as entity candidates
        text = str(r)
        # Title-cased multi-word phrases
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        names.extend(caps[:8])
        # Uppercase acronyms (MFCA, BFS, REST, LLM, etc.)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        names.extend(acronyms[:5])
        # Also use the full text as a potential entity name
        if len(text) < 100:
            names.append(text.strip())
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for n in names:
        lower = n.lower()
        if lower not in seen and n.strip():
            seen.add(lower)
            unique.append(n)
    return unique[:30]  # Cap at 30 entities


def _extract_query_bigrams(query: str) -> list[str]:
    """Extract bigrams from query text for better entity matching.

    E.g., 'spreading activation algorithm' → ['spreading activation', 'activation algorithm']
    """
    words = [w for w in query.split() if len(w) > 2]
    bigrams = []
    for i in range(len(words) - 1):
        bigrams.append(f"{words[i]} {words[i + 1]}")
    return bigrams


def _node_text(node: dict[str, Any]) -> str:
    """Extract display text from a node (Cognee uses 'description', not 'value')."""
    return str(
        node.get("description", "")
        or node.get("value", "")
        or node.get("name", "")
    )


async def _try_image_answer(
    query_text: str, context: str = "",
) -> tuple[str | None, list[GeneratedImage]]:
    """Try to get a combined text+image answer. Returns (answer_text, images).

    Returns (None, []) if image gen is not requested or fails.
    Never raises — falls back gracefully so the text-only path still works.
    """
    settings = get_settings()
    if not settings.image_gen_enabled or not should_generate_image(query_text):
        return None, []
    try:
        result = await generate_image_answer(
            prompt=query_text, context=context, model=settings.image_gen_model,
        )
        if result is not None:
            images = [result.image] if result.image else []
            logger.info("Image answer generated for query: %s", query_text[:60])
            return result.text or None, images
    except Exception as e:
        logger.warning("Image answer failed (non-blocking): %s", e)
    return None, []


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    api_key: str = Depends(verify_api_key),
    activation_engine: ActivationEngine = Depends(get_activation_engine),
    confidence_gate: ConfidenceGate = Depends(get_confidence_gate),
    meta_memory: MetaMemoryStore = Depends(get_meta_memory),
    semantic_memory: SemanticMemoryStore = Depends(get_semantic_memory),
):
    """Query CortexBrain with natural language.

    Full hybrid pipeline:
    1. Cognee vector+graph search → find relevant entities
    2. Extract entity names → seed list for activation
    3. Spreading activation → weighted BFS over knowledge graph
    4. Enrich with M_meta → confidence/salience/conflicted from PostgreSQL
    5. Confidence gate → weighted average confidence
    6. Access tracking → record_access for each used node
    7. LLM generation → context from activated nodes with confidence prefix
    8. Source attribution → SourceReference list
    """
    session_id = request.session_id or str(uuid.uuid4())

    # --- Step 1: Cognee search ---
    try:
        search_results = await cognee.search(query_text=request.query)
    except Exception as e:
        logger.warning("Cognee search failed: %s", e)
        search_results = []

    # --- Step 1b: Neo4j text search for corrected nodes ---
    # Corrected node descriptions may contain terms not in Cognee's vector index.
    # Search the graph directly by text to catch these.
    graph_text_nodes: list[dict[str, Any]] = []
    try:
        search_terms = [w for w in request.query.split() if len(w) > 2]
        graph_text_nodes = await semantic_memory.search_nodes_by_text(search_terms)
        if graph_text_nodes:
            logger.info("Graph text search found %d nodes for query", len(graph_text_nodes))
    except Exception as e:
        logger.warning("Graph text search failed: %s", e)

    # --- Step 2: Extract entity names ---
    entity_names = _extract_entity_names(search_results) if search_results else []
    # Add query bigrams for multi-word entity matching
    bigrams = _extract_query_bigrams(request.query)
    for bg in bigrams:
        if bg.lower() not in {n.lower() for n in entity_names}:
            entity_names.append(bg)
    # Also add the raw query words as fallback entity candidates
    query_words = [w for w in request.query.split() if len(w) > 3]
    entity_names.extend(query_words[:15])
    # Add uppercase acronyms from the query itself
    query_acronyms = re.findall(r"\b[A-Z]{2,}\b", request.query)
    for acr in query_acronyms:
        if acr.lower() not in {n.lower() for n in entity_names}:
            entity_names.append(acr)
    # Add names from graph text search results
    for gnode in graph_text_nodes:
        name = gnode.get("name", "")
        if name and name.lower() not in {n.lower() for n in entity_names}:
            entity_names.append(name)

    # --- Step 3: Spreading activation ---
    activated_nodes: list[dict[str, Any]] = []
    fallback = False

    if entity_names:
        try:
            activated_nodes = await activation_engine.activate_for_query(
                session_id=session_id,
                entities=entity_names,
            )
        except Exception as e:
            logger.warning("Activation engine failed: %s", e)

    # --- Fallback: if activation finds nothing, use graph text nodes or raw Cognee results ---
    if not activated_nodes and graph_text_nodes:
        # Graph text search found corrected/matching nodes — use them directly
        fallback = True
        activation_mode = "graph_text"
        context_parts = []
        sources: list[SourceReference] = []
        for gnode in graph_text_nodes:
            text = _node_text(gnode)
            name = str(gnode.get("name", "unknown"))
            conf = float(gnode.get("confidence", 0.7))
            sal = float(gnode.get("salience", 0.5))
            context_parts.append(f"[{name}]: {text}")
            node_id_str = str(gnode.get("id", ""))
            if node_id_str:
                try:
                    sources.append(
                        SourceReference(
                            node_id=uuid.UUID(node_id_str),
                            source_name=name,
                            confidence=conf,
                            salience=sal,
                            description=text[:200] if text else None,
                            conflicted=bool(gnode.get("conflicted", False)),
                        )
                    )
                except ValueError:
                    pass
        context = "\n".join(f"- {part}" for part in context_parts)
        avg_confidence = 0.7
        confidence_tier = ConfidenceLevel.MEDIUM
    elif not activated_nodes and search_results:
        fallback = True
        activation_mode = "vector"
        context_parts = [str(r) for r in search_results]
        context = "\n".join(f"- {part}" for part in context_parts)
        avg_confidence = 0.5
        confidence_tier = ConfidenceLevel.MEDIUM
        sources = []
    elif not activated_nodes:
        # --- Nothing found: Continuous Learning fallback ---
        settings = get_settings()
        cl_insights = QueryInsights(
            entities_extracted=entity_names[:10],
            activation_mode="continuous_learning",
        )

        # Try combined image+text answer first (single model call)
        img_answer, images = await _try_image_answer(request.query)

        if not settings.continuous_learning_enabled:
            return QueryResponse(
                answer=img_answer or "I don't have information about this in our knowledge base.",
                confidence=ConfidenceLevel.LOW,
                confidence_score=0.0,
                sources=[],
                tokens_used=TokenUsage(input=0, output=14),
                session_id=session_id,
                fallback=True,
                insights=cl_insights,
                images=images,
            )

        try:
            from cortexbrain.ingestion.continuous_learning import (
                generate_fallback_answer,
                ingest_learned_knowledge,
            )

            # If image model already provided text, use it; otherwise get CL answer
            if img_answer:
                final_answer = img_answer
            else:
                fallback_answer, usage = await generate_fallback_answer(request.query)
                # Fire-and-forget background ingestion
                asyncio.create_task(
                    ingest_learned_knowledge(request.query, fallback_answer, session_id)
                )
                prefix = (
                    "I don't have this in my knowledge base yet, but based on "
                    "general knowledge: "
                )
                final_answer = prefix + fallback_answer

            return QueryResponse(
                answer=final_answer,
                confidence=ConfidenceLevel.LOW,
                confidence_score=settings.continuous_learning_confidence,
                sources=[],
                tokens_used=TokenUsage(
                    input=len(request.query) // 4,
                    output=len(final_answer) // 4,
                ),
                session_id=session_id,
                fallback=True,
                auto_learned=not bool(img_answer),
                insights=cl_insights,
                images=images,
            )
        except Exception as e:
            logger.warning("Continuous learning fallback failed: %s", e)
            return QueryResponse(
                answer=img_answer or "I don't have information about this in our knowledge base.",
                confidence=ConfidenceLevel.LOW,
                confidence_score=0.0,
                sources=[],
                tokens_used=TokenUsage(input=0, output=14),
                session_id=session_id,
                fallback=True,
                insights=cl_insights,
                images=images,
            )
    else:
        # --- Step 4: Enrich with M_meta ---
        activation_mode = "spreading"
        enriched_nodes: list[dict[str, Any]] = []
        for node in activated_nodes:
            node_id_str = str(node.get("id", ""))
            if not node_id_str:
                enriched_nodes.append(node)
                continue
            try:
                node_uuid = uuid.UUID(node_id_str)
                meta = await meta_memory.get_or_create_metadata(
                    node_id=node_uuid,
                    org_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                )
                node["confidence"] = meta.confidence
                node["salience"] = meta.salience
                node["conflicted"] = meta.conflicted
            except Exception as e:
                logger.debug("M_meta lookup failed for %s: %s", node_id_str, e)
            enriched_nodes.append(node)

        # --- Step 5: Confidence gate ---
        avg_confidence, confidence_tier = confidence_gate.compute_aggregate_confidence(
            enriched_nodes
        )

        # --- Step 6: Access tracking ---
        for node in enriched_nodes:
            node_id_str = str(node.get("id", ""))
            if node_id_str:
                try:
                    await meta_memory.record_access(uuid.UUID(node_id_str))
                except Exception:
                    pass  # Non-critical — don't fail query for tracking

        # --- Build sources from ALL activated nodes (for insights panel) ---
        sources = []
        for node in enriched_nodes:
            text = _node_text(node)
            name = str(node.get("name", "unknown"))
            score = node.get("activation_score", 0.0)
            conf = node.get("confidence", 0.5)
            sal = node.get("salience", 0.5)
            node_id_str = str(node.get("id", ""))
            if node_id_str:
                try:
                    sources.append(
                        SourceReference(
                            node_id=uuid.UUID(node_id_str),
                            source_name=name,
                            confidence=conf,
                            activation_score=score,
                            salience=sal,
                            description=text[:200] if text else None,
                            conflicted=bool(node.get("conflicted", False)),
                        )
                    )
                except ValueError:
                    pass

        # --- Build LLM context from TOP nodes (sorted by score + salience) ---
        # Use a token budget (~2000 tokens ≈ 8000 chars) to include as many
        # relevant nodes as possible without overwhelming the LLM.
        MAX_CONTEXT_CHARS = 20000
        MIN_DESCRIPTION_LEN = 2  # skip only truly empty nodes
        ranked_nodes = sorted(
            enriched_nodes,
            key=lambda n: (n.get("activation_score", 0), n.get("salience", 0)),
            reverse=True,
        )
        context_parts = []
        context_chars = 0
        for node in ranked_nodes:
            text = _node_text(node)
            name = str(node.get("name", "unknown"))
            # Skip empty, trivial, or single-word descriptions
            if not text or text == name or len(text) < MIN_DESCRIPTION_LEN:
                continue
            part = f"[{name}]: {text}"
            if context_chars + len(part) > MAX_CONTEXT_CHARS:
                break
            context_parts.append(part)
            context_chars += len(part)

        context = "\n".join(f"- {part}" for part in context_parts)

    # --- Step 7: Confidence prefix ---
    prefix = confidence_gate.format_confidence_prefix(confidence_tier)

    # --- Step 8: LLM generation (combined text+image if image requested) ---
    images: list[GeneratedImage] = []
    img_text, images = await _try_image_answer(request.query, context)

    if img_text:
        # Image model provided both text and image — use its text answer
        answer = prefix + img_text
    else:
        # Standard text-only LLM path
        try:
            llm_model = os.environ.get("LLM_MODEL", "gemini/gemini-2.0-flash")
            response = await litellm.acompletion(
                model=llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
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
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {request.query}",
                    },
                ],
            )
            answer = prefix + response.choices[0].message.content
        except Exception as e:
            logger.warning("LLM generation failed: %s", e)
            # Build a clean fallback from the top context parts (already filtered/ranked)
            if context_parts:
                clean_parts = []
                for part in context_parts[:5]:
                    if "]: " in part:
                        clean_parts.append(part.split("]: ", 1)[1])
                    else:
                        clean_parts.append(part)
                answer = prefix + "Based on available knowledge: " + ". ".join(
                    p.rstrip(".") for p in clean_parts if p
                ) + "."
            else:
                answer = prefix + "I found relevant information but couldn't generate a summary. Please check the source nodes below."

    # --- Step 9: Low-confidence fallback → Continuous Learning ---
    settings = get_settings()

    _cant_answer_phrases = (
        "i'm sorry", "i am sorry", "i don't have", "i do not have",
        "does not contain", "doesn't contain", "no information",
        "not mentioned", "cannot answer", "can't answer",
        "cannot be answered", "can't be answered",
        "not available in", "not found in", "not in the context",
        "context does not", "context doesn't",
        "don't have information", "no relevant information",
    )
    answer_lower = answer.lower()

    if (
        settings.continuous_learning_enabled
        and avg_confidence < 0.9
        and any(phrase in answer_lower for phrase in _cant_answer_phrases)
    ):
        try:
            from cortexbrain.ingestion.continuous_learning import (
                generate_fallback_answer,
                ingest_learned_knowledge,
            )

            fallback_answer, usage = await generate_fallback_answer(request.query)

            asyncio.create_task(
                ingest_learned_knowledge(request.query, fallback_answer, session_id)
            )

            cl_prefix = (
                "I don't have this in my knowledge base yet, but based on "
                "general knowledge: "
            )

            return QueryResponse(
                answer=cl_prefix + fallback_answer,
                confidence=ConfidenceLevel.LOW,
                confidence_score=settings.continuous_learning_confidence,
                sources=[],
                tokens_used=TokenUsage(
                    input=usage.get("input", len(request.query) // 4),
                    output=usage.get("output", len(fallback_answer) // 4),
                ),
                session_id=session_id,
                fallback=True,
                auto_learned=True,
                insights=QueryInsights(
                    entities_extracted=entity_names[:10],
                    activation_mode="continuous_learning",
                ),
                images=images,
            )
        except Exception as e:
            logger.warning("Continuous learning (post-LLM) failed: %s", e)

    # --- Compute query insights ---
    insights = QueryInsights(
        total_nodes_activated=len(sources),
        entities_extracted=entity_names[:10],
        activation_mode=activation_mode,
        max_activation_score=max((s.activation_score or 0 for s in sources), default=0),
        avg_salience=sum(s.salience or 0 for s in sources) / max(len(sources), 1),
    )

    return QueryResponse(
        answer=answer,
        confidence=confidence_tier,
        confidence_score=round(avg_confidence, 4),
        sources=sources,
        tokens_used=TokenUsage(
            input=len(context) // 4,
            output=len(answer) // 4,
        ),
        session_id=session_id,
        fallback=fallback,
        insights=insights,
        images=images,
    )
