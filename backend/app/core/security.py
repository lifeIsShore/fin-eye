"""
app/core/security.py
Password hashing and JWT token utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# ── Password hashing ───────────────────────────────────────────────────────────
# Using bcrypt directly — passlib is not compatible with Python 3.14+

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ────────────────────────────────────────────────────────────────────────

def _make_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": subject,          # user id (UUID string)
        "type": token_type,      # "access" | "refresh"
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: str) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(user_id: str) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        token_type="refresh",
    )


def create_2fa_pending_token(user_id: str) -> str:
    """
    Short-lived token (5 minutes) issued when a user with 2FA enabled successfully
    enters their password. The client must then call POST /auth/2fa/verify with
    this token + their TOTP code to receive full access/refresh tokens.
    """
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(minutes=5),
        token_type="2fa_pending",
    )


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT. Returns the payload dict or None if invalid.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None