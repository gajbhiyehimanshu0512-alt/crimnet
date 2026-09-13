"""
api/routes/auth.py — Authentication endpoints.
Provides login (JWT) and current-user info endpoints.
"""

import logging
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth import (
    verify_password,
    create_access_token,
    get_user,
    get_current_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Rate Limiter ────────────────────────────────────────────────────────────
# Simple in-memory rate limiter: 5 login attempts per IP per minute.

RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60

_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if this IP has exceeded the login rate limit."""
    now = time.monotonic()
    # Prune old attempts outside the window
    _login_attempts[ip] = [
        t for t in _login_attempts[ip] if now - t < RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(_login_attempts[ip]) >= RATE_LIMIT_MAX_ATTEMPTS:
        logger.warning(f"Rate limit exceeded for IP {ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    _login_attempts[ip].append(now)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse, summary="Authenticate and obtain JWT")
async def login(request: LoginRequest, req: Request):
    """Authenticate with username/password and return a JWT access token."""
    client_ip = req.client.host if req.client else "unknown"
    _check_rate_limit(client_ip)

    user = get_user(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    # Clear successful attempts for this IP
    _login_attempts.pop(client_ip, None)
    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    logger.info(f"User '{user['username']}' authenticated successfully.")
    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )


@router.get("/me", summary="Get current authenticated user")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the current user's profile (requires valid JWT)."""
    return {
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }
