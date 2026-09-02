"""
backend/tests/test_cases.py — Unit tests for case management CRUD endpoints.
Run with: pytest backend/tests/test_cases.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch


# ── Schema Validation Tests (no Neo4j needed) ────────────────────────────────

def test_case_create_schema():
    from graph.schema import CaseCreate
    c = CaseCreate(name="Test Case", description="A test", priority="HIGH")
    assert c.name == "Test Case"
    assert c.priority == "HIGH"
    assert c.tags == []


def test_case_update_schema():
    from graph.schema import CaseUpdate
    u = CaseUpdate(status="ACTIVE", assigned_to="Officer A")
    data = u.model_dump(exclude_unset=True)
    assert "status" in data
    assert "name" not in data  # unset fields excluded


def test_case_status_enum():
    from graph.schema import CaseStatus
    assert CaseStatus.OPEN.value == "OPEN"
    assert CaseStatus.ACTIVE.value == "ACTIVE"
    assert CaseStatus.CLOSED.value == "CLOSED"
    assert CaseStatus.ARCHIVED.value == "ARCHIVED"


# ── API Endpoint Tests (require auth, mock Neo4j) ────────────────────────────

MOCK_CASE = {
    "id": "case-001",
    "name": "Operation Nightfall",
    "description": "Multi-state smuggling ring",
    "status": "OPEN",
    "priority": "HIGH",
    "assigned_to": "Inspector Sharma",
    "tags": ["smuggling", "interstate"],
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00",
}


@patch("api.routes.cases.neo4j_client")
def test_list_cases(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(return_value=[{"c": MOCK_CASE}])
    resp = client.get("/api/cases", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 0


@patch("api.routes.cases.neo4j_client")
def test_get_case(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(side_effect=[
        [{"c": MOCK_CASE}],                    # _get_case
        [{"eid": "entity-1"}, {"eid": "entity-2"}],  # _get_case_entities
    ])
    resp = client.get("/api/cases/case-001", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "case-001"
    assert data["name"] == "Operation Nightfall"
    assert len(data["entity_ids"]) == 2


@patch("api.routes.cases.neo4j_client")
def test_create_case(mock_nc, client, auth_headers):
    mock_nc.upsert_entity = AsyncMock(return_value="new-case-id")
    mock_nc.run = AsyncMock(return_value=[{
        "c": {**MOCK_CASE, "id": "new-case-id", "name": "New Case"}
    }])
    resp = client.post("/api/cases", headers=auth_headers, json={
        "name": "New Case",
        "description": "Testing creation",
        "priority": "MEDIUM",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Case"
    assert data["status"] == "OPEN"


@patch("api.routes.cases.neo4j_client")
def test_update_case(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(side_effect=[
        [{"c": MOCK_CASE}],  # _get_case (check exists)
        [],                   # SET query result
        [{"c": {**MOCK_CASE, "status": "ACTIVE"}}],  # _get_case after update
        [],                   # _get_case_entities
    ])
    resp = client.put("/api/cases/case-001", headers=auth_headers, json={"status": "ACTIVE"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"


@patch("api.routes.cases.neo4j_client")
def test_delete_case(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(side_effect=[
        [{"c": MOCK_CASE}],  # _get_case (check exists)
        [],                   # DETACH DELETE
    ])
    resp = client.delete("/api/cases/case-001", headers=auth_headers)
    assert resp.status_code == 204


@patch("api.routes.cases.neo4j_client")
def test_get_case_not_found(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(return_value=[])
    resp = client.get("/api/cases/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


@patch("api.routes.cases.neo4j_client")
def test_add_entity_to_case(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(side_effect=[
        [{"c": MOCK_CASE}],  # _get_case
        [],                   # MERGE INCLUDES
        [{"eid": "entity-1"}],  # _get_case_entities
        [{"c": MOCK_CASE}],  # _get_case
    ])
    mock_nc.get_entity = AsyncMock(return_value={"n": {"id": "entity-1"}})

    resp = client.post("/api/cases/case-001/entities", headers=auth_headers, json={
        "entity_id": "entity-1"
    })
    assert resp.status_code == 200


@patch("api.routes.cases.neo4j_client")
def test_add_entity_case_not_found(mock_nc, client, auth_headers):
    mock_nc.run = AsyncMock(return_value=[])
    resp = client.post("/api/cases/nonexistent/entities", headers=auth_headers, json={
        "entity_id": "entity-1"
    })
    assert resp.status_code == 404


# ── Auth Tests ────────────────────────────────────────────────────────────────

def test_cases_endpoint_requires_auth(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 401
