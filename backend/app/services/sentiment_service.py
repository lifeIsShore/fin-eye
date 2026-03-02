import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.data_models import NewsData
from app.models.sentiment import NewsArticle, SentimentAggregate
from app.services.news_data import NewsFetcher

logger = logging.getLogger(__name__)

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
except ImportError:  # pragma: no cover - handled gracefully in runtime, tests will mock
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    pipeline = None


class FinBERTSentimentAnalyzer:
    """
    Lightweight wrapper around FinBERT sentiment model.

    If transformers/torch are not installed, this falls back to a neutral
    sentiment score of 0.0 so the rest of the pipeline can still run in
    development and tests can mock behaviour.
    """

    _pipeline = None

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return

        if pipeline is None:
            logger.warning(
                "transformers not available; FinBERTSentimentAnalyzer will "
                "return neutral scores (0.0). Install `transformers` and "
                "`torch` to enable real FinBERT scoring."
            )
            return

        logger.info("Loading FinBERT sentiment model...")
        model_name = "ProsusAI/finbert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._pipeline = pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            return_all_scores=False,
        )
        logger.info("FinBERT sentiment model loaded.")

    def score_text(self, text: str) -> float:
        """
        Return a numeric sentiment score in the range roughly -1..1.

        FinBERT labels: POSITIVE / NEGATIVE / NEUTRAL.
        We map: positive -> +score, negative -> -score, neutral -> 0.
        """
        if not text:
            return 0.0

        self._ensure_pipeline()
        if self._pipeline is None:
            # transformers not installed; neutral fallback
            return 0.0

        try:
            result = self._pipeline(text[:512])[0]  # type: ignore[index]
            label = result.get("label", "").lower()
            score = float(result.get("score", 0.0))

            if "positive" in label:
                return score
            if "negative" in label:
                return -score
            return 0.0
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"FinBERT scoring failed: {exc}")
            return 0.0


