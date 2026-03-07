"""
app/api/v1/endpoints/adv_sentiment.py
───────────────────────────────────────────────────────────────────────────────
P3-SENT-ADV-01 — Advanced Sentiment endpoints

Routes:
  GET /adv-sentiment/{symbol}          — full analysis (Google Trends + StockTwits)
  GET /adv-sentiment/{symbol}/trends   — Google Trends data only
  GET /adv-sentiment/{symbol}/stocktwits — StockTwits snapshot only
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.adv_sentiment_service import (
    AdvancedSentimentAnalysis,
    GoogleTrendsData,
    RelatedQuery,
    StockTwitsMessage,
    StockTwitsSnapshot,
    TrendPoint,
    analyse_advanced_sentiment,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TrendPointDto(BaseModel):
    date: str
    interest: int


class RelatedQueryDto(BaseModel):
    query: str
    value: str


class GoogleTrendsDto(BaseModel):
    keyword: str
    timeframe: str
    interest_over_time: List[TrendPointDto]
    rising_queries: List[RelatedQueryDto]
    avg_interest: float
    peak_interest: int
    recent_vs_avg: float
    trend_direction: str


class StockTwitsMessageDto(BaseModel):
    username: str
    body: str
    sentiment: str
    likes: int
    created_at: str


class StockTwitsSnapshotDto(BaseModel):
    symbol: str
    total_messages: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    bullish_pct: float
    bearish_pct: float
    bull_bear_ratio: Optional[float]
    sentiment_label: str
    top_bullish: List[StockTwitsMessageDto]
    top_bearish: List[StockTwitsMessageDto]
    recent_messages: List[StockTwitsMessageDto]


class AdvancedSentimentDto(BaseModel):
    symbol: str
    google_trends: Optional[GoogleTrendsDto]
    stocktwits: Optional[StockTwitsSnapshotDto]
    composite_score: float
    composite_label: str
    disclaimer: str


# ─── Converters ──────────────────────────────────────────────────────────────

def _trends_to_dto(t: GoogleTrendsData) -> GoogleTrendsDto:
    return GoogleTrendsDto(
        keyword=t.keyword,
        timeframe=t.timeframe,
        interest_over_time=[TrendPointDto(date=p.date, interest=p.interest) for p in t.interest_over_time],
        rising_queries=[RelatedQueryDto(query=r.query, value=r.value) for r in t.rising_queries],
        avg_interest=t.avg_interest,
        peak_interest=t.peak_interest,
        recent_vs_avg=t.recent_vs_avg,
        trend_direction=t.trend_direction,
    )


def _msg_to_dto(m: StockTwitsMessage) -> StockTwitsMessageDto:
    return StockTwitsMessageDto(**m.__dict__)


def _twits_to_dto(s: StockTwitsSnapshot) -> StockTwitsSnapshotDto:
    return StockTwitsSnapshotDto(
        symbol=s.symbol,
        total_messages=s.total_messages,
        bullish_count=s.bullish_count,
        bearish_count=s.bearish_count,
        neutral_count=s.neutral_count,
        bullish_pct=s.bullish_pct,
        bearish_pct=s.bearish_pct,
        bull_bear_ratio=s.bull_bear_ratio,
        sentiment_label=s.sentiment_label,
        top_bullish=[_msg_to_dto(m) for m in s.top_bullish],
        top_bearish=[_msg_to_dto(m) for m in s.top_bearish],
        recent_messages=[_msg_to_dto(m) for m in s.recent_messages],
    )


def _to_dto(a: AdvancedSentimentAnalysis) -> AdvancedSentimentDto:
    return AdvancedSentimentDto(
        symbol=a.symbol,
        google_trends=_trends_to_dto(a.google_trends) if a.google_trends else None,
        stocktwits=_twits_to_dto(a.stocktwits) if a.stocktwits else None,
        composite_score=a.composite_score,
        composite_label=a.composite_label,
        disclaimer=a.disclaimer,
    )


async def _fetch(symbol: str) -> AdvancedSentimentAnalysis:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_advanced_sentiment, symbol.upper())
    except Exception as exc:
        logger.error("Advanced sentiment failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Advanced sentiment temporarily unavailable for {symbol}: {exc}",
        ) from exc


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}",
    response_model=AdvancedSentimentDto,
    summary="Full advanced sentiment — Google Trends + StockTwits composite",
)
async def get_advanced_sentiment(symbol: str) -> AdvancedSentimentDto:
    """
    Returns advanced sentiment analysis combining:
    - **Google Trends**: 90-day weekly interest-over-time, rising related queries,
      trend direction (Rising/Falling/Stable), and recent momentum vs average.
    - **StockTwits**: live bullish/bearish/neutral counts from the latest ~30 messages,
      bull/bear ratio, top-liked bullish and bearish messages, recent feed.
    - **Composite score** (0–100): weighted blend of StockTwits bullish ratio (60%)
      and Google Trends momentum (40%). 50 = neutral.

    Google Trends cached 4 hours (pytrends rate limits). StockTwits cached 15 minutes.
    No API key required.
    """
    result = await _fetch(symbol)
    return _to_dto(result)


@router.get(
    "/{symbol}/trends",
    response_model=Optional[GoogleTrendsDto],
    summary="Google Trends interest-over-time for a symbol",
)
async def get_trends(symbol: str) -> Optional[GoogleTrendsDto]:
    result = await _fetch(symbol)
    return _trends_to_dto(result.google_trends) if result.google_trends else None


@router.get(
    "/{symbol}/stocktwits",
    response_model=Optional[StockTwitsSnapshotDto],
    summary="StockTwits snapshot — live bullish/bearish ratio and message feed",
)
async def get_stocktwits(symbol: str) -> Optional[StockTwitsSnapshotDto]:
    result = await _fetch(symbol)
    return _twits_to_dto(result.stocktwits) if result.stocktwits else None
