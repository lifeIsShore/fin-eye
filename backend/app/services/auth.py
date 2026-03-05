"""
app/services/auth.py

Shared FastAPI dependencies for authentication and authorisation.

Provides:
  - get_current_user      — resolves JWT → User (sync-compatible via db session)
  - require_admin         — like get_current_user but enforces is_admin=True
  - optional_current_user — resolves JWT → User | None (never raises, for optional auth)

These are deliberately thin wrappers around the lower-level auth_service
so that endpoint code stays declarative:

    @router.get("/admin/stuff", dependencies=[Depends(require_admin)])
    async def admin_stuff(): ...

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)): ...
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


# ─── Async variants (for async endpoints) ────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate Bearer token and return the authenticated User (async).
    Raises HTTP 401 if token is missing, invalid, or expired.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise exc

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise exc

    uid_str: str | None = payload.get("sub")
    if not uid_str:
        raise exc

    try:
        user_id = uuid.UUID(uid_str)
    except ValueError:
        raise exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise exc

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that enforces the caller is an active admin user.
    Raises HTTP 403 for authenticated non-admin users.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Soft auth dependency — resolves to a User if a valid token is present,
    or None if no token / invalid token. Never raises.
    Use for endpoints that behave differently for authed vs anon users.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload is None or payload.get("type") != "access":
            return None
        uid_str = payload.get("sub")
        if not uid_str:
            return None
        user = await get_user_by_id(db, uuid.UUID(uid_str))
        return user if (user and user.is_active) else None
    except Exception:
        return None
