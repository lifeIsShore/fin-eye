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

Sprint 40 additions:
  - fear_greed_fetch               – hourly at :05 (CNN + Crypto Fear & Greed)
  - google_trends_fetch            – daily at 08:15 UTC (pytrends, geo=DE)
  - wikipedia_pageviews_fetch      – daily at 08:30 UTC (252-day z-score)
  - reddit_external_signals        – every 6h at 00:45/06:45/12:45/18:45
"""
import logging
import time
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # BUG-007
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.metrics import get_metrics

logger = logging.getLogger(__name__)
settings = get_settings()


# ── BUG-007 FIX: Persist jobs in PostgreSQL so misfired jobs survive restarts ─
def _make_scheduler() -> AsyncIOScheduler:
    """
    Build AsyncIOScheduler with a SQLAlchemy jobstore backed by PostgreSQL.
    APScheduler auto-creates the `apscheduler_jobs` table on first start —
    no Alembic migration required.
    Falls back to in-memory if DATABASE_URL is not set (e.g. unit tests).
    """
    sync_url = settings.database_url
    if sync_url:
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=sync_url,
                tablename="apscheduler_jobs",
            )
        }
        logger.info("APScheduler: using SQLAlchemy jobstore (table=apscheduler_jobs)")
    else:
        jobstores = {}
        logger.warning("APScheduler: DATABASE_URL not set — falling back to in-memory jobstore")

    return AsyncIOScheduler(timezone="UTC", jobstores=jobstores)


scheduler = _make_scheduler()


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


async def job_rebalancing_alerts() -> None:
    """Sprint 31 — check grade drops and fire rebalancing suggestions."""
    try:
        from app.services.alert_service import check_and_fire_rebalancing_alerts  # noqa: PLC0415
        async with AsyncSessionLocal() as session:
            summary = await check_and_fire_rebalancing_alerts(session)
        logger.info("Rebalancing alerts: %s", summary)
    except Exception as exc:
        logger.error("job_rebalancing_alerts failed: %s", exc)


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


# ── Sprint 40: External signal jobs ─────────────────────────────────────────

async def job_fear_greed_fetch() -> None:
    """
    Fetch CNN + Crypto Fear & Greed indexes every hour.
    Both use free public APIs — no credentials needed.
    """
    from app.services.scrapers.cnn_fear_greed import CnnFearGreedFetcher        # noqa: PLC0415
    from app.services.scrapers.crypto_fear_greed import CryptoFearGreedFetcher  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            cnn_r    = await CnnFearGreedFetcher().fetch_and_store(session)
            crypto_r = await CryptoFearGreedFetcher().fetch_and_store(session)
        detail = (
            f"cnn={cnn_r.get('score')}({cnn_r.get('label')}) "
            f"crypto={crypto_r.get('score')}({crypto_r.get('label')})"
        )
        get_metrics().record_pipeline_run(
            "fear_greed_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
        logger.info("Fear & Greed fetched: %s", detail)
    except Exception as exc:
        get_metrics().record_pipeline_run(
            "fear_greed_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        logger.error("job_fear_greed_fetch failed: %s", exc)


async def job_google_trends_fetch() -> None:
    """
    Fetch Google Trends weekly interest for all active ticker universe symbols.
    Runs once daily at 08:00 UTC (after macro refresh).
    Uses a 2s inter-request delay to respect pytrends rate limits.
    """
    from app.services.scrapers.google_trends import GoogleTrendsFetcher  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                        # noqa: PLC0415
    from sqlalchemy import select as sql_select                           # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = GoogleTrendsFetcher()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(
                    TickerUniverse.is_active == True,   # noqa: E712
                    TickerUniverse.yf_valid.isnot(False),
                )
                .order_by(TickerUniverse.tr_rank.nullslast())
                .limit(100)  # cap at 100 to stay within rate limits
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await fetcher.fetch_and_store(session, symbols=symbols, geo="DE")
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])} skipped={len(summary['skipped'])}"
        get_metrics().record_pipeline_run(
            "google_trends_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
        logger.info("Google Trends batch: %s", detail)
    except Exception as exc:
        get_metrics().record_pipeline_run(
            "google_trends_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        logger.error("job_google_trends_fetch failed: %s", exc)


async def job_wikipedia_pageviews_fetch() -> None:
    """
    Fetch Wikipedia daily pageviews + compute 252-day z-score for all active symbols.
    Runs once daily at 08:30 UTC (30 min after Google Trends to avoid concurrent HTTP load).
    """
    from app.services.scrapers.wikipedia_pageviews import WikipediaPageviewsFetcher  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                                    # noqa: PLC0415
    from sqlalchemy import select as sql_select                                       # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        fetcher = WikipediaPageviewsFetcher()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(
                    TickerUniverse.is_active == True,   # noqa: E712
                    TickerUniverse.yf_valid.isnot(False),
                )
                .order_by(TickerUniverse.tr_rank.nullslast())
                .limit(200)
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await fetcher.fetch_and_store(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])} skipped={len(summary['skipped'])}"
        get_metrics().record_pipeline_run(
            "wikipedia_pageviews_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
        logger.info("Wikipedia pageviews batch: %s", detail)
    except Exception as exc:
        get_metrics().record_pipeline_run(
            "wikipedia_pageviews_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        logger.error("job_wikipedia_pageviews_fetch failed: %s", exc)


async def job_reddit_external_signals() -> None:
    """
    Compute Reddit mention volume + sentiment for all active symbols and
    persist in external_signals. Runs every 6 hours.
    Gracefully falls back to zero-signal rows when Reddit credentials are absent.
    """
    from app.services.reddit_service import RedditService   # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse          # noqa: PLC0415
    from sqlalchemy import select as sql_select             # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        svc = RedditService()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(
                    TickerUniverse.is_active == True,   # noqa: E712
                    TickerUniverse.yf_valid.isnot(False),
                )
                .order_by(TickerUniverse.tr_rank.nullslast())
                .limit(50)  # Reddit search is slow — cap per run
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await svc.fetch_and_store_external_signals(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])}"
        get_metrics().record_pipeline_run(
            "reddit_external_signals", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
        logger.info("Reddit external signals: %s", detail)
    except Exception as exc:
        get_metrics().record_pipeline_run(
            "reddit_external_signals", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )
        logger.error("job_reddit_external_signals failed: %s", exc)

# ── Sprint 42: External signals & scrapers ──────────────────────────────────

async def job_finanzen_net_fetch() -> None:
    from app.services.external.finanzen_net import fetch_and_store_news  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                       # noqa: PLC0415
    from sqlalchemy import select as sql_select                          # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            # Finanzen.net only for German stocks (.DE)
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(TickerUniverse.is_active == True, TickerUniverse.symbol.endswith('.DE'))  # noqa: E712
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await fetch_and_store_news(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])} added={summary['articles_added']}"
        get_metrics().record_pipeline_run(
            "finanzen_net_fetch", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail
        )
    except Exception as exc:
        logger.error("job_finanzen_net_fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "finanzen_net_fetch", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc)
        )

async def job_open_insider_signals() -> None:
    from app.services.external.open_insider import fetch_and_store_signals  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                          # noqa: PLC0415
    from sqlalchemy import select as sql_select                             # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            # OpenInsider is US only
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(TickerUniverse.is_active == True, ~TickerUniverse.symbol.endswith('.DE'))  # noqa: E712
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await fetch_and_store_signals(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])}"
        get_metrics().record_pipeline_run(
            "open_insider_signals", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail
        )
    except Exception as exc:
        logger.error("job_open_insider_signals failed: %s", exc)
        get_metrics().record_pipeline_run(
            "open_insider_signals", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc)
        )

async def job_stocktwits_external_signals() -> None:
    from app.services.stocktwits_service import StockTwitsService  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                 # noqa: PLC0415
    from sqlalchemy import select as sql_select                    # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        svc = StockTwitsService()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(TickerUniverse.is_active == True)  # noqa: E712
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await svc.fetch_and_store_external_signals(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])}"
        get_metrics().record_pipeline_run(
            "stocktwits_external_signals", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, True, detail
        )
    except Exception as exc:
        logger.error("job_stocktwits_external_signals failed: %s", exc)
        get_metrics().record_pipeline_run(
            "stocktwits_external_signals", started, datetime.now(timezone.utc).isoformat(), (time.perf_counter()-t0)*1000, False, str(exc)
        )


async def job_bot_evaluate() -> None:
    """
    Sprint 47 — Paper Trading Bot evaluation cycle.
    Runs every 15 minutes during market hours (2 min after GAS precompute).
    Evaluates each bot-enabled user’s watchlist symbols and fires BUY/SELL/HOLD decisions.
    """
    from app.services.bot_service import run_bot_cycle  # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            stats = await run_bot_cycle(session)
        detail = (
            f"users={stats['users']} evals={stats['evaluations']} "
            f"buys={stats['buys']} sells={stats['sells']} "
            f"halts={stats['halts']} errors={stats['errors']}"
        )
        if stats["buys"] + stats["sells"] > 0:
            logger.info("Bot cycle: %s", detail)
        get_metrics().record_pipeline_run(
            "bot_evaluate", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:
        logger.error("job_bot_evaluate failed: %s", exc)
        get_metrics().record_pipeline_run(
            "bot_evaluate", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


async def job_earnings_signals_fetch() -> None:
    """
    Daily job: compute earnings-derived ML features for all active tickers.
    Stores earnings_days_until_norm, earnings_surprise_score_norm,
    earnings_beat_streak_norm in external_signals table.
    Runs at 07:00 UTC (before market open, after FOMC countdown page refreshes).
    Skips crypto/FX/commodity tickers — no earnings data available for those.
    """
    from app.services.earnings_signal_store import compute_and_store_earnings_signals  # noqa: PLC0415
    from app.models.bulk_ops import TickerUniverse                                      # noqa: PLC0415
    from sqlalchemy import select as sql_select                                         # noqa: PLC0415
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            # Only equities — earnings data not available for crypto/FX/commodities
            result = await session.execute(
                sql_select(TickerUniverse.symbol)
                .where(
                    TickerUniverse.is_active == True,         # noqa: E712
                    TickerUniverse.yf_valid.isnot(False),
                    # Exclude crypto (ends -USD), FX (ends =X), commodities (ends =F)
                    ~TickerUniverse.symbol.like("%-USD"),
                    ~TickerUniverse.symbol.like("%=X"),
                    ~TickerUniverse.symbol.like("%=F"),
                )
                .order_by(TickerUniverse.tr_rank.nullslast())
                .limit(200)  # cap: yfinance is slow, 200 * ~0.5s ≈ 100s
            )
            symbols = [r[0] for r in result.fetchall()]
            summary = await compute_and_store_earnings_signals(session, symbols=symbols)
        detail = f"ok={len(summary['ok'])} failed={len(summary['failed'])}"
        get_metrics().record_pipeline_run(
            "earnings_signals_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
        logger.info("Earnings ML signals: %s", detail)
    except Exception as exc:
        logger.error("job_earnings_signals_fetch failed: %s", exc)
        get_metrics().record_pipeline_run(
            "earnings_signals_fetch", started,
            datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


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


# Sprint 44 — Churn early warning job implementation

async def job_churn_check() -> None:
    """
    Sprint 44 — Pro user churn early warning.
    Sends a re-engagement email to Pro users inactive for >7 days.
    14-day cooldown prevents repeat emails. Requires RESEND_API_KEY in .env.
    """
    from sqlalchemy import select, update  # noqa: PLC0415
    from app.models.user import User       # noqa: PLC0415

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    sent = errors = 0

    try:
        cutoff_login   = datetime.now(timezone.utc) - timedelta(days=7)
        cooldown_after = datetime.now(timezone.utc) - timedelta(days=14)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(
                    User.subscription_tier.in_(["pro", "institutional"]),
                    User.last_login < cutoff_login,
                    (
                        User.churn_email_sent_at.is_(None)
                        | (User.churn_email_sent_at < cooldown_after)
                    ),
                ).limit(200)
            )
            users = result.scalars().all()
            logger.info("Churn check: %d candidate(s)", len(users))

            resend_key = getattr(settings, "resend_api_key", None)
            if not resend_key:
                logger.warning("Churn check: RESEND_API_KEY not configured — skipping sends")
                return

            import httpx  # noqa: PLC0415
            for user in users:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(
                            "https://api.resend.com/emails",
                            headers={"Authorization": f"Bearer {resend_key}"},
                            json={
                                "from":    "Fin-Eye <noreply@fin-eye.app>",
                                "to":      [user.email],
                                "subject": "We miss you — your watchlist has moved",
                                "html": (
                                    f"<p>Hi {user.name or 'there'},</p>"
                                    "<p>You haven’t visited Fin-Eye in a while. Your watchlist "
                                    "symbols may have had significant GAS score changes.</p>"
                                    "<p><a href='https://fin-eye.app'>Check your dashboard →</a></p>"
                                    "<p style='color:#94a3b8;font-size:12px'>Active Pro account. "
                                    "<a href='https://fin-eye.app/settings'>Manage preferences</a>.</p>"
                                ),
                            },
                        )
                    resp.raise_for_status()
                    await session.execute(
                        update(User).where(User.id == user.id)
                        .values(churn_email_sent_at=datetime.now(timezone.utc))
                    )
                    sent += 1
                except Exception as exc:
                    logger.warning("Churn email failed for %s: %s", user.id, exc)
                    errors += 1

            await session.commit()

        detail = f"sent={sent} errors={errors} candidates={len(users)}"
        logger.info("Churn check complete: %s", detail)
        get_metrics().record_pipeline_run(
            "churn_check", started, datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, True, detail,
        )
    except Exception as exc:
        logger.error("job_churn_check failed: %s", exc)
        get_metrics().record_pipeline_run(
            "churn_check", started, datetime.now(timezone.utc).isoformat(),
            (time.perf_counter() - t0) * 1000, False, str(exc),
        )


# ── Sprint 52: Weekly Poll Creator ──────────────────────────────────────────────

async def job_create_weekly_poll() -> None:
    """Creates the current week's SPY Bull vs Bear poll if it doesn't exist."""
    from app.models.weekly_poll import WeeklyPoll  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    now = datetime.now(timezone.utc)
    iso_cal = now.isocalendar()
    week_num, year = iso_cal.week, iso_cal.year
    # opens_at = this Monday 00:01 UTC, closes_at = Sunday 23:59 UTC
    monday = now - timedelta(days=now.weekday())
    opens_at = monday.replace(hour=0, minute=1, second=0, microsecond=0)
    closes_at = opens_at + timedelta(days=6, hours=23, minutes=58)
    question = "Are you Bullish, Bearish, or Neutral on SPY this week?"
    try:
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(WeeklyPoll).where(
                    WeeklyPoll.week_number == week_num,
                    WeeklyPoll.year == year,
                    WeeklyPoll.symbol == "SPY",
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(WeeklyPoll(
                    week_number=week_num, year=year, symbol="SPY",
                    question=question, opens_at=opens_at, closes_at=closes_at,
                ))
                await session.commit()
                logger.info("Sprint52: created weekly poll week=%d year=%d", week_num, year)
            else:
                logger.info("Sprint52: poll already exists for week=%d year=%d", week_num, year)
    except Exception as exc:
        logger.error("job_create_weekly_poll failed: %s", exc)


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

    # BUG-BE-18: Sprint 33 plan specifies 07:00 UTC; was incorrectly set to 08:00.
    scheduler.add_job(job_weekly_digest,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
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

    # Sprint 31 — rebalancing alerts: runs 5 min after GAS precompute so grade history is fresh
    scheduler.add_job(job_rebalancing_alerts,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute="5,20,35,50"),
        id="rebalancing_alerts", name="Grade-Drop Rebalancing Alerts",
        replace_existing=True, misfire_grace_time=120)

    scheduler.add_job(job_backup_db,
        trigger=CronTrigger(hour=2, minute=0),
        id="backup_db", name="PostgreSQL DB Backup",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 40 — Fear & Greed: hourly (both CNN and Crypto, same job, free APIs)
    scheduler.add_job(job_fear_greed_fetch,
        trigger=CronTrigger(minute=5),  # at :05 every hour
        id="fear_greed_fetch", name="CNN + Crypto Fear & Greed Fetch",
        replace_existing=True, misfire_grace_time=300)

    # Sprint 40 — Google Trends: daily at 08:15 UTC (right after macro refresh)
    scheduler.add_job(job_google_trends_fetch,
        trigger=CronTrigger(hour=8, minute=15),
        id="google_trends_fetch", name="Google Trends Daily Fetch",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 40 — Wikipedia pageviews: daily at 08:30 UTC
    scheduler.add_job(job_wikipedia_pageviews_fetch,
        trigger=CronTrigger(hour=8, minute=30),
        id="wikipedia_pageviews_fetch", name="Wikipedia Pageviews Daily Fetch",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 40 — Reddit external signals: every 6 hours
    scheduler.add_job(job_reddit_external_signals,
        trigger=CronTrigger(hour="0,6,12,18", minute=45),
        id="reddit_external_signals", name="Reddit External Signals (6h)",
        replace_existing=True, misfire_grace_time=1800)

    # Sprint 47 — Paper trading bot: runs 2 min after GAS precompute during market hours
    scheduler.add_job(job_bot_evaluate,
        trigger=CronTrigger(day_of_week="mon-fri", hour="13-21", minute="2,17,32,47"),
        id="bot_evaluate", name="Paper Trading Bot Evaluation",
        replace_existing=True, misfire_grace_time=120)

    # Earnings calendar ML signals: daily at 07:00 UTC (before market open)
    # Feeds earnings_days_until_norm, earnings_surprise_score_norm, earnings_beat_streak_norm
    # into the external_signals table for ML pipeline consumption.
    scheduler.add_job(job_earnings_signals_fetch,
        trigger=CronTrigger(hour=7, minute=0),
        id="earnings_signals_fetch", name="Earnings Calendar ML Signals",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 42 — Finanzen.net external signals: every 4 hours
    scheduler.add_job(job_finanzen_net_fetch,
        trigger=CronTrigger(day_of_week="mon-fri", hour="2,6,10,14,18,22", minute=30),
        id="finanzen_net_fetch", name="Finanzen.net News Fetch",
        replace_existing=True, misfire_grace_time=600)

    # Sprint 42 — OpenInsider signals: daily at 09:30 UTC (offset from churn_check at 09:00)
    scheduler.add_job(job_open_insider_signals,
        trigger=CronTrigger(hour=9, minute=30),
        id="open_insider_signals", name="OpenInsider Daily Fetch",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 42 — StockTwits external signals: every 6 hours
    scheduler.add_job(job_stocktwits_external_signals,
        trigger=CronTrigger(hour="2,8,14,20", minute=45),
        id="stocktwits_external_signals", name="StockTwits External Signals (6h)",
        replace_existing=True, misfire_grace_time=1800)

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

    # Sprint 44 — Churn early warning: daily at 09:00 UTC
    scheduler.add_job(job_churn_check,
        trigger=CronTrigger(hour=9, minute=0),
        id="churn_check", name="Pro User Churn Early Warning",
        replace_existing=True, misfire_grace_time=3600)

    # Sprint 52 — Create weekly SPY poll every Monday at 00:01 UTC
    scheduler.add_job(job_create_weekly_poll,
        trigger=CronTrigger(day_of_week="mon", hour=0, minute=1),
        id="create_weekly_poll", name="Create Weekly SPY Poll",
        replace_existing=True, misfire_grace_time=3600)

    logger.info(
        "Scheduler configured with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )
    return scheduler
