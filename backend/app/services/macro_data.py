"""
app/services/macro_data.py
FRED + Yahoo Finance data fetcher — extended for P2-MACRO-ADV-01.

New series vs MVP:
  DGS2   → treasury_2y       (2-Year CMT yield)
  DGS5   → treasury_5y       (5-Year CMT yield)
  DGS10  → treasury_10y      (10-Year CMT yield)
  DGS30  → treasury_30y      (30-Year CMT yield)
  USREC  → recession_indicator (NBER recession dummy)
  PAYEMS → nonfarm_payrolls  (level; MoM delta computed in scoring)
  INDPRO → industrial_production (index level)

Existing series retained:
  FEDFUNDS → fed_funds_rate
  UNRATE   → unemployment_rate
  T10Y2Y   → yield_spread_10y_2y
  CPIAUCSL → cpi_yoy (YoY computed here)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from app.config import settings
from app.schemas.data_models import MacroData

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class MacroFetcher:
    """Async FRED data fetcher with one public method per indicator family."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.fred_api_key
        if not self._has_key():
            logger.warning("FRED API key not configured — macro fetches will be skipped.")

    def _has_key(self) -> bool:
        return bool(self.api_key) and self.api_key != "your_key_here"

    def _start(self, days: int) -> str:
        return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # ── Core fetch primitive ──────────────────────────────────────────────────

    async def fetch_series(
        self,
        series_id: str,
        indicator_name: str,
        observation_start: str,
    ) -> List[MacroData]:
        """Fetch one FRED series and return a list of MacroData records."""
        if not self._has_key():
            logger.error("FRED key missing — skipping %s", series_id)
            return []

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": observation_start,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(FRED_BASE_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP %s for %s: %s", exc.response.status_code, series_id, exc)
            return []
        except Exception as exc:
            logger.error("Fetch error for %s: %s", series_id, exc)
            return []

        results: List[MacroData] = []
        for obs in payload.get("observations", []):
            raw = obs.get("value", ".")
            if raw == ".":
                continue
            try:
                results.append(MacroData(
                    indicator_name=indicator_name,
                    value=float(raw),
                    date=datetime.strptime(obs["date"], "%Y-%m-%d").date(),
                ))
            except Exception as exc:
                logger.warning("Parse error %s @ %s: %s", series_id, obs.get("date"), exc)

        logger.info("Fetched %d records for %s (%s)", len(results), indicator_name, series_id)
        return results

    # ── MVP indicators ────────────────────────────────────────────────────────

    async def fetch_fed_funds_rate(self) -> List[MacroData]:
        return await self.fetch_series("FEDFUNDS", "fed_funds_rate", self._start(60))

    async def fetch_unemployment_rate(self) -> List[MacroData]:
        return await self.fetch_series("UNRATE", "unemployment_rate", self._start(60))

    async def fetch_yield_spread(self) -> List[MacroData]:
        """10Y–2Y spread (FRED computed series T10Y2Y)."""
        return await self.fetch_series("T10Y2Y", "yield_spread_10y_2y", self._start(14))

    async def fetch_cpi_yoy(self) -> List[MacroData]:
        """Compute YoY CPI % change from raw CPIAUCSL observations."""
        raw = await self.fetch_series("CPIAUCSL", "cpi_raw", self._start(400))
        if len(raw) < 13:
            logger.warning("Insufficient CPI data for YoY computation (%d points)", len(raw))
            return []
        raw.sort(key=lambda x: x.date)
        results: List[MacroData] = []
        for i in range(12, len(raw)):
            curr, prev = raw[i], raw[i - 12]
            if prev.value == 0:
                continue
            results.append(MacroData(
                indicator_name="cpi_yoy",
                value=round((curr.value - prev.value) / prev.value * 100, 2),
                date=curr.date,
            ))
        return results

    # ── Advanced: full yield curve ────────────────────────────────────────────

    async def fetch_dgs2(self) -> List[MacroData]:
        """2-Year Treasury Constant Maturity Rate."""
        return await self.fetch_series("DGS2", "treasury_2y", self._start(14))

    async def fetch_dgs5(self) -> List[MacroData]:
        """5-Year Treasury Constant Maturity Rate."""
        return await self.fetch_series("DGS5", "treasury_5y", self._start(14))

    async def fetch_dgs10(self) -> List[MacroData]:
        """10-Year Treasury Constant Maturity Rate."""
        return await self.fetch_series("DGS10", "treasury_10y", self._start(14))

    async def fetch_dgs30(self) -> List[MacroData]:
        """30-Year Treasury Constant Maturity Rate."""
        return await self.fetch_series("DGS30", "treasury_30y", self._start(14))

    # ── Advanced: recession + labour depth ───────────────────────────────────

    async def fetch_recession_indicator(self) -> List[MacroData]:
        """NBER Recession Indicator (USREC): 1 = recession, 0 = expansion."""
        return await self.fetch_series("USREC", "recession_indicator", self._start(90))

    async def fetch_nonfarm_payrolls(self) -> List[MacroData]:
        """Non-Farm Payrolls level (PAYEMS, thousands)."""
        return await self.fetch_series("PAYEMS", "nonfarm_payrolls", self._start(90))

    async def fetch_industrial_production(self) -> List[MacroData]:
        """Industrial Production Index (INDPRO)."""
        return await self.fetch_series("INDPRO", "industrial_production", self._start(90))
