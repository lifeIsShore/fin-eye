"""
app/services/api_key_service.py

P3-API-01 — API key lifecycle + auth + rate limiting.

Key format: fe_live_<32 random urlsafe bytes>
  - prefix stored in DB (first 12 chars after "fe_live_")
  - full key hashed with SHA-256 and stored as hex
  - raw key shown ONCE at creation and never retrievable again

Rate limiting: simple in-memory sliding window counter backed by Redis.
  - Key: api_rl:{api_key_id}
  - TTL: 60 seconds
  - If Redis unavailable, falls back to allow (fail open)

Scopes:
  "gas"        — /public/v1/gas/{symbol}
  "macro"      — /public/v1/macro/latest, /public/v1/macro/advanced
  "sentiment"  — /public/v1/sentiment/{symbol}
  "technical"  — /public/v1/technical/{symbol}
  "risk"       — /public/v1/risk/stress/{symbol}
  "backtest"   — /public/v1/backtest
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey, ApiKeyUsageLog

logger = logging.getLogger(__name__)

# Available scopes
ALL_SCOPES = {"gas", "macro", "sentiment", "technical", "risk", "backtest"}
DEFAULT_SCOPES = "gas,macro,sentiment"
DEFAULT_RATE_LIMIT = 30  # requests per minute


# ─── Key generation ───────────────────────────────────────────────────────────

def _generate_raw_key() -> str:
    """Generate a random API key: fe_live_<64 hex chars>"""
    return "fe_live_" + secrets.token_hex(32)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hex digest of the raw key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _prefix(raw_key: str) -> str:
    """First 12 chars after 'fe_live_' — shown in UI for identification."""
    return raw_key[8:20]  # chars 8-19


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_api_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT,
    expires_at: Optional[datetime] = None,
) -> tuple[ApiKey, str]:
    """
    Create a new API key.
    Returns (ApiKey ORM object, raw_key string).
    raw_key is shown ONCE and not stored — only its hash is persisted.
    """
    if scopes is None:
        scopes = DEFAULT_SCOPES.split(",")

    # Validate scopes
    invalid = set(scopes) - ALL_SCOPES
    if invalid:
        raise ValueError(f"Invalid scopes: {invalid}. Valid: {ALL_SCOPES}")

    raw_key = _generate_raw_key()

    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_prefix=_prefix(raw_key),
        hashed_key=_hash_key(raw_key),
        scopes=",".join(scopes),
        rate_limit_per_minute=rate_limit_per_minute,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()

    logger.info("Created API key '%s' (prefix=%s) for user_id=%s", name, api_key.key_prefix, user_id)
    return api_key, raw_key


async def list_api_keys(db: AsyncSession, user_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession,
    api_key_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str = "user_revoked",
) -> bool:
    """Soft-delete an API key. Returns True if found and revoked."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        return False
    key.is_active = False
    key.revoked_at = datetime.now(timezone.utc)
    key.revoke_reason = reason
    return True


async def update_api_key_scopes(
    db: AsyncSession,
    api_key_id: uuid.UUID,
    user_id: uuid.UUID,
    scopes: list[str],
) -> ApiKey | None:
    invalid = set(scopes) - ALL_SCOPES
    if invalid:
        raise ValueError(f"Invalid scopes: {invalid}")
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        return None
    key.scopes = ",".join(scopes)
    return key


# ─── Authentication ───────────────────────────────────────────────────────────

async def authenticate_api_key(
    db: AsyncSession,
    raw_key: str,
) -> ApiKey | None:
    """
    Validate a raw API key.
    Returns the ApiKey if valid and active, None otherwise.
    Also checks expiry.
    """
    hashed = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.hashed_key == hashed)
    )
    key = result.scalar_one_or_none()
    if key is None or not key.is_active:
        return None

    # Check expiry
    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
        return None

    return key


async def record_api_call(
    db: AsyncSession,
    api_key: ApiKey,
    endpoint: str,
    method: str = "GET",
    status_code: int = 200,
    response_ms: int = 0,
) -> None:
    """Non-fatal usage recording. Updates counter and last_used_at."""
    try:
        key_id = api_key.id
        # Upsert stats on the key (increment total_calls, set last_used_at)
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(
                total_calls=ApiKey.total_calls + 1,
                last_used_at=datetime.now(timezone.utc),
            )
        )
        # Append log row
        log = ApiKeyUsageLog(
            api_key_id=key_id,
            endpoint=endpoint[:256],
            method=method,
            status_code=status_code,
            response_ms=response_ms,
        )
        db.add(log)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to record API key usage: %s", exc)


# ─── Rate limiting (Redis-backed, fail-open) ─────────────────────────────────

async def check_rate_limit(api_key: ApiKey) -> tuple[bool, int]:
    """
    Sliding-window rate limit check using Redis.
    Returns (allowed: bool, remaining: int).
    Fails open if Redis is unavailable.
    """
    try:
        from app.db.redis_client import get_redis  # noqa: PLC0415

        redis = await get_redis()
        if redis is None:
            return True, api_key.rate_limit_per_minute

        rl_key = f"api_rl:{api_key.id}"
        pipe = redis.pipeline()
        now_ms = int(time.time() * 1000)
        window_ms = 60_000  # 1 minute

        pipe.zremrangebyscore(rl_key, 0, now_ms - window_ms)
        pipe.zcard(rl_key)
        pipe.zadd(rl_key, {str(now_ms): now_ms})
        pipe.expire(rl_key, 65)  # 65s TTL — slightly more than window

        results = await pipe.execute()
        current_count = results[1]  # count BEFORE adding current request

        if current_count >= api_key.rate_limit_per_minute:
            remaining = 0
            # Remove the request we just added (rejected)
            await redis.zrem(rl_key, str(now_ms))
            return False, remaining

        remaining = max(0, api_key.rate_limit_per_minute - current_count - 1)
        return True, remaining

    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate limit check failed (fail-open): %s", exc)
        return True, api_key.rate_limit_per_minute
