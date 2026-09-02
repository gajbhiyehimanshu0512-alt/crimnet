"""
analytics/timeline_builder.py — Builds chronological event timelines
per entity and detects co-location/co-occurrence events.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Builds event timelines for entities in the knowledge graph."""

    async def get_entity_timeline(self, entity_id: str) -> Dict[str, Any]:
        """
        Retrieve all events involving an entity, ordered by time.
        """
        # Get all relationships touching this entity that have a timestamp
        query = """
        MATCH (n {id: $id})-[r]-(other)
        WHERE r.timestamp IS NOT NULL OR r.created_at IS NOT NULL
        RETURN
            coalesce(r.timestamp, toString(r.created_at)) AS timestamp,
            type(r) AS relation_type,
            other.name AS other_name,
            labels(other) AS other_labels,
            other.id AS other_id,
            coalesce(r.duration_sec, r.amount, r.weight) AS value,
            r.tower_location AS location,
            r.source_doc AS source_doc
        ORDER BY timestamp ASC
        """
        records = await neo4j_client.run(query, {"id": entity_id})

        events = []
        for r in records:
            events.append({
                "timestamp": r.get("timestamp", ""),
                "event_type": self._map_relation_to_event(r.get("relation_type", "")),
                "relation": r.get("relation_type", ""),
                "other_entity": r.get("other_name", ""),
                "other_entity_id": r.get("other_id", ""),
                "other_entity_type": (r.get("other_labels") or ["Unknown"])[0],
                "value": r.get("value"),
                "location": r.get("location"),
                "source_doc": r.get("source_doc"),
            })

        # Get entity info
        entity = await neo4j_client.get_entity(entity_id)
        entity_name = ""
        if entity:
            node = entity.get("n", {})
            entity_name = node.get("name", entity_id)

        return {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "total_events": len(events),
            "events": events,
        }

    async def detect_colocation(
        self, location_name: str, time_window_hours: int = 2
    ) -> List[Dict]:
        """
        Find all entities co-located at the same location within a time window.
        """
        query = """
        MATCH (loc:Location {name: $location})<-[r1:PRESENT_AT]-(a)
        MATCH (loc)<-[r2:PRESENT_AT]-(b)
        WHERE a.id <> b.id
          AND r1.timestamp IS NOT NULL
          AND r2.timestamp IS NOT NULL
        RETURN a.name AS person_a, b.name AS person_b,
               r1.timestamp AS time_a, r2.timestamp AS time_b,
               loc.name AS location
        LIMIT 100
        """
        records = await neo4j_client.run(query, {"location": location_name})
        return records

    def _map_relation_to_event(self, rel_type: str) -> str:
        mapping = {
            "CALLED":          "📞 Phone Call",
            "MET_WITH":        "🤝 Meeting",
            "PRESENT_AT":      "📍 Location Visit",
            "TRANSFERRED_TO":  "💰 Financial Transfer",
            "ASSOCIATED_WITH": "🔗 Association",
            "MEMBER_OF":       "👥 Membership",
            "CO_ACCUSED_IN":   "⚖️ Legal Action",
            "TRAVELED_TO":     "✈️ Travel",
            "OWNS":            "🔑 Ownership",
        }
        return mapping.get(rel_type, f"🔄 {rel_type}")


# ── Singleton ─────────────────────────────────────────────────────────────────
timeline_builder = TimelineBuilder()
