"""
graph/graph_builder.py — Builds and updates the Neo4j knowledge graph
from extracted entities and relationships produced by the NLP pipeline.
"""

import logging
import uuid
from typing import Any, Dict, List

from graph.neo4j_client import neo4j_client
from graph.schema import EntityBase, RelationshipModel, EntityType

logger = logging.getLogger(__name__)

# Map EntityType enum → Neo4j label
ENTITY_LABEL_MAP: Dict[EntityType, str] = {
    EntityType.PERSON:       "Person",
    EntityType.ORGANIZATION: "Organization",
    EntityType.LOCATION:     "Location",
    EntityType.PHONE:        "PhoneNumber",
    EntityType.VEHICLE:      "Vehicle",
    EntityType.ACCOUNT:      "BankAccount",
    EntityType.EVENT:        "Event",
    EntityType.DEVICE:       "Device",
}


class GraphBuilder:
    """Translates NLP extraction output into Neo4j nodes and relationships."""

    async def ingest_entities(self, entities: List[Dict[str, Any]], source_doc: str = "") -> Dict[str, str]:
        """
        Upsert a list of entity dicts into Neo4j.

        Args:
            entities: List of entity dicts with at least {name, entity_type}.
            source_doc: Filename/ID of the originating document.

        Returns:
            Mapping of temporary entity name → Neo4j node id.
        """
        name_to_id: Dict[str, str] = {}
        for ent in entities:
            label = ENTITY_LABEL_MAP.get(EntityType(ent["entity_type"]), "Entity")
            props = {k: v for k, v in ent.items() if v is not None}
            props.setdefault("id", str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{label}:{ent['name']}")))
            # Append source document without duplicating
            existing = props.get("source_documents", [])
            if source_doc and source_doc not in existing:
                existing.append(source_doc)
            props["source_documents"] = existing

            node_id = await neo4j_client.upsert_entity(label, props)
            name_to_id[ent["name"]] = node_id
            logger.debug(f"Upserted {label}: {ent['name']} → {node_id}")

        logger.info(f"Ingested {len(entities)} entities from '{source_doc}'")
        return name_to_id

    async def ingest_relationships(
        self,
        relationships: List[Dict[str, Any]],
        name_to_id: Dict[str, str],
        source_doc: str = "",
    ) -> int:
        """
        Upsert a list of relationship dicts into Neo4j.

        Args:
            relationships: List of {source_name, target_name, relation_type, properties}.
            name_to_id: Name → Neo4j id lookup built during entity ingestion.
            source_doc: Originating document reference.

        Returns:
            Number of relationships successfully created.
        """
        count = 0
        for rel in relationships:
            src_id = name_to_id.get(rel.get("source_name", ""))
            tgt_id = name_to_id.get(rel.get("target_name", ""))
            if not src_id or not tgt_id:
                logger.warning(
                    f"Skipping relationship {rel.get('source_name')} → {rel.get('target_name')}: "
                    "one or both entities not found."
                )
                continue

            props = rel.get("properties", {})
            if source_doc:
                props["source_doc"] = source_doc

            ok = await neo4j_client.upsert_relationship(
                source_id=src_id,
                target_id=tgt_id,
                rel_type=rel["relation_type"],
                properties=props,
            )
            if ok:
                count += 1

        logger.info(f"Ingested {count}/{len(relationships)} relationships from '{source_doc}'")
        return count

    async def ingest_extraction_result(self, result: Dict[str, Any], source_doc: str = "") -> Dict:
        """
        High-level method: takes the full output of the NLP extraction pipeline
        and stores everything in Neo4j.

        Expected result format:
        {
            "entities": [...],
            "relationships": [...],
            "document_text": "..."
        }
        """
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])

        name_to_id = await self.ingest_entities(entities, source_doc)
        rel_count = await self.ingest_relationships(relationships, name_to_id, source_doc)

        return {
            "entities_stored": len(name_to_id),
            "relationships_stored": rel_count,
            "entity_ids": list(name_to_id.values()),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
graph_builder = GraphBuilder()
