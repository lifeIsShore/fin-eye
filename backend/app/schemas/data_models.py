from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List


class OHLCVData(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MacroData(BaseModel):
    indicator_name: str
    value: float
    date: date


class NewsData(BaseModel):
    symbol: str
    title: str
    sentiment_score: Optional[float] = None
    source: Optional[str] = None
    published_at: datetime


class SentimentAggregateData(BaseModel):
    date: date
    sentiment_score: float
    mentions: int


class SentimentTimeseriesResponse(BaseModel):
    symbol: str
    series: List[SentimentAggregateData]
    sentiment_1d: Optional[float] = Field(default=None)
    sentiment_7d: Optional[float] = Field(default=None)
    sentiment_30d: Optional[float] = Field(default=None)
    articles: List[NewsData]


class SentimentSourceBreakdownEntry(BaseModel):
    source: str
    positive: int
    negative: int
    neutral: int


class SentimentSourceBreakdownResponse(BaseModel):
    symbol: str
    days: int
    breakdown: List[SentimentSourceBreakdownEntry]


class TechnicalFeatureRow(BaseModel):
    """
    Canonical per-timestamp feature vector for the technical ML layer.

    This captures a subset of the 25-feature set from the PRD, grouped into
    price/technical, sentiment, macro, and temporal dimensions.
    """

    # Identification
    symbol: str
    timestamp: datetime

    # Price / technical indicators
    return_1d: float
    return_5d: float
    volatility_20d: float
    rsi_14: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_middle: float
    bb_lower: float

    # Sentiment aggregates
    news_sentiment_1d: float
    news_sentiment_7d: float
    news_sentiment_30d: float
    news_source_diversity_30d: float  # e.g., effective number of distinct sources

    # Macro & volatility backdrop
    macro_score: float
    vix_level: float
    yield_spread_10y_2y: float

    # Temporal features
    day_of_week: int  # 0=Monday..6=Sunday
    month: int        # 1..12
    hour_of_day: int  # 0..23 (for intraday timeframes)

