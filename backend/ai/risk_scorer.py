"""
ai/risk_scorer.py — Composite risk scoring for entities in the network.
Combines centrality rank, anomaly scores, criminal history, and network density
into a single risk score (0–100) with risk level classification.
"""

import logging
from typing import Any, Dict, Optional

from graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

# Weight coefficients for composite risk score
WEIGHTS = {
    "pagerank":               0.30,
    "betweenness_centrality": 0.25,
    "degree_centrality":      0.15,
    "community_size":         0.10,
    "criminal_history":       0.20,
}

RISK_THRESHOLDS = {
    "CRITICAL": 75,
    "HIGH":     50,
    "MEDIUM":   25,
    "LOW":      0,
}


class RiskScorer:
    """Computes composite risk scores for entities."""

    async def score_entity(self, entity_id: str) -> Dict[str, Any]:
        """Compute risk score for a single entity."""
        record = await neo4j_client.run(
            """
            MATCH (n {id: $id})
            OPTIONAL MATCH (n)-[:MEMBER_OF|ASSOCIATED_WITH]-(peer)
            RETURN n,
                   labels(n) AS labels,
                   count(DISTINCT peer) AS network_size,
                   coalesce(n.pagerank, 0) AS pagerank,
                   coalesce(n.betweenness_centrality, 0) AS betweenness,
                   coalesce(n.degree_centrality, 0) AS degree,
                   size(coalesce(n.criminal_history, [])) AS crim_hist_count
            """,
            {"id": entity_id},
        )
        if not record:
            return {"error": "Entity not found"}

        r = record[0]

        # Normalise each metric to 0–100
        pagerank_score     = min(100, r["pagerank"] * 5000)
        betweenness_score  = min(100, r["betweenness"] * 300)
        degree_score       = min(100, r["degree"] * 200)
        community_score    = min(100, r["network_size"] * 2)
        crim_hist_score    = min(100, r["crim_hist_count"] * 20)

        composite = (
            pagerank_score    * WEIGHTS["pagerank"]
            + betweenness_score * WEIGHTS["betweenness_centrality"]
            + degree_score      * WEIGHTS["degree_centrality"]
            + community_score   * WEIGHTS["community_size"]
            + crim_hist_score   * WEIGHTS["criminal_history"]
        )

        risk_level = "LOW"
        for level, threshold in RISK_THRESHOLDS.items():
            if composite >= threshold:
                risk_level = level
                break

        node = r["n"]
        result = {
            "entity_id": entity_id,
            "entity_name": node.get("name", entity_id),
            "risk_score": round(composite, 2),
            "risk_level": risk_level,
            "breakdown": {
                "pagerank_contribution":     round(pagerank_score    * WEIGHTS["pagerank"], 2),
                "betweenness_contribution":  round(betweenness_score * WEIGHTS["betweenness_centrality"], 2),
                "degree_contribution":       round(degree_score      * WEIGHTS["degree_centrality"], 2),
                "community_contribution":    round(community_score   * WEIGHTS["community_size"], 2),
                "criminal_history_contribution": round(crim_hist_score * WEIGHTS["criminal_history"], 2),
            },
        }

        # Store risk_score and risk_level back to Neo4j
        await neo4j_client.run(
            "MATCH (n {id: $id}) SET n.risk_score = $score, n.risk_level = $level",
            {"id": entity_id, "score": composite, "level": risk_level},
        )

        return result

    async def score_all_entities(self) -> int:
        """Score all Person and Organization nodes. Returns count scored."""
        nodes = await neo4j_client.run(
            "MATCH (n) WHERE 'Person' IN labels(n) OR 'Organization' IN labels(n) RETURN n.id AS id"
        )
        count = 0
        for node in nodes:
            try:
                await self.score_entity(node["id"])
                count += 1
            except Exception as e:
                logger.warning(f"Scoring failed for {node['id']}: {e}")
        logger.info(f"Risk scoring complete: {count} entities scored.")
        return count


# ── Singleton ─────────────────────────────────────────────────────────────────
risk_scorer = RiskScorer()
