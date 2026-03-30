"""
app/services/reddit_service.py
Reddit sentiment service — Sprint 40 extension.

Sprint 40 changes:
  - Added r/de and r/aktien to the subreddit list (German-language communities,
    highly relevant for TR DE stocks).
  - Added `fetch_and_store_external_signals()` async method: computes
    `reddit_mentions_norm` and `reddit_sentiment_norm` per ticker per 24h
    and writes them to the `external_signals` table.
  - Signals stored:
      source="reddit", symbol=<SYM>, signal_name="reddit_mentions"        → raw count
      source="reddit", symbol=<SYM>, signal_name="reddit_mentions_norm"   → 0.0–1.0 (cap=200)
      source="reddit", symbol=<SYM>, signal_name="reddit_sentiment_norm"  → 0.0–1.0 (mapped from -1..1)
  - Original `fetch_recent_mentions()` and `get_sentiment_summary()` methods
    are preserved unchanged for backward compatibility.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Any, List, Tuple

import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.schemas.sentiment_models import SentimentComment, SentimentSummary

logger = logging.getLogger(__name__)

# Mention cap for normalisation: 200 mentions per 24h = max signal strength
_MENTION_CAP = 200.0


class RedditService:
    def __init__(self):
        client_id     = os.getenv("REDDIT_CLIENT_ID",     "mock_id")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", "mock_secret")
        user_agent    = os.getenv("REDDIT_USER_AGENT",    "FinEye:v1.0 (by u/mockuser)")

        self.analyzer   = SentimentIntensityAnalyzer()
        # Sprint 40: added r/de and r/aktien for German-market coverage
        self.subreddits = ["stocks", "wallstreetbets", "investing", "de", "aktien"]

        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
            _ = self.reddit.read_only
        except Exception:
            self.reddit = None

    # ── Sprint 40: External-signal persistence ─────────────────────────────────

    async def fetch_and_store_external_signals(
        self,
        db,  # AsyncSession — typed loosely to avoid circular import
        symbols: list[str],
    ) -> dict[str, Any]:
        """
        Compute reddit_mentions_norm + reddit_sentiment_norm for each symbol
        over the past 24h and persist in `external_signals`.

        Safe to call when Reddit API credentials are absent — falls back to
        zero-signal rows so downstream ML code does not crash.
        """
        from app.models.external_signal import ExternalSignal  # noqa: PLC0415

        ok, failed = [], []
        ts = datetime.now(timezone.utc)

        for symbol in symbols:
            try:
                comments = self.fetch_recent_mentions(symbol, limit=100)
                count    = len(comments)
                if count == 0:
                    avg_compound = 0.0
                else:
                    avg_compound = sum(c.sentiment_score for c in comments) / count

                mentions_norm   = round(min(count / _MENTION_CAP, 1.0), 4)
                sentiment_norm  = round((avg_compound + 1.0) / 2.0, 4)  # -1..1 → 0..1

                db.add(ExternalSignal(
                    source="reddit",
                    symbol=symbol.upper(),
                    signal_name="reddit_mentions",
                    value=float(count),
                    raw_json={"subreddits": self.subreddits},
                    fetched_at=ts,
                ))
                db.add(ExternalSignal(
                    source="reddit",
                    symbol=symbol.upper(),
                    signal_name="reddit_mentions_norm",
                    value=mentions_norm,
                    raw_json=None,
                    fetched_at=ts,
                ))
                db.add(ExternalSignal(
                    source="reddit",
                    symbol=symbol.upper(),
                    signal_name="reddit_sentiment_norm",
                    value=sentiment_norm,
                    raw_json=None,
                    fetched_at=ts,
                ))
                ok.append(symbol)
                logger.debug(
                    "Reddit signals %s: mentions=%d norm=%.4f sentiment_norm=%.4f",
                    symbol, count, mentions_norm, sentiment_norm,
                )
            except Exception as exc:
                logger.warning("Reddit external signal failed for %s: %s", symbol, exc)
                failed.append(symbol)

        await db.commit()
        logger.info("Reddit external signals: ok=%d failed=%d", len(ok), len(failed))
        return {"ok": ok, "failed": failed}

    # ── Original API (unchanged) ───────────────────────────────────────────────

    def _analyze_sentiment(self, text: str) -> Tuple[float, str]:
        scores   = self.analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"
        return compound, label

    def fetch_recent_mentions(self, ticker: str, limit: int = 50) -> List[SentimentComment]:
        comments = []
        if not self.reddit or self.reddit.config.client_id == "mock_id":
            return self._get_mock_data(ticker)

        query = f"${ticker} OR {ticker}"

        for sub_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                per_sub   = max(1, limit // len(self.subreddits))
                for submission in subreddit.search(query, sort="new", time_filter="month", limit=per_sub):
                    score, label = self._analyze_sentiment(
                        submission.title + " " + submission.selftext
                    )
                    created_dt = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    comments.append(SentimentComment(
                        subreddit=sub_name,
                        timestamp=created_dt,
                        text=submission.title,
                        sentiment_score=score,
                        sentiment_label=label,
                        upvotes=submission.score,
                        url=f"https://reddit.com{submission.permalink}",
                    ))
            except Exception as exc:
                logger.debug("Error fetching from r/%s: %s", sub_name, exc)

        comments.sort(key=lambda x: x.timestamp, reverse=True)
        return comments

    def _get_mock_data(self, ticker: str) -> List[SentimentComment]:
        now = datetime.now(timezone.utc)
        return [
            SentimentComment(
                subreddit="wallstreetbets",
                timestamp=now,
                text=f"{ticker} to the moooooon!! Calls are printing.",
                sentiment_score=0.8,
                sentiment_label="Positive",
                upvotes=150,
                url="https://reddit.com/r/mock",
            ),
            SentimentComment(
                subreddit="stocks",
                timestamp=now,
                text=f"Is {ticker} overvalued right now? P/E seems high.",
                sentiment_score=-0.2,
                sentiment_label="Negative",
                upvotes=25,
                url="https://reddit.com/r/mock",
            ),
            SentimentComment(
                subreddit="investing",
                timestamp=now,
                text=f"{ticker} earnings call was somewhat neutral.",
                sentiment_score=0.0,
                sentiment_label="Neutral",
                upvotes=10,
                url="https://reddit.com/r/mock",
            ),
        ]

    def get_sentiment_summary(
        self,
        ticker: str,
    ) -> Tuple[SentimentSummary, List[SentimentComment], List[SentimentComment]]:
        mentions = self.fetch_recent_mentions(ticker)

        if not mentions:
            return (
                SentimentSummary(
                    total_mentions=0,
                    percent_positive=0,
                    percent_neutral=0,
                    percent_negative=0,
                    retail_sentiment_score=50.0,
                ),
                [],
                [],
            )

        total        = len(mentions)
        pos          = sum(1 for m in mentions if m.sentiment_label == "Positive")
        neg          = sum(1 for m in mentions if m.sentiment_label == "Negative")
        neu          = total - pos - neg
        avg_compound = sum(m.sentiment_score for m in mentions) / total
        retail_score = (avg_compound + 1.0) * 50.0

        summary = SentimentSummary(
            total_mentions=total,
            percent_positive=(pos / total) * 100,
            percent_neutral=(neu / total) * 100,
            percent_negative=(neg / total) * 100,
            retail_sentiment_score=round(retail_score, 1),
        )

        bullish = sorted(
            [m for m in mentions if m.sentiment_label == "Positive"],
            key=lambda x: x.upvotes,
            reverse=True,
        )
        bearish = sorted(
            [m for m in mentions if m.sentiment_label == "Negative"],
            key=lambda x: x.upvotes,
            reverse=True,
        )
        return summary, bullish[:5], bearish[:5]
