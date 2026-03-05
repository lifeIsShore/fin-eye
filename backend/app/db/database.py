from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create sync engine for startup tasks (like tables creation)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --- Async Database ---
# Convert postgresql:// to postgresql+asyncpg:// for async engine
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base for models
Base = declarative_base()

async def get_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def init_db() -> bool:
    """Create all tables (synchronous operation)"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        return False

async def test_db_connection() -> bool:
    """Test database connection (asynchronous)"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("✅ Database connected (async)")
        return True
    except Exception as e:
        logger.error(f"❌ Async connection failed: {e}")
        return False
