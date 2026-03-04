import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app as fastapi_app
from app.db.database import Base, get_db
# Import models to ensure they are registered with Base.metadata
import app.models
from app.db.redis_client import init_redis, close_redis

# Configure pytest-asyncio loop scope to suppress deprecation warning
pytestmark = pytest.mark.asyncio

# Test DB setup — single shared engine for the entire session
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # Keep one connection alive for the in-memory DB across fixtures
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables once at session start
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def test_db():
    """Provide a clean DB session per test, rolling back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

# test_app and client are both function-scoped so pytest-asyncio
# can resolve fixture dependencies correctly.
@pytest_asyncio.fixture(scope="function")
async def test_app():
    """Yield the FastAPI app instance with Redis initialised."""
    await init_redis()
    yield fastapi_app
    await close_redis()

@pytest_asyncio.fixture(scope="function")
async def client(test_app, test_db) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client with overridden DB connection."""

    def override_get_db():
        yield test_db

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    test_app.dependency_overrides.clear()
