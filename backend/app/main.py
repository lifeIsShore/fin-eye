import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_db, test_db_connection
from app.db.redis_client import init_redis, close_redis
from app.services.scheduler import setup_scheduler
from app.services.llm_service import close_ollama_service

from app.middleware.metrics_middleware import MetricsMiddleware

import app.models  # noqa: F401 — side-effect: registers all ORM models with Base

from app.api.v1.health import router as health_router
from app.api.v1.data   import router as data_router
from app.api.v1.auth   import router as auth_router

from app.api.v1.endpoints import (
    macro, sentiment, technical, explanation, hedging,
    portfolios, backtesting, events, watchlist, legal, gdpr, cms, alerts, strategies,
    showcase, ops, analytics, experiments, email, api_keys, risk, admin_gas, options, sectors,
    insiders, earnings, shorts, adv_sentiment, fed_policy, indicators,
    admin_bulk,
)
from app.api.public.v1 import router as public_v1_router

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger   = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Fin-Eye Backend...")

    init_db()
    await test_db_connection()
    await init_redis()

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("📅 APScheduler started with %d jobs.", len(scheduler.get_jobs()))

    async def _warm_gas_cache_bg():
        await asyncio.sleep(10)
        try:
            from app.services.gas_precompute import run_gas_precompute_batch  # noqa: PLC0415
            from app.db.database import AsyncSessionLocal                      # noqa: PLC0415
            logger.info("🔥 Warming GAS snapshot cache (background)...")
            async with AsyncSessionLocal() as session:
                summary = await run_gas_precompute_batch(session)
            logger.info(
                "✅ GAS cache warmed — %d/%d symbols succeeded in %.0fms",
                summary["symbols_succeeded"],
                summary["symbols_attempted"],
                summary["elapsed_ms"],
            )
        except Exception as exc:
            logger.warning("⚠️  GAS cache warm failed (non-fatal): %s", exc)

    asyncio.create_task(_warm_gas_cache_bg())

    yield

    logger.info("🛑 Shutting down Fin-Eye Backend...")
    scheduler.shutdown(wait=False)
    await close_redis()
    await close_ollama_service()
    logger.info("👋 Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


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
        "docs":    "/docs",
        "health":  "/api/v1/health",
    }


# ── Core routers ──────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1/health", tags=["Health"])
app.include_router(auth_router,   prefix="/api/v1/auth",   tags=["Auth"])
app.include_router(data_router,   prefix="/api/v1/data",   tags=["Data Pipelines"])

# ── Domain routers ────────────────────────────────────────────────────────────
app.include_router(macro.router,          prefix="/api/v1/macro",          tags=["Macro Analysis"])
app.include_router(sentiment.router,      prefix="/api/v1/sentiment",      tags=["Sentiment Analysis"])
app.include_router(technical.router,      prefix="/api/v1/technical",      tags=["Technical Analysis"])
app.include_router(explanation.router,    prefix="/api/v1/explanation",    tags=["AI Explanations"])
app.include_router(hedging.router,        prefix="/api/v1/hedge",          tags=["Hedging Strategy"])
app.include_router(portfolios.router,     prefix="/api/v1/portfolios",     tags=["Portfolio Management"])
app.include_router(backtesting.router,    prefix="/api/v1/backtest",       tags=["Backtesting"])
app.include_router(events.router,         prefix="/api/v1/events",         tags=["Market Events"])
app.include_router(watchlist.router,      prefix="/api/v1/watchlist",      tags=["Watchlist"])
app.include_router(legal.router,          prefix="/api/v1/legal",          tags=["Legal & Privacy"])
app.include_router(gdpr.router,           prefix="/api/v1/gdpr",           tags=["GDPR Data Rights"])
app.include_router(cms.router,            prefix="/api/v1/cms",            tags=["Content Management"])
app.include_router(alerts.router,         prefix="/api/v1/alerts",         tags=["Alerts & Notifications"])
app.include_router(strategies.router,     prefix="/api/v1/strategies",     tags=["Strategy Library"])
app.include_router(showcase.router,       prefix="/api/v1/showcase",       tags=["Showcase / Pro Tools"])
app.include_router(ops.router,            prefix="/api/v1/ops",            tags=["Ops & Monitoring"])
app.include_router(analytics.router,      prefix="/api/v1/analytics",      tags=["Product Analytics"])
app.include_router(experiments.router,    prefix="/api/v1/experiments",    tags=["A/B Experiments"])
app.include_router(email.router,          prefix="/api/v1/email",          tags=["Email Preferences"])
app.include_router(api_keys.router,       prefix="/api/v1/api-keys",       tags=["API Key Management"])
app.include_router(risk.router,           prefix="/api/v1/risk",           tags=["Risk & Stress Testing"])
app.include_router(admin_gas.router,      prefix="/api/v1/admin/gas",      tags=["Admin — GAS Pre-Compute"])
app.include_router(options.router,        prefix="/api/v1/options",        tags=["Options Fear & Greed"])
app.include_router(sectors.router,        prefix="/api/v1/sectors",        tags=["Sector Rotation"])
app.include_router(insiders.router,       prefix="/api/v1/insiders",       tags=["Insider Trading"])
app.include_router(earnings.router,       prefix="/api/v1/earnings",       tags=["Earnings Calendar"])
app.include_router(shorts.router,         prefix="/api/v1/shorts",         tags=["Short Interest"])
app.include_router(adv_sentiment.router,  prefix="/api/v1/adv-sentiment",  tags=["Advanced Sentiment"])
app.include_router(fed_policy.router,     prefix="/api/v1/fed-policy",     tags=["Fed Policy"])
app.include_router(indicators.router,     prefix="/api/v1/indicators",     tags=["Custom Indicators"])

# ── todos-v4.md — bulk pipeline admin (two routers, two prefixes) ─────────────
# router_admin: single-ticker ops + ticker universe list
app.include_router(admin_bulk.router_admin, prefix="/api/v1/admin",       tags=["Admin — Pipeline"])
# router: bulk seed/train/news + pipeline overview
app.include_router(admin_bulk.router,       prefix="/api/v1/admin/bulk",  tags=["Admin — Bulk Pipeline"])

# ── Public external API ───────────────────────────────────────────────────────
app.include_router(public_v1_router.router, prefix="/public/v1", tags=["Public API"])
