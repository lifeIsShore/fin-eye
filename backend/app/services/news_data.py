"""
app/services/news_data.py
==========================
Cache-first Finnhub news fetcher with FinBERT scoring (todos-v4.md Phase 5.1-5.3).

Changes from original:
  - Stores url, last_fetched_at, fetch_source on each article
  - Cache-first: if last_fetched_at < TTL (6h), skips Finnhub and returns DB records
  - Runs FinBERT/VADER on new articles before persisting
  - Uses ON CONFLICT DO UPDATE to refresh stale articles (new URL, score, fetched_at)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.sentiment import NewsArticle
from app.schemas.data_models import NewsData
from app.services.sentiment_scorer import get_sentiment_scorer

logger = logging.getLogger(__name__)

# Re-fetch Finnhub if the last fetch was more than 6 hours ago
NEWS_CACHE_TTL_HOURS = 6


class NewsFetcher:
    """
    Fetch, score, and persist news for symbols.

    Fetch strategy
    --------------
    1. Check DB: if newest last_fetched_at for this symbol is within TTL → return DB rows
    2. Otherwise: call Finnhub API, score headlines with FinBERT/VADER, upsert into DB
    """

    BASE_URL = "https://finnhub.io/api/v1/company-news"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.finnhub_api_key
        if not settings.has_finnhub and not api_key:
            logger.warning(
                "Finnhub API key not configured. "
                "Set FINNHUB_API_KEY in backend/.env — get a free key at https://finnhub.io"
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_recent_news(
        self,
        symbol: str,
        days_back: int = 7,
    ) -> List[NewsData]:
        """
        Fetch news for a symbol from Finnhub (raw, no DB interaction).
        Used by schedulers that want the raw list before scoring/storing.
        """
        if not self.api_key or self.api_key in ("", "your_key_here"):
            logger.error("Cannot fetch Finnhub data — FINNHUB_API_KEY is empty or placeholder.")
            return []

        end_date   = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        _from = start_date.strftime("%Y-%m-%d")
        _to   = end_date.strftime("%Y-%m-%d")
        params = {"symbol": symbol, "from": _from, "to": _to, "token": self.api_key}

        logger.debug("Fetching Finnhub news for %s (%s → %s)", symbol, _from, _to)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Finnhub fetch failed for %s: %s", symbol, exc)
            return []

        results: List[NewsData] = []
        for item in data:
            try:
                published_at = datetime.fromtimestamp(item.get("datetime", 0), tz=pytz.UTC)
                results.append(
                    NewsData(
                        symbol=symbol,
                        title=item.get("headline", ""),
                        source=item.get("source"),
                        published_at=published_at,
                        sentiment_score=None,
                        url=item.get("url"),
                    )
                )
            except Exception as exc:
                logger.debug("Error parsing news item for %s: %s", symbol, exc)
        return results

    async def fetch_and_store(
        self,
        db: AsyncSession,
        symbols: Optional[List[str]] = None,
        lookback_days: int = 7,
    ) -> dict[str, int]:
        """
        Cache-first fetch + score + persist.

        Returns dict mapping symbol → number of NEW articles inserted this call.
        """
        symbols = symbols or list(settings.ohlcv_symbols_default)
        results: dict[str, int] = {}

        scorer = get_sentiment_scorer()

        for symbol in symbols:
            # 1. Check cache freshness
            if await self._is_fresh(db, symbol):
                logger.debug("News cache fresh for %s — skipping Finnhub call", symbol)
                results[symbol] = 0
                continue

            # 2. Fetch from Finnhub
            news_items = await self.fetch_recent_news(symbol, days_back=lookback_days)
            if not news_items:
                results[symbol] = 0
                continue

            # 3. Score headlines in batch
            titles   = [item.title for item in news_items]
            scored   = scorer.score_batch(titles)
            now_utc  = datetime.now(timezone.utc)

            # 4. Upsert into DB (on conflict update score + fetched_at)
            inserted = 0
            for item, sentiment in zip(news_items, scored):
                existing = await self._find_existing(db, item.symbol, item.title, item.published_at)
                if existing is None:
                    article = NewsArticle(
                        symbol          = item.symbol,
                        title           = item.title,
                        url             = getattr(item, "url", None),
                        source          = item.source,
                        published_at    = item.published_at,
                        sentiment_score = sentiment.vader_compound,   # VADER compound (-1 to +1)
                        sentiment_label = sentiment.label,            # 'bullish'/'bearish'/'neutral'
                        finbert_score   = sentiment.score,            # confidence
                        last_fetched_at = now_utc,
                        fetch_source    = "finnhub",
                    )
                    db.add(article)
                    inserted += 1
                else:
                    # Refresh stale article metadata
                    existing.last_fetched_at = now_utc
                    existing.sentiment_label = sentiment.label
                    existing.finbert_score   = sentiment.score
                    if not existing.url and getattr(item, "url", None):
                        existing.url = item.url

            await db.commit()
            results[symbol] = inserted
            logger.info("News upserted for %s: +%d new articles", symbol, inserted)

        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _is_fresh(self, db: AsyncSession, symbol: str) -> bool:
        """Return True if we fetched news for this symbol within the TTL window."""
        from sqlalchemy import func  # noqa: PLC0415
        result = await db.execute(
            select(func.max(NewsArticle.last_fetched_at)).where(
                NewsArticle.symbol == symbol.upper()
            )
        )
        last = result.scalar_one_or_none()
        if last is None:
            return False
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return age_hours < NEWS_CACHE_TTL_HOURS

    async def _find_existing(
        self,
        db: AsyncSession,
        symbol: str,
        title: str,
        published_at: datetime,
    ) -> Optional[NewsArticle]:
        result = await db.execute(
            select(NewsArticle).where(
                NewsArticle.symbol == symbol,
                NewsArticle.title == title,
                NewsArticle.published_at == published_at,
            )
        )
        return result.scalar_one_or_none()
