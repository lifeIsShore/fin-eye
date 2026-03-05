"""
app/services/scheduler.py
APScheduler-based background job scheduler for Fin-Eye data pipelines.

Jobs:
  - fetch_ohlcv_daily      – every weekday at 18:00 UTC (after US market close)
  - fetch_ohlcv_intraday   – every weekday, every hour during US market hours
  - fetch_macro            – daily at 08:00 UTC (FRED updates lag by 1 day)
  - fetch_news             – every 4 hours on weekdays

All jobs share a single AsyncSession obtained from the DB session factory.

FIX BUG-001: cache.set_macro_score() -> cache.set_macro() (method did not exist)
"""
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.metrics import get_metrics

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler(timezone="UTC")


# ── Job Implementations ────────────────────────────────────────────────────────

async def job_fetch_ohlcv_daily() -> None:
    """Fetch and persist daily OHLCV bars for all tracked symbols."""
    from app.services.ohlcv_fetcher import OHLCVFetcher  # noqa: PLC0415

    logger.info("Starting daily OHLCV fetch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = OHLCVFetcher()
        async with AsyncSessionLocal() as session:
            results = await fetcher.fetch_and_store_daily(session)
            await session.commit()
        logger.info("Daily OHLCV fetch complete: %s", results)
        get_metrics().record_pipeline_run(
            "fetch_ohlcv_daily", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, str(results),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Daily OHLCV fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "fetch_ohlcv_daily", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        raise


async def job_fetch_ohlcv_intraday() -> None:
    """Fetch and persist intraday (1h + 4h) bars for all tracked symbols."""
    from app.services.ohlcv_fetcher import OHLCVFetcher  # noqa: PLC0415

    logger.info("Starting intraday OHLCV fetch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = OHLCVFetcher()
        async with AsyncSessionLocal() as session:
            r1h = await fetcher.fetch_and_store_intraday(session, interval="1h")
            r4h = await fetcher.fetch_and_store_intraday(session, interval="4h")
            await session.commit()
        detail = f"1h={r1h} 4h={r4h}"
        logger.info("Intraday OHLCV fetch complete: %s", detail)
        get_metrics().record_pipeline_run(
            "fetch_ohlcv_intraday", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Intraday OHLCV fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "fetch_ohlcv_intraday", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        raise


async def job_fetch_macro() -> None:
    """Fetch FRED macro data and recompute the daily macro score."""
    from app.services.macro_data import MacroFetcher  # noqa: PLC0415
    from app.services.cache import get_cache  # noqa: PLC0415

    logger.info("Starting macro fetch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = MacroFetcher()
        cache = get_cache()
        async with AsyncSessionLocal() as session:
            await fetcher.fetch_and_store(session)
            score_data = await fetcher.compute_and_store_score(session)
            await session.commit()
        if score_data:
            await cache.set_macro(score_data)
            logger.info("Macro score updated in cache: %s", score_data)
        get_metrics().record_pipeline_run(
            "fetch_macro", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True,
            f"score={score_data.get('score') if score_data else 'n/a'}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Macro fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "fetch_macro", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        raise

async def job_fetch_news() -> None:
    """Fetch latest news articles from Finnhub for all tracked symbols."""
    from app.services.news_data import NewsFetcher  # noqa: PLC0415

    logger.info("Starting news fetch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = NewsFetcher()
        async with AsyncSessionLocal() as session:
            results = await fetcher.fetch_and_store(session, lookback_days=2)
            await session.commit()
        logger.info("News fetch complete: %s", results)
        get_metrics().record_pipeline_run(
            "fetch_news", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, str(results),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("News fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "fetch_news", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        raise


# ── Scheduler Setup ────────────────────────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler:
    """Register all jobs and return the configured scheduler."""

    # Daily OHLCV – weekdays at 18:05 UTC (30 min after US market close)
    scheduler.add_job(
        job_fetch_ohlcv_daily,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=5),
        id="fetch_ohlcv_daily",
        name="Fetch Daily OHLCV",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Intraday OHLCV – weekdays, every hour between 13:00-21:00 UTC (US hours)
    scheduler.add_job(
        job_fetch_ohlcv_intraday,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute=15),
        id="fetch_ohlcv_intraday",
        name="Fetch Intraday OHLCV",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Macro data – daily at 08:00 UTC
    scheduler.add_job(
        job_fetch_macro,
        trigger=CronTrigger(hour=8, minute=0),
        id="fetch_macro",
        name="Fetch Macro & Compute Score",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # News – weekdays every 4 hours
    scheduler.add_job(
        job_fetch_news,
        trigger=CronTrigger(day_of_week="mon-fri", hour="0,4,8,12,16,20", minute=30),
        id="fetch_news",
        name="Fetch Finnhub News",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        "Scheduler configured with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )
    return scheduler