import asyncio
from app.db.redis_client import init_redis, get_redis

async def test_health():
    await init_redis()
    redis = get_redis()
    try:
        ping = await redis.ping()
        print(f"Health Ping Result: {ping}")
    except Exception as e:
        print(f"Health Ping Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_health())
