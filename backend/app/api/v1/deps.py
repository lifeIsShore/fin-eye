"""
app/api/v1/deps.py
FastAPI dependencies — reusable across all route modules.

DEV BYPASS
----------
When REQUIRE_AUTH=False (set in .env), get_current_user returns a guaranteed
dev user instead of validating a JWT.  This matches the frontend AuthProvider
bypass which injects the same fixed UUID (00000000-0000-0000-0000-000000000001).
The dev user is upserted into the DB on first call so all DB-backed routes
(portfolios, watchlists, etc.) work without a real login flow.
"""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.core.security import decode_token, hash_password
from app.db.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

# Fixed UUID that matches the frontend AuthProvider mock user
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    """
    Return the dev bypass user, creating it in the DB if it doesn't exist yet.
    Called only when REQUIRE_AUTH=False.
    """
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=DEV_USER_ID,
            email="dev@mock.local",
            hashed_password=hash_password("dev-bypass-not-a-real-password"),
            name="Dev User",
            is_active=True,
            is_verified=True,
            is_admin=True,
            subscription_tier="pro",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate Bearer token and return the authenticated User.

    When REQUIRE_AUTH=False (dev mode) the JWT check is skipped entirely and
    the fixed dev user is returned so all portfolio/watchlist endpoints work
    without a real auth flow.
    """
    # ── Dev bypass ────────────────────────────────────────────────────────────
    if not settings.require_auth:
        return await _get_or_create_dev_user(db)

    # ── Production path: validate JWT ─────────────────────────────────────────
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_verified_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Extra guard — requires email to be verified."""
    if not settings.require_auth:
        return current_user  # dev bypass: always pass
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified.",
        )
    return current_user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Returns the current user if authenticated, else None (public access)."""
    if not settings.require_auth:
        return await _get_or_create_dev_user(db)
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload is None or payload.get("type") != "access":
            return None
        user_id = uuid.UUID(payload["sub"])
        user = await get_user_by_id(db, user_id)
        return user if (user and user.is_active) else None
    except Exception:
        return None


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to restrict access to superusers."""
    if not settings.require_auth:
        return current_user  # dev bypass: always pass
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user
