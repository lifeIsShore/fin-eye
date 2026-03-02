from sqlalchemy import Column, Integer, String, Float, DateTime, Date, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    sentiment_score = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SentimentAggregate(Base):
    __tablename__ = "sentiment_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    mentions = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)
    source_type = Column(String, nullable=False) # e.g., 'news', 'twitter', 'reddit'

    __table_args__ = (
        UniqueConstraint('symbol', 'date', 'source_type', name='_symbol_date_source_uc'),
    )
