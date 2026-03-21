"""
app/services/auth_security.py

Sprint 7 security hardening (SEC-03, SEC-04, SEC-05):

  Rate limiting  — enforced per IP address via Redis sliding-window counters.
                   login 10/min, register 5/min, 2FA verify 5/min (SEC-03).

  Account lockout — 10 failed login attempts in 15 minutes → 30-minute lockout.
                    Stored in Redis, not the DB (fast + no schema change) (SEC-05).

  JTI blacklist   — refresh token JTIs are stored in Redis on issue.
                    On logout the JTI is added to the blacklist with TTL = remaining
                    token lifetime, so the set never grows unboundedly (SEC-04).

All functions return False / raise HTTPException rather than crashing when Redis
is unavailable so that the API degrades gracefully if Redis is down.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_LOGIN_LIMIT_MAX     = 10    # max login attempts per IP per window
_LOGIN_LIMIT_WINDOW  = 60    # window in seconds
_REGISTER_LIMIT_MAX  = 5
_REGISTER_LIMIT_WINDOW = 60
_TOTP_LIMIT_MAX      = 5
_TOTP_LIMIT_WINDOW   = 60

_LOCKOUT_MAX_FAILS   = 10    # failed logins before lockout
_LOCKOUT_WINDOW      = 900   # 15 minutes sliding window for fail count
_LOCKOUT_DURATION    = 1800  # 30 minutes lockout once triggered

# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from reverse proxies."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _sliding_window_check(
    redis: Redis,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> bool:
    """
    Sliding-window rate limiter using Redis sorted sets.
    Returns True if the request is allowed, False if over limit.
    The key is auto-expired after window_seconds of inactivity.
    """
    try:
        now = time.time()
        cutoff = now - window_seconds
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()
        current_count = int(results[1])
        return current_count < max_requests
    except Exception as exc:
        logger.warning("Rate limit check failed (Redis error) — allowing: %s", exc)
        return True   # fail-open: don't block users if Redis is down


# ── Public API: Rate limiting ─────────────────────────────────────────────────

async def check_login_rate_limit(request: Request, redis: Redis) -> None:
    """Raise 429 if the IP has exceeded the login rate limit."""
    ip  = _client_ip(request)
    key = f"ratelimit:login:{ip}"
    if not await _sliding_window_check(redis, key, _LOGIN_LIMIT_MAX, _LOGIN_LIMIT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please wait {_LOGIN_LIMIT_WINDOW} seconds.",
            headers={"Retry-After": str(_LOGIN_LIMIT_WINDOW)},
        )


async def check_register_rate_limit(request: Request, redis: Redis) -> None:
    """Raise 429 if the IP has exceeded the registration rate limit."""
    ip  = _client_ip(request)
    key = f"ratelimit:register:{ip}"
    if not await _sliding_window_check(redis, key, _REGISTER_LIMIT_MAX, _REGISTER_LIMIT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Please wait {_REGISTER_LIMIT_WINDOW} seconds.",
            headers={"Retry-After": str(_REGISTER_LIMIT_WINDOW)},
        )


async def check_totp_rate_limit(request: Request, redis: Redis) -> None:
    """Raise 429 if the IP has exceeded the 2FA verify rate limit."""
    ip  = _client_ip(request)
    key = f"ratelimit:totp:{ip}"
    if not await _sliding_window_check(redis, key, _TOTP_LIMIT_MAX, _TOTP_LIMIT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many 2FA attempts. Please wait {_TOTP_LIMIT_WINDOW} seconds.",
            headers={"Retry-After": str(_TOTP_LIMIT_WINDOW)},
        )


# ── Public API: Account lockout (SEC-05) ─────────────────────────────────────

async def check_account_lockout(email: str, redis: Redis) -> None:
    """
    Raise 403 if the account is currently locked out due to too many
    failed login attempts. Called BEFORE credential verification.
    """
    try:
        lockout_key = f"lockout:{email.lower()}"
        locked = await redis.get(lockout_key)
        if locked:
            ttl = await redis.ttl(lockout_key)
            mins = max(1, ttl // 60)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Account temporarily locked due to too many failed login attempts. "
                    f"Try again in {mins} minute{'s' if mins != 1 else ''}."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Lockout check failed (Redis error) — allowing: %s", exc)


async def record_failed_login(email: str, redis: Redis) -> None:
    """
    Increment the failed login counter for this email.
    If it reaches _LOCKOUT_MAX_FAILS, set a lockout key for _LOCKOUT_DURATION.
    """
    try:
        fail_key    = f"loginfail:{email.lower()}"
        lockout_key = f"lockout:{email.lower()}"

        pipe = redis.pipeline()
        pipe.incr(fail_key)
        pipe.expire(fail_key, _LOCKOUT_WINDOW)
        results = await pipe.execute()
        fail_count = int(results[0])

        if fail_count >= _LOCKOUT_MAX_FAILS:
            await redis.setex(lockout_key, _LOCKOUT_DURATION, "1")
            await redis.delete(fail_key)   # reset counter after lockout is set
            logger.warning("Account locked out: %s (fail_count=%d)", email, fail_count)
    except Exception as exc:
        logger.warning("record_failed_login Redis error (non-fatal): %s", exc)


async def clear_failed_logins(email: str, redis: Redis) -> None:
    """Clear the failed login counter after a successful login."""
    try:
        await redis.delete(f"loginfail:{email.lower()}")
    except Exception:
        pass


# ── Public API: JTI blacklist (SEC-04) ───────────────────────────────────────

_JTI_PREFIX = "jti:blacklist:"


async def blacklist_jti(jti: str, ttl_seconds: int, redis: Redis) -> None:
    """
    Add a JTI to the Redis blacklist for the remainder of its lifetime.
    TTL ensures the set never grows unboundedly.
    """
    try:
        if ttl_seconds > 0:
            await redis.setex(f"{_JTI_PREFIX}{jti}", ttl_seconds, "1")
    except Exception as exc:
        logger.warning("blacklist_jti Redis error (non-fatal): %s", exc)


async def is_jti_blacklisted(jti: str, redis: Redis) -> bool:
    """Return True if the JTI has been blacklisted (token revoked)."""
    try:
        val = await redis.get(f"{_JTI_PREFIX}{jti}")
        return val is not None
    except Exception as exc:
        logger.warning("is_jti_blacklisted Redis error — allowing: %s", exc)
        return False   # fail-open: better to accept a possibly-revoked token
                        # than to block all refreshes when Redis is down
