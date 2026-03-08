#!/usr/bin/env python3
"""
scripts/bootstrap.py
════════════════════════════════════════════════════════════════════════════════
Fin-Eye — Full Bootstrap Script

Runs in order:
  Phase 1 — Database: init tables + seed all data  (seed_all_data.py)
  Phase 2 — Sentiment: fetch news + score with FinBERT for all symbols
  Phase 3 — ML Training: train Logistic + XGBoost per symbol × timeframe,
             pick the best winner by Sharpe ratio, persist artifacts
  Phase 4 — GAS pre-compute: run a full batch so scores are warm

FLAGS
─────
  --symbols   Comma-separated list of tickers (default: all 16 default symbols)
  --fast      Skip intraday OHLCV, news, and sentiment scoring (DB + daily OHLCV only)
  --skip-ml   Skip ML training phase entirely
  --skip-sent Skip FinBERT sentiment phase
  --reset     Drop and recreate all tables before seeding (DESTRUCTIVE)
  --start     Training history start date  (default: 2018-01-01)
  --end       Training history end date    (default: today)

USAGE
─────
  cd backend
  python scripts/bootstrap.py
  python scripts/bootstrap.py --fast --symbols AAPL,MSFT,SPY
  python scripts/bootstrap.py --reset   # wipe and rebuild from scratch

════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Bootstrap path ────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bootstrap")

# Default symbol set — must match seed_all_data.py defaults
DEFAULT_SYMBOLS = settings.ohlcv_symbols_default or [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "SPY",  "QQQ",  "NVDA",  "META", "JPM",
    "GLD",  "TLT",  "BTC-USD", "ETH-USD",
    "GC=F", "CL=F",
]

# Symbols that have enough equity history for meaningful ML training.
# Crypto, forex and commodity futures are excluded — insufficient OHLCV depth.
ML_ELIGIBLE_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "SPY",  "QQQ",  "NVDA",  "META", "JPM",
    "GLD",  "TLT",
]

PHASE_WIDTH = 65


def banner(title: str) -> None:
    logger.info("═" * PHASE_WIDTH)
    logger.info("  %s", title)
    logger.info("═" * PHASE_WIDTH)


def elapsed(t0: float) -> str:
    s = time.perf_counter() - t0
    return f"{s:.1f}s" if s < 60 else f"{s/60:.1f}min"


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Seed DB
# ═════════════════════════════════════════════════════════════════════════════

async def phase_seed(args: argparse.Namespace, symbols: list[str]) -> None:
    banner("PHASE 1 — Seeding database")
    t0 = time.perf_counter()

    # Import and call seed_all_data's main() directly so we don't subprocess
    from scripts.seed_all_data import main as seed_main  # type: ignore[import]

    seed_args = argparse.Namespace(
        symbols=",".join(symbols) if symbols != DEFAULT_SYMBOLS else "",
        skip_ml=True,          # we handle ML ourselves in Phase 3
        fast=args.fast,
        demo_only=False,
        reset=args.reset,
    )
    await seed_main(seed_args)
    logger.info("  ✓ Phase 1 complete in %s", elapsed(t0))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2 — FinBERT sentiment scoring
# ═════════════════════════════════════════════════════════════════════════════

async def phase_sentiment(symbols: list[str]) -> None:
    banner("PHASE 2 — FinBERT sentiment scoring")
    t0 = time.perf_counter()

    from app.db.database import AsyncSessionLocal
    from app.services.sentiment_service import SentimentService

    # SentimentService uses a sync db session internally
    from app.db.database import SessionLocal

    ok = 0
    fail = 0
    for sym in symbols:
        try:
            db = SessionLocal()
            try:
                svc = SentimentService(db=db)
                articles, aggregates = await svc.refresh_symbol_sentiment(
                    symbol=sym, days_back=60
                )
                logger.info(
                    "  %s → %d articles scored, %d daily aggregates",
                    sym, len(articles), len(aggregates),
                )
                ok += 1
            finally:
                db.close()
        except Exception as exc:
            logger.warning("  ⚠ Sentiment failed for %s: %s", sym, exc)
            fail += 1

    logger.info(
        "  ✓ Phase 2 complete — %d/%d symbols scored in %s",
        ok, len(symbols), elapsed(t0),
    )


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3 — ML Training
# ═════════════════════════════════════════════════════════════════════════════

def _train_symbol(
    symbol: str,
    start: datetime,
    end: datetime,
) -> dict:
    """Train all timeframes for one symbol. Runs synchronously (no async needed)."""
    from app.db.database import SessionLocal
    from app.services.feature_builder import DbFeatureBuilder
    from app.services.model_registry import JsonlFileModelRegistry
    from app.services.technical_models import Timeframe
    from app.services.technical_training import train_all_models_for_timeframe
    from app.services.model_artifacts import ModelArtifactStore

    registry_path = str(BACKEND_DIR / "model_store" / "registry.jsonl")
    artifact_dir  = str(BACKEND_DIR / "model_store" / "artifacts")

    timeframes = [
        Timeframe.ONE_DAY,
        Timeframe.ONE_WEEK,
        # ONE_HOUR and FOUR_HOUR fall back to StubFeatureBuilder until intraday
        # bars are dense enough; include them so stubs still register entries.
        Timeframe.ONE_HOUR,
        Timeframe.FOUR_HOUR,
    ]

    db = SessionLocal()
    results = {}
    try:
        builder  = DbFeatureBuilder(db=db)
        registry = JsonlFileModelRegistry(registry_path)
        store    = ModelArtifactStore(artifact_dir)

        for tf in timeframes:
            try:
                result = train_all_models_for_timeframe(
                    timeframe=tf,
                    registry=registry,
                    symbol=symbol,
                    start=start,
                    end=end,
                    feature_builder=builder,
                    artifact_store=store,
                )
                perfs = result.performances
                if perfs:
                    best = max(perfs, key=lambda p: p.sharpe_ratio)
                    results[tf.value] = {
                        "winner": best.model_kind.value,
                        "sharpe": round(best.sharpe_ratio, 3),
                        "accuracy": round(best.accuracy, 3),
                    }
                    logger.info(
                        "    [%s] %s → winner=%s  sharpe=%.3f  acc=%.3f",
                        symbol, tf.value, best.model_kind.value,
                        best.sharpe_ratio, best.accuracy,
                    )
                else:
                    results[tf.value] = {"winner": None, "note": "no data"}
                    logger.warning("    [%s] %s → no performances (insufficient data)", symbol, tf.value)
            except Exception as exc:
                results[tf.value] = {"error": str(exc)}
                logger.warning("    [%s] %s → training failed: %s", symbol, tf.value, exc)
    finally:
        db.close()

    return results


async def phase_train(
    symbols: list[str],
    start: datetime,
    end: datetime,
) -> None:
    banner("PHASE 3 — ML model training")
    t0 = time.perf_counter()

    # Create model_store directories if they don't exist
    (BACKEND_DIR / "model_store" / "artifacts").mkdir(parents=True, exist_ok=True)

    # Filter to ML-eligible symbols only
    train_symbols = [s for s in symbols if s in ML_ELIGIBLE_SYMBOLS]
    skipped = [s for s in symbols if s not in ML_ELIGIBLE_SYMBOLS]
    if skipped:
        logger.info("  ↩ Skipping non-equity symbols (no OHLCV history): %s", skipped)

    all_results: dict[str, dict] = {}
    for i, sym in enumerate(train_symbols, 1):
        logger.info("  [%d/%d] Training %s...", i, len(train_symbols), sym)
        sym_t0 = time.perf_counter()
        # Run synchronously in a thread pool to avoid blocking the event loop
        all_results[sym] = await asyncio.get_event_loop().run_in_executor(
            None, _train_symbol, sym, start, end
        )
        logger.info("    → %s done in %s", sym, elapsed(sym_t0))

    # Summary table
    logger.info("")
    logger.info("  ML Training Summary:")
    logger.info("  %-10s  %-8s  %-12s  %-8s  %-8s", "Symbol", "TF", "Winner", "Sharpe", "Acc")
    logger.info("  " + "-" * 54)
    for sym, tfs in all_results.items():
        for tf, info in tfs.items():
            if "error" in info:
                logger.info("  %-10s  %-8s  ERROR: %s", sym, tf, info["error"][:35])
            elif info.get("winner"):
                logger.info(
                    "  %-10s  %-8s  %-12s  %-8.3f  %-8.3f",
                    sym, tf, info["winner"], info.get("sharpe", 0), info.get("accuracy", 0),
                )
            else:
                logger.info("  %-10s  %-8s  no data", sym, tf)

    logger.info("  ✓ Phase 3 complete in %s", elapsed(t0))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4 — GAS pre-compute warm-up
# ═════════════════════════════════════════════════════════════════════════════

async def phase_gas(symbols: list[str]) -> None:
    banner("PHASE 4 — GAS pre-compute (final warm-up)")
    t0 = time.perf_counter()

    from app.db.database import AsyncSessionLocal
    from app.services.gas_precompute import run_gas_precompute_batch

    try:
        async with AsyncSessionLocal() as session:
            summary = await run_gas_precompute_batch(
                session,
                symbols=symbols if symbols != DEFAULT_SYMBOLS else None,
            )
            await session.commit()
        logger.info(
            "  ✓ GAS: %d/%d succeeded, macro_score=%.1f, elapsed=%.0fms",
            summary["symbols_succeeded"],
            summary["symbols_attempted"],
            summary["macro_score_shared"],
            summary["elapsed_ms"],
        )
    except Exception as exc:
        logger.warning("  ⚠ GAS pre-compute failed (non-fatal): %s", exc)

    logger.info("  ✓ Phase 4 complete in %s", elapsed(t0))


# ═════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════════════════════════════════════

def print_final_summary(symbols: list[str], total_t0: float) -> None:
    print("\n" + "═" * PHASE_WIDTH)
    print("  FIN-EYE BOOTSTRAP COMPLETE")
    print("═" * PHASE_WIDTH)
    print(f"  Total time     : {elapsed(total_t0)}")
    print(f"  Symbols        : {', '.join(symbols[:8])}{'...' if len(symbols) > 8 else ''}")
    print()
    print("  ML artifacts   : backend/model_store/artifacts/")
    print("  ML registry    : backend/model_store/registry.jsonl")
    print()
    print("  Demo login     : demo@fin-eye.com  /  DemoFinEye2024!")
    print("  Admin login    : admin@fin-eye.com /  AdminFinEye2024!")
    print()
    print("  App URLs:")
    print("    Frontend     → http://localhost:3000")
    print("    API docs     → http://localhost:8000/docs")
    print("═" * PHASE_WIDTH + "\n")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

async def main(args: argparse.Namespace) -> None:
    total_t0 = time.perf_counter()

    symbols = (
        [s.strip().upper() for s in args.symbols.split(",")]
        if args.symbols
        else DEFAULT_SYMBOLS
    )

    train_start = datetime.fromisoformat(args.start)
    train_end   = datetime.fromisoformat(args.end)

    banner(
        f"FIN-EYE BOOTSTRAP  |  symbols={len(symbols)}  "
        f"fast={args.fast}  skip_ml={args.skip_ml}  skip_sent={args.skip_sent}"
    )

    # Phase 1 — Seed DB
    await phase_seed(args, symbols)

    # Phase 2 — FinBERT sentiment
    if not args.skip_sent and not args.fast:
        await phase_sentiment(symbols)
    else:
        logger.info("▶ Phase 2 skipped (--fast or --skip-sent)")

    # Phase 3 — ML training
    if not args.skip_ml:
        await phase_train(symbols, train_start, train_end)
    else:
        logger.info("▶ Phase 3 skipped (--skip-ml)")

    # Phase 4 — GAS warm-up
    await phase_gas(symbols)

    # Done
    print_final_summary(symbols, total_t0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fin-Eye full bootstrap: seed DB + sentiment + ML training + GAS warm-up"
    )
    parser.add_argument("--symbols",    default="",              help="Comma-separated tickers (default: all)")
    parser.add_argument("--fast",       action="store_true",     help="Skip intraday OHLCV, news, sentiment")
    parser.add_argument("--skip-ml",    action="store_true",     help="Skip ML training phase")
    parser.add_argument("--skip-sent",  action="store_true",     help="Skip FinBERT sentiment phase")
    parser.add_argument("--reset",      action="store_true",     help="Drop + recreate all tables (DESTRUCTIVE)")
    parser.add_argument("--start",      default="2018-01-01T00:00:00", help="ML training history start (ISO date)")
    parser.add_argument("--end",        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00"),
                        help="ML training history end (ISO date, default: today)")
    args = parser.parse_args()

    if args.reset:
        confirm = input("⚠  --reset will DROP all tables. Type 'yes' to confirm: ").strip()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)

    asyncio.run(main(args))
