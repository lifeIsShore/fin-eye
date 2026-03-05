"""
app/services/ohlcv_fetcher.py
OHLCV data fetcher using yfinance.
Fetches daily + intraday bars for a list of symbols and upserts into PostgreSQL.

FIX BUG-003: adj_close was set via row.get("Close", row["Close"]) which always
             returned the plain Close value. With auto_adjust=True, yfinance
             adjusts all columns in-place so Close IS already the adjusted close.
             Now stored explicitly as float(row["Close"]) to make intent clear.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.market import OHLCVDaily, OHLCVIntraday

logger = logging.getLogger(__name__)
settings = get_settings()

# Map our interval names to yfinance interval strings
INTRADAY_INTERVALS = {
    "1h": "1h",
    "4h": "1h",  # yfinance doesn't have 4h; we resample 1h → 4h
}

FRED_MACRO_SERIES = [
    "FEDFUNDS",   # Federal Funds Rate
    "CPIAUCSL",   # CPI All Urban Consumers
    "UNRATE",     # Unemployment Rate
    "T10Y2Y",     # 10Y-2Y Treasury Spread
    "VIXCLS",     # CBOE Volatility Index (via FRED)
    "USREC",      # NBER Recession Indicator
    "DGS10",      # 10-Year Treasury
    "DGS2",       # 2-Year Treasury
    "DGS5",       # 5-Year Treasury
    "DGS30",      # 30-Year Treasury
    "PAYEMS",     # Non-Farm Payroll
    "INDPRO",     # Industrial Production Index
]


class OHLCVFetcher:
    """
    Fetches and persists OHLCV data from Yahoo Finance.

    Usage:
        fetcher = OHLCVFetcher()
        await fetcher.fetch_and_store_daily(session, ["AAPL", "TSLA"])
        await fetcher.fetch_and_store_intraday(session, ["AAPL"], interval="1h")
    """

    def __init__(self) -> None:
        self.lookback_years = settings.ohlcv_lookback_years

    # ── Daily ──────────────────────────────────────────────────────────────────

    async def fetch_and_store_daily(
        self,
        session: AsyncSession,
        symbols: Optional[List[str]] = None,
    ) -> dict:
        """
        Fetch daily OHLCV for all symbols and upsert into ohlcv_daily.
        Returns a summary dict with counts per symbol.
        """
        symbols = symbols or settings.ohlcv_symbols_default
        start_date = date.today() - timedelta(days=self.lookback_years * 365)
        results: dict = {}

        for symbol in symbols:
            try:
                df = self._download_daily(symbol, start_date)
                if df.empty:
                    logger.warning("No daily data returned for %s", symbol)
                    results[symbol] = {"status": "no_data", "rows": 0}
                    continue

                rows = self._df_to_daily_rows(df, symbol)
                count = await self._upsert_daily(session, rows)
                results[symbol] = {"status": "ok", "rows": count}
                logger.info("Upserted %d daily rows for %s", count, symbol)

            except Exception as exc:
                logger.exception("Failed to fetch daily data for %s: %s", symbol, exc)
                results[symbol] = {"status": "error", "error": str(exc), "rows": 0}

        return results

    def _download_daily(self, symbol: str, start: date) -> pd.DataFrame:
        """Download daily bars via yfinance. Returns cleaned DataFrame."""
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start.isoformat(),
            interval="1d",
            auto_adjust=True,
            actions=False,
        )
        if df.empty:
            return df
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None)  # strip tz; store as date
        return df

    def _df_to_daily_rows(self, df: pd.DataFrame, symbol: str) -> list[dict]:
        rows = []
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            rows.append(
                {
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    # FIX BUG-003: auto_adjust=True means Close IS the adjusted close.
                    # Original: row.get("Close", row["Close"]) — always returned Close,
                    # never read "Adj Close". This makes the intent explicit and correct.
                    "adj_close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "data_source": "yahoo_finance",
                }
            )
        return rows

    async def _upsert_daily(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = (
            pg_insert(OHLCVDaily)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_ohlcv_symbol_date",
                set_={
                    "open": pg_insert(OHLCVDaily).excluded.open,
                    "high": pg_insert(OHLCVDaily).excluded.high,
                    "low": pg_insert(OHLCVDaily).excluded.low,
                    "close": pg_insert(OHLCVDaily).excluded.close,
                    "adj_close": pg_insert(OHLCVDaily).excluded.adj_close,
                    "volume": pg_insert(OHLCVDaily).excluded.volume,
                },
            )
        )
        await session.execute(stmt)
        await session.flush()
        return len(rows)

    # ── Intraday ───────────────────────────────────────────────────────────────

    async def fetch_and_store_intraday(
        self,
        session: AsyncSession,
        symbols: Optional[List[str]] = None,
        interval: str = "1h",
    ) -> dict:
        """
        Fetch intraday bars (1h or 4h) for symbols.
        yfinance provides 1h data for the last 730 days.
        4h bars are resampled from 1h.
        """
        symbols = symbols or settings.ohlcv_symbols_default
        results: dict = {}

        for symbol in symbols:
            try:
                df_1h = self._download_intraday(symbol)
                if df_1h.empty:
                    results[symbol] = {"status": "no_data", "rows": 0}
                    continue

                if interval == "4h":
                    df = self._resample_4h(df_1h)
                else:
                    df = df_1h

                rows = self._df_to_intraday_rows(df, symbol, interval)
                count = await self._upsert_intraday(session, rows)
                results[symbol] = {"status": "ok", "rows": count}
                logger.info("Upserted %d intraday(%s) rows for %s", count, interval, symbol)

            except Exception as exc:
                logger.exception("Failed to fetch intraday for %s: %s", symbol, exc)
                results[symbol] = {"status": "error", "error": str(exc), "rows": 0}

        return results

    def _download_intraday(self, symbol: str) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d", interval="1h", auto_adjust=True, actions=False)
        if df.empty:
            return df
        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        return df

    def _resample_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.resample("4h", label="left", closed="left").agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        ).dropna()

    def _df_to_intraday_rows(
        self, df: pd.DataFrame, symbol: str, interval: str
    ) -> list[dict]:
        rows = []
        for idx, row in df.iterrows():
            bar_time = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            if bar_time.tzinfo is None:
                bar_time = bar_time.replace(tzinfo=timezone.utc)
            rows.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "bar_time": bar_time,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "data_source": "yahoo_finance",
                }
            )
        return rows

    async def _upsert_intraday(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = (
            pg_insert(OHLCVIntraday)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_ohlcv_intraday",
                set_={
                    "open": pg_insert(OHLCVIntraday).excluded.open,
                    "high": pg_insert(OHLCVIntraday).excluded.high,
                    "low": pg_insert(OHLCVIntraday).excluded.low,
                    "close": pg_insert(OHLCVIntraday).excluded.close,
                    "volume": pg_insert(OHLCVIntraday).excluded.volume,
                },
            )
        )
        await session.execute(stmt)
        await session.flush()
        return len(rows)

    # ── Validation ─────────────────────────────────────────────────────────────

    @staticmethod
    def validate_row(row: dict) -> list[str]:
        """
        Basic sanity checks on an OHLCV row.
        Returns a list of validation error strings (empty = OK).
        """
        errors = []
        if row["high"] < row["low"]:
            errors.append(f"high < low: {row['high']} < {row['low']}")
        if row["close"] <= 0:
            errors.append(f"close <= 0: {row['close']}")
        if row["volume"] < 0:
            errors.append(f"volume < 0: {row['volume']}")
        return errors