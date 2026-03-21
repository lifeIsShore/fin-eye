"""
app/services/bulk_seed_service.py
===================================
Slowly-changing window OHLCV seeder for the bulk pipeline (todos-v4.md Phase 3.2).

Algorithm (per symbol):
  1. SELECT MAX(trade_date) FROM ohlcv_daily WHERE symbol = symbol
  2. If NULL (no data):   fetch full 5y history via yfinance
     If exists:           fetch only (last_date + 1 day) → today
  3. Upsert daily rows — never touches existing rows
  4. Repeat same logic for ohlcv_intraday (1h): check MAX(bar_time)
  5. If total daily rows < 200: mark as 'skipped', reason = 'insufficient_data'
  6. Log result to bulk_job_runs table

All DB writes are append-only — idempotent when called multiple times.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import OHLCVDaily, OHLCVIntraday
from app.models.bulk_ops import BulkJobRun

logger = logging.getLogger(__name__)

MIN_BARS_REQUIRED = 200  # below this → mark as skipped/insufficient_data

# Correct constraint names from market.py ORM model definitions
_CONSTRAINT_DAILY   = "uq_ohlcv_symbol_date"   # UniqueConstraint('symbol','trade_date')
_CONSTRAINT_INTRADAY = "uq_ohlcv_intraday"      # UniqueConstraint('symbol','interval','bar_time')


@dataclass
class SeedResult:
    symbol:              str
    status:              str   # 'done', 'skipped', 'failed'
    reason:              Optional[str]
    rows_added_daily:    int
    rows_added_intraday: int

    @property
    def rows_added(self) -> int:
        return self.rows_added_daily + self.rows_added_intraday


# ── Low-level yfinance helpers (sync — run in executor) ───────────────────────

def _fetch_daily(symbol: str, start: Optional[date], end: date) -> pd.DataFrame:
    """Return a clean DataFrame of daily OHLCV bars."""
    ticker = yf.Ticker(symbol)
    if start is None:
        df = ticker.history(period="5y", auto_adjust=True)
    else:
        df = ticker.history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),  # yfinance end is exclusive
            auto_adjust=True,
        )
    if df is None or df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC")
    return df


def _fetch_intraday(symbol: str, start: Optional[datetime], end: datetime) -> pd.DataFrame:
    """Return clean 1h intraday bars. yfinance supports max 730 days of 1h history."""
    ticker = yf.Ticker(symbol)
    if start is None:
        df = ticker.history(period="730d", interval="1h", auto_adjust=True)
    else:
        df = ticker.history(
            start=start.isoformat()[:10],
            end=(end + timedelta(days=1)).isoformat()[:10],
            interval="1h",
            auto_adjust=True,
        )
    if df is None or df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC")
    return df


# ── Per-symbol incremental seed ───────────────────────────────────────────────

async def seed_symbol_incremental(
    db: AsyncSession,
    symbol: str,
    *,
    log_to_db: bool = True,
) -> SeedResult:
    """
    Append-only, idempotent seed for one symbol.
    Returns a SeedResult; never raises — errors are captured in the result.
    """
    sym = symbol.upper()
    logger.info("Seeding %s …", sym)

    try:
        loop  = asyncio.get_running_loop()
        today = date.today()

        # ── Daily ─────────────────────────────────────────────────────────────
        max_daily_result = await db.execute(
            select(func.max(OHLCVDaily.trade_date)).where(OHLCVDaily.symbol == sym)
        )
        max_daily: Optional[date] = max_daily_result.scalar_one_or_none()

        daily_start = (max_daily + timedelta(days=1)) if max_daily else None
        df_daily = await loop.run_in_executor(None, _fetch_daily, sym, daily_start, today)

        rows_daily = 0
        if not df_daily.empty:
            daily_rows = [
                {
                    "symbol":      sym,
                    "trade_date":  idx.date() if hasattr(idx, "date") else idx,
                    "open":        float(row["Open"]),
                    "high":        float(row["High"]),
                    "low":         float(row["Low"]),
                    "close":       float(row["Close"]),
                    "volume":      int(row["Volume"]),
                    "adj_close":   float(row["Close"]),   # auto_adjust=True means Close IS adj
                    "data_source": "yfinance_bulk",
                }
                for idx, row in df_daily.iterrows()
                if pd.notna(row["Close"]) and float(row["Close"]) > 0
            ]
            if daily_rows:
                stmt = (
                    pg_insert(OHLCVDaily)
                    .values(daily_rows)
                    .on_conflict_do_nothing(constraint=_CONSTRAINT_DAILY)
                )
                await db.execute(stmt)
                rows_daily = len(daily_rows)
                await db.flush()

        # Check total daily bars to decide whether to continue
        count_result = await db.execute(
            select(func.count()).select_from(OHLCVDaily).where(OHLCVDaily.symbol == sym)
        )
        total_daily: int = count_result.scalar_one_or_none() or 0

        if total_daily < MIN_BARS_REQUIRED:
            result = SeedResult(
                symbol=sym,
                status="skipped",
                reason=f"insufficient_data ({total_daily} daily rows / {MIN_BARS_REQUIRED} required)",
                rows_added_daily=rows_daily,
                rows_added_intraday=0,
            )
            await _log_result(db, result, log_to_db)
            await db.commit()
            return result

        # ── Intraday (1h) ─────────────────────────────────────────────────────
        max_intra_result = await db.execute(
            select(func.max(OHLCVIntraday.bar_time)).where(
                OHLCVIntraday.symbol == sym,
                OHLCVIntraday.interval == "1h",
            )
        )
        max_intra: Optional[datetime] = max_intra_result.scalar_one_or_none()

        intra_start = (max_intra + timedelta(hours=1)) if max_intra else None
        now_utc     = datetime.now(timezone.utc)
        df_intra    = await loop.run_in_executor(None, _fetch_intraday, sym, intra_start, now_utc)

        rows_intra = 0
        if not df_intra.empty:
            intra_rows = []
            for idx, row in df_intra.iterrows():
                bar_time = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                if bar_time.tzinfo is None:
                    bar_time = bar_time.replace(tzinfo=timezone.utc)
                if pd.isna(row["Close"]) or float(row["Close"]) <= 0:
                    continue
                intra_rows.append({
                    "symbol":      sym,
                    "interval":    "1h",
                    "bar_time":    bar_time,
                    "open":        float(row["Open"]),
                    "high":        float(row["High"]),
                    "low":         float(row["Low"]),
                    "close":       float(row["Close"]),
                    "volume":      int(row["Volume"]),
                    "data_source": "yfinance_bulk",
                })
            if intra_rows:
                stmt = (
                    pg_insert(OHLCVIntraday)
                    .values(intra_rows)
                    .on_conflict_do_nothing(constraint=_CONSTRAINT_INTRADAY)
                )
                await db.execute(stmt)
                rows_intra = len(intra_rows)
                await db.flush()

        result = SeedResult(
            symbol=sym,
            status="done",
            reason=None,
            rows_added_daily=rows_daily,
            rows_added_intraday=rows_intra,
        )
        await _log_result(db, result, log_to_db)
        await db.commit()
        logger.info("Seeded %s: +%d daily, +%d intraday bars", sym, rows_daily, rows_intra)
        return result

    except Exception as exc:
        err_msg = str(exc)[:500]
        logger.warning("Seed failed for %s: %s", sym, err_msg)
        try:
            await db.rollback()
        except Exception:
            pass
        result = SeedResult(
            symbol=sym,
            status="failed",
            reason=err_msg,
            rows_added_daily=0,
            rows_added_intraday=0,
        )
        # Try to log the failure in a fresh nested transaction
        try:
            async with db.begin_nested():
                await _log_result(db, result, log_to_db)
        except Exception:
            pass
        return result


# ── DB logging helper ─────────────────────────────────────────────────────────

async def _log_result(db: AsyncSession, result: SeedResult, log_to_db: bool) -> None:
    if not log_to_db:
        return
    try:
        now = datetime.now(timezone.utc)
        job = BulkJobRun(
            job_type     = "seed",
            scope        = "single",
            symbol       = result.symbol,
            status       = result.status,
            reason       = result.reason,
            rows_added   = result.rows_added,
            started_at   = now,
            completed_at = now,
        )
        db.add(job)
        await db.flush()
    except Exception as exc:
        logger.debug("Could not log seed result to DB: %s", exc)
