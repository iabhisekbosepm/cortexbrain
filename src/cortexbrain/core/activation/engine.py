"""Activation Engine — Spreading activation for token-bounded context selection.

Novel CortexBrain layer (not in Cognee). Implements weighted BFS over the
knowledge graph with configurable dampening and threshold.

Core equation: neighbor_activation = source_activation × edge_weight × dampening_factor
"""

import asyncio
from collections import deque
from typing import Any
from uuid import UUID

from cortexbrain.config import get_settings
from cortexbrain.memory.active import ActiveMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.memory.raw import RawMemoryStore


class ActivationEngine:
    """Performs spreading activation over the Cognee knowledge graph.

    Pipeline: entity extraction → graph lookup → spreading activation → token-bounded serialization.
    """

    def __init__(
        self,
        active_memory: ActiveMemoryStore,
        semantic_memory: SemanticMemoryStore,
        raw_memory: RawMemoryStore,
    ):
        self.active = active_memory
        self.semantic = semantic_memory
        self.raw = raw_memory
        self.settings = get_settings()

    async def activate_for_query(
        self,
        session_id: str,
        entities: list[str],
        initial_score: float = 100.0,
    ) -> list[dict[str, Any]]:
        """Run spreading activation starting from extracted entities.

        Steps:
        1. Look up each entity in the knowledge graph (M_s) — parallelized
        2. Assign initial activation scores — batched Redis write
        3. BFS-spread activation to neighbors with dampening — level-batched
        4. Filter by threshold and token budget — uses cached node data
        5. If no graph matches, fall back to vector search (M_r)

        Returns list of activated nodes with scores, bounded by max_context_tokens.
        """
        activated: dict[str, float] = {}
        node_cache: dict[str, dict[str, Any]] = {}  # cache to avoid re-fetching
        seed_nodes: list[dict[str, Any]] = []

        # Step 1 & 2: Find seed nodes from entities — parallelized
        entity_results = await asyncio.gather(
            *(self.semantic.find_nodes_by_name(entity) for entity in entities)
        )
        seed_scores: dict[str, float] = {}
        for matches in entity_results:
            for node in matches:
                node_id = str(node.get("id", ""))
                if node_id:
                    activated[node_id] = initial_score
                    seed_scores[node_id] = initial_score
                    node_cache[node_id] = node
                    seed_nodes.append(node)

        # Batch-activate seeds in Redis
        if seed_scores:
            await self.active.activate_batch(session_id, seed_scores)

        # Step 5: Fallback to vector search if no graph matches
        if not seed_nodes:
            query_text = " ".join(entities)
            return await self.raw.search(query_text, top_k=30)

        # Step 3: Level-batched BFS spreading activation
        dampening = self.settings.dampening_factor
        threshold = self.settings.activation_threshold
        visited: set[str] = set(activated.keys())

        # Process BFS in levels: gather all nodes at current level, batch-fetch
        # their neighbors in one Cypher query, then process the next level.
        current_level: list[tuple[str, float]] = list(activated.items())

        while current_level:
            # Batch-fetch neighbors for all nodes in this level
            level_ids = [UUID(nid) for nid, _ in current_level]
            neighbors_map = await self.semantic.get_neighbors_batch(
                level_ids, limit_per_node=15
            )

            next_level: list[tuple[str, float]] = []
            batch_scores: dict[str, float] = {}

            for current_id, current_score in current_level:
                neighbor_pairs = neighbors_map.get(current_id, [])
                for neighbor_data, edge_weight in neighbor_pairs:
                    neighbor_id = str(neighbor_data.get("id", ""))
                    if not neighbor_id or neighbor_id in visited:
                        continue

                    # Skip archived nodes
                    if str(neighbor_data.get("status", "")) == "archived":
                        visited.add(neighbor_id)
                        continue

                    # Core equation from PRD
                    neighbor_score = current_score * edge_weight * dampening

                    if neighbor_score >= threshold:
                        prev = activated.get(neighbor_id, 0)
                        if neighbor_score > prev:
                            activated[neighbor_id] = neighbor_score
                            batch_scores[neighbor_id] = neighbor_score
                            node_cache[neighbor_id] = neighbor_data
                            next_level.append((neighbor_id, neighbor_score))

                    visited.add(neighbor_id)

            # Batch-activate this level's nodes in Redis
            if batch_scores:
                await self.active.activate_batch(session_id, batch_scores)

            current_level = next_level

        # Step 4: Sort by score, apply token budget using cached node data
        sorted_nodes = sorted(activated.items(), key=lambda x: x[1], reverse=True)
        return await self._apply_token_budget(sorted_nodes, node_cache)

    async def get_session_context(self, session_id: str) -> list[tuple[str, float]]:
        """Get currently active nodes for a session (session-aware priming)."""
        threshold = self.settings.activation_threshold
        return await self.active.get_active_nodes(session_id, min_score=threshold)

    async def _apply_token_budget(
        self,
        scored_nodes: list[tuple[str, float]],
        node_cache: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Truncate activated nodes to fit within max_context_tokens.

        Uses node_cache to avoid re-fetching nodes already seen during BFS.
        Falls back to a batch fetch for any missing nodes.
        """
        max_tokens = self.settings.max_context_tokens
        node_cache = node_cache or {}

        # Batch-fetch any nodes not in cache
        missing_ids = [
            UUID(nid) for nid, _ in scored_nodes if nid not in node_cache
        ]
        if missing_ids:
            fetched = await self.semantic.get_nodes_batch(missing_ids)
            node_cache.update(fetched)

        result: list[dict[str, Any]] = []
        token_count = 0

        for node_id, score in scored_nodes:
            node = node_cache.get(node_id)
            if node is None:
                continue

            # Cognee Entity nodes use "description", not "value"
            node_text = str(
                node.get("description", "") or node.get("value", "") or node.get("name", "")
            )
            # Rough token estimate: 1 token ≈ 4 chars
            estimated_tokens = len(node_text) // 4 + 1

            if token_count + estimated_tokens > max_tokens:
                break

            result.append({**node, "activation_score": score})
            token_count += estimated_tokens

        return result