class SentimentService:
    """
    Orchestrates news fetching, FinBERT scoring and daily aggregation.

    This service supports MVP-SENT-01:
      - fetch recent news from Finnhub
      - score each article with FinBERT
      - aggregate daily sentiment over 1d/7d/30d windows
    """

    def __init__(
        self,
        db: Session,
        analyzer: Optional[FinBERTSentimentAnalyzer] = None,
        news_fetcher: Optional[NewsFetcher] = None,
    ):
        self.db = db
        self.analyzer = analyzer or FinBERTSentimentAnalyzer()
        self.news_fetcher = news_fetcher or NewsFetcher()

    async def refresh_symbol_sentiment(
        self,
        symbol: str,
        days_back: int = 30,
        max_per_day: int = 50,
    ) -> Tuple[List[NewsArticle], List[SentimentAggregate]]:
        """
        Fetch news for the symbol, score each article, persist articles and
        daily aggregates (source_type='news') for the last `days_back` days.
        """
        raw_news: List[NewsData] = await self.news_fetcher.fetch_recent_news(
            symbol=symbol,
            days_back=days_back,
        )

        if not raw_news:
            logger.info(f"No news returned for {symbol}")
            return [], []

        # Sort by published_at ascending for consistent behaviour
        raw_news.sort(key=lambda n: n.published_at)

        scored_articles: List[NewsArticle] = []
        daily_buckets: Dict[date, List[float]] = {}

        for item in raw_news:
            pub_date = item.published_at.date()

            # Respect max_per_day limit
            if (
                pub_date in daily_buckets
                and len(daily_buckets[pub_date]) >= max_per_day
            ):
                continue

            score = self.analyzer.score_text(item.title)
            item.sentiment_score = score

            # Upsert NewsArticle (avoid naive duplicates)
            existing_stmt = select(NewsArticle).where(
                NewsArticle.symbol == item.symbol,
                NewsArticle.title == item.title,
                NewsArticle.published_at == item.published_at,
            )
            existing = self.db.execute(existing_stmt).scalar_one_or_none()

            if existing:
                existing.sentiment_score = score
                news_record = existing
            else:
                news_record = NewsArticle(
                    symbol=item.symbol,
                    title=item.title,
                    source=item.source,
                    published_at=item.published_at,
                    sentiment_score=score,
                )
                self.db.add(news_record)

            scored_articles.append(news_record)

            if pub_date not in daily_buckets:
                daily_buckets[pub_date] = []
            daily_buckets[pub_date].append(score)

        # Persist daily aggregates
        aggregates: List[SentimentAggregate] = []
        for agg_date, scores in daily_buckets.items():
            if not scores:
                continue

            avg_score = sum(scores) / len(scores)
            mentions = len(scores)

            agg_stmt = select(SentimentAggregate).where(
                SentimentAggregate.symbol == symbol,
                SentimentAggregate.date == agg_date,
                SentimentAggregate.source_type == "news",
            )
            existing_agg = self.db.execute(agg_stmt).scalar_one_or_none()

            if existing_agg:
                existing_agg.sentiment_score = avg_score
                existing_agg.mentions = mentions
                aggregate_record = existing_agg
            else:
                aggregate_record = SentimentAggregate(
                    symbol=symbol,
                    date=agg_date,
                    mentions=mentions,
                    sentiment_score=avg_score,
                    source_type="news",
                )
                self.db.add(aggregate_record)

            aggregates.append(aggregate_record)

        self.db.commit()
        return scored_articles, aggregates

    def get_aggregated_sentiment(
        self,
        symbol: str,
        days: int = 30,
    ) -> List[SentimentAggregate]:
        """Return last `days` of news-based sentiment aggregates for a symbol."""
        cutoff = date.today() - timedelta(days=days)

        stmt = (
            select(SentimentAggregate)
            .where(
                SentimentAggregate.symbol == symbol,
                SentimentAggregate.source_type == "news",
                SentimentAggregate.date >= cutoff,
            )
            .order_by(SentimentAggregate.date.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def compute_window_averages(
        self,
        aggregates: List[SentimentAggregate],
    ) -> Dict[str, Optional[float]]:
        """
        Compute 1d, 7d, and 30d weighted averages (by mentions) from
        a list of SentimentAggregate rows.
        """
        if not aggregates:
            return {"1d": None, "7d": None, "30d": None}

        today = date.today()

        def avg_for_window(window_days: int) -> Optional[float]:
            start = today - timedelta(days=window_days - 1)
            window_points = [
                a for a in aggregates if start <= a.date <= today and a.mentions > 0
            ]
            if not window_points:
                return None

            total_weight = sum(a.mentions for a in window_points)
            if total_weight == 0:
                return None

            weighted_sum = sum((a.sentiment_score or 0.0) * a.mentions for a in window_points)
            return weighted_sum / total_weight

        return {
            "1d": avg_for_window(1),
            "7d": avg_for_window(7),
            "30d": avg_for_window(30),
        }

    def get_source_breakdown(
        self,
        symbol: str,
        days: int = 30,
        positive_threshold: float = 0.2,
        negative_threshold: float = -0.2,
    ) -> Dict[str, Dict[str, int]]:
        """
        Aggregate sentiment by news source over the last `days` days.

        Returns a mapping:
        {
          "Reuters": {"positive": 10, "negative": 3, "neutral": 7},
          "Bloomberg": {...},
        }
        """
        cutoff_dt = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(NewsArticle)
            .where(
                NewsArticle.symbol == symbol,
                NewsArticle.published_at >= cutoff_dt,
                NewsArticle.sentiment_score.is_not(None),
            )
        )
        rows: List[NewsArticle] = self.db.execute(stmt).scalars().all()

        breakdown: Dict[str, Dict[str, int]] = {}

        for row in rows:
            source = row.source or "Unknown"
            score = row.sentiment_score or 0.0

            if source not in breakdown:
                breakdown[source] = {"positive": 0, "negative": 0, "neutral": 0}

            if score >= positive_threshold:
                bucket = "positive"
            elif score <= negative_threshold:
                bucket = "negative"
            else:
                bucket = "neutral"

            breakdown[source][bucket] += 1

        return breakdown


