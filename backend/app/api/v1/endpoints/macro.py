"""
app/api/v1/endpoints/macro.py
Macro dashboard endpoints — fully async, typed responses.

Routes:
  GET  /macro/latest          — MVP core indicators + macro score (backward-compat)
  GET  /macro/advanced        — Full advanced view (P2-MACRO-ADV-01)
  GET  /macro/history/{name}  — Time-series for any single indicator
  POST /macro/refresh         — Trigger a full FRED refresh (admin / scheduler)
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.macro import get_history_async, get_latest_async, get_latest_batch_async
from app.db.database import get_db
from app.schemas.macro_models import (
    IndicatorHistoryResponse,
    IndicatorLatest,
    IndicatorPoint,
    LeadingIndicatorsDto,
    MacroAdvancedResponse,
    MacroLatestResponse,
    MacroScoreDto,
)
from app.services.macro_orchestrator import refresh_all_macro_indicators
from app.services.macro_scoring import (
    compute_macro_score,
    compute_macro_stress_index,
    compute_recession_risk,
    compute_yield_curve,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Indicator metadata ────────────────────────────────────────────────────────

_CORE_INDICATORS = [
    "fed_funds_rate",
    "unemployment_rate",
    "yield_spread_10y_2y",
    "cpi_yoy",
    "vix",
]

_ADVANCED_INDICATORS = [
    "treasury_2y",
    "treasury_5y",
    "treasury_10y",
    "treasury_30y",
    "recession_indicator",
    "nonfarm_payrolls",
    "industrial_production",
]


def _interpret(name: str, value: Optional[float]) -> str:
    if value is None:
        return "Data unavailable"
    match name:
        case "fed_funds_rate":
            if value > 5.0:   return "Rates highly restrictive"
            if value > 4.0:   return "Rates restrictive"
            if value < 1.0:   return "Rates very accommodative"
            return "Rates neutral"
        case "unemployment_rate":
            if value > 6.0:   return "Labour market weakening"
            if value < 3.5:   return "Labour market very tight"
            if value < 4.5:   return "Labour market healthy"
            return "Labour market balanced"
        case "yield_spread_10y_2y":
            if value < -0.5:  return "Yield curve deeply inverted — recession risk high"
            if value < 0:     return "Yield curve inverted — watch for slowdown"
            if value < 0.3:   return "Yield curve flat — growth uncertain"
            return "Yield curve normal"
        case "cpi_yoy":
            if value > 4.0:   return "Inflation high — policy restrictive"
            if value > 3.0:   return "Inflation above target"
            if value < 1.5:   return "Inflation below target"
            return "Inflation near target"
        case "vix":
            if value > 35:    return "Extreme market fear"
            if value > 25:    return "Elevated market fear"
            if value > 18:    return "Mildly elevated volatility"
            return "Market calm"
        case _:
            return "—"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _build_core_response(db: AsyncSession) -> tuple[MacroLatestResponse, dict[str, Optional[float]]]:
    """
    Fetch all core indicators and return (response_dto, indicator_value_dict).
    The value dict is passed to scoring functions to avoid re-querying.
    """
    rows = await get_latest_batch_async(db, _CORE_INDICATORS)
    data: dict[str, IndicatorLatest] = {}
    values: dict[str, Optional[float]] = {}

    for name in _CORE_INDICATORS:
        row = rows.get(name)
        val = row.value if row else None
        values[name] = val
        data[name] = IndicatorLatest(
            value=val,
            date=row.date.isoformat() if row and row.date else None,
            interpretation=_interpret(name, val),
        )

    macro_score: Optional[MacroScoreDto] = (
        compute_macro_score(values) if any(v is not None for v in values.values()) else None
    )
    return MacroLatestResponse(data=data, macro_score=macro_score), values


# ─────────────────────────────────────────────────────────────────────────────
# GET /latest  — MVP-compatible
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=MacroLatestResponse,
    summary="Core macro indicators + macro score",
)
async def get_latest(db: AsyncSession = Depends(get_db)) -> MacroLatestResponse:
    response, _ = await _build_core_response(db)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# GET /advanced  — P2-MACRO-ADV-01
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/advanced",
    response_model=MacroAdvancedResponse,
    summary="Full advanced macro dashboard — yield curve, recession risk, stress index",
)
async def get_advanced(db: AsyncSession = Depends(get_db)) -> MacroAdvancedResponse:
    # Core
    core_response, core_values = await _build_core_response(db)

    # Advanced indicators
    adv_rows = await get_latest_batch_async(db, _ADVANCED_INDICATORS)
    adv_values: dict[str, Optional[float]] = {
        name: (row.value if row else None)
        for name, row in adv_rows.items()
    }
    adv_dates: dict[str, Optional[str]] = {
        name: (row.date.isoformat() if row and row.date else None)
        for name, row in adv_rows.items()
    }

    # Merge all values for scoring (scoring functions accept a flat dict)
    all_values = {**core_values, **adv_values}

    # ── Compute NFP MoM if we have history ────────────────────────────────
    nfp_series = await get_history_async(db, "nonfarm_payrolls", limit=3)
    nfp_mom: Optional[float] = None
    if len(nfp_series) >= 2:
        nfp_mom = round(nfp_series[-1].value - nfp_series[-2].value, 1)
        all_values["nonfarm_payrolls_mom"] = nfp_mom

    # ── Industrial production YoY ──────────────────────────────────────────
    ip_series = await get_history_async(db, "industrial_production", limit=14)
    ip_yoy: Optional[float] = None
    if len(ip_series) >= 13:
        curr, prev = ip_series[-1].value, ip_series[-13].value
        if prev and prev != 0:
            ip_yoy = round((curr - prev) / abs(prev) * 100, 2)
            all_values["industrial_production_yoy"] = ip_yoy

    # ── Derived components ─────────────────────────────────────────────────
    yield_curve = compute_yield_curve(adv_values, adv_dates)
    recession = compute_recession_risk(all_values)
    stress_index = compute_macro_stress_index(all_values)

    # ── Leading indicators DTO ─────────────────────────────────────────────
    leading = LeadingIndicatorsDto(
        nonfarm_payrolls_latest=adv_values.get("nonfarm_payrolls"),
        nonfarm_payrolls_mom=nfp_mom,
        industrial_production_latest=adv_values.get("industrial_production"),
        industrial_production_yoy=ip_yoy,
    )

    return MacroAdvancedResponse(
        core=core_response,
        yield_curve=yield_curve,
        recession=recession,
        stress_index=stress_index,
        leading_indicators=leading,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /history/{indicator_name}
# ─────────────────────────────────────────────────────────────────────────────

_ALL_VALID_INDICATORS = set(_CORE_INDICATORS + _ADVANCED_INDICATORS)


@router.get(
    "/history/{indicator_name}",
    response_model=IndicatorHistoryResponse,
    summary="Historical time-series for any single indicator",
)
async def get_indicator_history(
    indicator_name: str,
    limit: int = Query(default=60, ge=1, le=365, description="Max number of data points"),
    db: AsyncSession = Depends(get_db),
) -> IndicatorHistoryResponse:
    if indicator_name not in _ALL_VALID_INDICATORS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown indicator '{indicator_name}'. Valid options: {sorted(_ALL_VALID_INDICATORS)}",
        )
    rows = await get_history_async(db, indicator_name, limit=limit)
    return IndicatorHistoryResponse(
        indicator_name=indicator_name,
        series=[IndicatorPoint(date=r.date.isoformat(), value=r.value) for r in rows],
        count=len(rows),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /refresh
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    summary="Trigger a full FRED + VIX data refresh (scheduler / admin)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_macro_data(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await refresh_all_macro_indicators(db)
    except Exception as exc:
        logger.error("Macro refresh failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return {"status": "accepted", "message": "Macro data refreshed successfully."}
