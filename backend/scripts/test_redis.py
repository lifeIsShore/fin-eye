import asyncio
import os
import sys

# Ensure this path matches the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__name__), "..")))

from app.db.redis_client import init_redis, close_redis, get_redis
from app.services.cache_service import CacheService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis():
    await init_redis()
    redis_client = get_redis()
    cache = CacheService(redis_client)

    logger.info("Setting test key...")
    await cache.set("test_key", {"status": "success", "message": "Hello from Redis"})
    
    logger.info("Getting test key...")
    val = await cache.get("test_key")
    logger.info(f"Retrieved: {val}")

    logger.info("Testing get_or_set fallback...")
    
    async def dummy_fetch():
        logger.info("Dummy fetch triggered!")
        return {"fetched": True, "data": "New data"}

    data = await cache.get_or_set("dummy_key", dummy_fetch, ttl=60)
    logger.info(f"Fallback retrieved: {data}")
    
    data2 = await cache.get_or_set("dummy_key", dummy_fetch, ttl=60)
    logger.info(f"Second fetch (should hit cache): {data2}")

    logger.info("Cleaning up...")
    await cache.delete("test_key")
    await cache.delete("dummy_key")
    await close_redis()
    logger.info("✅ Redis Test Complete")

if __name__ == "__main__":
    asyncio.run(test_redis())
