import redis.asyncio as redis
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Global redis client instance
redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize the Redis connection pool."""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis_url, 
            encoding="utf-8", 
            decode_responses=True
        )
        # Test connection
        await redis_client.ping()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        redis_client = None

async def close_redis():
    """Close the Redis connection pool."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

def get_redis() -> redis.Redis:
    """Dependency for getting the Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client
