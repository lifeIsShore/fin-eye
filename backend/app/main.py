import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.db.database import init_db, test_db_connection
from app.db.redis_client import init_redis, close_redis
from app.services.scheduler import setup_scheduler
from app.services.llm_service import close_ollama_service

from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware  # SEC-06
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler  # BUG-005

import app.models  # noqa: F401 — side-effect: registers all ORM models with Base

from app.api.v1.health import router as health_router
from app.api.v1.data   import router as data_router
from app.api.v1.auth   import router as auth_router

from app.api.v1.endpoints import (
    macro, sentiment, technical, explanation, hedging,
    portfolios, backtesting, events, watchlist, legal, gdpr, cms, alerts, strategies,
    showcase, ops, analytics, experiments, email, api_keys, risk, admin_gas, options, sectors,
    insiders, earnings, shorts, adv_sentiment, fed_policy, indicators,
    admin_bulk, symbols, allocation, billing, social_signals, tenants, bot, montecarlo,
    referral, comments, polls, compliance,
)
from app.api.v1.endpoints.admin_ml import router as admin_ml_router  # Sprint 6
from app.api.public.v1 import router as public_v1_router

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger   = logging.getLogger(__name__)

# Sprint 44 — Sentry error monitoring (no-op when SENTRY_DSN is unset)
try:
    import sentry_sdk  # type: ignore
    import os as _os
    _sentry_dsn = _os.environ.get("SENTRY_DSN", "")
    if _sentry_dsn:
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.05,
            environment=_os.environ.get("APP_ENV", "production"),
        )
        logger.info("Sentry initialised (DSN configured)")
except ImportError:
    pass  # sentry-sdk not installed — monitoring disabled


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Fin-Eye Backend...")

    # SEC-02: Production config lock
    if settings.app_env == "production":
        assert not settings.debug, (
            "DEBUG must be False in production. Set DEBUG=False in .env."
        )
        assert "*" not in settings.allowed_origins, (
            "ALLOWED_ORIGINS must not contain '*' in production. "
            "Set ALLOWED_ORIGINS=[\"https://fin-eye.app\"] in .env."
        )
        assert settings.secret_key not in ("change-in-production", "", "REPLACE_ME"), (
            "JWT_SECRET must be a real secret in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
        logger.info("🔒 Production config assertions passed")
    logger.info("⚙️  Running in %s mode", settings.app_env)

    init_db()
    await test_db_connection()
    await init_redis()

    scheduler = setup_scheduler()
    try:
        scheduler.start()
        logger.info("📅 APScheduler started with %d jobs.", len(scheduler.get_jobs()))
    except Exception as exc:
        logger.warning("⚠️  Scheduler failed to start (DB may be unavailable): %s — continuing without scheduler", exc)

    async def _warm_gas_cache_bg() -> None:
        await asyncio.sleep(10)
        try:
            from app.services.gas_precompute import run_gas_precompute_batch  # noqa: PLC0415
            from app.db.database import AsyncSessionLocal                      # noqa: PLC0415
            logger.info("🔥 Warming GAS snapshot cache (background)...")
            async with AsyncSessionLocal() as session:
                summary = await run_gas_precompute_batch(session)
            logger.info(
                "✅ GAS cache warmed — %d/%d symbols succeeded in %.0fms",
                summary["symbols_succeeded"], summary["symbols_attempted"], summary["elapsed_ms"],
            )
        except Exception as exc:
            logger.warning("⚠️  GAS cache warm failed (non-fatal): %s", exc)

    async def _sync_r2_models_bg() -> None:
        await asyncio.sleep(5)
        try:
            from app.services.model_storage import sync_models_from_r2  # noqa: PLC0415
            stats = await sync_models_from_r2()
            if stats["downloaded"] > 0:
                logger.info("☁️  R2 sync: downloaded %d missing model(s)", stats["downloaded"])
        except Exception as exc:
            logger.warning("⚠️  R2 model sync failed (non-fatal): %s", exc)

    # SEC-08: Both background tasks start concurrently — R2 sync at +5s, GAS warm at +10s
    asyncio.create_task(_sync_r2_models_bg())
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

# ── BUG-005: Rate limiting ─────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# ── Middleware stack (outermost first) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)  # SEC-06


@app.get("/")
async def root() -> dict:
    return {
        "message": "Fin-Eye API",
        "version": settings.app_version,
        "docs":    "/docs",
        "health":  "/api/v1/health",
    }


# ── Core routers ──────────────────────────────────────────────────────────────
app.include_router(health_router,     prefix="/api/v1/health",   tags=["Health"])
app.include_router(auth_router,       prefix="/api/v1/auth",     tags=["Auth"])
app.include_router(data_router,       prefix="/api/v1/data",     tags=["Data Pipelines"])
app.include_router(symbols.router,    prefix="/api/v1/symbols",  tags=["Symbol Search"])

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
app.include_router(allocation.router,     prefix="/api/v1/allocation",     tags=["AI Allocation"])
app.include_router(billing.router,        prefix="/api/v1/billing",        tags=["Billing & Monetisation"])
app.include_router(social_signals.router, prefix="/api/v1/social-signals",  tags=["Social Signals"])
app.include_router(tenants.router,       prefix="/api/v1/tenants",        tags=["B2B Tenants"])
app.include_router(bot.router,           prefix="/api/v1/bot",            tags=["Paper Trading Bot"])
app.include_router(montecarlo.router,    prefix="/api/v1/montecarlo",     tags=["Monte Carlo Simulation"])
app.include_router(referral.router,      prefix="/api/v1",                 tags=["Referral"])
app.include_router(comments.router,      prefix="/api/v1",                 tags=["Comments"])  # Sprint 52
app.include_router(polls.router,         prefix="/api/v1",                 tags=["Polls"])     # Sprint 52

# ── Admin ─────────────────────────────────────────────────────────────────────
app.include_router(admin_bulk.router_admin, prefix="/api/v1/admin",              tags=["Admin — Pipeline"])
app.include_router(admin_bulk.router,       prefix="/api/v1/admin/bulk",          tags=["Admin — Bulk Pipeline"])
app.include_router(admin_ml_router,         prefix="/api/v1/admin/ml",            tags=["Admin — ML Pipeline"])
app.include_router(compliance.router,       prefix="/api/v1/admin/compliance",    tags=["Admin — Compliance"])  # Sprint 55

# ── Public external API ───────────────────────────────────────────────────────
app.include_router(public_v1_router.router, prefix="/public/v1", tags=["Public API"])
