"""
app/api/v1/endpoints/risk.py

P3-RISK-01 — Scenario & Stress Testing API

Routes:
  GET  /risk/scenarios                          — list scenario library
  GET  /risk/scenarios/{scenario_id}            — get a single scenario definition
  GET  /risk/stress/{symbol}                    — stress-test a single stock
  POST /risk/stress/{symbol}/multi              — stress-test across all (or selected) scenarios
  POST /risk/portfolio/stress                   — portfolio-level stress test
  POST /risk/portfolio/stress/multi             — portfolio vs multiple scenarios
  POST /risk/custom                             — run a custom hypothetical shock
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.services.risk_service import (
    SCENARIO_LIBRARY,
    SCENARIO_MAP,
    PortfolioStressResult,
    PositionInput,
    StockStressResult,
    build_custom_scenario,
    stress_test_portfolio,
    stress_test_symbol,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    category: str
    start_date: Optional[str]
    end_date: Optional[str]
    macro_notes: str
    market_shocks: dict[str, float]


class StockStressResponse(BaseModel):
    symbol: str
    scenario_id: str
    scenario_name: str
    portfolio_value: float
    estimated_pnl: float
    estimated_pnl_pct: float
    beta_adjusted_pnl: float
    var_95: Optional[float]
    var_99: Optional[float]
    cvar_95: Optional[float]
    cvar_99: Optional[float]
    max_drawdown_historical: float
    annualised_vol: float
    beta_vs_spy: float
    macro_notes: str
    recovery_estimate_days: Optional[int]
    disclaimer: str = (
        "These figures are estimates based on historical data and beta-scaling. "
        "They are for educational purposes only and do not constitute investment advice. "
        "Actual outcomes may differ materially."
    )


class MultiScenarioStockResponse(BaseModel):
    symbol: str
    portfolio_value: float
    results: list[StockStressResponse]
    worst_scenario: Optional[str]
    best_scenario: Optional[str]


class PortfolioPosition(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    weight: float = Field(..., ge=0.0, le=1.0)
    value: float = Field(..., gt=0.0)

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.upper()


class PortfolioStressRequest(BaseModel):
    positions: list[PortfolioPosition] = Field(..., min_length=1, max_length=20)
    scenario_id: str


class PortfolioMultiStressRequest(BaseModel):
    positions: list[PortfolioPosition] = Field(..., min_length=1, max_length=20)
    scenario_ids: list[str] = Field(default=[], description="Empty = all scenarios")


class PortfolioStressResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    total_portfolio_value: float
    total_estimated_pnl: float
    total_estimated_pnl_pct: float
    positions: list[dict]
    portfolio_var_95: Optional[float]
    portfolio_var_99: Optional[float]
    portfolio_cvar_95: Optional[float]
    worst_position: Optional[str]
    best_position: Optional[str]
    macro_notes: str
    disclaimer: str = (
        "Portfolio stress results are estimated using historical beta and correlation data. "
        "For educational purposes only. Not investment advice."
    )


class CustomShockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    portfolio_value: float = Field(default=10_000.0, gt=0)
    name: str = Field(default="Custom Scenario", max_length=80)
    description: str = Field(default="", max_length=300)
    shocks: dict[str, float] = Field(
        ...,
        description="Per-ticker shock as decimal (e.g. {'SPY': -0.20} for -20%)",
    )

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.upper()


# ─── Helper ───────────────────────────────────────────────────────────────────

def _to_response(r: StockStressResult) -> StockStressResponse:
    return StockStressResponse(**r.__dict__)


def _portfolio_to_response(r: PortfolioStressResult) -> PortfolioStressResponse:
    return PortfolioStressResponse(**r.__dict__)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/scenarios", response_model=list[ScenarioSummary], summary="List all scenario definitions")
async def list_scenarios(
    category: Optional[str] = Query(None, description="Filter by category: historical|hypothetical|macro"),
) -> list[ScenarioSummary]:
    """
    Return the full scenario library.
    Optionally filter by category (`historical`, `hypothetical`, `macro`).
    """
    scenarios = SCENARIO_LIBRARY
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    return [
        ScenarioSummary(
            id=s.id,
            name=s.name,
            description=s.description,
            category=s.category,
            start_date=s.start_date,
            end_date=s.end_date,
            macro_notes=s.macro_notes,
            market_shocks=s.market_shocks,
        )
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioSummary, summary="Get a single scenario")
async def get_scenario(scenario_id: str) -> ScenarioSummary:
    s = SCENARIO_MAP.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return ScenarioSummary(
        id=s.id, name=s.name, description=s.description, category=s.category,
        start_date=s.start_date, end_date=s.end_date,
        macro_notes=s.macro_notes, market_shocks=s.market_shocks,
    )


@router.get("/stress/{symbol}", response_model=StockStressResponse, summary="Stress-test a single stock")
async def stress_stock(
    symbol: str,
    scenario_id: str = Query(..., description="Scenario ID from /risk/scenarios"),
    portfolio_value: float = Query(10_000.0, gt=0, le=10_000_000, description="$ value of position"),
) -> StockStressResponse:
    """
    Apply a named scenario to a single-stock position.
    Returns estimated P&L, VaR/CVaR, max drawdown, beta, and recovery estimate.
    """
    try:
        result = stress_test_symbol(symbol.upper(), scenario_id, portfolio_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stress test failed for %s", symbol)
        raise HTTPException(status_code=500, detail="Stress test computation failed.") from exc
    return _to_response(result)


@router.get(
    "/stress/{symbol}/multi",
    response_model=MultiScenarioStockResponse,
    summary="Stress-test a stock across multiple scenarios",
)
async def stress_stock_multi(
    symbol: str,
    portfolio_value: float = Query(10_000.0, gt=0, le=10_000_000),
    scenario_ids: str = Query(
        "",
        description="Comma-separated scenario IDs. Empty = all scenarios.",
    ),
) -> MultiScenarioStockResponse:
    """
    Run stress tests across all (or selected) scenarios for one symbol.
    Useful for generating a comparison table.
    """
    sym = symbol.upper()
    ids = [s.strip() for s in scenario_ids.split(",") if s.strip()] if scenario_ids else [s.id for s in SCENARIO_LIBRARY]

    results = []
    for sid in ids:
        try:
            r = stress_test_symbol(sym, sid, portfolio_value)
            results.append(_to_response(r))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping scenario %s for %s: %s", sid, sym, exc)

    if not results:
        raise HTTPException(status_code=422, detail="No valid scenarios could be computed.")

    worst = min(results, key=lambda r: r.estimated_pnl_pct).scenario_id
    best = max(results, key=lambda r: r.estimated_pnl_pct).scenario_id

    return MultiScenarioStockResponse(
        symbol=sym,
        portfolio_value=portfolio_value,
        results=results,
        worst_scenario=worst,
        best_scenario=best,
    )


@router.post(
    "/portfolio/stress",
    response_model=PortfolioStressResponse,
    summary="Portfolio-level stress test for a single scenario",
)
async def stress_portfolio(body: PortfolioStressRequest) -> PortfolioStressResponse:
    """
    Apply a named scenario to a multi-position portfolio.
    Returns total P&L, per-position impact, and aggregate VaR/CVaR.
    """
    positions = [PositionInput(symbol=p.symbol, weight=p.weight, value=p.value) for p in body.positions]
    try:
        result = stress_test_portfolio(positions, body.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Portfolio stress test failed")
        raise HTTPException(status_code=500, detail="Portfolio stress test failed.") from exc
    return _portfolio_to_response(result)


@router.post(
    "/portfolio/stress/multi",
    response_model=list[PortfolioStressResponse],
    summary="Portfolio stress test across multiple scenarios",
)
async def stress_portfolio_multi(body: PortfolioMultiStressRequest) -> list[PortfolioStressResponse]:
    """
    Run portfolio stress tests across all (or selected) scenarios.
    Returns a list of results — one per scenario.
    """
    positions = [PositionInput(symbol=p.symbol, weight=p.weight, value=p.value) for p in body.positions]
    ids = body.scenario_ids or [s.id for s in SCENARIO_LIBRARY]

    results = []
    for sid in ids:
        try:
            r = stress_test_portfolio(positions, sid)
            results.append(_portfolio_to_response(r))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping portfolio scenario %s: %s", sid, exc)

    if not results:
        raise HTTPException(status_code=422, detail="No valid scenarios could be computed.")
    return results


@router.post(
    "/custom",
    response_model=StockStressResponse,
    summary="Run a custom hypothetical shock on a single stock",
)
async def custom_shock(body: CustomShockRequest) -> StockStressResponse:
    """
    Define your own shock magnitudes per benchmark ticker and apply to a stock.
    Example: `{"shocks": {"SPY": -0.30, "QQQ": -0.40}}` models a 30% equity decline.
    """
    scenario = build_custom_scenario(
        shocks=body.shocks,
        name=body.name,
        description=body.description,
    )
    # Temporarily inject into map for this request
    SCENARIO_MAP["custom"] = scenario
    try:
        result = stress_test_symbol(body.symbol, "custom", body.portfolio_value)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        SCENARIO_MAP.pop("custom", None)
    return _to_response(result)
