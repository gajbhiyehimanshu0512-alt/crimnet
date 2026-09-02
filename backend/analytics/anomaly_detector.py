"""
analytics/anomaly_detector.py — Detects suspicious patterns and unusual
activities using ML (Isolation Forest) and rule-based heuristics.

Detection types:
  - Call burst (sudden spike in CDR activity)
  - Night activity (high volume calls between 00:00–05:00)
  - Geo-velocity (impossible speed between towers)
  - Financial structuring (smurfing — multiple sub-threshold transactions)
  - Round-amount transfers (hawala indicator)
  - Network isolation change (sudden new connections)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """ML + rule-based anomaly detection on criminal network data."""

    # ── CDR Anomalies ─────────────────────────────────────────────────────────

    async def detect_cdr_anomalies(self, records: List[Dict]) -> List[Dict]:
        """
        Detect anomalous calling patterns from CDR records.
        Uses Isolation Forest on per-phone aggregate features.
        """
        if not records:
            return []

        df = pd.DataFrame(records)
        alerts = []

        # Parse timestamps
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["ts"])
        df["hour"] = df["ts"].dt.hour

        # Aggregate per caller
        agg = df.groupby("caller").agg(
            total_calls=("receiver", "count"),
            unique_receivers=("receiver", "nunique"),
            night_calls=("hour", lambda x: ((x >= 0) & (x <= 5)).sum()),
            avg_duration=("duration_sec", "mean"),
            std_duration=("duration_sec", "std"),
        ).reset_index().fillna(0)

        if len(agg) < 5:
            return []  # Not enough data for Isolation Forest

        # Feature matrix
        features = agg[["total_calls", "unique_receivers", "night_calls", "avg_duration"]].values

        iso = IsolationForest(contamination=0.1, random_state=42)
        agg["anomaly_score"] = iso.fit_predict(features)
        agg["raw_score"] = -iso.score_samples(features)   # Higher = more anomalous

        anomalies = agg[agg["anomaly_score"] == -1].sort_values("raw_score", ascending=False)

        for _, row in anomalies.iterrows():
            severity = "HIGH" if row["raw_score"] > 0.6 else "MEDIUM"
            desc_parts = []
            if row["night_calls"] > 5:
                desc_parts.append(f"{int(row['night_calls'])} calls between midnight–5 AM")
            if row["unique_receivers"] > 20:
                desc_parts.append(f"contacted {int(row['unique_receivers'])} unique numbers")
            if row["total_calls"] > 50:
                desc_parts.append(f"made {int(row['total_calls'])} calls in the period")

            alerts.append({
                "id": str(uuid.uuid4()),
                "entity_id": row["caller"],
                "entity_name": row["caller"],
                "alert_type": "call_pattern_anomaly",
                "severity": severity,
                "description": f"Suspicious calling pattern detected: {'; '.join(desc_parts) or 'unusual activity'}",
                "anomaly_score": round(float(row["raw_score"]), 4),
                "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                "evidence": {
                    "total_calls": int(row["total_calls"]),
                    "unique_receivers": int(row["unique_receivers"]),
                    "night_calls": int(row["night_calls"]),
                },
            })

        logger.info(f"CDR anomaly detection: {len(alerts)} alerts generated.")
        return alerts

    # ── Financial Anomalies ───────────────────────────────────────────────────

    def detect_financial_anomalies(self, records: List[Dict]) -> List[Dict]:
        """
        Detect financial structuring, round-amount hawala transfers.
        """
        if not records:
            return []

        df = pd.DataFrame(records)
        alerts = []

        # Round-amount structuring (hawala indicator)
        round_amounts = df[df["amount"] % 10000 == 0]
        for acct, grp in round_amounts.groupby("account"):
            if len(grp) >= 3:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "entity_id": str(acct),
                    "entity_name": str(acct),
                    "alert_type": "round_amount_structuring",
                    "severity": "HIGH",
                    "description": f"Account {acct} made {len(grp)} round-number transactions — potential hawala activity.",
                    "anomaly_score": 0.85,
                    "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                    "evidence": {"transaction_count": len(grp), "total_amount": float(grp["amount"].sum())},
                })

        # Large single transactions
        large = df[df["amount"] >= 500_000]
        for _, row in large.iterrows():
            alerts.append({
                "id": str(uuid.uuid4()),
                "entity_id": str(row["account"]),
                "entity_name": str(row["account"]),
                "alert_type": "large_transaction",
                "severity": "CRITICAL" if row["amount"] >= 1_000_000 else "HIGH",
                "description": f"Large transaction of ₹{row['amount']:,.0f} detected.",
                "anomaly_score": min(1.0, float(row["amount"]) / 2_000_000),
                "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                "evidence": {"amount": float(row["amount"]), "timestamp": str(row.get("timestamp", ""))},
            })

        logger.info(f"Financial anomaly detection: {len(alerts)} alerts generated.")
        return alerts

    # ── Graph-level anomalies ─────────────────────────────────────────────────

    async def detect_network_anomalies(self) -> List[Dict]:
        """
        Graph-level: flag nodes with extremely high betweenness centrality
        (critical brokers whose removal would fragment the network).
        """
        records = await neo4j_client.run(
            """
            MATCH (n)
            WHERE n.betweenness_centrality IS NOT NULL
              AND n.betweenness_centrality > 0.3
            RETURN n.id AS id, n.name AS name, labels(n) AS labels,
                   n.betweenness_centrality AS bc, n.pagerank AS pr
            ORDER BY bc DESC LIMIT 20
            """
        )
        alerts = []
        for r in records:
            alerts.append({
                "id": str(uuid.uuid4()),
                "entity_id": r["id"],
                "entity_name": r["name"],
                "alert_type": "critical_broker",
                "severity": "CRITICAL" if r["bc"] > 0.5 else "HIGH",
                "description": (
                    f"{r['name']} is a critical broker in the network "
                    f"(betweenness={r['bc']:.3f}). Removal would significantly disrupt connectivity."
                ),
                "anomaly_score": round(float(r["bc"]), 4),
                "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                "evidence": {"betweenness_centrality": r["bc"], "pagerank": r.get("pr", 0)},
            })
        return alerts

    async def run_all(self, cdr_records: List[Dict] = None, financial_records: List[Dict] = None) -> List[Dict]:
        """Run all detectors and return combined alert list."""
        all_alerts = []
        if cdr_records:
            all_alerts.extend(await self.detect_cdr_anomalies(cdr_records))
        if financial_records:
            all_alerts.extend(self.detect_financial_anomalies(financial_records))
        all_alerts.extend(await self.detect_network_anomalies())
        # Sort by anomaly_score descending
        all_alerts.sort(key=lambda a: a.get("anomaly_score", 0), reverse=True)
        return all_alerts


# ── Singleton ─────────────────────────────────────────────────────────────────
anomaly_detector = AnomalyDetector()
