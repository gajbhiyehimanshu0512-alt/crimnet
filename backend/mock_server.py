"""
mock_server.py — Lightweight mock backend for demo/preview purposes.
Implements auth endpoints without requiring Neo4j or other heavy dependencies.
Run with: python mock_server.py
"""

import logging
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

SECRET_KEY = "demo-secret-key-not-for-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "full_name": "System Administrator",
        "role": "admin",
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": pwd_context.hash("analyst123"),
        "full_name": "Intelligence Analyst",
        "role": "analyst",
    },
}

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="CrimNet Mock API")

# ── Auth Middleware ───────────────────────────────────────────────────────────

PUBLIC_PREFIXES = ("/api/auth", "/health")


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None or sub not in USERS_DB:
            return JSONResponse(status_code=401, content={"detail": "Invalid token or user not found"})
    except JWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    return await call_next(request)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth Endpoints ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = USERS_DB.get(request.username)
    if not user or not pwd_context.verify(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user["username"], "role": user["role"], "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@app.get("/api/auth/me")
async def get_me():
    # In a real app, this would use Depends(get_current_user)
    # For the mock, we just check the middleware already validated
    return {"username": "admin", "full_name": "System Administrator", "role": "admin"}


# ── Mock Graph Endpoints ─────────────────────────────────────────────────────

@app.get("/api/graph/stats")
async def graph_stats():
    return {
        "total_nodes": 42,
        "total_edges": 87,
        "persons": 15,
        "organizations": 5,
        "locations": 8,
        "phones": 10,
        "vehicles": 4,
        "accounts": 3,
        "critical_risk": 2,
        "high_risk": 5,
    }


@app.get("/api/graph/network")
async def get_network(limit: int = 300):
    return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}


@app.get("/api/graph/search")
async def search_entities(q: str = "", limit: int = 20):
    return {"results": [], "count": 0, "query": q}


@app.get("/api/graph/communities")
async def get_communities():
    return {"communities": [], "total": 0}


@app.get("/api/analytics/influencers")
async def get_influencers(top_n: int = 20):
    return {"influencers": [], "count": 0}


@app.get("/api/analytics/anomalies")
async def get_anomalies():
    return {"alerts": [], "count": 0}


@app.post("/api/analytics/run")
async def run_analytics():
    return {"status": "complete", "centrality": {"nodes_analyzed": 0}, "communities": {"total_communities": 0}, "risk_scoring": {"entities_scored": 0}}


@app.get("/api/ai/report/{entity_id}")
async def get_report(entity_id: str, use_llm: bool = True):
    return {"error": "No data available in demo mode"}


@app.get("/api/cases")
async def list_cases():
    return {"cases": [], "count": 0}


@app.post("/api/cases")
async def create_case(payload: dict):
    return {"id": "demo-1", "name": payload.get("name", "Demo Case"), "status": "OPEN", "priority": "MEDIUM"}


# ── Ingestion Endpoints (Mock) ───────────────────────────────────────────────

@app.post("/api/ingest/fir")
async def ingest_fir():
    return {
        "status": "success",
        "parsed_fields": {"fir_number": "FIR-2024-001", "police_station": "Dharavi"},
        "source": "FIR_Sample",
        "entities_extracted": 6,
        "entities_stored": 6,
        "relationships_stored": 8,
        "entity_ids": ["ent-1", "ent-2", "ent-3"],
    }


@app.post("/api/ingest/cdr")
async def ingest_cdr():
    return {
        "status": "success",
        "total_records": 50,
        "entities_stored": 12,
        "relationships_stored": 50,
        "entity_ids": ["phone-1", "phone-2"],
    }


@app.post("/api/ingest/financial")
async def ingest_financial():
    return {
        "status": "success",
        "total_records": 30,
        "suspicious_count": 8,
        "entities_stored": 10,
        "relationships_stored": 30,
        "entity_ids": ["acct-1", "acct-2"],
    }


@app.post("/api/ingest/surveillance")
async def ingest_surveillance():
    return {
        "status": "success",
        "parsed_fields": {"subject": "Rajan Sharma"},
        "entities_stored": 5,
        "relationships_stored": 7,
        "entity_ids": ["surv-1", "surv-2"],
    }


@app.post("/api/ingest/social")
async def ingest_social():
    return {
        "status": "success",
        "entities_stored": 6,
        "relationships_stored": 9,
        "entity_ids": ["soc-1", "soc-2"],
    }


@app.post("/api/ingest/text")
async def ingest_text():
    return {
        "status": "success",
        "entities_extracted": 8,
        "entities_stored": 8,
        "relationships_stored": 11,
        "entity_ids": ["text-1", "text-2"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0-demo"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
