"""
scripts/seed_live_data.py
─────────────────────────────────────────────────────────────────────────────
One-shot script to manually trigger all data pipelines and populate the
database with real live data.

Run this ONCE after `alembic upgrade head` and before starting the server
for the first time. The scheduler will keep data fresh after that.

Usage:
    cd Y:\\programing\\projects\\fin-eye\\backend
    python scripts/seed_live_data.py

What this does:
  1. Macro data  — fetches FRED + VIX → macro_indicators table
  2. OHLCV daily — fetches 5yr daily bars for all default symbols
  3. OHLCV intraday — fetches 60d of 1h + 4h bars
  4. News          — fetches last 7 days of Finnhub news for all symbols
  5. Sentiment     — scores all news articles via FinBERT (or VADER fallback)

Progress is printed to the console with timing.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

# ── Make sure `app` is importable when run as a script ────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_live_data")


def _banner(title: str) -> None:
    bar = "─" * 60
    logger.info("")
    logger.info(bar)
    logger.info("  %s", title)
    logger.info(bar)


async def step_macro(session) -> None:
    _banner("Step 1 / 5  —  Macro data (FRED + VIX)")
    from app.services.macro_orchestrator import refresh_all_macro_indicators
    t0 = time.perf_counter()
    await refresh_all_macro_indicators(session)
    logger.info("✅  Macro done in %.1fs", time.perf_counter() - t0)


async def step_ohlcv_daily(session) -> None:
    _banner("Step 2 / 5  —  OHLCV daily bars (Yahoo Finance)")
    from app.services.ohlcv_fetcher import OHLCVFetcher
    t0 = time.perf_counter()
    fetcher = OHLCVFetcher()
    results = await fetcher.fetch_and_store_daily(session)
    await session.commit()
    for sym, info in results.items():
        status = info.get("status", "?")
        rows   = info.get("rows", 0)
        err    = info.get("error", "")
        icon   = "✅" if status == "ok" else "⚠️ "
        msg    = f"{rows} rows" if status == "ok" else err
        logger.info("  %s  %-8s  %s", icon, sym, msg)
    logger.info("✅  OHLCV daily done in %.1fs", time.perf_counter() - t0)


async def step_ohlcv_intraday(session) -> None:
    _banner("Step 3 / 5  —  OHLCV intraday (1h + 4h)")
    from app.services.ohlcv_fetcher import OHLCVFetcher
    t0 = time.perf_counter()
    fetcher = OHLCVFetcher()

    logger.info("  Fetching 1h bars…")
    r1h = await fetcher.fetch_and_store_intraday(session, interval="1h")
    await session.commit()

    logger.info("  Fetching 4h bars (resampled from 1h)…")
    r4h = await fetcher.fetch_and_store_intraday(session, interval="4h")
    await session.commit()

    total_rows = sum(v.get("rows", 0) for v in {**r1h, **r4h}.values())
    logger.info("✅  OHLCV intraday done in %.1fs  (%d total rows)", time.perf_counter() - t0, total_rows)


async def step_news(session) -> None:
    _banner("Step 4 / 5  —  News articles (Finnhub)")
    from app.services.news_data import NewsFetcher
    t0 = time.perf_counter()
    fetcher = NewsFetcher()
    results = await fetcher.fetch_and_store(session, lookback_days=7)
    for sym, count in results.items():
        logger.info("  %-8s  %d new articles", sym, count)
    logger.info("✅  News done in %.1fs", time.perf_counter() - t0)


async def step_sentiment(session) -> None:
    _banner("Step 5 / 5  —  Sentiment scoring (FinBERT / VADER fallback)")
    from app.config import settings
    from app.services.sentiment_service import SentimentService

    t0 = time.perf_counter()
    svc = SentimentService(db=session)
    symbols = settings.ohlcv_symbols_default
    for sym in symbols:
        try:
            articles, aggregates = await svc.refresh_symbol_sentiment(sym, days_back=7)
            logger.info("  %-8s  %d articles scored  %d daily aggregates", sym, len(articles), len(aggregates))
        except Exception as exc:
            logger.warning("  %-8s  ⚠️  sentiment failed: %s", sym, exc)

    logger.info("✅  Sentiment done in %.1fs", time.perf_counter() - t0)


def _print_api_key_status() -> None:
    """Print a quick health-check of which API keys are loaded."""
    from app.config import settings
    checks = [
        ("FINNHUB_API_KEY",  settings.has_finnhub,  "news + earnings"),
        ("FRED_API_KEY",     settings.has_fred,     "macro indicators"),
        ("OPENAI_API_KEY",   settings.has_openai,   "AI narration (optional)"),
        ("STRIPE_SECRET_KEY",settings.has_stripe,   "billing (optional)"),
    ]
    logger.info("  API key status:")
    for name, ok, purpose in checks:
        icon = "✅" if ok else "❌"
        note = "" if ok else f"  ← add to backend/.env  ({purpose})"
        logger.info("    %s  %-30s %s", icon, name, note)
    logger.info("")


async def main() -> None:
    from app.db.database import AsyncSessionLocal
    from app.db.redis_client import init_redis, close_redis

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║         Fin-Eye  —  Live Data Seed Script                ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")
    _print_api_key_status()
    logger.info("This will populate your database with real data.")
    logger.info("Estimated time: 2-5 minutes depending on network speed.")
    logger.info("")

    # Redis is needed for cache writes in some services
    await init_redis()

    t_total = time.perf_counter()

    async with AsyncSessionLocal() as session:
        await step_macro(session)
        await step_ohlcv_daily(session)
        await step_ohlcv_intraday(session)
        await step_news(session)
        await step_sentiment(session)

    await close_redis()

    elapsed = time.perf_counter() - t_total
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  ✅  All done in %.0fs!                                  ║", elapsed)
    logger.info("║                                                          ║")
    logger.info("║  Your database now has live macro, OHLCV, news and       ║")
    logger.info("║  sentiment data. Start the server and open the app.      ║")
    logger.info("║                                                          ║")
    logger.info("║  Backend:  uvicorn app.main:app --reload --port 8000     ║")
    logger.info("║  Frontend: cd frontend && npm run dev                    ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    asyncio.run(main())
