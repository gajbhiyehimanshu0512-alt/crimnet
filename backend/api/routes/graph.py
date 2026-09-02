"""
api/routes/graph.py — Knowledge graph query endpoints.
Provides entity lookup, neighbor expansion, path finding, and full-graph export.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from graph.neo4j_client import neo4j_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/entity/{entity_id}", summary="Get entity with its neighbors")
async def get_entity(entity_id: str, depth: int = Query(default=1, ge=1, le=3)):
    """Return a single entity node plus all neighbors up to `depth` hops."""
    entity = await neo4j_client.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    neighbors = await neo4j_client.get_neighbors(entity_id, depth=depth)
    return {
        "entity": entity,
        "neighbors": neighbors,
    }


@router.get("/path", summary="Find shortest path between two entities")
async def shortest_path(
    from_id: str = Query(..., description="Source entity ID"),
    to_id:   str = Query(..., description="Target entity ID"),
):
    """Find the shortest path between two entities in the graph."""
    paths = await neo4j_client.shortest_path(from_id, to_id)
    if not paths:
        return {"message": "No path found between entities", "paths": []}
    return {"paths": paths}


@router.get("/network", summary="Get full network for visualization")
async def get_network(limit: int = Query(default=300, ge=10, le=1000)):
    """
    Return all nodes and edges for rendering in the frontend graph visualizer.
    Limit controls maximum number of nodes returned.
    """
    graph = await neo4j_client.get_full_graph(limit=limit)
    return {
        "nodes": graph.get("nodes", []),
        "edges": [e for e in graph.get("edges", []) if e.get("source") and e.get("target")],
        "total_nodes": len(graph.get("nodes", [])),
        "total_edges": len(graph.get("edges", [])),
    }


@router.get("/communities", summary="Get all community clusters")
async def get_communities():
    """Return all community clusters with their members."""
    from analytics.community_detection import community_detector
    communities = await community_detector.get_communities()
    return {"communities": communities, "total": len(communities)}


@router.get("/search", summary="Search entities by name")
async def search_entities(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Full-text search across entity names and aliases."""
    results = await neo4j_client.search_entities(q, limit=limit)
    return {"results": results, "count": len(results), "query": q}


@router.get("/stats", summary="Graph statistics summary")
async def graph_stats():
    """Return aggregate statistics about the knowledge graph."""
    stats = await neo4j_client.run("""
        MATCH (n)
        RETURN
          count(n) AS total_nodes,
          count(CASE WHEN 'Person' IN labels(n) THEN 1 END) AS persons,
          count(CASE WHEN 'Organization' IN labels(n) THEN 1 END) AS organizations,
          count(CASE WHEN 'Location' IN labels(n) THEN 1 END) AS locations,
          count(CASE WHEN 'PhoneNumber' IN labels(n) THEN 1 END) AS phones,
          count(CASE WHEN 'Vehicle' IN labels(n) THEN 1 END) AS vehicles,
          count(CASE WHEN 'BankAccount' IN labels(n) THEN 1 END) AS accounts,
          count(CASE WHEN n.risk_level = 'CRITICAL' THEN 1 END) AS critical_risk,
          count(CASE WHEN n.risk_level = 'HIGH' THEN 1 END) AS high_risk
    """)
    rel_stats = await neo4j_client.run("MATCH ()-[r]->() RETURN count(r) AS total_edges")

    result = stats[0] if stats else {}
    result["total_edges"] = rel_stats[0].get("total_edges", 0) if rel_stats else 0
    return result
