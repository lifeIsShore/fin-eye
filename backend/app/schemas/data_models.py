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
