"""Login / logout / session-status endpoints.

Route summary:
  POST /auth/login   -> 200 {ok: true}  sets HttpOnly cookie
  POST /auth/logout  -> 204            clears cookie (requires auth)
  GET  /auth/status  -> 200 {authenticated: bool}
"""
import asyncio
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

import config
from auth import (
    create_session_token,
    current_owner,
    require_owner,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory sliding-window rate limit on /auth/login.
# Single-instance deploy only — a second process would not share this state.
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 15 * 60
_attempts: dict[str, deque[float]] = {}


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    bucket = _attempts.setdefault(ip, deque())
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
    bucket.append(now)


class LoginPayload(BaseModel):
    password: str


class StatusResponse(BaseModel):
    authenticated: bool


@router.post("/login")
async def login(payload: LoginPayload, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if not verify_password(payload.password):
        # Small jitter to blunt timing side-channels without being annoying.
        await asyncio.sleep(0.2)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=config.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=config.is_production(),
        path="/",
    )
    return {"ok": True}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, _: bool = Depends(require_owner)):
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.is_production(),
    )


@router.get("/status", response_model=StatusResponse)
async def status_endpoint(is_authed: bool = Depends(current_owner)):
    return StatusResponse(authenticated=is_authed)
