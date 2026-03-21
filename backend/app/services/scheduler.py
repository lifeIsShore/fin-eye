"""
app/services/scheduler.py
APScheduler-based background job scheduler for Fin-Eye data pipelines.

Jobs:
  - fetch_ohlcv_daily          – every weekday at 18:00 UTC (after US market close)
  - fetch_ohlcv_intraday       – every weekday, every hour during US market hours
  - fetch_macro                – daily at 08:00 UTC (FRED updates lag by 1 day)
  - fetch_news                 – weekdays every 4 hours
  - news_daily_refresh         – weekdays at 06:00 UTC (todos-v4.md Phase 5.6)
  - news_ttl_cleanup           – every Sunday at 02:00 UTC (todos-v4.md Phase 5.5)

FIX BUG-001: cache.set_macro_score() -> cache.set_macro() (method did not exist)
"""
import logging
import time
from datetime import datetime, timedelta, timezone

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
    from app.services.macro_orchestrator import refresh_all_macro_indicators  # noqa: PLC0415
    from app.services.cache import get_cache  # noqa: PLC0415

    logger.info("Starting macro fetch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await refresh_all_macro_indicators(session)
        cache = get_cache()
        if cache:
            await cache.set("macro:last_refresh", started)
            logger.info("Macro refresh complete, cache updated")
        get_metrics().record_pipeline_run(
            "fetch_macro", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, "ok",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Macro fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "fetch_macro", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        raise


async def job_onboarding_day3() -> None:
    """Send Day-3 onboarding email to eligible users."""
    from app.services.onboarding_email_service import run_onboarding_day3_batch  # noqa: PLC0415

    logger.info("Starting onboarding day-3 email job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_onboarding_day3_batch(session)
        get_metrics().record_pipeline_run(
            "onboarding_day3", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, f"sent={sent}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Onboarding day-3 job failed: %s", exc)
        get_metrics().record_pipeline_run(
            "onboarding_day3", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_onboarding_day7() -> None:
    """Send Day-7 onboarding email to eligible users."""
    from app.services.onboarding_email_service import run_onboarding_day7_batch  # noqa: PLC0415

    logger.info("Starting onboarding day-7 email job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_onboarding_day7_batch(session)
        get_metrics().record_pipeline_run(
            "onboarding_day7", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, f"sent={sent}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Onboarding day-7 job failed: %s", exc)
        get_metrics().record_pipeline_run(
            "onboarding_day7", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_weekly_digest() -> None:
    """Send weekly digest to all opted-in users."""
    from app.services.onboarding_email_service import run_weekly_digest_batch  # noqa: PLC0415

    week_number = datetime.now(timezone.utc).isocalendar()[1]
    is_biweekly_week = (week_number % 2 == 0)
    logger.info("Starting weekly digest job (week=%d)", week_number)
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_weekly_digest_batch(session, is_biweekly_week=is_biweekly_week)
        get_metrics().record_pipeline_run(
            "weekly_digest", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, f"sent={sent}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Weekly digest job failed: %s", exc)
        get_metrics().record_pipeline_run(
            "weekly_digest", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_alert_email_notifications() -> None:
    """Evaluate active email-channel alerts and dispatch any that breached threshold."""
    from app.services.alert_service import evaluate_all_email_alerts  # noqa: PLC0415

    logger.info("Starting alert email notification job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await evaluate_all_email_alerts(session)
            await session.commit()
        detail = (
            f"checked={summary['checked']} fired={summary['fired']} "
            f"emailed={summary['emailed']} errors={summary['errors']}"
        )
        logger.info("Alert email job complete: %s", detail)
        get_metrics().record_pipeline_run(
            "alert_email_notifications", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Alert email notification job failed: %s", exc)
        get_metrics().record_pipeline_run(
            "alert_email_notifications", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_gas_precompute() -> None:
    """Pre-compute GAS scores for all default symbols."""
    from app.services.gas_precompute import run_gas_precompute_batch  # noqa: PLC0415

    logger.info("Starting GAS pre-compute batch job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await run_gas_precompute_batch(session)
        detail = (
            f"ok={summary['symbols_succeeded']}/"
            f"{summary['symbols_attempted']} "
            f"elapsed={summary['elapsed_ms']:.0f}ms"
        )
        logger.info("GAS pre-compute complete: %s", detail)
        get_metrics().record_pipeline_run(
            "gas_precompute", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("GAS pre-compute job failed: %s", exc)
        get_metrics().record_pipeline_run(
            "gas_precompute", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_backup_db() -> None:
    """Run a full PostgreSQL backup and rotate old local copies."""
    import sys, os  # noqa: PLC0415
    sys.path.insert(0, os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "backup")
    ))

    logger.info("Starting scheduled DB backup job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        from backup_db import run_backup  # noqa: PLC0415
        dump_path = run_backup()
        detail = f"Saved: {dump_path.name}"
        logger.info("DB backup complete: %s", detail)
        get_metrics().record_pipeline_run(
            "backup_db", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("DB backup failed: %s", exc)
        get_metrics().record_pipeline_run(
            "backup_db", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


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


# ── Phase 5.6 — Daily news refresh at 06:00 UTC ──────────────────────────────

async def job_news_daily_refresh() -> None:
    """
    todos-v4.md Phase 5.6 — fetch last 2 days of news for all active tickers.
    Skips any ticker whose last_fetched_at is within the 6-hour TTL.
    Runs at 06:00 UTC every weekday so fresh headlines are available before
    European markets open (08:00 CET).
    """
    from app.services.news_data import NewsFetcher  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse   # noqa: PLC0415
    from sqlalchemy import select                     # noqa: PLC0415

    logger.info("Starting daily news refresh job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = NewsFetcher()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TickerUniverse.symbol)
                .where(TickerUniverse.is_active == True, TickerUniverse.yf_valid.isnot(False))  # noqa: E712
                .order_by(TickerUniverse.tr_rank.nullslast())
            )
            symbols = [r[0] for r in result.fetchall()]
            counts = await fetcher.fetch_and_store(session, symbols=symbols, lookback_days=2)
            await session.commit()
        total_new = sum(counts.values())
        logger.info("Daily news refresh complete: %d new articles across %d symbols", total_new, len(symbols))
        get_metrics().record_pipeline_run(
            "news_daily_refresh", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, f"new_articles={total_new}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Daily news refresh failed: %s", exc)
        get_metrics().record_pipeline_run(
            "news_daily_refresh", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


# ── Phase 5.5 — Weekly TTL cleanup (delete articles > 365 days) ──────────────

async def job_news_ttl_cleanup() -> None:
    """
    todos-v4.md Phase 5.5 — delete news_articles older than 365 days.
    Runs every Sunday at 02:00 UTC (low traffic, alongside DB backup).
    Keeps storage bounded at ~1 year of headlines regardless of volume.
    """
    from sqlalchemy import delete as sql_delete  # noqa: PLC0415
    from app.models.sentiment import NewsArticle   # noqa: PLC0415

    logger.info("Starting weekly news TTL cleanup job")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sql_delete(NewsArticle).where(NewsArticle.published_at < cutoff)
            )
            await session.commit()
        deleted = result.rowcount
        logger.info("News TTL cleanup: deleted %d articles older than %s", deleted, cutoff.date())
        get_metrics().record_pipeline_run(
            "news_ttl_cleanup", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, f"deleted={deleted}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("News TTL cleanup failed: %s", exc)
        get_metrics().record_pipeline_run(
            "news_ttl_cleanup", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


# ── Scheduler Setup ────────────────────────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler:
    """Register all jobs and return the configured scheduler."""

    # Daily OHLCV – weekdays at 18:05 UTC (after US market close)
    scheduler.add_job(
        job_fetch_ohlcv_daily,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=5),
        id="fetch_ohlcv_daily", name="Fetch Daily OHLCV",
        replace_existing=True, misfire_grace_time=300,
    )

    # Intraday OHLCV – weekdays, every hour between 13:00–21:00 UTC
    scheduler.add_job(
        job_fetch_ohlcv_intraday,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute=15),
        id="fetch_ohlcv_intraday", name="Fetch Intraday OHLCV",
        replace_existing=True, misfire_grace_time=120,
    )

    # Macro data – daily at 08:00 UTC
    scheduler.add_job(
        job_fetch_macro,
        trigger=CronTrigger(hour=8, minute=0),
        id="fetch_macro", name="Fetch Macro & Compute Score",
        replace_existing=True, misfire_grace_time=600,
    )

    # News (existing 4h job) – weekdays every 4 hours
    scheduler.add_job(
        job_fetch_news,
        trigger=CronTrigger(day_of_week="mon-fri", hour="0,4,8,12,16,20", minute=30),
        id="fetch_news", name="Fetch Finnhub News",
        replace_existing=True, misfire_grace_time=300,
    )

    # Phase 5.6 — Daily news refresh – weekdays at 06:00 UTC
    scheduler.add_job(
        job_news_daily_refresh,
        trigger=CronTrigger(day_of_week="mon-fri", hour=6, minute=0),
        id="news_daily_refresh", name="Daily News Refresh (all tickers)",
        replace_existing=True, misfire_grace_time=1800,
    )

    # Phase 5.5 — Weekly news TTL cleanup – every Sunday at 02:30 UTC
    scheduler.add_job(
        job_news_ttl_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=30),
        id="news_ttl_cleanup", name="Weekly News TTL Cleanup (>365d)",
        replace_existing=True, misfire_grace_time=3600,
    )

    # Onboarding email Day-3 — daily at 09:00 UTC
    scheduler.add_job(
        job_onboarding_day3,
        trigger=CronTrigger(hour=9, minute=0),
        id="onboarding_day3", name="Onboarding Email Day 3",
        replace_existing=True, misfire_grace_time=3600,
    )

    # Onboarding email Day-7 — daily at 09:05 UTC
    scheduler.add_job(
        job_onboarding_day7,
        trigger=CronTrigger(hour=9, minute=5),
        id="onboarding_day7", name="Onboarding Email Day 7",
        replace_existing=True, misfire_grace_time=3600,
    )

    # Weekly digest — every Monday at 08:00 UTC
    scheduler.add_job(
        job_weekly_digest,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_digest", name="Weekly Email Digest",
        replace_existing=True, misfire_grace_time=3600,
    )

    # Alert email notifications — weekdays every 5 min during US market hours
    scheduler.add_job(
        job_alert_email_notifications,
        trigger=CronTrigger(
            day_of_week="mon-fri", hour="13-21",
            minute="0,5,10,15,20,25,30,35,40,45,50,55",
        ),
        id="alert_email_notifications", name="Alert Email Notifications",
        replace_existing=True, misfire_grace_time=60,
    )

    # GAS pre-compute — weekdays every 15 min during US market hours
    scheduler.add_job(
        job_gas_precompute,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute="0,15,30,45"),
        id="gas_precompute", name="GAS Pre-Computation",
        replace_existing=True, misfire_grace_time=120,
    )

    # DB backup — daily at 02:00 UTC
    scheduler.add_job(
        job_backup_db,
        trigger=CronTrigger(hour=2, minute=0),
        id="backup_db", name="PostgreSQL DB Backup",
        replace_existing=True, misfire_grace_time=3600,
    )

    logger.info(
        "Scheduler configured with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )
    return scheduler
