"""Test Redis connection directly."""
import asyncio
from redis.asyncio import Redis
from app.config import settings

async def test_redis():
    print(f"Connecting to: {settings.redis_url}")
    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5.0
        )
        await redis_client.ping()
        print("SUCCESS! Ping successful.")
    except Exception as e:
        print(f"FAILED! Error: {type(e).__name__} - {e}")
    finally:
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(test_redis())
