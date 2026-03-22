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
    # Phase 5.1 — FinBERT label + confidence score
    sentiment_label: Optional[str] = None
    finbert_score: Optional[float] = None
    source: Optional[str] = None
    published_at: datetime
    # Phase 5.1 — URL for article click-through
    url: Optional[str] = None


class SentimentAggregateData(BaseModel):
    date: date
    sentiment_score: float
    mentions: int


class SentimentTimeseriesResponse(BaseModel):
    symbol: str
    series: List[SentimentAggregateData]
    sentiment_1d:  Optional[float] = Field(default=None)
    sentiment_7d:  Optional[float] = Field(default=None)
    sentiment_30d: Optional[float] = Field(default=None)
    articles:      List[NewsData]  = Field(default_factory=list)
    # Sprint 11 (UX-TRUST-01): ISO UTC timestamp of the most recent article
    # fetched, so the frontend FreshnessIndicator can show sentiment staleness.
    fetched_at: Optional[str] = Field(default=None)


class SentimentSourceBreakdownEntry(BaseModel):
    source: str
    positive: int
    negative: int
    neutral: int


class SentimentSourceBreakdownResponse(BaseModel):
    symbol: str
    days: int
    breakdown: List[SentimentSourceBreakdownEntry]
