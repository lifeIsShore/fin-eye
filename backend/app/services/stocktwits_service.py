"""
app/services/stocktwits_service.py
─────────────────────────────────────────────────────────────────────────────
StockTwits retail sentiment service — replaces reddit_service.py.

Why StockTwits over Reddit:
  • No API key, no OAuth, no rate-limit registration required.
  • Users self-tag every message as Bullish or Bearish — zero NLP needed.
  • Purpose-built for financial markets, not general social media.
  • Free public endpoint returns the 30 most recent messages per symbol.

API:
  GET https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json
  Response: { messages: [ { body, sentiment: { basic: "Bullish"|"Bearish" }, created_at, likes: { total } } ] }

Fallback:
  If StockTwits is unreachable or the ticker has no messages, mock data is
  returned so the UI never breaks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Tuple

import httpx

from app.schemas.sentiment_models import SentimentComment, SentimentSummary

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_TIMEOUT  = 8.0  # seconds


class StockTwitsService:
    """
    Fetches retail sentiment from StockTwits.

    Usage:
        svc = StockTwitsService()
        summary, bullish, bearish = svc.get_sentiment_summary("AAPL")
    """

    async def fetch_messages(self, ticker: str) -> List[SentimentComment]:
        """
        Fetch the ~30 most recent StockTwits messages for a ticker.
        Returns a list of SentimentComment objects.
        """
        url = _BASE_URL.format(ticker=ticker.upper())
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
                # 422 = ticker not found on StockTwits
                if resp.status_code == 422:
                    logger.info("StockTwits: ticker %s not found — using mock data", ticker)
                    return self._mock_data(ticker)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("StockTwits request timed out for %s — using mock data", ticker)
            return self._mock_data(ticker)
        except httpx.HTTPStatusError as exc:
            logger.warning("StockTwits HTTP %s for %s — using mock data", exc.response.status_code, ticker)
            return self._mock_data(ticker)
        except Exception as exc:
            logger.error("StockTwits unexpected error for %s: %s — using mock data", ticker, exc)
            return self._mock_data(ticker)

        messages = data.get("messages", [])
        if not messages:
            return self._mock_data(ticker)

        comments: List[SentimentComment] = []
        for msg in messages:
            # StockTwits sentiment is user-supplied: {"basic": "Bullish"} or {"basic": "Bearish"} or None
            raw_sentiment = msg.get("entities", {}).get("sentiment") or msg.get("sentiment")
            basic = (raw_sentiment or {}).get("basic")  # "Bullish", "Bearish", or None

            if basic == "Bullish":
                label = "Positive"
                score = 0.7
            elif basic == "Bearish":
                label = "Negative"
                score = -0.7
            else:
                # No tag — treat as neutral, still include for mention count
                label = "Neutral"
                score = 0.0

            try:
                created = datetime.strptime(msg["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                created = datetime.now(timezone.utc)

            likes = (msg.get("likes") or {}).get("total", 0)
            username = msg.get("user", {}).get("username", "anonymous")

            comments.append(SentimentComment(
                subreddit=f"@{username}",   # reuse field; frontend label is "Source"
                timestamp=created,
                text=msg.get("body", ""),
                sentiment_score=score,
                sentiment_label=label,
                upvotes=likes,
                url=f"https://stocktwits.com/{username}",
            ))

        comments.sort(key=lambda c: c.timestamp, reverse=True)
        logger.info("StockTwits: fetched %d messages for %s", len(comments), ticker)
        return comments

    def get_sentiment_summary(
        self, ticker: str
    ) -> Tuple[SentimentSummary, List[SentimentComment], List[SentimentComment]]:
        """
        Sync wrapper — runs the async fetch in a new event loop.
        Kept sync to match the original RedditService interface so the
        endpoint requires zero changes.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Inside an async context (e.g. FastAPI) — use nest_asyncio or
                # call the async variant directly from the endpoint instead.
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.fetch_messages(ticker))
                    comments = future.result(timeout=12)
            else:
                comments = loop.run_until_complete(self.fetch_messages(ticker))
        except Exception as exc:
            logger.error("get_sentiment_summary failed for %s: %s", ticker, exc)
            comments = self._mock_data(ticker)

        return self._summarise(ticker, comments)

    async def get_sentiment_summary_async(
        self, ticker: str
    ) -> Tuple[SentimentSummary, List[SentimentComment], List[SentimentComment]]:
        """Async variant — preferred when called from an async endpoint."""
        comments = await self.fetch_messages(ticker)
        return self._summarise(ticker, comments)

    # ─────────────────────────────────────────────────────────────────────────

    def _summarise(
        self, ticker: str, comments: List[SentimentComment]
    ) -> Tuple[SentimentSummary, List[SentimentComment], List[SentimentComment]]:
        if not comments:
            return (
                SentimentSummary(
                    total_mentions=0,
                    percent_positive=0.0,
                    percent_neutral=100.0,
                    percent_negative=0.0,
                    retail_sentiment_score=50.0,
                ),
                [],
                [],
            )

        total = len(comments)
        pos   = sum(1 for c in comments if c.sentiment_label == "Positive")
        neg   = sum(1 for c in comments if c.sentiment_label == "Negative")
        neu   = total - pos - neg

        # Score:  100% bullish → 100,  100% bearish → 0,  balanced → 50
        labeled = pos + neg
        if labeled == 0:
            retail_score = 50.0
        else:
            retail_score = round((pos / labeled) * 100, 1)

        summary = SentimentSummary(
            total_mentions=total,
            percent_positive=round((pos / total) * 100, 1),
            percent_neutral=round((neu / total) * 100, 1),
            percent_negative=round((neg / total) * 100, 1),
            retail_sentiment_score=retail_score,
        )

        bullish = sorted(
            [c for c in comments if c.sentiment_label == "Positive"],
            key=lambda c: c.upvotes, reverse=True,
        )
        bearish = sorted(
            [c for c in comments if c.sentiment_label == "Negative"],
            key=lambda c: c.upvotes, reverse=True,
        )

        return summary, bullish[:5], bearish[:5]

    # ── Sprint 42: External-signal persistence ──────────────────────────────
    async def fetch_and_store_external_signals(
        self,
        db,  # AsyncSession — typed loosely to avoid circular import
        symbols: list[str],
    ) -> dict:
        """
        Compute stocktwits_sentiment_norm + stocktwits_mentions per symbol
        and persist in `external_signals` table.

        Signals stored:
          source="stocktwits", signal_name="stocktwits_mentions"         → raw count
          source="stocktwits", signal_name="stocktwits_sentiment_norm"   → 0.0–1.0
        """
        from app.models.external_signal import ExternalSignal  # noqa: PLC0415

        ok, failed = [], []
        ts = datetime.now(timezone.utc)
        _MENTION_CAP = 30.0  # StockTwits returns ~30 msgs max

        for symbol in symbols:
            try:
                comments = await self.fetch_messages(symbol)
                count = len(comments)
                if count == 0:
                    bull_ratio = 0.5
                else:
                    pos = sum(1 for c in comments if c.sentiment_label == "Positive")
                    neg = sum(1 for c in comments if c.sentiment_label == "Negative")
                    labeled = pos + neg
                    bull_ratio = (pos / labeled) if labeled > 0 else 0.5

                mentions_norm = round(min(count / _MENTION_CAP, 1.0), 4)
                sentiment_norm = round(bull_ratio, 4)

                db.add(ExternalSignal(
                    source="stocktwits",
                    symbol=symbol.upper(),
                    signal_name="stocktwits_mentions",
                    value=float(count),
                    raw_json=None,
                    fetched_at=ts,
                ))
                db.add(ExternalSignal(
                    source="stocktwits",
                    symbol=symbol.upper(),
                    signal_name="stocktwits_sentiment_norm",
                    value=sentiment_norm,
                    raw_json=None,
                    fetched_at=ts,
                ))

                ok.append(symbol)
                logger.info(
                    "StockTwits signals %s: mentions=%d norm=%.4f sentiment_norm=%.4f",
                    symbol, count, mentions_norm, sentiment_norm,
                )
            except Exception as exc:
                logger.warning("StockTwits external signal failed for %s: %s", symbol, exc)
                failed.append(symbol)

        await db.commit()
        logger.info("StockTwits external signals: ok=%d failed=%d", len(ok), len(failed))
        return {"ok": ok, "failed": failed}

    def _mock_data(self, ticker: str) -> List[SentimentComment]:
        """Fallback mock data when StockTwits is unavailable."""
        now = datetime.now(timezone.utc)
        return [
            SentimentComment(
                subreddit="@mock_bull",
                timestamp=now,
                text=f"{ticker} is looking strong here. Holding my position.",
                sentiment_score=0.7,
                sentiment_label="Positive",
                upvotes=12,
                url="https://stocktwits.com",
            ),
            SentimentComment(
                subreddit="@mock_bear",
                timestamp=now,
                text=f"Not sure about {ticker} at these levels. Seems overextended.",
                sentiment_score=-0.7,
                sentiment_label="Negative",
                upvotes=4,
                url="https://stocktwits.com",
            ),
            SentimentComment(
                subreddit="@mock_neutral",
                timestamp=now,
                text=f"Watching {ticker} closely. No position yet.",
                sentiment_score=0.0,
                sentiment_label="Neutral",
                upvotes=2,
                url="https://stocktwits.com",
            ),
        ]
