from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.db.database import init_db, test_db_connection
from app.db.redis_client import init_redis, close_redis, redis_client
from app.api.v1.endpoints import macro, sentiment, technical

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Fin-Eye...")
    test_db_connection()
    init_db()
    await init_redis()
    yield
    # Shutdown
    logger.info("🛑 Shutting down Fin-Eye...")
    await close_redis()

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
    redis_status = "connected" if redis_client and await redis_client.ping() else "disconnected"
    return {"status": "ok", "version": settings.app_version, "redis_status": redis_status}

@app.get("/")
async def root() -> dict:
    return {"message": "Fin-Eye Backend", "docs": "/docs"}

app.include_router(macro.router, prefix="/api/v1/macro", tags=["macro"])
app.include_router(
    sentiment.router,
    prefix="/api/v1/sentiment",
    tags=["sentiment"],
)
app.include_router(
    technical.router,
    prefix="/api/v1/technical",
    tags=["technical"],
)
