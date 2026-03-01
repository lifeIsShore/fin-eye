from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base for models
Base = declarative_base()

def get_db() -> Session:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> bool:
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        return False

def test_db_connection() -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Database connected")
        return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False
