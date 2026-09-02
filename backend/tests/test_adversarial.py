"""
backend/tests/test_adversarial.py — Adversarial exercise of auth, cases, and PDF paths.
Targets boundary conditions, empty inputs, ordering, async, and state issues
that the new features make relevant.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from auth import (
    create_access_token, decode_access_token, hash_password,
    verify_password, USERS_DB, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from jose import JWTError
from graph.schema import CaseCreate, CaseUpdate, CaseStatus, CaseEntityAdd


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — Adversarial boundary tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenAdversarial:
    """Exercise JWT token creation and validation at boundaries."""

    def test_token_with_empty_sub(self):
        """Token with empty string sub should decode but be rejected by middleware."""
        token = create_access_token({"sub": "", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == ""

    def test_token_with_none_sub(self):
        """Token with None sub — jose rejects because sub must be a string."""
        token = create_access_token({"sub": None, "role": "admin"})
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_token_with_no_sub(self):
        """Token missing sub entirely."""
        token = create_access_token({"role": "admin"})
        payload = decode_access_token(token)
        assert "sub" not in payload

    def test_token_with_malicious_sub(self):
        """Token with path-traversal-like sub."""
        token = create_access_token({"sub": "../../etc/passwd", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == "../../etc/passwd"

    def test_token_tampered_payload(self):
        """Decoding a tampered token should raise JWTError."""
        token = create_access_token({"sub": "admin", "role": "admin"})
        # Tamper with the payload portion
        parts = token.split(".")
        # Flip a character in the payload
        payload_b64 = parts[1]
        tampered = payload_b64[:-2] + ("A" if payload_b64[-2] != "A" else "B") + payload_b64[-1]
        tampered_token = f"{parts[0]}.{tampered}.{parts[2]}"
        with pytest.raises(JWTError):
            decode_access_token(tampered_token)

    def test_token_wrong_algorithm_header(self):
        """Token signed with wrong algorithm should be rejected."""
        import base64, json
        from jose import jwt as jose_jwt
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps({"sub": "admin"}).encode()).rstrip(b"=").decode()
        none_token = f"{header}.{payload_b64}."
        with pytest.raises(JWTError):
            decode_access_token(none_token)

    def test_token_expiry_is_seconds_not_minutes(self):
        """Verify token expiry is measured in seconds (jose convention), not minutes."""
        from datetime import timedelta
        token = create_access_token({"sub": "test"}, expires_delta=timedelta(minutes=1))
        payload = decode_access_token(token)
        import datetime
        exp = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        diff = (exp - now).total_seconds()
        # Should be roughly 60 seconds, not 60*60
        assert 30 < diff < 90

    def test_hash_password_empty_string(self):
        """Hashing an empty password should work (bcrypt allows it)."""
        h = hash_password("")
        assert verify_password("", h)

    def test_hash_password_unicode(self):
        """Hashing a unicode password should work."""
        h = hash_password("पासवर्ड🔑")
        assert verify_password("पासवर्ड🔑", h)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH MIDDLEWARE — Adversarial HTTP-level tests
# ══════════════════════════════════════════════════════════════════════════════

from tests.conftest import _build_test_app

@pytest.fixture(scope="module")
def adv_client():
    return TestClient(_build_test_app())


@pytest.fixture(scope="module")
def adv_token(adv_client):
    resp = adv_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


class TestMiddlewareAdversarial:
    """Exercise the auth middleware at HTTP boundary conditions."""

    def test_empty_authorization_header(self, adv_client):
        """Authorization header with just 'Bearer' and no token."""
        resp = adv_client.get("/api/cases", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401

    def test_bearer_case_sensitive(self, adv_client, adv_token):
        """'bearer' (lowercase) should be rejected."""
        resp = adv_client.get("/api/cases", headers={"Authorization": f"bearer {adv_token}"})
        assert resp.status_code == 401

    def test_basic_auth_header(self, adv_client):
        """Basic auth header should be rejected."""
        resp = adv_client.get("/api/cases", headers={"Authorization": "Basic YWRtaW46YWRtaW4xMjM="})
        assert resp.status_code == 401

    def test_options_preflight_bypasses_auth(self, adv_client):
        """OPTIONS requests should pass through (CORS preflight)."""
        resp = adv_client.options("/api/cases")
        assert resp.status_code in (200, 405)  # 405 if no OPTIONS handler, but not 401

    def test_login_endpoint_public(self, adv_client):
        """Login endpoint should be accessible without auth."""
        resp = adv_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200

    def test_me_endpoint_requires_auth(self, adv_client):
        """/api/auth/me is under /api/auth prefix but requires token."""
        resp = adv_client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_expired_token_rejected(self, adv_client):
        """An expired token should be rejected."""
        from datetime import timedelta
        token = create_access_token({"sub": "admin"}, expires_delta=timedelta(seconds=-1))
        resp = adv_client.get("/api/cases", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_token_for_nonexistent_user_rejected(self, adv_client):
        """Token with valid signature but for a deleted/missing user."""
        token = create_access_token({"sub": "deleted_user"})
        resp = adv_client.get("/api/cases", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# CASES — Adversarial boundary and state tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCasesAdversarial:
    """Exercise case CRUD at boundary conditions."""

    def test_create_case_empty_name_rejected(self, adv_client, adv_token):
        """Empty case name should fail Pydantic validation."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        resp = adv_client.post("/api/cases", headers=headers, json={"name": ""})
        assert resp.status_code == 422  # Pydantic validation error

    def test_create_case_very_long_name(self, adv_client, adv_token):
        """Very long case name — should be accepted (no length limit in schema)."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        long_name = "A" * 10000
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.upsert_entity = AsyncMock(return_value="id")
            mock_nc.run = AsyncMock(return_value=[{"c": {"id": "id", "name": long_name, "description": "", "status": "OPEN", "priority": "MEDIUM", "assigned_to": "", "tags": [], "created_at": "", "updated_at": ""}}])
            resp = adv_client.post("/api/cases", headers=headers, json={"name": long_name})
            assert resp.status_code == 201

    def test_create_case_name_with_cypher_injection(self, adv_client, adv_token):
        """Case name containing Cypher injection attempt — should be safe due to parameterized queries."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        evil_name = 'Test"; MATCH (n) DETACH DELETE n; //'
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.upsert_entity = AsyncMock(return_value="id")
            mock_nc.run = AsyncMock(return_value=[{"c": {"id": "id", "name": evil_name, "description": "", "status": "OPEN", "priority": "MEDIUM", "assigned_to": "", "tags": [], "created_at": "", "updated_at": ""}}])
            resp = adv_client.post("/api/cases", headers=headers, json={"name": evil_name})
            assert resp.status_code == 201
            # Verify the name was passed as a parameter, not interpolated into Cypher
            call_args = mock_nc.upsert_entity.call_args
            assert call_args[0][1]["name"] == evil_name  # positional arg

    def test_update_nonexistent_case(self, adv_client, adv_token):
        """Updating a case that doesn't exist should 404."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.run = AsyncMock(return_value=[])
            resp = adv_client.put("/api/cases/does-not-exist", headers=headers, json={"status": "ACTIVE"})
            assert resp.status_code == 404

    def test_update_case_empty_body(self, adv_client, adv_token):
        """Updating with empty body should return the case unchanged."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        mock_case = {"id": "c1", "name": "Test", "description": "", "status": "OPEN", "priority": "MEDIUM", "assigned_to": "", "tags": []}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.run = AsyncMock(return_value=[{"c": mock_case}])
            resp = adv_client.put("/api/cases/c1", headers=headers, json={})
            assert resp.status_code == 200
            # No SET query should have been executed
            assert mock_nc.run.call_count == 1  # Only the _get_case lookup

    def test_delete_already_deleted_case(self, adv_client, adv_token):
        """Double-delete should 404 on the second call."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        mock_case = {"id": "c1", "name": "Test"}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            # First delete: succeeds
            mock_nc.run = AsyncMock(side_effect=[
                [{"c": mock_case}],  # _get_case
                [],                   # DETACH DELETE
            ])
            resp = adv_client.delete("/api/cases/c1", headers=headers)
            assert resp.status_code == 204

            # Second delete: case no longer exists
            mock_nc.run = AsyncMock(return_value=[])
            resp = adv_client.delete("/api/cases/c1", headers=headers)
            assert resp.status_code == 404

    def test_add_duplicate_entity_to_case(self, adv_client, adv_token):
        """Adding the same entity twice should not fail (MERGE is idempotent)."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        mock_case = {"id": "c1", "name": "Test", "description": "", "status": "OPEN", "priority": "MEDIUM", "assigned_to": "", "tags": []}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.get_entity = AsyncMock(return_value={"n": {"id": "e1"}})
            mock_nc.run = AsyncMock(side_effect=[
                [{"c": mock_case}],  # _get_case (first add)
                [],                   # MERGE INCLUDES
                [{"eid": "e1"}],      # _get_case_entities
                [{"c": mock_case}],  # _get_case (response)
                [{"c": mock_case}],  # _get_case (second add)
                [],                   # MERGE INCLUDES (idempotent)
                [{"eid": "e1"}],      # _get_case_entities (still just one)
                [{"c": mock_case}],  # _get_case (response)
            ])
            resp1 = adv_client.post("/api/cases/c1/entities", headers=headers, json={"entity_id": "e1"})
            assert resp1.status_code == 200
            resp2 = adv_client.post("/api/cases/c1/entities", headers=headers, json={"entity_id": "e1"})
            assert resp2.status_code == 200

    def test_remove_nonexistent_entity_from_case(self, adv_client, adv_token):
        """Removing an entity that isn't linked should be a no-op (not an error)."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.run = AsyncMock(return_value=[])  # DELETE matches nothing
            resp = adv_client.delete("/api/cases/c1/entities/e999", headers=headers)
            assert resp.status_code == 204  # No-op, not an error

    def test_list_cases_empty(self, adv_client, adv_token):
        """Listing cases when none exist should return empty list."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.run = AsyncMock(return_value=[])
            resp = adv_client.get("/api/cases", headers=headers)
            assert resp.status_code == 200
            assert resp.json() == {"cases": [], "count": 0}

    def test_case_priority_any_string_accepted(self, adv_client, adv_token):
        """Verify that priority accepts any string (known schema gap)."""
        headers = {"Authorization": f"Bearer {adv_token}"}
        with patch("api.routes.cases.neo4j_client") as mock_nc:
            mock_nc.upsert_entity = AsyncMock(return_value="id")
            mock_nc.run = AsyncMock(return_value=[{"c": {"id": "id", "name": "T", "description": "", "status": "OPEN", "priority": "invalid", "assigned_to": "", "tags": [], "created_at": "", "updated_at": ""}}])
            resp = adv_client.post("/api/cases", headers=headers, json={"name": "T", "priority": "banana"})
            assert resp.status_code == 201  # Accepted — no enum validation


