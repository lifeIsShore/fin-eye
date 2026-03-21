"""
app/services/scheduler.py
APScheduler-based background job scheduler for Fin-Eye data pipelines.

Jobs:
  - fetch_ohlcv_daily              – every weekday at 18:00 UTC
  - fetch_ohlcv_intraday           – every weekday, every hour during US market hours
  - fetch_macro                    – daily at 08:00 UTC
  - fetch_news                     – weekdays every 4 hours
  - news_daily_refresh             – weekdays at 06:00 UTC
  - news_ttl_cleanup               – every Sunday at 02:30 UTC
  - resolve_prediction_outcomes    – every hour at :45 (todos-v5 Phase 5.3)
  - detect_model_drift             – every hour at :50 (todos-v5 Phase 5.5)
  - run_optuna_tuning              – nightly at 01:00 UTC when ENABLE_HYPERTUNING=True (Sprint 6)
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
    from app.services.ohlcv_fetcher import OHLCVFetcher  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = OHLCVFetcher()
        async with AsyncSessionLocal() as session:
            results = await fetcher.fetch_and_store_daily(session)
            await session.commit()
        get_metrics().record_pipeline_run("fetch_ohlcv_daily", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, str(results))
    except Exception as exc:
        get_metrics().record_pipeline_run("fetch_ohlcv_daily", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))
        raise


async def job_fetch_ohlcv_intraday() -> None:
    from app.services.ohlcv_fetcher import OHLCVFetcher  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = OHLCVFetcher()
        async with AsyncSessionLocal() as session:
            r1h = await fetcher.fetch_and_store_intraday(session, interval="1h")
            r4h = await fetcher.fetch_and_store_intraday(session, interval="4h")
            await session.commit()
        detail = f"1h={r1h} 4h={r4h}"
        get_metrics().record_pipeline_run("fetch_ohlcv_intraday", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)
    except Exception as exc:
        get_metrics().record_pipeline_run("fetch_ohlcv_intraday", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))
        raise


async def job_fetch_macro() -> None:
    from app.services.macro_orchestrator import refresh_all_macro_indicators  # noqa: PLC0415
    from app.services.cache import get_cache  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await refresh_all_macro_indicators(session)
        cache = get_cache()
        if cache:
            await cache.set("macro:last_refresh", started)
        get_metrics().record_pipeline_run("fetch_macro", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, "ok")
    except Exception as exc:
        get_metrics().record_pipeline_run("fetch_macro", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))
        raise


async def job_onboarding_day3() -> None:
    from app.services.onboarding_email_service import run_onboarding_day3_batch  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_onboarding_day3_batch(session)
        get_metrics().record_pipeline_run("onboarding_day3", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"sent={sent}")
    except Exception as exc:
        get_metrics().record_pipeline_run("onboarding_day3", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_onboarding_day7() -> None:
    from app.services.onboarding_email_service import run_onboarding_day7_batch  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_onboarding_day7_batch(session)
        get_metrics().record_pipeline_run("onboarding_day7", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"sent={sent}")
    except Exception as exc:
        get_metrics().record_pipeline_run("onboarding_day7", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_weekly_digest() -> None:
    from app.services.onboarding_email_service import run_weekly_digest_batch  # noqa: PLC0415
    week_number = datetime.now(timezone.utc).isocalendar()[1]
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            sent = await run_weekly_digest_batch(session, is_biweekly_week=(week_number % 2 == 0))
        get_metrics().record_pipeline_run("weekly_digest", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"sent={sent}")
    except Exception as exc:
        get_metrics().record_pipeline_run("weekly_digest", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_alert_email_notifications() -> None:
    from app.services.alert_service import evaluate_all_email_alerts  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await evaluate_all_email_alerts(session)
            await session.commit()
        detail = f"checked={summary['checked']} fired={summary['fired']} emailed={summary['emailed']} errors={summary['errors']}"
        get_metrics().record_pipeline_run("alert_email_notifications", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)
    except Exception as exc:
        get_metrics().record_pipeline_run("alert_email_notifications", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_gas_precompute() -> None:
    from app.services.gas_precompute import run_gas_precompute_batch  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await run_gas_precompute_batch(session)
        detail = f"ok={summary['symbols_succeeded']}/{summary['symbols_attempted']} elapsed={summary['elapsed_ms']:.0f}ms"
        logger.info("GAS pre-compute complete: %s", detail)
        get_metrics().record_pipeline_run("gas_precompute", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)
    except Exception as exc:
        get_metrics().record_pipeline_run("gas_precompute", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_backup_db() -> None:
    import sys, os  # noqa: PLC0415
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "backup")))
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        from backup_db import run_backup  # noqa: PLC0415
        dump_path = run_backup()
        get_metrics().record_pipeline_run("backup_db", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"Saved: {dump_path.name}")
    except Exception as exc:
        get_metrics().record_pipeline_run("backup_db", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_fetch_news() -> None:
    from app.services.news_data import NewsFetcher  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = NewsFetcher()
        async with AsyncSessionLocal() as session:
            results = await fetcher.fetch_and_store(session, lookback_days=2)
            await session.commit()
        get_metrics().record_pipeline_run("fetch_news", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, str(results))
    except Exception as exc:
        get_metrics().record_pipeline_run("fetch_news", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))
        raise


async def job_news_daily_refresh() -> None:
    from app.services.news_data import NewsFetcher   # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse   # noqa: PLC0415
    from sqlalchemy import select                     # noqa: PLC0415
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
            counts  = await fetcher.fetch_and_store(session, symbols=symbols, lookback_days=2)
            await session.commit()
        total_new = sum(counts.values())
        get_metrics().record_pipeline_run("news_daily_refresh", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"new_articles={total_new}")
    except Exception as exc:
        get_metrics().record_pipeline_run("news_daily_refresh", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


async def job_news_ttl_cleanup() -> None:
    from sqlalchemy import delete as sql_delete  # noqa: PLC0415
    from app.models.sentiment import NewsArticle   # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        async with AsyncSessionLocal() as session:
            result = await session.execute(sql_delete(NewsArticle).where(NewsArticle.published_at < cutoff))
            await session.commit()
        get_metrics().record_pipeline_run("news_ttl_cleanup", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, f"deleted={result.rowcount}")
    except Exception as exc:
        get_metrics().record_pipeline_run("news_ttl_cleanup", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


# ── todos-v5 Phase 5.3 — Prediction outcome resolver ─────────────────────────

async def job_resolve_prediction_outcomes() -> None:
    from app.services.prediction_service import resolve_pending_outcomes  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await resolve_pending_outcomes(session)
            await session.commit()
        detail = f"resolved={summary['resolved']} failed={summary['failed']} skipped={summary['skipped']}"
        if summary["resolved"] > 0:
            logger.info("Prediction outcome resolution: %s", detail)
        get_metrics().record_pipeline_run("resolve_prediction_outcomes", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)
    except Exception as exc:
        logger.error("Prediction outcome resolution failed: %s", exc)
        get_metrics().record_pipeline_run("resolve_prediction_outcomes", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


# ── todos-v5 Phase 5.5 — Model drift detection (Sprint 6) ────────────────────

async def job_detect_model_drift() -> None:
    """
    Detect model accuracy drift — runs after outcome resolution each hour.
    Creates ModelDriftAlert rows when live accuracy drops > DRIFT_THRESHOLD_PP
    below validation accuracy. Set AUTO_RETRAIN_ON_DRIFT=True to auto-retrain.
    """
    from app.services.drift_service import detect_and_record_drift  # noqa: PLC0415
    s = get_settings()
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            summary = await detect_and_record_drift(
                session,
                auto_retrain=s.auto_retrain_on_drift,
            )
            await session.commit()
        detail = (
            f"checked={summary['checked']} drifted={summary['drifted']} "
            f"alerts={summary['alerts_created']} auto_retrains={summary['auto_retrains']}"
        )
        if summary["alerts_created"] > 0:
            logger.warning("Drift detected: %s", detail)
        get_metrics().record_pipeline_run("detect_model_drift", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)
    except Exception as exc:
        logger.error("Drift detection failed: %s", exc)
        get_metrics().record_pipeline_run("detect_model_drift", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc))


# ── todos-v5 Phase 4.4 — Overnight Optuna hyperparameter tuning (Sprint 6) ───

async def job_run_optuna_tuning() -> None:
    """
    Nightly Optuna tuning for all trained symbols.
    Only runs when ENABLE_HYPERTUNING=True in .env.
    Best params are saved as JSON sidecars and loaded automatically on next retrain.
    Runs in executor — compute-intensive, do not block the event loop.
    """
    import asyncio  # noqa: PLC0415
    s = get_settings()
    if not s.enable_hypertuning:
        logger.debug("Optuna tuning skipped — ENABLE_HYPERTUNING=False")
        return

    from app.services.optuna_tuner import run_tuning_for_symbol  # noqa: PLC0415
    import json, os  # noqa: PLC0415
    from app.services.ml_pipeline import REGISTRY_FILE, ARTIFACT_DIR  # noqa: PLC0415

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    # Read trained symbols from registry
    trained: set[tuple[str, str]] = set()
    try:
        if os.path.exists(REGISTRY_FILE):
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        sym = rec.get("symbol", "").upper()
                        tf  = rec.get("timeframe", "")
                        artifact = os.path.join(ARTIFACT_DIR, rec.get("artifact_file", ""))
                        if sym and tf and os.path.exists(artifact):
                            trained.add((sym, tf))
                    except Exception:
                        continue
    except Exception as exc:
        logger.error("Optuna tuning: could not read registry: %s", exc)
        return

    if not trained:
        logger.info("Optuna tuning: no trained models found — skipping")
        return

    loop    = asyncio.get_running_loop()
    results = []
    for sym, tf in sorted(trained):
        try:
            result = await loop.run_in_executor(None, run_tuning_for_symbol, sym, tf)
            results.append(result)
            logger.info("Optuna tuning %s/%s: %s", sym, tf, result.get("status"))
        except Exception as exc:
            logger.error("Optuna tuning crashed for %s/%s: %s", sym, tf, exc)

    ok_count   = sum(1 for r in results if r.get("status") == "ok")
    skip_count = len(results) - ok_count
    detail = f"tuned={ok_count} skipped={skip_count} total={len(results)}"
    logger.info("Optuna tuning complete: %s", detail)
    get_metrics().record_pipeline_run("optuna_tuning", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail)


# ── Scheduler Setup ────────────────────────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler:
    """Register all jobs and return the configured scheduler."""

    scheduler.add_job(job_fetch_ohlcv_daily,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=5),
        id="fetch_ohlcv_daily", name="Fetch Daily OHLCV",
        replace_existing=True, misfire_grace_time=300)

    scheduler.add_job(job_fetch_ohlcv_intraday,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute=15),
        id="fetch_ohlcv_intraday", name="Fetch Intraday OHLCV",
        replace_existing=True, misfire_grace_time=120)

    scheduler.add_job(job_fetch_macro,
        trigger=CronTrigger(hour=8, minute=0),
        id="fetch_macro", name="Fetch Macro & Compute Score",
        replace_existing=True, misfire_grace_time=600)

    scheduler.add_job(job_fetch_news,
        trigger=CronTrigger(day_of_week="mon-fri", hour="0,4,8,12,16,20", minute=30),
        id="fetch_news", name="Fetch Finnhub News",
        replace_existing=True, misfire_grace_time=300)

    scheduler.add_job(job_news_daily_refresh,
        trigger=CronTrigger(day_of_week="mon-fri", hour=6, minute=0),
        id="news_daily_refresh", name="Daily News Refresh (all tickers)",
        replace_existing=True, misfire_grace_time=1800)

    scheduler.add_job(job_news_ttl_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=30),
        id="news_ttl_cleanup", name="Weekly News TTL Cleanup",
        replace_existing=True, misfire_grace_time=3600)

    scheduler.add_job(job_onboarding_day3,
        trigger=CronTrigger(hour=9, minute=0),
        id="onboarding_day3", name="Onboarding Email Day 3",
        replace_existing=True, misfire_grace_time=3600)

    scheduler.add_job(job_onboarding_day7,
        trigger=CronTrigger(hour=9, minute=5),
        id="onboarding_day7", name="Onboarding Email Day 7",
        replace_existing=True, misfire_grace_time=3600)

    scheduler.add_job(job_weekly_digest,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_digest", name="Weekly Email Digest",
        replace_existing=True, misfire_grace_time=3600)

    scheduler.add_job(job_alert_email_notifications,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21",
            minute="0,5,10,15,20,25,30,35,40,45,50,55"),
        id="alert_email_notifications", name="Alert Email Notifications",
        replace_existing=True, misfire_grace_time=60)

    scheduler.add_job(job_gas_precompute,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute="0,15,30,45"),
        id="gas_precompute", name="GAS Pre-Computation",
        replace_existing=True, misfire_grace_time=120)

    scheduler.add_job(job_backup_db,
        trigger=CronTrigger(hour=2, minute=0),
        id="backup_db", name="PostgreSQL DB Backup",
        replace_existing=True, misfire_grace_time=3600)

    # todos-v5 Phase 5.3 — Prediction outcome resolver, every hour at :45
    scheduler.add_job(job_resolve_prediction_outcomes,
        trigger=CronTrigger(minute=45),
        id="resolve_prediction_outcomes", name="ML Prediction Outcome Resolver",
        replace_existing=True, misfire_grace_time=300)

    # todos-v5 Phase 5.5 — Model drift detection, every hour at :50
    # Runs after outcome resolution so it always sees fresh accuracy data
    scheduler.add_job(job_detect_model_drift,
        trigger=CronTrigger(minute=50),
        id="detect_model_drift", name="Model Drift Detector",
        replace_existing=True, misfire_grace_time=300)

    # todos-v5 Phase 4.4 — Optuna hypertuning, nightly at 01:00 UTC
    # Only active when ENABLE_HYPERTUNING=True in .env
    scheduler.add_job(job_run_optuna_tuning,
        trigger=CronTrigger(hour=1, minute=0),
        id="optuna_tuning", name="Overnight Optuna Hyperparameter Tuning",
        replace_existing=True, misfire_grace_time=7200)

    logger.info(
        "Scheduler configured with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )
    return scheduler
