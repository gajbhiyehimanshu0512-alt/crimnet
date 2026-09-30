"""
auth.py — JWT authentication utilities.
Provides token creation/validation, password hashing, and a FastAPI dependency
for protecting routes. Uses a simple in-memory user store for development.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

logger = logging.getLogger(__name__)

# ── Password Hashing ─────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Settings ─────────────────────────────────────────────────────────────

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours


# ── In-Memory User Store ─────────────────────────────────────────────────────
# For production, replace with PostgreSQL / OAuth provider.

USERS_DB: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "hashed_password": hash_password("admin123"),
        "full_name": "System Administrator",
        "role": "admin",
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": hash_password("analyst123"),
        "full_name": "Intelligence Analyst",
        "role": "analyst",
    },
}


def get_user(username: str) -> Optional[dict]:
    return USERS_DB.get(username)


# ── Token Helpers ────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

class _Bearer(HTTPBearer):
    """HTTPBearer that always answers 401 when credentials are absent.

    fastapi==0.111.0 — the pin in requirements.txt, and therefore what CI and
    Render install — raises 403 from HTTPBearer for a missing header. Newer
    releases were corrected to 401 to match RFC 7235. Normalising here keeps
    behaviour identical whichever FastAPI the environment resolves, and keeps
    the frontend's 401 interceptor firing on unauthenticated requests.
    """

    async def __call__(self, request: Request):
        try:
            return await super().__call__(request)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            raise


security = _Bearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency: extracts and validates the JWT from the Authorization header.
    Returns the user dict on success, or raises 401."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
