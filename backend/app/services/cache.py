"""
app/services/cache.py
Lazily initialises CacheService. Returns None gracefully if Redis is unavailable,
so callers can degrade without crashing.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

_cache_service: Optional["CacheService"] = None


def get_cache() -> Optional["CacheService"]:
    """
    Return the global CacheService, or None if Redis is not available.

    Usage::
        cache = get_cache()
        if cache:
            await cache.set("key", value)
    """
    global _cache_service

    if _cache_service is not None:
        return _cache_service

    try:
        from app.db.redis_client import redis_client  # noqa: PLC0415
        from app.services.cache_service import CacheService  # noqa: PLC0415

        if redis_client is None:
            logger.warning("Redis not yet initialised — cache unavailable")
            return None

        _cache_service = CacheService(redis_client)
        return _cache_service
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache init failed (Redis down?): %s", exc)
        return None


def reset_cache() -> None:
    """Force re-init on next call (e.g. after Redis reconnects)."""
    global _cache_service
    _cache_service = None
