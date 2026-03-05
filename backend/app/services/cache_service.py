import json
import logging
from typing import Any, Optional, Callable, Dict
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = settings.cache_ttl

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache and deserialize it."""
        try:
            val = await self.redis.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serialize and set a value in the cache with a TTL."""
        try:
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            serialized_val = json.dumps(value)
            await self.redis.set(key, serialized_val, ex=ttl_to_use)
            return True
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {e}")
            return False

    async def set_macro(self, data: Dict[str, Any]) -> bool:
        """Helper to set macro scores in cache with default key."""
        return await self.set("macro_scores", data)

    async def ping(self) -> bool:
        """Check if Redis is alive."""
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error(f"Cache PING error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for {key}: {e}")
            return False

    async def get_or_set(self, key: str, fetch_func: Callable, ttl: Optional[int] = None, **kwargs) -> Any:
        """
        Generic function to get from cache, or fetch and set if not exists.
        `fetch_func` should be an async callable that returns the data to cache.
        """
        cached_data = await self.get(key)
        if cached_data is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_data

        logger.debug(f"Cache miss for key: {key}, fetching data...")
        try:
            data = await fetch_func(**kwargs)
            # Only cache if we got data back (not None or empty depending on use case, but generally not None)
            if data is not None:
                await self.set(key, data, ttl)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            raise
