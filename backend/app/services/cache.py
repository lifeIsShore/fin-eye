from app.services.cache_service import CacheService
from app.db.redis_client import get_redis

_cache_service = None

def get_cache() -> CacheService:
    """Helper to get or create a global CacheService instance."""
    global _cache_service
    if _cache_service is None:
        redis_client = get_redis()
        _cache_service = CacheService(redis_client)
    return _cache_service
