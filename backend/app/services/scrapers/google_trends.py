"""
app/services/scrapers/google_trends.py
Google Trends relative search interest per ticker (Sprint 40 — todos-v4 Phase 6 #3).

Uses pytrends (already in requirements.txt).
Fetches weekly relative interest (0-100) for each ticker symbol.
Geo: 'DE' for TR-DE stocks; '' (worldwide) fallback for non-DE symbols.

Signals stored per symbol:
  source="google_trends", symbol=<SYM>, signal_name="google_trends_interest"  → 0-100
  source="google_trends", symbol=<SYM>, signal_name="google_trends_norm"       → 0.0–1.0

Cron: daily at 08:00 UTC (after macro refresh) to avoid rate limits.
pytrends can rate-limit — this service uses a 2s delay between tickers.

Usage:
    fetcher = GoogleTrendsFetcher()
    result  = await fetcher.fetch_and_store(db, symbols=["AAPL", "MSFT"])
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_signal import ExternalSignal

logger = logging.getLogger(__name__)

# Symbols that are primarily traded on German/EU exchanges → use geo='DE'
_DE_EXCHANGES = {"DE", "XETRA", "FSE"}
_INTER_REQUEST_DELAY = 2.0  # seconds between pytrends requests to avoid rate limiting


class GoogleTrendsFetcher:
    """
    Fetches Google Trends weekly search interest for a list of ticker symbols.
    Runs synchronously inside run_in_executor to avoid blocking the event loop.
    """

    async def fetch_and_store(
        self,
        db: AsyncSession,
        symbols: list[str],
        geo: str = "DE",
    ) -> dict[str, Any]:
        """
        Fetch trends for all symbols (one at a time, rate-limit safe).
        Returns summary dict: {"ok": [...], "failed": [...], "skipped": [...]}.
        """
        loop   = asyncio.get_running_loop()
        ok, failed, skipped = [], [], []

        for symbol in symbols:
            try:
                interest = await loop.run_in_executor(
                    None, self._fetch_for_symbol, symbol, geo
                )
                if interest is None:
                    skipped.append(symbol)
                    continue

                norm = round(interest / 100.0, 4)
                ts   = datetime.now(timezone.utc)
                db.add(ExternalSignal(
                    source="google_trends",
                    symbol=symbol.upper(),
                    signal_name="google_trends_interest",
                    value=float(interest),
                    raw_json={"geo": geo},
                    fetched_at=ts,
                ))
                db.add(ExternalSignal(
                    source="google_trends",
                    symbol=symbol.upper(),
                    signal_name="google_trends_norm",
                    value=norm,
                    raw_json=None,
                    fetched_at=ts,
                ))
                ok.append(symbol)
                logger.debug("Google Trends %s: interest=%d, norm=%.4f", symbol, interest, norm)
                await asyncio.sleep(_INTER_REQUEST_DELAY)

            except Exception as exc:
                logger.warning("Google Trends failed for %s: %s", symbol, exc)
                failed.append(symbol)

        await db.commit()
        logger.info(
            "Google Trends batch complete: ok=%d failed=%d skipped=%d",
            len(ok), len(failed), len(skipped),
        )
        return {"ok": ok, "failed": failed, "skipped": skipped}

    async def get_latest(self, db: AsyncSession, symbol: str) -> dict[str, Any] | None:
        """Read most recently stored Trends score for a symbol (no API call)."""
        from sqlalchemy import select, desc  # noqa: PLC0415
        sym = symbol.upper()
        result = await db.execute(
            select(ExternalSignal)
            .where(
                ExternalSignal.source == "google_trends",
                ExternalSignal.symbol == sym,
                ExternalSignal.signal_name == "google_trends_interest",
            )
            .order_by(desc(ExternalSignal.fetched_at))
            .limit(1)
        )
        row = result.scalars().first()
        if row is None:
            return None
        return {
            "symbol":     sym,
            "interest":   row.value,
            "norm":       round(row.value / 100.0, 4),
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        }

    # ── private (sync — runs in executor) ────────────────────────────────────

    def _fetch_for_symbol(self, symbol: str, geo: str) -> float | None:
        """
        Blocking call — use inside run_in_executor.
        Returns the most recent weekly interest value (0-100) or None if unavailable.
        """
        try:
            from pytrends.request import TrendReq  # noqa: PLC0415
            pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=2, backoff_factor=0.5)
            pt.build_payload([symbol], timeframe="now 7-d", geo=geo)
            df = pt.interest_over_time()
            if df.empty or symbol not in df.columns:
                # Retry worldwide if geo-specific returns nothing
                if geo:
                    pt.build_payload([symbol], timeframe="now 7-d", geo="")
                    df = pt.interest_over_time()
            if df.empty or symbol not in df.columns:
                return None
            # Most recent non-partial data point
            col = df[symbol]
            if "isPartial" in df.columns:
                col = col[~df["isPartial"]]
            if col.empty:
                return None
            return float(col.iloc[-1])
        except Exception as exc:
            logger.debug("pytrends error for %s: %s", symbol, exc)
            return None
