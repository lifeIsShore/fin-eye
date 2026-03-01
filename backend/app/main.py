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
    test_db_connection()
    init_db()
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
