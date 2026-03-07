"""
app/api/v1/endpoints/options.py
─────────────────────────────────────────────────────────────────────────────
EXP-OPT-01 — Options Fear & Greed endpoints

Routes:
  GET /options/{symbol}           — full analysis (PCR + IV Skew + Max Pain + FG score)
  GET /options/{symbol}/summary   — lightweight headline card (FG score + PCR label)
  GET /options/{symbol}/expiries  — per-expiry PCR breakdown table

All routes:
  - No auth required — options data is educational and public
  - CPU-bound yfinance call offloaded to thread pool executor so we
    never block the asyncio event loop
  - 15-min in-process cache inside options_service
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.options_service import OptionsAnalysis, OptionChainSummary, analyse_options

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class ExpiryBreakdownDto(BaseModel):
    expiry: str
    calls_oi: int
    puts_oi: int
    pcr: float
    total_call_volume: int
    total_put_volume: int
    max_pain_strike: Optional[float]


class OptionsAnalysisDto(BaseModel):
    symbol: str
    spot_price: float

    # Aggregate PCR
    total_calls_oi: int
    total_puts_oi: int
    aggregate_pcr: float
    pcr_label: str
    pcr_interpretation: str

    # IV skew
    iv_skew: Optional[float]
    iv_skew_label: str
    near_put_iv: Optional[float]
    near_call_iv: Optional[float]

    # Max pain
    max_pain_strike: Optional[float]
    max_pain_distance_pct: Optional[float]

    # Composite
    fear_greed_score: float
    fear_greed_label: str

    # Detail
    expiry_breakdown: List[ExpiryBreakdownDto]

    disclaimer: str


class OptionsSummaryDto(BaseModel):
    """Lightweight response for dashboard cards."""
    symbol: str
    spot_price: float
    fear_greed_score: float
    fear_greed_label: str
    aggregate_pcr: float
    pcr_label: str
    max_pain_strike: Optional[float]
    max_pain_distance_pct: Optional[float]
    disclaimer: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _chain_to_dto(c: OptionChainSummary) -> ExpiryBreakdownDto:
    return ExpiryBreakdownDto(
        expiry=c.expiry,
        calls_oi=c.calls_oi,
        puts_oi=c.puts_oi,
        pcr=c.pcr,
        total_call_volume=c.total_call_volume,
        total_put_volume=c.total_put_volume,
        max_pain_strike=c.max_pain_strike,
    )


def _analysis_to_dto(a: OptionsAnalysis) -> OptionsAnalysisDto:
    return OptionsAnalysisDto(
        symbol=a.symbol,
        spot_price=a.spot_price,
        total_calls_oi=a.total_calls_oi,
        total_puts_oi=a.total_puts_oi,
        aggregate_pcr=a.aggregate_pcr,
        pcr_label=a.pcr_label,
        pcr_interpretation=a.pcr_interpretation,
        iv_skew=a.iv_skew,
        iv_skew_label=a.iv_skew_label,
        near_put_iv=a.near_put_iv,
        near_call_iv=a.near_call_iv,
        max_pain_strike=a.max_pain_strike,
        max_pain_distance_pct=a.max_pain_distance_pct,
        fear_greed_score=a.fear_greed_score,
        fear_greed_label=a.fear_greed_label,
        expiry_breakdown=[_chain_to_dto(c) for c in a.expiry_breakdown],
        disclaimer=a.disclaimer,
    )


async def _fetch(symbol: str) -> OptionsAnalysis:
    """Run synchronous options analysis in the thread pool."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_options, symbol.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Options analysis failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Options data temporarily unavailable for {symbol}: {exc}",
        ) from exc


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}",
    response_model=OptionsAnalysisDto,
    summary="Full options analysis — PCR, IV Skew, Max Pain, Fear & Greed score",
)
async def get_options_analysis(symbol: str) -> OptionsAnalysisDto:
    """
    Returns the full options analysis for a symbol including:
    - Aggregate Put/Call Ratio across all available expiries
    - IV Skew (10% OTM put IV minus 10% OTM call IV, nearest expiry)
    - Max Pain strike for the nearest expiry
    - Options Fear & Greed Score (0–100)
    - Per-expiry PCR breakdown (up to 5 nearest expiries)

    Data is sourced from yfinance (15-min delayed) and cached for 15 minutes.
    """
    analysis = await _fetch(symbol)
    return _analysis_to_dto(analysis)


@router.get(
    "/{symbol}/summary",
    response_model=OptionsSummaryDto,
    summary="Lightweight options summary for dashboard cards",
)
async def get_options_summary(symbol: str) -> OptionsSummaryDto:
    """
    Returns just the headline signals — ideal for embedding in the main
    dashboard without loading the full expiry breakdown.
    """
    analysis = await _fetch(symbol)
    return OptionsSummaryDto(
        symbol=analysis.symbol,
        spot_price=analysis.spot_price,
        fear_greed_score=analysis.fear_greed_score,
        fear_greed_label=analysis.fear_greed_label,
        aggregate_pcr=analysis.aggregate_pcr,
        pcr_label=analysis.pcr_label,
        max_pain_strike=analysis.max_pain_strike,
        max_pain_distance_pct=analysis.max_pain_distance_pct,
        disclaimer=analysis.disclaimer,
    )


@router.get(
    "/{symbol}/expiries",
    response_model=List[ExpiryBreakdownDto],
    summary="Per-expiry PCR breakdown (up to 5 nearest expiries)",
)
async def get_options_expiries(symbol: str) -> List[ExpiryBreakdownDto]:
    """
    Returns the PCR and open interest breakdown for up to 5 nearest
    option expiries. Useful for seeing whether bearish positioning is
    concentrated in near-term or longer-dated contracts.
    """
    analysis = await _fetch(symbol)
    return [_chain_to_dto(c) for c in analysis.expiry_breakdown]
