"""
backend/tests/test_auth.py — Unit tests for JWT authentication.
Run with: pytest backend/tests/test_auth.py -v
"""

import pytest
from jose import JWTError

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_user,
    USERS_DB,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


# ── Password Hashing ─────────────────────────────────────────────────────────

def test_hash_password_returns_string():
    h = hash_password("testpass")
    assert isinstance(h, str)
    assert h != "testpass"


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_incorrect():
    h = hash_password("secret123")
    assert verify_password("wrong", h) is False


def test_different_hashes_for_same_password():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


# ── JWT Token ────────────────────────────────────────────────────────────────

def test_create_and_decode_token():
    token = create_access_token({"sub": "admin", "role": "admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_access_token("not.a.valid.token")


def test_token_has_expiry():
    import datetime
    token = create_access_token({"sub": "test"})
    payload = decode_access_token(token)
    exp = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    assert exp > now
    max_exp = now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES + 1)
    assert exp <= max_exp


def test_token_with_custom_expiry():
    import datetime
    from datetime import timedelta
    token = create_access_token({"sub": "test"}, expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    exp = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    assert (exp - now) <= timedelta(minutes=6)


# ── User Store ───────────────────────────────────────────────────────────────

def test_get_existing_user():
    user = get_user("admin")
    assert user is not None
    assert user["username"] == "admin"
    assert user["role"] == "admin"
    assert "hashed_password" in user


def test_get_nonexistent_user():
    user = get_user("doesnotexist")
    assert user is None


def test_default_users_exist():
    assert "admin" in USERS_DB
    assert "analyst" in USERS_DB


def test_default_admin_password_works():
    user = get_user("admin")
    assert verify_password("admin123", user["hashed_password"])


def test_default_analyst_password_works():
    user = get_user("analyst")
    assert verify_password("analyst123", user["hashed_password"])


# ── API Integration (uses shared test_client fixture) ────────────────────────

def test_health_not_available_on_test_app(client):
    """The test app doesn't include /health, so it's blocked by auth middleware."""
    resp = client.get("/health")
    assert resp.status_code in (401, 404, 405)


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


def test_protected_endpoint_no_token(client):
    """Protected /api/cases should reject requests without a token."""
    resp = client.get("/api/cases")
    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token(client, auth_headers):
    """Protected endpoint should accept a valid JWT."""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_protected_endpoint_with_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code == 401


def test_me_endpoint_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
