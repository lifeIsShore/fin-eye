import redis.asyncio as redis
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Global redis client instance
redis_client: Optional[redis.Redis] = None

def _build_redis_url() -> str:
    """
    Build Redis URL, injecting password if needed but avoiding double injection.
    """
    url = settings.redis_url
    password = settings.redis_password
    
    # Only inject if password exists AND it's not already in the URL
    if password and password not in url and "@" not in url:
        url = url.replace("redis://", f"redis://default:{password}@", 1)
    return url


async def init_redis():
    """Initialize the Redis connection pool."""
    global redis_client
    try:
        redis_url = _build_redis_url()
        print(f"INIT_REDIS URL: {redis_url}")
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5.0
        )
        # Test connection
        await redis_client.ping()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        print(f"INIT_REDIS ERROR [{type(e).__name__}]: {e}")
        logger.error(f"❌ Redis connection failed: {e}")
        redis_client = None

async def close_redis():
    """Close the Redis connection pool."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed")

def get_redis() -> redis.Redis:
    """Dependency for getting the Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client
