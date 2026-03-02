import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the /health endpoint to ensure it returns 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    # redis_status might be 'connected' or 'disconnected' depending on the environment,
    # but the key must be present
    assert "redis_status" in data
