"""
backend/tests/conftest.py — Shared test fixtures.
Provides a lightweight FastAPI test app that only registers the routers
needed by auth, report PDF, and case management tests, avoiding heavy
dependency imports (networkx, spacy, pandas, torch, etc.).
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError

from auth import decode_access_token, get_user
from api.routes import auth as auth_routes, cases as cases_routes, ai as ai_routes


PUBLIC_PREFIXES = ("/api/auth",)


def _build_test_app() -> FastAPI:
    """Create a minimal FastAPI app with only the routers our tests need."""
    app = FastAPI(title="CrimNet Test App")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware — mirrors main.py's auth_middleware
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing authentication token"})

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub is None or not get_user(sub):
                return JSONResponse(status_code=401, content={"detail": "Invalid token or user not found"})
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        return await call_next(request)

    # Only the routers exercised by our three test files
    app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(ai_routes.router,   prefix="/api/ai",   tags=["AI / LLM"])
    app.include_router(cases_routes.router, prefix="/api/cases", tags=["Case Management"])

    return app


@pytest.fixture(scope="session")
def test_app():
    """A lightweight FastAPI app for testing without heavy deps."""
    return _build_test_app()


@pytest.fixture(scope="session")
def client(test_app):
    """A sync TestClient bound to the lightweight test app."""
    from starlette.testclient import TestClient
    return TestClient(test_app)


@pytest.fixture(scope="session")
def token(client):
    """A valid JWT token obtained by logging in as admin."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    """Authorization headers dict with a valid Bearer token."""
    return {"Authorization": f"Bearer {token}"}
