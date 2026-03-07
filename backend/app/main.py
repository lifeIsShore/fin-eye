import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_db, test_db_connection
from app.db.redis_client import init_redis, close_redis
from app.services.scheduler import setup_scheduler

# Import versioned routers
# Observability middleware
from app.middleware.metrics_middleware import MetricsMiddleware

# Register models so init_db() creates all tables
from app.models import blog, showcase, analytics, experiment, email_preference, api_key, gas_snapshot  # noqa: F401 — side-effect import

from app.api.v1.health import router as health_router
from app.api.v1.data import router as data_router
from app.api.v1.auth import router as auth_router

# Import existing endpoint routers
from app.api.v1.endpoints import (
    macro, sentiment, technical, explanation, hedging,
    portfolios, backtesting, events, watchlist, legal, gdpr, cms, alerts, strategies,
    showcase, ops, analytics, experiments, email, api_keys, risk, admin_gas, options, sectors,
    insiders, earnings, shorts, adv_sentiment, fed_policy
)
from app.api.public.v1 import router as public_v1_router

# Configuration
settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.
    """
    logger.info("🚀 Starting Fin-Eye Backend...")
    
    # 1. Initialize Database (Sync tables creation)
    init_db()
    
    # 2. Test Database Connection (Async)
    await test_db_connection()
    
    # 3. Initialize Redis
    await init_redis()
    
    # 4. Setup and Start Scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("📅 APScheduler started with %d jobs.", len(scheduler.get_jobs()))

    # 5. Warm the GAS snapshot cache on startup so the first user sees data
    #    immediately without waiting for the 15-min scheduler tick.
    try:
        from app.services.gas_precompute import run_gas_precompute_batch  # noqa: PLC0415
        from app.db.database import AsyncSessionLocal  # noqa: PLC0415
        logger.info("🔥 Warming GAS snapshot cache on startup...")
        async with AsyncSessionLocal() as session:
            summary = await run_gas_precompute_batch(session)
        logger.info(
            "✅ GAS cache warmed — %d/%d symbols succeeded in %.0fms",
            summary["symbols_succeeded"],
            summary["symbols_attempted"],
            summary["elapsed_ms"],
        )
    except Exception as exc:
        # Never crash startup — the scheduler will retry at the next tick
        logger.warning("⚠️  GAS cache warm failed (non-fatal): %s", exc)

    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Fin-Eye Backend...")
    scheduler.shutdown(wait=False)
    await close_redis()
    logger.info("👋 Shutdown complete.")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)

@app.get("/")
async def root() -> dict:
    return {
        "message": "Fin-Eye API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# --- Include Routers ---

# Core API v1 (Consolidated)
app.include_router(health_router, prefix="/api/v1/health", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(data_router, prefix="/api/v1/data", tags=["Data Pipelines"])

# Domain Specific Endpoints (v1)
app.include_router(macro.router, prefix="/api/v1/macro", tags=["Macro Analysis"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment Analysis"])
app.include_router(technical.router, prefix="/api/v1/technical", tags=["Technical Analysis"])
app.include_router(explanation.router, prefix="/api/v1/explanation", tags=["AI Explanations"])
app.include_router(hedging.router, prefix="/api/v1/hedge", tags=["Hedging Strategy"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["Portfolio Management"])
app.include_router(backtesting.router, prefix="/api/v1/backtest", tags=["Backtesting"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Market Events"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["Watchlist"])
app.include_router(legal.router, prefix="/api/v1/legal", tags=["Legal & Privacy"])
app.include_router(gdpr.router, prefix="/api/v1/gdpr", tags=["GDPR Data Rights"])
app.include_router(cms.router, prefix="/api/v1/cms", tags=["Content Management"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts & Notifications"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["Strategy Library"])
app.include_router(showcase.router, prefix="/api/v1/showcase", tags=["Showcase / Pro Tools"])
app.include_router(ops.router, prefix="/api/v1/ops", tags=["Ops & Monitoring"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Product Analytics"])
app.include_router(experiments.router, prefix="/api/v1/experiments", tags=["A/B Experiments"])
app.include_router(email.router, prefix="/api/v1/email", tags=["Email Preferences"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Key Management"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk & Stress Testing"])
app.include_router(admin_gas.router, prefix="/api/v1/admin/gas", tags=["Admin — GAS Pre-Compute"])
app.include_router(options.router, prefix="/api/v1/options", tags=["Options Fear & Greed"])
app.include_router(sectors.router, prefix="/api/v1/sectors", tags=["Sector Rotation"])
app.include_router(insiders.router, prefix="/api/v1/insiders", tags=["Insider Trading"])
app.include_router(earnings.router, prefix="/api/v1/earnings", tags=["Earnings Calendar"])
app.include_router(shorts.router, prefix="/api/v1/shorts", tags=["Short Interest"])
app.include_router(adv_sentiment.router, prefix="/api/v1/adv-sentiment", tags=["Advanced Sentiment"])
app.include_router(fed_policy.router, prefix="/api/v1/fed-policy", tags=["Fed Policy"])

# Public external API (API-key authenticated)
app.include_router(public_v1_router.router, prefix="/public/v1", tags=["Public API"])
