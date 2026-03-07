"""
app/api/v1/endpoints/earnings.py
───────────────────────────────────────────────────────────────────────────────
EXP-EARN-01 — Earnings Calendar & Surprise Tracker

Routes:
  GET /earnings/{symbol}           — full earnings analysis (history + upcoming + surprise score)
  GET /earnings/{symbol}/upcoming  — just the next earnings date card
  POST /earnings/calendar          — upcoming earnings for a list of tickers (watchlist-style)

All routes:
  - No auth required
  - CPU-bound yfinance work runs in thread pool (non-blocking asyncio)
  - 6-hour in-process cache inside earnings_service
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel

from app.services.earnings_service import (
    EarningsAnalysis,
    EarningsRecord,
    SurpriseScore,
    UpcomingEarnings,
    analyse_earnings,
    get_upcoming_calendar,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class EarningsRecordDto(BaseModel):
    period_label: str
    earnings_date: str
    eps_estimate: Optional[float]
    eps_actual: Optional[float]
    eps_surprise: Optional[float]
    eps_surprise_pct: Optional[float]
    revenue_estimate: Optional[float]
    revenue_actual: Optional[float]
    revenue_surprise_pct: Optional[float]
    beat_eps: Optional[bool]


class SurpriseScoreDto(BaseModel):
    score: float
    label: str
    quarters_beat: int
    quarters_missed: int
    quarters_inline: int
    avg_eps_surprise_pct: Optional[float]
    consecutive_beats: int


class UpcomingEarningsDto(BaseModel):
    symbol: str
    company_name: str
    earnings_date: str
    days_until: int
    eps_estimate: Optional[float]
    revenue_estimate: Optional[float]
    time_of_day: str


class EarningsAnalysisDto(BaseModel):
    symbol: str
    company_name: str
    history: List[EarningsRecordDto]
    upcoming: Optional[UpcomingEarningsDto]
    surprise_score: SurpriseScoreDto
    disclaimer: str


class CalendarRequest(BaseModel):
    symbols: List[str]
    days_ahead: int = 30


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _record_to_dto(r: EarningsRecord) -> EarningsRecordDto:
    return EarningsRecordDto(**r.__dict__)


def _upcoming_to_dto(u: UpcomingEarnings) -> UpcomingEarningsDto:
    return UpcomingEarningsDto(**u.__dict__)


def _score_to_dto(s: SurpriseScore) -> SurpriseScoreDto:
    return SurpriseScoreDto(**s.__dict__)


def _analysis_to_dto(a: EarningsAnalysis) -> EarningsAnalysisDto:
    return EarningsAnalysisDto(
        symbol=a.symbol,
        company_name=a.company_name,
        history=[_record_to_dto(r) for r in a.history],
        upcoming=_upcoming_to_dto(a.upcoming) if a.upcoming else None,
        surprise_score=_score_to_dto(a.surprise_score),
        disclaimer=a.disclaimer,
    )


async def _fetch(symbol: str) -> EarningsAnalysis:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_earnings, symbol.upper())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Earnings analysis failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Earnings data temporarily unavailable for {symbol}: {exc}",
        ) from exc


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}",
    response_model=EarningsAnalysisDto,
    summary="Full earnings analysis — history, upcoming date, and surprise score",
)
async def get_earnings_analysis(symbol: str) -> EarningsAnalysisDto:
    """
    Returns full earnings data for a US-listed symbol including:

    - **Earnings history** (up to 8 quarters): EPS estimate vs actual, surprise %,
      revenue actuals, beat/miss flag.
    - **Upcoming earnings**: next scheduled date, EPS estimate, days until event.
    - **Surprise score** (0–100): composite of last 4 quarters' EPS beat/miss
      magnitude and consistency. 50 = neutral / no data. > 60 = consistent beater.

    Data sourced from Yahoo Finance via yfinance. Cached 6 hours.
    Only US-listed securities are supported.
    """
    analysis = await _fetch(symbol)
    return _analysis_to_dto(analysis)


@router.get(
    "/{symbol}/upcoming",
    response_model=Optional[UpcomingEarningsDto],
    summary="Next earnings date card for a single symbol",
)
async def get_upcoming_earnings(symbol: str) -> Optional[UpcomingEarningsDto]:
    """
    Returns just the next earnings event — date, EPS estimate, days until.
    Returns null if no upcoming earnings are scheduled within Yahoo Finance's
    calendar window (~3 months ahead).
    """
    analysis = await _fetch(symbol)
    return _upcoming_to_dto(analysis.upcoming) if analysis.upcoming else None


@router.post(
    "/calendar",
    response_model=List[UpcomingEarningsDto],
    summary="Upcoming earnings calendar for a watchlist of symbols",
)
async def get_earnings_calendar(body: CalendarRequest) -> List[UpcomingEarningsDto]:
    """
    Returns all upcoming earnings events within `days_ahead` days for the
    provided list of symbols, sorted by date ascending.

    Maximum 30 symbols per request. Useful for a watchlist earnings widget
    or daily morning prep view.
    """
    if len(body.symbols) > 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 30 symbols per calendar request.",
        )
    if body.days_ahead < 1 or body.days_ahead > 90:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="days_ahead must be between 1 and 90.",
        )

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None,
        get_upcoming_calendar,
        body.symbols,
        body.days_ahead,
    )
    return [_upcoming_to_dto(u) for u in results]
