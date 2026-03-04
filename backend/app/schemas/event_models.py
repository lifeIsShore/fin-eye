from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MarketEvent(BaseModel):
    id: str
    date: str  # e.g. "2026-03-05" or full ISO 8601
    time: Optional[str] = None
    title: str
    description: Optional[str] = None
    impact: str  # Expected values: "Low", "Medium", "High"
    country: str # e.g. "US", "EU", "CN", "UK"
    actual: Optional[str] = None
    estimate: Optional[str] = None
    previous: Optional[str] = None

class EventResponse(BaseModel):
    events: List[MarketEvent]
