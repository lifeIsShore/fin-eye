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
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
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

async def _build_core_response(
    db: AsyncSession,
) -> tuple[MacroLatestResponse, dict[str, Optional[float]]]:
    """
    Fetch all core indicators and return (response_dto, indicator_value_dict).
    The value dict is passed to scoring functions to avoid re-querying.

    Sprint 10 (UX-TRUST-01): injects `fetched_at` as the most recent
    `date` field across all indicators, falling back to current UTC time.
    This lets the frontend FreshnessIndicator show how stale macro data is.
    """
    rows = await get_latest_batch_async(db, _CORE_INDICATORS)
    data: dict[str, IndicatorLatest] = {}
    values: dict[str, Optional[float]] = {}
    latest_date: Optional[str] = None

    for name in _CORE_INDICATORS:
        row = rows.get(name)
        val = row.value if row else None
        values[name] = val
        row_date = row.date.isoformat() if row and row.date else None
        data[name] = IndicatorLatest(
            value=val,
            date=row_date,
            interpretation=_interpret(name, val),
        )
        # Track the most recently updated indicator date for freshness
        if row_date and (latest_date is None or row_date > latest_date):
            latest_date = row_date

    macro_score: Optional[MacroScoreDto] = (
        compute_macro_score(values) if any(v is not None for v in values.values()) else None
    )

    # fetched_at: use the most recent indicator date, or current time as fallback
    # VIX updates daily so this is a good proxy for "when was macro last refreshed"
    fetched_at = latest_date or datetime.now(timezone.utc).isoformat()

    return MacroLatestResponse(
        data=data,
        macro_score=macro_score,
        fetched_at=fetched_at,
    ), values


# ─────────────────────────────────────────────────────────────────────────────
# GET /latest  — MVP-compatible
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=MacroLatestResponse,
    summary="Core macro indicators + macro score",
)
async def get_latest(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MacroLatestResponse:
    # Sprint 29 — Cache-Control: macro data refreshes hourly
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    result, _ = await _build_core_response(db)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /advanced  — P2-MACRO-ADV-01
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/advanced",
    response_model=MacroAdvancedResponse,
    summary="Full advanced macro dashboard — yield curve, recession risk, stress index",
)
async def get_advanced(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MacroAdvancedResponse:
    # Sprint 29 — Cache-Control: advanced macro is heavier, cache slightly longer
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=600"
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
    yield_curve  = compute_yield_curve(adv_values, adv_dates)
    recession    = compute_recession_risk(all_values)
    stress_index = compute_macro_stress_index(all_values)

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
            detail=(
                f"Unknown indicator '{indicator_name}'. "
                f"Valid options: {sorted(_ALL_VALID_INDICATORS)}"
            ),
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return {"status": "accepted", "message": "Macro data refreshed successfully."}


# ───────────────────────────────────────────────────────────────────────────────
# GET /fear-greed/cnn + /fear-greed/crypto  (Sprint 40)
# ───────────────────────────────────────────────────────────────────────────────

@router.get(
    "/fear-greed/cnn",
    summary="CNN Fear & Greed Index — latest reading (Sprint 40)",
)
async def get_cnn_fear_greed(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the most recently stored CNN Fear & Greed score from the
    `external_signals` table. Falls back to a live fetch on first call
    (before the hourly cron has populated the table).

    Response schema:
        score      float  0–100
        label      str    e.g. "Greed", "Extreme Fear"
        norm       float  0.0–1.0
        fetched_at str    ISO-8601 timestamp
        source     str    "cache" | "live"
    """
    from app.services.scrapers.cnn_fear_greed import CnnFearGreedFetcher  # noqa: PLC0415
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    fetcher = CnnFearGreedFetcher()
    cached  = await fetcher.get_latest(db)
    if cached:
        return {**cached, "source": "cache"}
    # First call before cron has run — fetch live and store
    result = await fetcher.fetch_and_store(db)
    if not result.get("stored"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CNN Fear & Greed index is temporarily unavailable.",
        )
    return {**result, "source": "live"}


@router.get(
    "/fear-greed/crypto",
    summary="Crypto Fear & Greed Index — latest reading (Sprint 40)",
)
async def get_crypto_fear_greed(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the most recently stored Crypto Fear & Greed score from the
    `external_signals` table (Alternative.me API). Falls back to live fetch
    on first call.

    Response schema:
        score      float  0–100
        label      str    e.g. "Fear", "Greed"
        norm       float  0.0–1.0
        fetched_at str    ISO-8601 timestamp
        source     str    "cache" | "live"
    """
    from app.services.scrapers.crypto_fear_greed import CryptoFearGreedFetcher  # noqa: PLC0415
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    fetcher = CryptoFearGreedFetcher()
    cached  = await fetcher.get_latest(db)
    if cached:
        return {**cached, "source": "cache"}
    result = await fetcher.fetch_and_store(db)
    if not result.get("stored"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Crypto Fear & Greed index is temporarily unavailable.",
        )
    return {**result, "source": "live"}


# ── Bond Ladder Builder (Sprint 54) ────────────────────────────────────────────

# Treasury yield series names as stored in the macro DB
_BOND_SERIES: list[tuple[str, str]] = [
    ("treasury_1m",  "1 month"),
    ("treasury_3m",  "3 months"),
    ("treasury_6m",  "6 months"),
    ("treasury_1y",  "1 year"),
    ("treasury_2y",  "2 years"),
    ("treasury_5y",  "5 years"),
    ("treasury_10y", "10 years"),
    ("treasury_30y", "30 years"),
]


@router.get("/bond-ladder", summary="Bond Ladder Builder — Sprint 54")
async def bond_ladder(
    total_investment: float = Query(default=10000.0, gt=0, description="Total amount to invest"),
    currency: str = Query(default="EUR", pattern="^[A-Z]{3}$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns a bond ladder allocation across 8 Treasury maturities.
    Reads latest yields from the macro DB (FRED data).
    Equal split across available maturities by default.
    """
    series_names = [s for s, _ in _BOND_SERIES]
    rows = await get_latest_batch_async(db, series_names)
    # rows is a dict: {name: IndicatorLatest | None}

    rungs = []
    available_labels = []
    for name, label in _BOND_SERIES:
        row = rows.get(name)
        if row and row.value is not None:
            available_labels.append((label, float(row.value)))

    if not available_labels:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Treasury yield data unavailable. Try again after next FRED refresh.",
        )

    n = len(available_labels)
    per_rung = round(total_investment / n, 2)

    total_income = 0.0
    for label, yield_pct in available_labels:
        annual_income = round(per_rung * (yield_pct / 100), 2)
        total_income += annual_income
        rungs.append({
            "maturity":     label,
            "yield_pct":    round(yield_pct, 4),
            "allocation":   per_rung,
            "annual_income": annual_income,
        })

    blended = round(sum(r["yield_pct"] for r in rungs) / n, 4) if n else 0.0

    # Yield curve shape
    if len(available_labels) >= 2:
        short_yield = available_labels[0][1]
        long_yield  = available_labels[-1][1]
        if long_yield > short_yield + 0.25:
            curve_shape = "Normal"
        elif long_yield < short_yield - 0.25:
            curve_shape = "Inverted"
        else:
            curve_shape = "Flat"
    else:
        curve_shape = "Unknown"

    return {
        "total_investment":   total_investment,
        "currency":           currency,
        "rungs":              rungs,
        "total_annual_income": round(total_income, 2),
        "blended_yield":      blended,
        "curve_shape":        curve_shape,
        "disclaimer":         "Treasury yields from FRED. For illustrative purposes only. Not financial advice.",
    }
