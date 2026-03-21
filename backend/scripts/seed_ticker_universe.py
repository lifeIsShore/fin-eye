"""
scripts/seed_ticker_universe.py
================================
Populate (or refresh) the tickers_universe table from data/tickers_predefined.json.

Usage:
    cd backend
    python scripts/seed_ticker_universe.py

What it does:
    1. Reads backend/data/tickers_predefined.json
    2. Upserts every ticker into the tickers_universe table
    3. Validates each symbol via yf.Ticker(sym).fast_info (sets yf_valid)
    4. Prints a summary: N valid / N invalid / N total

Options:
    --skip-validation    Upsert without calling yfinance (much faster, sets yf_valid=NULL)
    --symbol AAPL        Validate/re-upsert a single symbol only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# ── Make sure `backend/` is on sys.path so app.* imports work ─────────────────
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_tickers")

TICKER_JSON = BACKEND_DIR / "data" / "tickers_predefined.json"


# ── yfinance validation (sync — will be run in executor) ──────────────────────

def _yf_valid_sync(symbol: str) -> bool:
    """Return True if yfinance can resolve the symbol (has a current price)."""
    try:
        import yfinance as yf
        info  = yf.Ticker(symbol).fast_info
        price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
        return price is not None and float(price) > 0
    except Exception:
        return False


# ── DB upsert ─────────────────────────────────────────────────────────────────

async def upsert_tickers(
    tickers: list[dict],
    *,
    skip_validation: bool = False,
) -> tuple[int, int, int]:
    """
    Upsert all tickers into the DB.
    Returns (valid_count, invalid_count, total).
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.db.database import AsyncSessionLocal, init_db
    from app.models.bulk_ops import TickerUniverse  # noqa: F401 — ensures table registered

    init_db()  # creates tables if they don't exist yet

    valid   = 0
    invalid = 0
    loop    = asyncio.get_running_loop()

    async with AsyncSessionLocal() as session:
        for t in tickers:
            sym = t["symbol"].upper()

            yf_valid_val: Optional[bool] = None
            if not skip_validation:
                # Run the blocking yfinance call in the default thread-pool executor
                yf_valid_val = await loop.run_in_executor(None, _yf_valid_sync, sym)
                if yf_valid_val:
                    valid += 1
                    logger.info("  ✓  %-12s  %s", sym, t.get("name", ""))
                else:
                    invalid += 1
                    logger.warning("  ✗  %-12s  yfinance returned no price", sym)

            stmt = (
                pg_insert(TickerUniverse)
                .values(
                    symbol      = sym,
                    name        = t.get("name"),
                    asset_class = t.get("class"),
                    exchange    = t.get("exchange"),
                    tr_rank     = t.get("tr_rank"),
                    is_active   = True,
                    yf_valid    = yf_valid_val,
                )
                .on_conflict_do_update(
                    constraint="uq_ticker_universe_symbol",
                    set_={
                        "name":        pg_insert(TickerUniverse).excluded.name,
                        "asset_class": pg_insert(TickerUniverse).excluded.asset_class,
                        "exchange":    pg_insert(TickerUniverse).excluded.exchange,
                        "tr_rank":     pg_insert(TickerUniverse).excluded.tr_rank,
                        "is_active":   True,
                        # Only overwrite yf_valid when we just validated it
                        **({"yf_valid": pg_insert(TickerUniverse).excluded.yf_valid}
                           if not skip_validation else {}),
                    },
                )
            )
            await session.execute(stmt)

        await session.commit()

    return valid, invalid, len(tickers)


# ── CLI entry point ───────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed tickers_universe from tickers_predefined.json"
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip yfinance validation (sets yf_valid=NULL, much faster)",
    )
    parser.add_argument(
        "--symbol", metavar="SYM",
        help="Process a single symbol only",
    )
    args = parser.parse_args()

    if not TICKER_JSON.exists():
        logger.error("tickers_predefined.json not found at %s", TICKER_JSON)
        sys.exit(1)

    with open(TICKER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    tickers: list[dict] = data.get("tickers", [])
    if not tickers:
        logger.error("No tickers found in %s", TICKER_JSON)
        sys.exit(1)

    if args.symbol:
        sym_upper = args.symbol.upper()
        tickers   = [t for t in tickers if t["symbol"].upper() == sym_upper]
        if not tickers:
            logger.error("Symbol %s not found in tickers_predefined.json", sym_upper)
            sys.exit(1)

    logger.info(
        "Processing %d tickers  (skip_validation=%s) …",
        len(tickers), args.skip_validation,
    )

    valid, invalid, total = await upsert_tickers(
        tickers, skip_validation=args.skip_validation
    )

    print()
    print("─" * 48)
    print(f"  Total tickers : {total}")
    if not args.skip_validation:
        print(f"  yf_valid=True : {valid}")
        print(f"  yf_valid=False: {invalid}")
    else:
        print("  Validation    : skipped (yf_valid=NULL)")
    print("─" * 48)
    print("  ✅ tickers_universe populated successfully.")
    print()
    print("  Next steps:")
    print("    1. Run migrations if not done:  alembic upgrade head")
    print("    2. Seed OHLCV:  POST /api/v1/admin/bulk/run-seed")
    print("    3. Train ML:    POST /api/v1/admin/bulk/run-train")


if __name__ == "__main__":
    asyncio.run(main())