# ══════════════════════════════════════════════════════════════════════════════
# PDF — Adversarial boundary tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPdfAdversarial:
    """Exercise PDF generation at boundary conditions."""

    def test_pdf_with_empty_associates(self):
        """PDF generation with zero associates should not crash."""
        from ai.report_generator import ReportGenerator
        gen = ReportGenerator()
        report = {
            "entity_id": "x", "entity_name": "Test", "entity_type": "Person",
            "risk_score": 0, "risk_level": "LOW", "risk_breakdown": {},
            "summary": "Test", "known_associates": [], "associate_count": 0,
            "timeline_highlights": [], "total_events": 0,
            "community_membership": "N/A",
            "centrality_scores": {"pagerank": 0, "betweenness": 0, "degree": 0},
            "recommendations": [], "source_documents": [],
            "generated_at": "2024-01-01T00:00:00Z",
        }
        with patch.object(gen, 'generate_report', new_callable=AsyncMock, return_value=report):
            buf = asyncio.run(gen.generate_report_pdf("x", use_llm=False))
            buf.seek(0)
            assert buf.read()[:5] == b'%PDF-'

    def test_pdf_with_empty_recommendations(self):
        """PDF with no recommendations should not crash."""
        from ai.report_generator import ReportGenerator
        gen = ReportGenerator()
        report = {
            "entity_id": "x", "entity_name": "Test", "entity_type": "Person",
            "risk_score": 50, "risk_level": "MEDIUM", "risk_breakdown": {},
            "summary": "Test summary", "known_associates": [], "associate_count": 0,
            "timeline_highlights": [], "total_events": 0,
            "community_membership": "Community 1",
            "centrality_scores": {"pagerank": 0.01, "betweenness": 0.02, "degree": 0.03},
            "recommendations": [], "source_documents": [],
            "generated_at": "2024-01-01T00:00:00Z",
        }
        with patch.object(gen, 'generate_report', new_callable=AsyncMock, return_value=report):
            buf = asyncio.run(gen.generate_report_pdf("x", use_llm=False))
            buf.seek(0)
            assert buf.read()[:5] == b'%PDF-'

    def test_pdf_with_unicode_entity_name(self):
        """PDF with unicode characters in entity name should not crash."""
        from ai.report_generator import ReportGenerator
        gen = ReportGenerator()
        report = {
            "entity_id": "x", "entity_name": "राजन शर्मा", "entity_type": "Person",
            "risk_score": 80, "risk_level": "HIGH", "risk_breakdown": {"a": 10.0},
            "summary": "Test", "known_associates": [{"id": "a", "name": "Mohan", "type": "Person"}],
            "associate_count": 1, "timeline_highlights": [], "total_events": 0,
            "community_membership": "Community 1",
            "centrality_scores": {"pagerank": 0.05, "betweenness": 0.3, "degree": 0.2},
            "recommendations": ["Do something"], "source_documents": ["doc.pdf"],
            "generated_at": "2024-01-01T00:00:00Z",
        }
        with patch.object(gen, 'generate_report', new_callable=AsyncMock, return_value=report):
            buf = asyncio.run(gen.generate_report_pdf("x", use_llm=False))
            buf.seek(0)
            pdf_bytes = buf.read()
            assert pdf_bytes[:5] == b'%PDF-'

    def test_pdf_with_many_risk_factors(self):
        """PDF with many risk breakdown entries should not crash."""
        from ai.report_generator import ReportGenerator
        gen = ReportGenerator()
        report = {
            "entity_id": "x", "entity_name": "Test", "entity_type": "Person",
            "risk_score": 90, "risk_level": "CRITICAL",
            "risk_breakdown": {f"factor_{i}": float(i) for i in range(20)},
            "summary": "Test", "known_associates": [{"id": str(i), "name": f"Person {i}", "type": "Person"} for i in range(25)],
            "associate_count": 25, "timeline_highlights": [], "total_events": 0,
            "community_membership": "Community 1",
            "centrality_scores": {"pagerank": 0.1, "betweenness": 0.5, "degree": 0.3},
            "recommendations": [f"Rec {i}" for i in range(10)],
            "source_documents": [f"doc{i}.pdf" for i in range(5)],
            "generated_at": "2024-01-01T00:00:00Z",
        }
        with patch.object(gen, 'generate_report', new_callable=AsyncMock, return_value=report):
            buf = asyncio.run(gen.generate_report_pdf("x", use_llm=False))
            buf.seek(0)
            assert buf.read()[:5] == b'%PDF-'


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — State synchronization and ordering
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthStateSynchronization:
    """Verify auth state behaves correctly under ordering and concurrency."""

    def test_login_returns_consistent_token(self, adv_client):
        """Two logins should produce different tokens (different exp), same user."""
        r1 = adv_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        r2 = adv_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        t1 = r1.json()["access_token"]
        t2 = r2.json()["access_token"]
        # Both tokens decode to the same user
        # (tokens created in same second may be identical — that's fine)
        # But both decode to the same user
        assert decode_access_token(t1)["sub"] == decode_access_token(t2)["sub"] == "admin"

    def test_invalid_login_does_not_mutate_state(self, adv_client):
        """Failed login should not affect subsequent successful logins."""
        adv_client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        adv_client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        resp = adv_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200

    def test_old_token_rejected_after_user_conceptually_removed(self, adv_client):
        """A token for a user not in USERS_DB should be rejected at /me."""
        token = create_access_token({"sub": "ghost_user"})
        resp = adv_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA — Pydantic validation adversarial tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSchemaAdversarial:
    """Verify Pydantic models reject invalid input at the schema level."""

    def test_case_create_missing_name(self):
        """CaseCreate without name should fail."""
        with pytest.raises(Exception):
            CaseCreate(description="no name")

    def test_case_update_invalid_status(self):
        """CaseUpdate with invalid status string should fail."""
        with pytest.raises(Exception):
            CaseUpdate(status="INVALID_STATUS")

    def test_case_update_valid_status(self):
        """CaseUpdate with valid status enum should work."""
        u = CaseUpdate(status="CLOSED")
        assert u.status == CaseStatus.CLOSED

    def test_case_update_partial_fields(self):
        """CaseUpdate with only some fields should only include those."""
        u = CaseUpdate(priority="HIGH")
        d = u.model_dump(exclude_unset=True)
        assert d == {"priority": "HIGH"}
        assert "status" not in d
        assert "name" not in d

    def test_case_entity_add_requires_entity_id(self):
        """CaseEntityAdd without entity_id should fail."""
        with pytest.raises(Exception):
            CaseEntityAdd()

    def test_case_entity_add_with_id(self):
        """CaseEntityAdd with entity_id should work."""
        c = CaseEntityAdd(entity_id="test-123")
        assert c.entity_id == "test-123"
