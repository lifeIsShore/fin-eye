"""
app/api/v1/endpoints/shorts.py
───────────────────────────────────────────────────────────────────────────────
EXP-SHORT-01 — Short Interest & Squeeze Risk endpoints

Routes:
  GET /shorts/{symbol}          — full analysis (short metrics + squeeze score + trend)
  GET /shorts/{symbol}/summary  — lightweight headline card (score + key stats)
  GET /shorts/{symbol}/trend    — FINRA daily short volume trend only

All routes:
  - No auth required
  - CPU-bound work in thread pool
  - 4-hour in-process cache inside short_service
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.short_service import (
    ShortAnalysis,
    ShortVolumeDay,
    SqueezeScore,
    analyse_short_interest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class ShortVolumeDayDto(BaseModel):
    date: str
    short_volume: int
    total_volume: int
    short_volume_ratio: float


class SqueezeScoreDto(BaseModel):
    score: float
    label: str
    drivers: List[str]


class ShortAnalysisDto(BaseModel):
    symbol: str
    company_name: str
    shares_short: Optional[int]
    short_float_pct: Optional[float]
    short_ratio: Optional[float]
    float_shares: Optional[int]
    shares_outstanding: Optional[int]
    borrow_fee_rate: Optional[float]
    current_price: Optional[float]
    price_52w_high: Optional[float]
    price_52w_low: Optional[float]
    pct_from_52w_high: Optional[float]
    avg_volume_10d: Optional[int]
    short_volume_trend: List[ShortVolumeDayDto]
    trend_direction: str
    squeeze_score: SqueezeScoreDto
    disclaimer: str


class ShortSummaryDto(BaseModel):
    symbol: str
    company_name: str
    squeeze_score: float
    squeeze_label: str
    short_float_pct: Optional[float]
    short_ratio: Optional[float]
    borrow_fee_rate: Optional[float]
    trend_direction: str
    disclaimer: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _day_to_dto(d: ShortVolumeDay) -> ShortVolumeDayDto:
    return ShortVolumeDayDto(**d.__dict__)


def _score_to_dto(s: SqueezeScore) -> SqueezeScoreDto:
    return SqueezeScoreDto(**s.__dict__)


def _analysis_to_dto(a: ShortAnalysis) -> ShortAnalysisDto:
    return ShortAnalysisDto(
        symbol=a.symbol,
        company_name=a.company_name,
        shares_short=a.shares_short,
        short_float_pct=a.short_float_pct,
        short_ratio=a.short_ratio,
        float_shares=a.float_shares,
        shares_outstanding=a.shares_outstanding,
        borrow_fee_rate=a.borrow_fee_rate,
        current_price=a.current_price,
        price_52w_high=a.price_52w_high,
        price_52w_low=a.price_52w_low,
        pct_from_52w_high=a.pct_from_52w_high,
        avg_volume_10d=a.avg_volume_10d,
        short_volume_trend=[_day_to_dto(d) for d in a.short_volume_trend],
        trend_direction=a.trend_direction,
        squeeze_score=_score_to_dto(a.squeeze_score),
        disclaimer=a.disclaimer,
    )


async def _fetch(symbol: str) -> ShortAnalysis:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_short_interest, symbol.upper())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Short analysis failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Short interest data temporarily unavailable for {symbol}: {exc}",
        ) from exc


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}",
    response_model=ShortAnalysisDto,
    summary="Full short interest analysis — metrics, squeeze score, and FINRA trend",
)
async def get_short_analysis(symbol: str) -> ShortAnalysisDto:
    """
    Returns full short interest analysis for a US-listed symbol including:

    - **Short float %**: percentage of float shares that are currently sold short.
    - **Days-to-cover (short ratio)**: short interest divided by average daily volume —
      how many days it would take shorts to cover at normal trading pace.
    - **Borrow fee rate**: annualised cost to borrow the stock (when available from Yahoo Finance).
    - **FINRA short volume trend**: last 5 available daily REGSHO settlement readings,
      showing short volume as a % of total volume.
    - **Squeeze score** (0–100): composite risk of a short squeeze driven by short float,
      days-to-cover, distance from 52w high, trend direction, and borrow fee.

    Data from Yahoo Finance (via yfinance) + FINRA REGSHO daily files. Cached 4 hours.
    """
    analysis = await _fetch(symbol)
    return _analysis_to_dto(analysis)


@router.get(
    "/{symbol}/summary",
    response_model=ShortSummaryDto,
    summary="Lightweight short interest headline card",
)
async def get_short_summary(symbol: str) -> ShortSummaryDto:
    """
    Returns just the headline short interest signals — ideal for embedding
    in the main dashboard or a watchlist widget.
    """
    analysis = await _fetch(symbol)
    return ShortSummaryDto(
        symbol=analysis.symbol,
        company_name=analysis.company_name,
        squeeze_score=analysis.squeeze_score.score,
        squeeze_label=analysis.squeeze_score.label,
        short_float_pct=analysis.short_float_pct,
        short_ratio=analysis.short_ratio,
        borrow_fee_rate=analysis.borrow_fee_rate,
        trend_direction=analysis.trend_direction,
        disclaimer=analysis.disclaimer,
    )


@router.get(
    "/{symbol}/trend",
    response_model=List[ShortVolumeDayDto],
    summary="FINRA daily short volume trend (last 5 trading days)",
)
async def get_short_trend(symbol: str) -> List[ShortVolumeDayDto]:
    """
    Returns the last 5 available FINRA REGSHO daily short volume readings,
    newest first. Short volume ratio = short volume / total FINRA-reported volume.
    Note: FINRA volume excludes some dark pool and off-exchange prints.
    """
    analysis = await _fetch(symbol)
    return [_day_to_dto(d) for d in analysis.short_volume_trend]
