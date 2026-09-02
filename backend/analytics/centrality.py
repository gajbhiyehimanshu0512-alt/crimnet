"""
analytics/centrality.py — Computes graph centrality metrics to identify
key influencers in criminal networks.

Metrics computed:
  - Degree Centrality        (most connections)
  - Betweenness Centrality   (brokers/middlemen)
  - PageRank                 (influence weighted by neighbors)
  - Eigenvector Centrality   (connected to important nodes)
"""

import logging
from typing import Any, Dict, List, Tuple

import networkx as nx

from graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class CentralityAnalyzer:
    """Runs centrality algorithms and writes results back to Neo4j."""

    async def build_networkx_graph(self) -> Tuple[nx.DiGraph, Dict[str, str]]:
        """
        Fetch all nodes and edges from Neo4j, build a NetworkX DiGraph.
        Returns (graph, id→name mapping).
        """
        nodes = await neo4j_client.get_all_nodes_for_analytics()
        edges = await neo4j_client.get_all_edges_for_analytics()

        G = nx.DiGraph()
        id_to_name: Dict[str, str] = {}

        for n in nodes:
            nid = n["id"]
            G.add_node(nid, name=n.get("name", ""), labels=n.get("labels", []))
            id_to_name[nid] = n.get("name", nid)

        for e in edges:
            src, tgt = e["source"], e["target"]
            w = float(e.get("weight", 1) or 1)
            if src and tgt and src in G and tgt in G:
                if G.has_edge(src, tgt):
                    G[src][tgt]["weight"] += w
                else:
                    G.add_edge(src, tgt, weight=w, rel_type=e.get("type", ""))

        logger.info(f"NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G, id_to_name

    async def compute_all(self) -> List[Dict[str, Any]]:
        """
        Compute all centrality metrics and store results on Neo4j nodes.
        Returns sorted list of top influencers.
        """
        G, id_to_name = await self.build_networkx_graph()
        if G.number_of_nodes() == 0:
            logger.warning("Empty graph — skipping centrality computation.")
            return []

        UG = G.to_undirected()

        logger.info("Computing degree centrality...")
        degree = nx.degree_centrality(G)

        logger.info("Computing betweenness centrality...")
        betweenness = nx.betweenness_centrality(UG, normalized=True, weight="weight")

        logger.info("Computing PageRank...")
        pagerank = nx.pagerank(G, alpha=0.85, weight="weight")

        logger.info("Computing eigenvector centrality...")
        try:
            eigenvector = nx.eigenvector_centrality(UG, max_iter=500, weight="weight")
        except nx.PowerIterationFailedConvergence:
            logger.warning("Eigenvector centrality did not converge, using degree instead.")
            eigenvector = degree

        # Store back to Neo4j
        results = []
        for node_id in G.nodes():
            analytics = {
                "degree_centrality":      round(degree.get(node_id, 0), 6),
                "betweenness_centrality": round(betweenness.get(node_id, 0), 6),
                "pagerank":               round(pagerank.get(node_id, 0), 6),
                "eigenvector_centrality": round(eigenvector.get(node_id, 0), 6),
            }
            # Write to Neo4j
            set_items = ", ".join(f"n.{k} = ${k}" for k in analytics)
            query = f"MATCH (n {{id: $id}}) SET {set_items}"
            await neo4j_client.run(query, {"id": node_id, **analytics})

            results.append({
                "id": node_id,
                "name": id_to_name.get(node_id, node_id),
                **analytics,
            })

        # Sort by PageRank (composite influence score)
        results.sort(key=lambda x: x["pagerank"], reverse=True)
        logger.info(f"Centrality computed for {len(results)} nodes.")
        return results

    async def get_top_influencers(self, top_n: int = 20) -> List[Dict]:
        """
        Fetch pre-computed centrality scores from Neo4j (fast — no recomputation).
        """
        records = await neo4j_client.run(
            """
            MATCH (n)
            WHERE n.pagerank IS NOT NULL
            RETURN n.id AS id, n.name AS name, labels(n) AS labels,
                   n.pagerank AS pagerank,
                   n.degree_centrality AS degree_centrality,
                   n.betweenness_centrality AS betweenness_centrality,
                   n.risk_level AS risk_level
            ORDER BY n.pagerank DESC
            LIMIT $top_n
            """,
            {"top_n": top_n},
        )
        return records


# ── Singleton ─────────────────────────────────────────────────────────────────
centrality_analyzer = CentralityAnalyzer()
