from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SentimentComment(BaseModel):
    subreddit: str
    timestamp: datetime
    text: str
    sentiment_score: float
    sentiment_label: str  # e.g., "Positive", "Neutral", "Negative"
    upvotes: int
    url: str

class SentimentSummary(BaseModel):
    total_mentions: int
    percent_positive: float
    percent_neutral: float
    percent_negative: float
    retail_sentiment_score: float  # 0 to 100

class SentimentResponse(BaseModel):
    ticker: str
    summary: SentimentSummary
    top_bullish: List[SentimentComment]
    top_bearish: List[SentimentComment]
