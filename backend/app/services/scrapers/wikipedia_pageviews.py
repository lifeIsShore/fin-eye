"""
app/services/scrapers/wikipedia_pageviews.py
Wikipedia pageview attention signal (Sprint 40 — todos-v4 Phase 6 #5).

Daily article view count per company Wikipedia page.
Computes z-score vs 252-day rolling mean → `wikipedia_attention_zscore`.
Unusual attention (z > 2.0) flagged in raw_json for surfacing in UI.

Signals stored per symbol:
  source="wikipedia", symbol=<SYM>, signal_name="wikipedia_views"          → raw daily views
  source="wikipedia", symbol=<SYM>, signal_name="wikipedia_attention_zscore" → z-score

Wikipedia REST API is free, no key required.
Endpoint: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/

Symbol → article name mapping uses a manual override dict first, then falls
back to the company name if available, or the symbol itself.

Cron: daily at 08:30 UTC (30 min after macro + trends, rate-limit safe).

Usage:
    fetcher = WikipediaPageviewsFetcher()
    result  = await fetcher.fetch_and_store(db, symbols=["AAPL", "MSFT"])
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_signal import ExternalSignal

logger = logging.getLogger(__name__)

_WP_BASE  = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
_PROJECT  = "en.wikipedia"
_ACCESS   = "all-access"
_AGENT    = "all-agents"
_TIMEOUT  = 20.0

# Manual overrides: ticker → Wikipedia article title
_ARTICLE_MAP: dict[str, str] = {
    "AAPL":    "Apple_Inc.",
    "MSFT":    "Microsoft",
    "GOOGL":   "Alphabet_Inc.",
    "GOOG":    "Alphabet_Inc.",
    "AMZN":    "Amazon_(company)",
    "NVDA":    "Nvidia",
    "META":    "Meta_Platforms",
    "TSLA":    "Tesla,_Inc.",
    "JPM":     "JPMorgan_Chase",
    "V":       "Visa_Inc.",
    "SAP":     "SAP",
    "SIE.DE":  "Siemens",
    "BAYN.DE": "Bayer_AG",
    "DTE.DE":  "Deutsche_Telekom",
    "BMW.DE":  "BMW",
    "MBG.DE":  "Mercedes-Benz_Group",
    "DBK.DE":  "Deutsche_Bank",
    "VOW3.DE": "Volkswagen_Group",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}


def _article_for(symbol: str) -> str:
    return _ARTICLE_MAP.get(symbol.upper(), symbol.replace("-", "_"))


class WikipediaPageviewsFetcher:
    """Fetches daily Wikipedia pageviews and computes a z-score attention signal."""

    async def fetch_and_store(
        self,
        db: AsyncSession,
        symbols: list[str],
    ) -> dict[str, Any]:
        ok, failed, skipped = [], [], []
        ts_today = datetime.now(timezone.utc)

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for symbol in symbols:
                try:
                    article    = _article_for(symbol)
                    views_252  = await self._fetch_history(client, article, days=252)
                    if not views_252:
                        skipped.append(symbol)
                        continue

                    latest_views = views_252[-1]
                    mean_252     = sum(views_252) / len(views_252)
                    std_252      = _std(views_252)
                    zscore       = (latest_views - mean_252) / (std_252 or 1.0)
                    is_unusual   = zscore > 2.0

                    db.add(ExternalSignal(
                        source="wikipedia",
                        symbol=symbol.upper(),
                        signal_name="wikipedia_views",
                        value=float(latest_views),
                        raw_json={
                            "article": article,
                            "mean_252": round(mean_252, 1),
                            "unusual": is_unusual,
                        },
                        fetched_at=ts_today,
                    ))
                    db.add(ExternalSignal(
                        source="wikipedia",
                        symbol=symbol.upper(),
                        signal_name="wikipedia_attention_zscore",
                        value=round(zscore, 4),
                        raw_json=None,
                        fetched_at=ts_today,
                    ))
                    ok.append(symbol)
                    logger.debug(
                        "Wikipedia %s (%s): views=%d zscore=%.2f unusual=%s",
                        symbol, article, latest_views, zscore, is_unusual,
                    )
                except Exception as exc:
                    logger.warning("Wikipedia fetch failed for %s: %s", symbol, exc)
                    failed.append(symbol)

        await db.commit()
        logger.info(
            "Wikipedia pageviews batch: ok=%d failed=%d skipped=%d",
            len(ok), len(failed), len(skipped),
        )
        return {"ok": ok, "failed": failed, "skipped": skipped}

    async def get_latest(self, db: AsyncSession, symbol: str) -> dict[str, Any] | None:
        from sqlalchemy import select, desc  # noqa: PLC0415
        sym = symbol.upper()
        result = await db.execute(
            select(ExternalSignal)
            .where(
                ExternalSignal.source == "wikipedia",
                ExternalSignal.symbol == sym,
                ExternalSignal.signal_name == "wikipedia_attention_zscore",
            )
            .order_by(desc(ExternalSignal.fetched_at))
            .limit(1)
        )
        row = result.scalars().first()
        if row is None:
            return None
        return {
            "symbol":     sym,
            "zscore":     row.value,
            "unusual":    row.value > 2.0,
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        }

    # ── private ───────────────────────────────────────────────────────────────

    async def _fetch_history(
        self,
        client: httpx.AsyncClient,
        article: str,
        days: int = 252,
    ) -> list[int]:
        """
        Returns a list of daily view counts (oldest → newest), up to `days` long.
        Wikipedia REST API: /metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/daily/{start}/{end}
        """
        end_dt   = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        start    = start_dt.strftime("%Y%m%d")
        end      = end_dt.strftime("%Y%m%d")
        url      = f"{_WP_BASE}/{_PROJECT}/{_ACCESS}/{_AGENT}/{article}/daily/{start}/{end}"

        try:
            resp = await client.get(url, headers={"User-Agent": "fin-eye/1.0 (research)"})
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [int(item["views"]) for item in items if "views" in item]
        except Exception as exc:
            logger.debug("Wikipedia API error for %s: %s", article, exc)
            return []


def _std(values: list[float | int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5
