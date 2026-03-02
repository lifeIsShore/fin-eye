import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
# Import models to ensure they are registered with Base.metadata
import app.models
from app.db.redis_client import init_redis, close_redis

# Optional: configure pytest to use asyncio
pytestmark = pytest.mark.asyncio

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest_asyncio.fixture(scope="session")
async def test_app():
    """Yield the FastAPI app instances."""
    await init_redis()
    yield app
    await close_redis()
    
@pytest_asyncio.fixture(scope="function")
async def client(test_app, test_db) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client with overridden DB connection."""
    
    def override_get_db():
        yield test_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
