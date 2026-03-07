"""
app/api/v1/endpoints/fed_policy.py
───────────────────────────────────────────────────────────────────────────────
EXP-MACRO-ADV-02 — Fed Policy Visualiser endpoints

Routes:
  GET /fed-policy            — full Fed policy snapshot
  GET /fed-policy/dot-plot   — SEP dot plot projections only
  GET /fed-policy/rates      — historical target range + effective rate only
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.fed_policy_service import (
    DotPlotProjection,
    FedPolicySnapshot,
    ForwardExpectation,
    RatePoint,
    RateRange,
    analyse_fed_policy,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RatePointDto(BaseModel):
    date: str
    value: float


class RateRangeDto(BaseModel):
    date: str
    lower: float
    upper: float
    midpoint: float


class DotPlotProjectionDto(BaseModel):
    year: str
    median_rate: float
    as_of_label: str


class ForwardExpectationDto(BaseModel):
    label: str
    implied_rate: float
    source: str


class FedPolicyDto(BaseModel):
    current_target_lower: float
    current_target_upper: float
    current_midpoint: float
    current_effective_rate: Optional[float]
    target_range_history: List[RateRangeDto]
    effective_rate_history: List[RatePointDto]
    balance_sheet_history: List[RatePointDto]
    current_balance_sheet_b: Optional[float]
    reverse_repo_history: List[RatePointDto]
    current_reverse_repo_b: Optional[float]
    sofr_history: List[RatePointDto]
    forward_expectations: List[ForwardExpectationDto]
    dot_plot: List[DotPlotProjectionDto]
    hike_or_cut_trend: str
    total_moves_ytd: int
    disclaimer: str


class FedRatesOnlyDto(BaseModel):
    current_target_lower: float
    current_target_upper: float
    current_midpoint: float
    current_effective_rate: Optional[float]
    target_range_history: List[RateRangeDto]
    effective_rate_history: List[RatePointDto]
    hike_or_cut_trend: str
    total_moves_ytd: int


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_dto(s: FedPolicySnapshot) -> FedPolicyDto:
    return FedPolicyDto(
        current_target_lower=s.current_target_lower,
        current_target_upper=s.current_target_upper,
        current_midpoint=s.current_midpoint,
        current_effective_rate=s.current_effective_rate,
        target_range_history=[RateRangeDto(**r.__dict__) for r in s.target_range_history],
        effective_rate_history=[RatePointDto(**p.__dict__) for p in s.effective_rate_history],
        balance_sheet_history=[RatePointDto(**p.__dict__) for p in s.balance_sheet_history],
        current_balance_sheet_b=s.current_balance_sheet_b,
        reverse_repo_history=[RatePointDto(**p.__dict__) for p in s.reverse_repo_history],
        current_reverse_repo_b=s.current_reverse_repo_b,
        sofr_history=[RatePointDto(**p.__dict__) for p in s.sofr_history],
        forward_expectations=[ForwardExpectationDto(**f.__dict__) for f in s.forward_expectations],
        dot_plot=[DotPlotProjectionDto(**d.__dict__) for d in s.dot_plot],
        hike_or_cut_trend=s.hike_or_cut_trend,
        total_moves_ytd=s.total_moves_ytd,
        disclaimer=s.disclaimer,
    )


async def _fetch() -> FedPolicySnapshot:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_fed_policy)
    except Exception as exc:
        logger.error("Fed policy analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fed policy data temporarily unavailable: {exc}",
        ) from exc


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=FedPolicyDto,
    summary="Full Fed policy snapshot — target range, balance sheet, dot plot, forward expectations",
)
async def get_fed_policy() -> FedPolicyDto:
    """
    Returns the full Federal Reserve policy picture:

    - **Target range history** (3 years): DFEDTARL + DFEDTARU daily lower/upper bounds.
    - **Effective Fed Funds Rate** (DFF): daily, 3 years.
    - **SOFR**: Secured Overnight Financing Rate daily history.
    - **Balance sheet** (WALCL): weekly Fed total assets in USD billions.
    - **Reverse repo** (RRPONTSYD): overnight RRP facility usage, daily.
    - **Forward expectations**: Treasury yield proxies at 3m/1y/2y horizons.
    - **Dot plot** (SEP): FOMC median rate projections for 2025/2026/2027 and longer run.
    - **Hike/cut trend**: derived from 12-month delta in target midpoint.

    Data from FRED (Federal Reserve Economic Data). Cached 3 hours.
    Dot plot updated manually each FOMC meeting quarter.
    """
    snapshot = await _fetch()
    return _to_dto(snapshot)


@router.get(
    "/dot-plot",
    response_model=List[DotPlotProjectionDto],
    summary="FOMC SEP dot plot median projections",
)
async def get_dot_plot() -> List[DotPlotProjectionDto]:
    """
    Returns the FOMC participants' median rate projections from the most recent
    Summary of Economic Projections (SEP). Updated each FOMC meeting quarter.
    """
    snapshot = await _fetch()
    return [DotPlotProjectionDto(**d.__dict__) for d in snapshot.dot_plot]


@router.get(
    "/rates",
    response_model=FedRatesOnlyDto,
    summary="Historical Fed funds target range and effective rate",
)
async def get_fed_rates() -> FedRatesOnlyDto:
    """
    Lightweight endpoint — target range history and effective rate only.
    Useful for embedding a rate chart in a dashboard tile.
    """
    snapshot = await _fetch()
    return FedRatesOnlyDto(
        current_target_lower=snapshot.current_target_lower,
        current_target_upper=snapshot.current_target_upper,
        current_midpoint=snapshot.current_midpoint,
        current_effective_rate=snapshot.current_effective_rate,
        target_range_history=[RateRangeDto(**r.__dict__) for r in snapshot.target_range_history],
        effective_rate_history=[RatePointDto(**p.__dict__) for p in snapshot.effective_rate_history],
        hike_or_cut_trend=snapshot.hike_or_cut_trend,
        total_moves_ytd=snapshot.total_moves_ytd,
    )
