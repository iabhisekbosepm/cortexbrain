"""Graph visualization endpoints — nodes + edges for the /graph frontend page."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from cortexbrain.api.deps import get_meta_memory, get_semantic_memory
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.schemas import (
    GraphEdge,
    GraphNode,
    GraphOverviewResponse,
    GraphSubgraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


@router.get("/graph/overview", response_model=GraphOverviewResponse)
async def get_graph_overview(
    limit: int = Query(default=200, le=500),
    api_key: str = Depends(verify_api_key),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """Return top-salient entities and their edges for overview visualization."""
    # Get all entities from Neo4j
    entities = await semantic.get_all_entities_with_properties()
    if not entities:
        return GraphOverviewResponse(nodes=[], edges=[])

    # Build node list with metadata from PostgreSQL
    node_ids = [e["id"] for e in entities[:limit]]
    node_map: dict[str, GraphNode] = {}

    for entity in entities[:limit]:
        eid = str(entity.get("id", ""))
        if not eid:
            continue
        try:
            meta_data = await meta.get_or_create_metadata(
                node_id=UUID(eid), org_id=_DEFAULT_ORG
            )
            edge_count = await semantic.get_edge_count(UUID(eid))
            node_map[eid] = GraphNode(
                id=eid,
                name=str(entity.get("name", "")),
                description=str(entity.get("description", "") or ""),
                confidence=meta_data.confidence,
                salience=meta_data.salience,
                edge_count=edge_count,
                access_count=meta_data.access_count,
            )
        except Exception as e:
            logger.warning("Skipping entity %s: %s", eid, e)

    # Get edges between these nodes via Cypher
    engine = await semantic._get_engine()
    edge_query = """
    MATCH (n:Entity)-[r]-(m:Entity)
    WHERE n.id IN $ids AND m.id IN $ids AND n.id < m.id
    RETURN n.id AS source, m.id AS target, type(r) AS rel_type,
           coalesce(r.weight, 1.0) AS weight
    LIMIT 1000
    """
    edges: list[GraphEdge] = []
    try:
        results = await engine.query(edge_query, {"ids": node_ids})
        for row in results:
            if isinstance(row, dict):
                edges.append(GraphEdge(
                    source=str(row.get("source", "")),
                    target=str(row.get("target", "")),
                    rel_type=str(row.get("rel_type", "")),
                    weight=float(row.get("weight", 1.0)),
                ))
    except Exception as e:
        logger.warning("Failed to fetch edges: %s", e)

    return GraphOverviewResponse(
        nodes=list(node_map.values()),
        edges=edges,
    )


@router.get("/graph/subgraph", response_model=GraphSubgraphResponse)
async def get_graph_subgraph(
    center: UUID,
    depth: int = Query(default=2, le=3),
    api_key: str = Depends(verify_api_key),
    semantic: SemanticMemoryStore = Depends(get_semantic_memory),
    meta: MetaMemoryStore = Depends(get_meta_memory),
):
    """BFS from center node to depth, return nodes + edges."""
    center_node = await semantic.get_node(center)
    if center_node is None:
        return GraphSubgraphResponse(
            center=str(center), depth=depth, nodes=[], edges=[]
        )

    # BFS
    visited: set[str] = {str(center)}
    frontier: list[UUID] = [center]
    all_edges: list[GraphEdge] = []

    for _ in range(depth):
        if not frontier:
            break
        neighbors_batch = await semantic.get_neighbors_batch(frontier, limit_per_node=10)
        next_frontier: list[UUID] = []
        for nid_str, pairs in neighbors_batch.items():
            for neighbor_data, weight in pairs:
                neighbor_id = str(neighbor_data.get("id", ""))
                if not neighbor_id:
                    continue
                all_edges.append(GraphEdge(
                    source=nid_str,
                    target=neighbor_id,
                    weight=weight,
                ))
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    try:
                        next_frontier.append(UUID(neighbor_id))
                    except ValueError:
                        pass
        frontier = next_frontier

    # Build node data
    nodes: list[GraphNode] = []
    for nid_str in visited:
        try:
            nid = UUID(nid_str)
            node_data = await semantic.get_node(nid)
            meta_data = await meta.get_or_create_metadata(node_id=nid, org_id=_DEFAULT_ORG)
            edge_count = await semantic.get_edge_count(nid)
            nodes.append(GraphNode(
                id=nid_str,
                name=str(node_data.get("name", "")) if node_data else "",
                description=str(node_data.get("description", "") or "") if node_data else "",
                confidence=meta_data.confidence,
                salience=meta_data.salience,
                edge_count=edge_count,
                access_count=meta_data.access_count,
            ))
        except Exception as e:
            logger.warning("Skipping node %s in subgraph: %s", nid_str, e)

    return GraphSubgraphResponse(
        center=str(center),
        depth=depth,
        nodes=nodes,
        edges=all_edges,
    )
