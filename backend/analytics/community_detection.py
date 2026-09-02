"""
analytics/community_detection.py — Identifies criminal cells / syndicates
using graph community detection algorithms.

Algorithms:
  - Louvain Method  (primary — fast, scalable, high quality)
  - Label Propagation (fast alternative)
"""

import logging
from typing import Any, Dict, List

import networkx as nx

from graph.neo4j_client import neo4j_client
from analytics.centrality import centrality_analyzer

logger = logging.getLogger(__name__)


class CommunityDetector:
    """Detects communities (criminal cells) in the network graph."""

    async def detect(self, algorithm: str = "louvain") -> Dict[str, Any]:
        """
        Run community detection and store community_id on each Neo4j node.

        Args:
            algorithm: "louvain" | "label_propagation"

        Returns:
            Summary with community count, sizes, and top members per community.
        """
        G, id_to_name = await centrality_analyzer.build_networkx_graph()
        UG = G.to_undirected()

        if UG.number_of_nodes() == 0:
            return {"communities": [], "total_communities": 0}

        communities: List[set] = []

        if algorithm == "louvain":
            try:
                from community import best_partition  # python-louvain
                partition = best_partition(UG, weight="weight")
                # Invert partition dict: community_id → set of node ids
                community_map: Dict[int, set] = {}
                for node_id, comm_id in partition.items():
                    community_map.setdefault(comm_id, set()).add(node_id)
                communities = list(community_map.values())
                logger.info(f"Louvain: {len(communities)} communities found.")
            except ImportError:
                logger.warning("python-louvain not installed, falling back to label_propagation")
                algorithm = "label_propagation"

        if algorithm == "label_propagation":
            raw = nx.algorithms.community.label_propagation_communities(UG)
            communities = list(raw)
            logger.info(f"Label Propagation: {len(communities)} communities found.")

        # Write community_id back to Neo4j
        for comm_id, members in enumerate(communities):
            for node_id in members:
                await neo4j_client.run(
                    "MATCH (n {id: $id}) SET n.community_id = $cid",
                    {"id": node_id, "cid": comm_id},
                )

        # Build summary
        summary_communities = []
        for comm_id, members in enumerate(communities):
            top_members = sorted(
                [{"id": m, "name": id_to_name.get(m, m)} for m in members],
                key=lambda x: x["name"],
            )[:10]
            summary_communities.append({
                "community_id": comm_id,
                "size": len(members),
                "top_members": top_members,
                "color": f"hsl({(comm_id * 47) % 360}, 70%, 50%)",  # stable color
            })

        summary_communities.sort(key=lambda x: x["size"], reverse=True)

        logger.info(f"Community detection complete: {len(communities)} communities.")
        return {
            "algorithm": algorithm,
            "total_communities": len(communities),
            "communities": summary_communities,
        }

    async def get_communities(self) -> List[Dict]:
        """Return pre-computed community assignments from Neo4j."""
        records = await neo4j_client.run(
            """
            MATCH (n)
            WHERE n.community_id IS NOT NULL
            RETURN n.community_id AS community_id,
                   collect({id: n.id, name: n.name, type: labels(n)[0]}) AS members,
                   count(n) AS size
            ORDER BY size DESC
            """
        )
        return records


# ── Singleton ─────────────────────────────────────────────────────────────────
community_detector = CommunityDetector()
