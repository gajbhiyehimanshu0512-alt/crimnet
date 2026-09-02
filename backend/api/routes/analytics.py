"""
api/routes/analytics.py — Analytics endpoints.
Triggers centrality computation, community detection, anomaly detection,
and timeline building.
"""

import logging
from fastapi import APIRouter, Query

from analytics.centrality import centrality_analyzer
from analytics.community_detection import community_detector
from analytics.anomaly_detector import anomaly_detector
from analytics.timeline_builder import timeline_builder
from ai.risk_scorer import risk_scorer

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run", summary="Run full analytics pipeline")
async def run_full_analytics():
    """
    Trigger the complete analytics pipeline:
    1. Compute centrality metrics
    2. Detect communities
    3. Score all entity risks
    Returns a summary of results.
    """
    logger.info("Starting full analytics pipeline...")

    # Step 1: Centrality
    centrality_results = await centrality_analyzer.compute_all()

    # Step 2: Community detection
    communities = await community_detector.detect("louvain")

    # Step 3: Risk scoring
    scored_count = await risk_scorer.score_all_entities()

    return {
        "status": "complete",
        "centrality": {
            "nodes_analyzed": len(centrality_results),
            "top_5": centrality_results[:5],
        },
        "communities": {
            "total_communities": communities.get("total_communities", 0),
            "algorithm": communities.get("algorithm", "louvain"),
        },
        "risk_scoring": {
            "entities_scored": scored_count,
        },
    }


@router.get("/influencers", summary="Get top influencers by centrality")
async def get_influencers(top_n: int = Query(default=20, ge=5, le=100)):
    """Return the top N most influential entities sorted by PageRank."""
    influencers = await centrality_analyzer.get_top_influencers(top_n=top_n)
    return {"influencers": influencers, "count": len(influencers)}


@router.post("/centrality", summary="Recompute centrality metrics")
async def recompute_centrality():
    """Recompute all centrality metrics (may take time for large graphs)."""
    results = await centrality_analyzer.compute_all()
    return {
        "status": "complete",
        "nodes_analyzed": len(results),
        "top_influencers": results[:10],
    }


@router.post("/communities", summary="Rerun community detection")
async def rerun_communities(algorithm: str = Query(default="louvain")):
    """Rerun community detection with the specified algorithm."""
    result = await community_detector.detect(algorithm)
    return result


@router.get("/anomalies", summary="Get anomaly alerts")
async def get_anomalies():
    """Return all network-level anomaly alerts from pre-computed metrics."""
    alerts = await anomaly_detector.detect_network_anomalies()
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/timeline/{entity_id}", summary="Get entity timeline")
async def get_timeline(entity_id: str):
    """Return chronological event timeline for an entity."""
    timeline = await timeline_builder.get_entity_timeline(entity_id)
    return timeline


@router.get("/risk/{entity_id}", summary="Get entity risk score")
async def get_risk_score(entity_id: str):
    """Compute or retrieve the composite risk score for an entity."""
    result = await risk_scorer.score_entity(entity_id)
    return result
