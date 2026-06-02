"""Semantic Memory (M_s) — Extends Cognee's Neo4j graph with version history edges.

Uses Cognee's GraphDBInterface (via get_graph_engine()) for all standard operations.
Adds CortexBrain-specific methods: version history edges, correction tracking.
"""

import logging
from typing import Any
from uuid import UUID

from cognee.infrastructure.databases.graph import get_graph_engine
from cognee.infrastructure.databases.graph.graph_db_interface import GraphDBInterface

from cortexbrain.models.graph import KnowledgeNode, VersionEdge

logger = logging.getLogger(__name__)


class SemanticMemoryStore:
    """Wraps Cognee's graph engine with CortexBrain's version-history layer."""

    def __init__(self, graph_engine: GraphDBInterface | None = None):
        self._engine = graph_engine

    async def _get_engine(self) -> GraphDBInterface:
        if self._engine is None:
            self._engine = await get_graph_engine()
        return self._engine

    # --- Standard graph operations (delegated to Cognee) ---

    async def get_node(self, node_id: UUID) -> dict[str, Any] | None:
        engine = await self._get_engine()
        try:
            return await engine.get_node(str(node_id))
        except Exception as e:
            logger.warning("get_node failed for %s: %s", node_id, e)
            return None

    async def get_neighbors(self, node_id: UUID) -> list[dict[str, Any]]:
        """Get neighbor nodes via raw Cypher (Cognee's get_neighbours is broken)."""
        engine = await self._get_engine()
        query = """
        MATCH (n)-[r]-(neighbor)
        WHERE n.id = $node_id
        RETURN neighbor, type(r) AS rel_type, r.weight AS weight
        """
        try:
            results = await engine.query(query, {"node_id": str(node_id)})
            neighbors = []
            for row in results:
                node_data = row.get("neighbor", row) if isinstance(row, dict) else row
                if isinstance(node_data, dict):
                    node_data.setdefault("weight", row.get("weight", 1.0) if isinstance(row, dict) else 1.0)
                    neighbors.append(node_data)
            return neighbors
        except Exception as e:
            logger.warning("get_neighbors failed for %s: %s", node_id, e)
            return []

    async def get_neighbors_with_weights(
        self, node_id: UUID, limit: int = 25
    ) -> list[tuple[dict[str, Any], float]]:
        """Get neighbor nodes with edge weights for activation spreading."""
        engine = await self._get_engine()
        query = """
        MATCH (n)-[r]-(neighbor)
        WHERE n.id = $node_id
        RETURN neighbor, coalesce(r.weight, 1.0) AS weight
        LIMIT $limit
        """
        try:
            results = await engine.query(
                query, {"node_id": str(node_id), "limit": limit}
            )
            pairs = []
            for row in results:
                if isinstance(row, dict):
                    node_data = row.get("neighbor", {})
                    weight = float(row.get("weight", 1.0))
                    if isinstance(node_data, dict):
                        pairs.append((node_data, weight))
            return pairs
        except Exception as e:
            logger.warning("get_neighbors_with_weights failed for %s: %s", node_id, e)
            return []

    async def get_neighbors_batch(
        self, node_ids: list[UUID], limit_per_node: int = 15
    ) -> dict[str, list[tuple[dict[str, Any], float]]]:
        """Batch-fetch neighbors for multiple nodes in a single Cypher query.

        Returns {node_id_str: [(neighbor_data, weight), ...]}.
        """
        if not node_ids:
            return {}
        engine = await self._get_engine()
        query = """
        UNWIND $node_ids AS nid
        MATCH (n)-[r]-(neighbor)
        WHERE n.id = nid
        WITH nid, neighbor, coalesce(r.weight, 1.0) AS weight
        ORDER BY weight DESC
        WITH nid, collect({neighbor: neighbor, weight: weight})[..$limit] AS pairs
        RETURN nid, pairs
        """
        try:
            results = await engine.query(
                query,
                {
                    "node_ids": [str(nid) for nid in node_ids],
                    "limit": limit_per_node,
                },
            )
            out: dict[str, list[tuple[dict[str, Any], float]]] = {}
            for row in results:
                if not isinstance(row, dict):
                    continue
                nid = str(row.get("nid", ""))
                pairs_raw = row.get("pairs", [])
                pairs = []
                for p in pairs_raw:
                    if isinstance(p, dict):
                        nd = p.get("neighbor", {})
                        w = float(p.get("weight", 1.0))
                        if isinstance(nd, dict):
                            pairs.append((nd, w))
                out[nid] = pairs
            return out
        except Exception as e:
            logger.warning("get_neighbors_batch failed: %s", e)
            return {}

    async def get_nodes_batch(self, node_ids: list[UUID]) -> dict[str, dict[str, Any]]:
        """Batch-fetch node data for multiple IDs in a single Cypher query.

        Returns {node_id_str: node_data}.
        """
        if not node_ids:
            return {}
        engine = await self._get_engine()
        query = """
        UNWIND $node_ids AS nid
        MATCH (n)
        WHERE n.id = nid
        RETURN n
        """
        try:
            results = await engine.query(
                query, {"node_ids": [str(nid) for nid in node_ids]}
            )
            out: dict[str, dict[str, Any]] = {}
            for row in results:
                if isinstance(row, dict):
                    node_data = row.get("n", row)
                    if isinstance(node_data, dict):
                        nid = str(node_data.get("id", ""))
                        if nid:
                            out[nid] = node_data
            return out
        except Exception as e:
            logger.warning("get_nodes_batch failed: %s", e)
            return {}

    async def get_edge_count(self, node_id: UUID) -> int:
        """Count total edges for a node (used by salience scoring)."""
        engine = await self._get_engine()
        query = """
        MATCH (n)-[r]-()
        WHERE n.id = $node_id
        RETURN count(r) AS cnt
        """
        try:
            results = await engine.query(query, {"node_id": str(node_id)})
            if results and isinstance(results[0], dict):
                return int(results[0].get("cnt", 0))
            return 0
        except Exception as e:
            logger.warning("get_edge_count failed for %s: %s", node_id, e)
            return 0

    async def get_all_entity_ids(self) -> list[str]:
        """List all Entity node IDs (for batch salience recomputation)."""
        engine = await self._get_engine()
        query = "MATCH (n:Entity) RETURN n.id AS id"
        try:
            results = await engine.query(query, {})
            return [
                str(row["id"])
                for row in results
                if isinstance(row, dict) and row.get("id")
            ]
        except Exception as e:
            logger.warning("get_all_entity_ids failed: %s", e)
            return []

    async def get_connections(self, node_id: UUID) -> list[tuple]:
        engine = await self._get_engine()
        return await engine.get_connections(node_id)

    # --- CortexBrain-specific: Version History ---

    async def create_version_edge(self, edge: VersionEdge) -> None:
        """Archive current node state and create a PREVIOUS_VERSION edge.

        This is the core of the Mutation Engine's revision pipeline:
        Locate → Version (this method) → Mutate → Meta-Update.
        """
        engine = await self._get_engine()
        await engine.add_edge(
            from_node=edge.source_node_id,
            to_node=edge.target_node_id,
            relationship_name=edge.relationship_name,
            edge_properties={
                "changed_by": edge.changed_by,
                "reason": edge.reason,
                "previous_value": edge.previous_value,
                "new_value": edge.new_value,
            },
        )

    async def get_version_history(self, node_id: UUID) -> list[dict[str, Any]]:
        """Traverse PREVIOUS_VERSION edges to build full version chain.

        Returns ordered list: [current, v(n-1), v(n-2), ...].
        """
        engine = await self._get_engine()
        # Use Cypher query via Cognee's raw query interface
        query = """
        MATCH (current)-[r:PREVIOUS_VERSION*0..]->(version)
        WHERE current.id = $node_id
        RETURN version, r
        ORDER BY version.version DESC
        """
        results = await engine.query(query, {"node_id": str(node_id)})
        return results

    async def update_node_properties(
        self, node_id: UUID, properties: dict[str, Any]
    ) -> None:
        """Update specific properties on an existing node (used by Mutation Engine)."""
        engine = await self._get_engine()
        # Cypher MERGE/SET for property updates
        set_clauses = ", ".join(f"n.{k} = ${k}" for k in properties)
        query = f"MATCH (n) WHERE n.id = $node_id SET {set_clauses}"
        params = {"node_id": str(node_id), **properties}
        await engine.query(query, params)

    async def find_nodes_by_name(self, name: str) -> list[dict[str, Any]]:
        """Find Entity nodes by name (Cognee creates :Entity, not :KnowledgeNode)."""
        try:
            engine = await self._get_engine()
            query = """
            MATCH (n:Entity)
            WHERE toLower(n.name) CONTAINS toLower($name)
            RETURN n
            LIMIT 30
            """
            results = await engine.query(query, {"name": name})
            # Unwrap Cypher results: [{n: {...}}] → [{...}]
            nodes = []
            for row in results:
                if isinstance(row, dict) and "n" in row:
                    nodes.append(row["n"])
                elif isinstance(row, dict):
                    nodes.append(row)
            return nodes
        except Exception as e:
            logger.warning("find_nodes_by_name failed for '%s': %s", name, e)
            return []

    # --- Consolidation Support ---

    async def get_all_entities_with_properties(self) -> list[dict[str, Any]]:
        """Return all non-archived Entity nodes with full properties."""
        engine = await self._get_engine()
        query = """
        MATCH (n:Entity)
        WHERE n.status IS NULL OR (n.status <> 'archived' AND n.status <> 'merged')
        RETURN n.id AS id, n.name AS name, n.description AS description,
               n.confidence AS confidence, n.status AS status
        """
        try:
            results = await engine.query(query, {})
            return [row for row in results if isinstance(row, dict) and row.get("id")]
        except Exception as e:
            logger.warning("get_all_entities_with_properties failed: %s", e)
            return []

    async def get_version_chain_length(self, node_id: UUID) -> int:
        """Count PREVIOUS_VERSION edges from a node."""
        engine = await self._get_engine()
        query = """
        MATCH (n)-[:PREVIOUS_VERSION*]->(v)
        WHERE n.id = $node_id
        RETURN count(v) AS chain_len
        """
        try:
            results = await engine.query(query, {"node_id": str(node_id)})
            if results and isinstance(results[0], dict):
                return int(results[0].get("chain_len", 0))
            return 0
        except Exception as e:
            logger.warning("get_version_chain_length failed for %s: %s", node_id, e)
            return 0

    async def get_version_chain_nodes(self, node_id: UUID) -> list[dict[str, Any]]:
        """Get ordered PREVIOUS_VERSION chain (oldest first)."""
        engine = await self._get_engine()
        query = """
        MATCH (current)-[:PREVIOUS_VERSION*]->(v)
        WHERE current.id = $node_id
        RETURN v.id AS id, v.version AS version, v.value AS value,
               v.compressed AS compressed
        ORDER BY v.version ASC
        """
        try:
            results = await engine.query(query, {"node_id": str(node_id)})
            return [row for row in results if isinstance(row, dict)]
        except Exception as e:
            logger.warning("get_version_chain_nodes failed for %s: %s", node_id, e)
            return []

    async def create_merged_into_edge(
        self, deprecated_id: UUID, surviving_id: UUID, properties: dict[str, Any]
    ) -> None:
        """Create a MERGED_INTO edge from deprecated node to surviving node."""
        engine = await self._get_engine()
        query = """
        MATCH (dep), (sur)
        WHERE dep.id = $dep_id AND sur.id = $sur_id
        CREATE (dep)-[:MERGED_INTO $props]->(sur)
        """
        # Neo4j doesn't support map literal in CREATE, use SET instead
        set_clauses = ", ".join(f"r.{k} = ${k}" for k in properties)
        query = f"""
        MATCH (dep), (sur)
        WHERE dep.id = $dep_id AND sur.id = $sur_id
        CREATE (dep)-[r:MERGED_INTO]->(sur)
        SET {set_clauses}
        """ if properties else """
        MATCH (dep), (sur)
        WHERE dep.id = $dep_id AND sur.id = $sur_id
        CREATE (dep)-[r:MERGED_INTO]->(sur)
        """
        params = {"dep_id": str(deprecated_id), "sur_id": str(surviving_id), **properties}
        try:
            await engine.query(query, params)
        except Exception as e:
            logger.warning("create_merged_into_edge failed %s->%s: %s", deprecated_id, surviving_id, e)

    async def search_nodes_by_text(self, search_terms: list[str]) -> list[dict[str, Any]]:
        """Search Entity nodes where name or description contains any search term.

        Used by the query pipeline to find corrected nodes whose descriptions
        may contain terms not in the original vector index.
        """
        try:
            engine = await self._get_engine()
            # Filter and cap terms to avoid massive OR clauses
            filtered_terms = [t for t in search_terms if len(t) > 2][:6]
            if not filtered_terms:
                return []

            # Build OR conditions using parameterized variables
            conditions = []
            params: dict[str, str] = {}
            for i, term in enumerate(filtered_terms):
                param_name = f"term{i}"
                params[param_name] = term.lower()
                conditions.append(
                    f"toLower(n.name) CONTAINS ${param_name} "
                    f"OR toLower(n.description) CONTAINS ${param_name}"
                )

            where_clause = " OR ".join(conditions)
            query = f"""
            MATCH (n:Entity)
            WHERE {where_clause}
            RETURN n
            LIMIT 20
            """
            results = await engine.query(query, params)
            nodes = []
            for row in results:
                if isinstance(row, dict) and "n" in row:
                    nodes.append(row["n"])
                elif isinstance(row, dict):
                    nodes.append(row)
            return nodes
        except Exception as e:
            logger.warning("search_nodes_by_text failed: %s", e)
            return []
