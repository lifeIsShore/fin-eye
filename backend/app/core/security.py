"""
app/core/security.py

Password hashing and JWT token utilities.

Sprint 7 (SEC-04): Refresh tokens now carry a JTI (JWT ID — unique UUID per token).
The JTI is stored in Redis on issue. On logout the JTI is blacklisted.
The /auth/refresh endpoint rotates the JTI: old token is blacklisted, new one issued.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# ── Password hashing ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ────────────────────────────────────────────────────────────────────────

def _make_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str,
    jti: Optional[str] = None,
) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict = {
        "sub":  subject,
        "type": token_type,
        "exp":  expire,
    }
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: str) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(user_id: str, jti: Optional[str] = None) -> tuple[str, str]:
    """
    Create a refresh token. Returns (token, jti).
    The JTI is a UUID embedded in the token and returned so callers can
    store/blacklist it independently.
    """
    jti = jti or str(uuid.uuid4())
    token = _make_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        token_type="refresh",
        jti=jti,
    )
    return token, jti


def create_2fa_pending_token(user_id: str) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(minutes=5),
        token_type="2fa_pending",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
