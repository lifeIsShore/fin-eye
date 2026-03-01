# Sprint 1 - Task 1.1 Quick Start Guide

**Duration:** 4-6 hours  
**Goal:** Create project structure, config.py, database setup, update requirements  
**Output:** Backend skeleton ready to extend  

---

## 🎯 What You'll Create

After Task 1.1, your backend will have:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py (updated FastAPI app)
│   ├── config.py (NEW - Pydantic settings)
│   ├── models/ (NEW - SQLAlchemy ORM)
│   ├── schemas/ (NEW - Pydantic request/response)
│   ├── services/ (NEW - business logic)
│   ├── api/ (NEW - API routes)
│   └── db/ (NEW - database setup)
├── requirements.txt (updated with dependencies)
├── .env.example (NEW - configuration template)
└── README.md (updated)
```

---

## 📝 Implementation Steps

### Step 1: Create Folder Structure

```bash
cd backend
mkdir -p app/{models,schemas,services,api,db}
touch app/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/api/__init__.py
touch app/db/__init__.py
```

### Step 2: Update requirements.txt

Replace with:

```
# Core
fastapi==0.135.0
uvicorn[standard]==0.34.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Config
pydantic==2.6.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Cache
redis==5.0.1

# Data
pandas==2.1.4
numpy==1.26.3
yfinance==0.2.33
fredapi==0.5.1
requests==2.31.0

# Testing
pytest==7.4.3
pytest-asyncio==0.23.2
```

### Step 3: Create config.py

Create `app/config.py`:

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Fin-Eye Backend", alias="APP_NAME")
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/fin_eye",
        alias="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    cache_ttl: int = 900  # 15 minutes

    # External APIs
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")

    # JWT
    jwt_secret: str = Field(default="change-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### Step 4: Create database.py

Create `app/db/database.py`:

```python
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
```

### Step 5: Update main.py

Replace `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.db.database import init_db, test_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Fin-Eye...")
    await test_db_connection()
    await init_db()
    yield
    # Shutdown
    logger.info("🛑 Shutting down Fin-Eye...")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": settings.app_version}

@app.get("/")
async def root() -> dict:
    return {"message": "Fin-Eye Backend", "docs": "/docs"}
```

### Step 6: Create .env.example

Create `backend/.env.example`:

```bash
# Application
APP_NAME=Fin-Eye Backend
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=True

# Database (create database first: createdb fin_eye)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fin_eye

# Redis (or docker run -p 6379:6379 redis)
REDIS_URL=redis://localhost:6379

# APIs (get free keys from finnhub.io and stlouisfed.org)
FINNHUB_API_KEY=your_key_here
FRED_API_KEY=your_key_here

# JWT
JWT_SECRET=change-this-in-production
```

### Step 7: Test Locally

```bash
# Create .env from template
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Make sure PostgreSQL is running:
# createdb fin_eye

# Make sure Redis is running:
# docker run -p 6379:6379 redis

# Start backend
python -m uvicorn app.main:app --reload

# In another terminal, test:
curl http://localhost:8000/health
# Should return: {"status":"ok","version":"0.1.0"}
```

### Step 8: Commit to Git

```bash
git add .
git commit -m "feat: add project structure, config, and database setup"
git push origin feat/sprint-1
```

---

## ✅ Success Checklist

When Task 1.1 is complete:

- [ ] All folders created (models, schemas, services, api, db)
- [ ] All __init__.py files present
- [ ] config.py loads without errors
- [ ] database.py connection working
- [ ] main.py starts without import errors
- [ ] .env.example created
- [ ] requirements.txt updated
- [ ] Backend runs: `python -m uvicorn app.main:app --reload`
- [ ] /health endpoint returns 200
- [ ] Code committed to git

---

## 🚀 Next: Task 1.2

Once Task 1.1 is complete, move to Task 1.2:

**Task 1.2: Database Schema**
- Create user model
- Create stock OHLCV model
- Create macro indicator model
- Create news article model
- Create sentiment aggregate model
- Run migrations
- Verify tables in PostgreSQL

---

## ❓ Troubleshooting

**"Config won't load"**
→ Ensure .env file is in `backend/` directory, run `python -c "from app.config import settings; print(settings.app_name)"`

**"Cannot connect to PostgreSQL"**
→ Run `createdb fin_eye` and check DATABASE_URL in .env

**"Redis connection error"**
→ Start Redis: `docker run -p 6379:6379 redis` or `redis-server`

**"Import errors"**
→ Run `pip install -r requirements.txt` and check Python is 3.10+

---

**Estimated Time:** 4-6 hours  
**Difficulty:** ⭐⭐ (Mostly configuration boilerplate)  
**Next Step:** Task 1.2 (Database Schema)
