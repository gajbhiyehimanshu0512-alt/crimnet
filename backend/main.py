"""
main.py — FastAPI application entry point.
Wires up all routers, middleware, lifecycle events, and WebSocket support.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from graph.neo4j_client import neo4j_client
from api.routes import ingest, graph, analytics, ai as ai_routes, cases as cases_routes
from api.routes import auth as auth_routes
from auth import decode_access_token, get_user
from jose import JWTError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("🚀 Criminal Network Analyzer starting up...")
    await neo4j_client.connect()
    await neo4j_client.init_constraints()
    logger.info("✅ Neo4j connected and schema initialised.")
    yield
    logger.info("🛑 Shutting down...")
    await neo4j_client.close()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Criminal Network Analyzer API",
    description=(
        "AI-powered system for analyzing criminal networks, extracting entities, "
        "mapping relationships, and detecting suspicious patterns."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Auth-protected paths ──────────────────────────────────────────────────────
# All /api/* routes except /api/auth/* require a valid JWT Bearer token.
# /health and /api/auth/* are public.

PUBLIC_PREFIXES = ("/api/auth", "/health")

# In production, docs endpoints require authentication
IS_PRODUCTION = settings.app_env.lower() in ("production", "prod")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Always allow CORS preflight, health, and public API prefixes
    if (
        request.method == "OPTIONS"
        or path == "/health"
        or any(path.startswith(p) for p in PUBLIC_PREFIXES)
    ):
        return await call_next(request)

    # In production, gate docs behind authentication
    docs_paths = ("/docs", "/redoc", "/openapi.json")
    if IS_PRODUCTION and any(path.startswith(d) for d in docs_paths):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Authentication required to access API docs"})
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub is None or not get_user(sub):
                return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        return await call_next(request)

    # In development, allow docs without auth
    if not IS_PRODUCTION and any(path.startswith(d) for d in docs_paths):
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


# ── CORS ──────────────────────────────────────────────────────────────────────
# Added AFTER auth_middleware so it wraps the entire middleware stack and ensures
# CORS headers (e.g. Access-Control-Allow-Origin) are present on ALL responses,
# including 401s, 403s, and 500s returned by inner middlewares.

_LOCAL_ORIGIN = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
_EXTRA_ORIGINS = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        *_EXTRA_ORIGINS,
    ],
    allow_origin_regex=_LOCAL_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(ingest.router,    prefix="/api/ingest",    tags=["Ingestion"])
app.include_router(graph.router,     prefix="/api/graph",     tags=["Knowledge Graph"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ai_routes.router, prefix="/api/ai",        tags=["AI / LLM"])
app.include_router(cases_routes.router, prefix="/api/cases",     tags=["Case Management"])


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
async def root():
    """Index route — also used as a default health check by some hosts."""
    return {
        "service": "CrimNet API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
