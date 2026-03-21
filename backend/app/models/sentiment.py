"""Extended news_articles columns for todos-v4.md Phase 5."""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date,
    Text, Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.db.database import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id              = Column(Integer, primary_key=True, index=True)
    symbol          = Column(String(20), nullable=False, index=True)
    title           = Column(String(500), nullable=False)
    # Phase 5.1 — URL stored for 1-click article inspection
    url             = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)   # VADER compound: -1 to +1
    # Phase 5.1 — FinBERT output: 'bullish', 'bearish', 'neutral'
    sentiment_label = Column(String(10), nullable=True)
    # Phase 5.1 — raw FinBERT confidence score
    finbert_score   = Column(Float, nullable=True)
    source          = Column(String(100), nullable=True)
    # Phase 5.1 — when this article was last fetched from Finnhub or scrapers
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    # Phase 5.1 — 'finnhub', 'scraped', 'manual'
    fetch_source    = Column(String(20), nullable=True, server_default="finnhub")
    published_at    = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Prevent duplicate articles (same title from same source on same day)
        UniqueConstraint("symbol", "title", "published_at", name="uq_news_symbol_title_ts"),
        # Fast per-ticker chronological lookups
        Index("idx_news_symbol_date", "symbol", "published_at"),
        # Cache freshness check: find stale articles for a given symbol
        Index("idx_news_last_fetched", "symbol", "last_fetched_at"),
    )


class SentimentAggregate(Base):
    __tablename__ = "sentiment_aggregates"

    id             = Column(Integer, primary_key=True, index=True)
    symbol         = Column(String(20), nullable=False, index=True)
    date           = Column(Date, nullable=False, index=True)
    mentions       = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)
    source_type    = Column(String(30), nullable=False)  # 'news', 'reddit', 'stocktwits'

    __table_args__ = (
        UniqueConstraint("symbol", "date", "source_type", name="_symbol_date_source_uc"),
    )
