from __future__ import annotations

import logging
import math

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.market import OHLCVDaily
from app.schemas.montecarlo_models import (
    MCAssetParams,
    MCSimulationResult,
    MCPortfolioParams,
    MCPortfolioResult,
)
from app.services.mc_engine import run_asset_simulation, run_portfolio_simulation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/asset", response_model=MCSimulationResult)
def run_asset_mc(params: MCAssetParams):
    """Run Monte Carlo simulation for a single asset."""
    try:
        if params.paths > 50000:
            raise HTTPException(status_code=400, detail="Maximum paths allowed is 50000")
        if params.years * params.steps_per_year > 3650:
            raise HTTPException(status_code=400, detail="Maximum time steps allowed is 3650")
        return run_asset_simulation(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio", response_model=MCPortfolioResult)
def run_portfolio_mc(params: MCPortfolioParams):
    """Simulate combined portfolio matrix with covariances and cash flows."""
    try:
        if params.paths > 50000:
            raise HTTPException(status_code=400, detail="Maximum paths allowed is 50000")
        if len(params.assets) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 assets allowed")
        if params.years * params.steps_per_year > 1200:
            raise HTTPException(status_code=400, detail="Maximum time steps allowed is 1200")
        return run_portfolio_simulation(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vol-estimate")
async def get_vol_estimate(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    days: int = Query(default=252, ge=30, le=1260, description="Lookback days"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Sprint 56 Phase 2 — Compute annualised volatility and drift from OHLCV history.
    Reads adj_close from ohlcv_daily table.
    Returns: symbol, annualized_vol_pct, annualized_return_pct, data_days.
    """
    sym = symbol.upper().strip()

    result = await db.execute(
        select(OHLCVDaily.trade_date, OHLCVDaily.adj_close)
        .where(OHLCVDaily.symbol == sym)
        .order_by(desc(OHLCVDaily.trade_date))
        .limit(days)
    )
    rows = result.all()

    if len(rows) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient OHLCV data for {sym} ({len(rows)} days found, need ≥30).",
        )

    closes = np.array([float(r.adj_close) for r in reversed(rows)])
    log_returns = np.diff(np.log(closes))

    sigma_annual = float(log_returns.std() * math.sqrt(252))
    mu_annual = float(log_returns.mean() * 252)

    return {
        "symbol": sym,
        "annualized_vol_pct": round(sigma_annual, 4),
        "annualized_return_pct": round(mu_annual, 4),
        "data_days": len(rows),
    }
