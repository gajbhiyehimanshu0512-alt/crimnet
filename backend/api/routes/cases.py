"""
api/routes/cases.py — Case management CRUD endpoints.
Manages Case nodes in Neo4j, linking them to graph entities.
"""

import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException

from graph.neo4j_client import neo4j_client
from graph.schema import CaseCreate, CaseUpdate, CaseEntityAdd

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_case(case_id: str) -> dict | None:
    """Fetch a Case node from Neo4j."""
    records = await neo4j_client.run(
        "MATCH (c:Case {id: $id}) RETURN c",
        {"id": case_id},
    )
    if not records:
        return None
    return records[0]["c"]


async def _get_case_entities(case_id: str) -> List[str]:
    """Get all entity IDs linked to a case."""
    records = await neo4j_client.run(
        "MATCH (c:Case {id: $id})-[:INCLUDES]->(n) RETURN n.id AS eid",
        {"id": case_id},
    )
    return [r["eid"] for r in records if r.get("eid")]


def _case_to_response(case: dict, entity_ids: List[str] | None = None) -> dict:
    """Convert a Neo4j Case node dict to a CaseResponse-compatible dict."""
    return {
        "id": case["id"],
        "name": case.get("name", ""),
        "description": case.get("description", ""),
        "status": case.get("status", "OPEN"),
        "priority": case.get("priority", "MEDIUM"),
        "assigned_to": case.get("assigned_to"),
        "tags": case.get("tags", []),
        "entity_ids": entity_ids or [],
        "created_at": str(case.get("created_at", "")),
        "updated_at": str(case.get("updated_at", "")),
    }


# ── CRUD Endpoints ───────────────────────────────────────────────────────────

@router.get("", summary="List all cases")
async def list_cases():
    """Return all cases in the system."""
    records = await neo4j_client.run("MATCH (c:Case) RETURN c ORDER BY c.created_at DESC")
    cases = []
    for r in records:
        entity_ids = await _get_case_entities(r["c"]["id"])
        cases.append(_case_to_response(r["c"], entity_ids))
    return {"cases": cases, "count": len(cases)}


@router.get("/{case_id}", summary="Get a case by ID")
async def get_case(case_id: str):
    """Return a single case with its linked entities."""
    case = await _get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    entity_ids = await _get_case_entities(case_id)
    return _case_to_response(case, entity_ids)


@router.post("", status_code=201, summary="Create a new case")
async def create_case(payload: CaseCreate):
    """Create a new Case node in Neo4j."""
    case_id = str(uuid.uuid4())
    props = {
        "id": case_id,
        "name": payload.name,
        "description": payload.description,
        "status": "OPEN",
        "priority": payload.priority,
        "assigned_to": payload.assigned_to or "",
        "tags": payload.tags,
    }
    await neo4j_client.upsert_entity("Case", props)
    logger.info(f"Created case '{payload.name}' ({case_id})")
    case = await _get_case(case_id)
    return _case_to_response(case)


@router.put("/{case_id}", summary="Update an existing case")
async def update_case(case_id: str, payload: CaseUpdate):
    """Update fields on an existing Case node."""
    case = await _get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _case_to_response(case)

    # Convert enum to string for Neo4j
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else str(updates["status"])

    set_parts = ", ".join(f"c.{k} = ${k}" for k in updates)
    params = {"id": case_id, **updates}
    await neo4j_client.run(
        f"MATCH (c:Case {{id: $id}}) SET {set_parts}, c.updated_at = datetime()",
        params,
    )
    updated = await _get_case(case_id)
    entity_ids = await _get_case_entities(case_id)
    return _case_to_response(updated, entity_ids)


@router.delete("/{case_id}", status_code=204, summary="Delete a case")
async def delete_case(case_id: str):
    """Delete a Case node and all its INCLUDES relationships."""
    case = await _get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await neo4j_client.run(
        "MATCH (c:Case {id: $id}) DETACH DELETE c",
        {"id": case_id},
    )
    logger.info(f"Deleted case {case_id}")


# ── Entity Linking ───────────────────────────────────────────────────────────

@router.post("/{case_id}/entities", summary="Add an entity to a case")
async def add_entity_to_case(case_id: str, payload: CaseEntityAdd):
    """Link an existing graph entity to a case via INCLUDES relationship."""
    case = await _get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Verify entity exists
    entity = await neo4j_client.get_entity(payload.entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    await neo4j_client.run(
        """
        MATCH (c:Case {id: $case_id}), (n {id: $entity_id})
        MERGE (c)-[r:INCLUDES]->(n)
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """,
        {"case_id": case_id, "entity_id": payload.entity_id},
    )

    entity_ids = await _get_case_entities(case_id)
    updated = await _get_case(case_id)
    return _case_to_response(updated, entity_ids)


@router.delete("/{case_id}/entities/{entity_id}", status_code=204, summary="Remove an entity from a case")
async def remove_entity_from_case(case_id: str, entity_id: str):
    """Remove an INCLUDES relationship between a case and an entity."""
    await neo4j_client.run(
        """
        MATCH (c:Case {id: $case_id})-[r:INCLUDES]->(n {id: $entity_id})
        DELETE r
        """,
        {"case_id": case_id, "entity_id": entity_id},
    )
