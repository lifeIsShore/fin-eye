import pytest
from unittest.mock import AsyncMock
from app.services.cache_service import CacheService

@pytest.fixture
def mock_redis():
    """Returns an AsyncMock simulating a redis.Redis client."""
    mock = AsyncMock()
    # Mock behavior for get, set, delete
    mock.get.return_value = b'{"status": "cached"}'
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock

@pytest.fixture
def cache_service(mock_redis):
    # Pass our mocked redis client
    return CacheService(mock_redis)

@pytest.mark.asyncio
async def test_cache_get(cache_service, mock_redis):
    """Test getting a value from cache."""
    val = await cache_service.get("test_key")
    mock_redis.get.assert_called_once_with("test_key")
    assert val == {"status": "cached"}

@pytest.mark.asyncio
async def test_cache_get_miss(cache_service, mock_redis):
    """Test get behavior on a cache miss."""
    mock_redis.get.return_value = None
    val = await cache_service.get("missing_key")
    assert val is None

@pytest.mark.asyncio
async def test_cache_set(cache_service, mock_redis):
    """Test setting a value in cache with serialization."""
    success = await cache_service.set("test_key", {"data": 123}, ttl=60)
    mock_redis.set.assert_called_once_with("test_key", '{"data": 123}', ex=60)
    assert success is True

@pytest.mark.asyncio
async def test_cache_delete(cache_service, mock_redis):
    """Test deleting a key from cache."""
    success = await cache_service.delete("test_key")
    mock_redis.delete.assert_called_once_with("test_key")
    assert success is True

@pytest.mark.asyncio
async def test_cache_get_or_set_hit(cache_service, mock_redis):
    """Test fallback when key is in cache."""
    mock_fetch = AsyncMock()
    
    val = await cache_service.get_or_set("test_key", mock_fetch)
    
    # Should not call the mock fetch if data is in cache
    mock_fetch.assert_not_called()
    assert val == {"status": "cached"}

@pytest.mark.asyncio
async def test_cache_get_or_set_miss(cache_service, mock_redis):
    """Test fallback when key is NOT in cache."""
    mock_redis.get.return_value = None
    
    async def mock_fetch():
        return {"fetched_data": True}
        
    val = await cache_service.get_or_set("test_key", mock_fetch, ttl=60)
    
    assert val == {"fetched_data": True}
    # It should have set the newly fetched data
    mock_redis.set.assert_called_once_with("test_key", '{"fetched_data": true}', ex=60)
