"""
api/routes/auth.py — Authentication endpoints.
Provides login (JWT) and current-user info endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import (
    verify_password,
    create_access_token,
    get_user,
    get_current_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse, summary="Authenticate and obtain JWT")
async def login(request: LoginRequest):
    """Authenticate with username/password and return a JWT access token."""
    user = get_user(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
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
