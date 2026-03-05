"""
Hedging API Endpoints (MVP-HEDGE-01)

GET /api/v1/hedge/{symbol}/analysis   – Full hedging analysis
GET /api/v1/hedge/{symbol}/correlation – Correlation matrix only
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.services.hedging_service import (
    compute_correlation_matrix,
    get_full_hedge_analysis,
    compute_advanced_hedge,
)

router = APIRouter()


@router.get("/{symbol}/analysis")
async def hedge_analysis(
    symbol: str,
    hedge_type: str = Query("protective_put", pattern="^(protective_put|inverse_etf)$"),
    portfolio_value: float = Query(10_000, ge=100, le=10_000_000),
    period: str = Query("1y", pattern="^(6mo|1y|2y|5y)$"),
):
    """
    Full hedging analysis for *symbol*.

    Returns correlation matrix, beta, hedge ratio, payoff scenarios,
    cost estimate, and an educational disclaimer.
    """
    result = get_full_hedge_analysis(
        symbol=symbol.upper(),
        hedge_type=hedge_type,
        portfolio_value=portfolio_value,
        period=period,
    )
    return result


@router.get("/{symbol}/advanced")
async def hedge_advanced(
    symbol: str,
    portfolio_value: float = Query(10_000, ge=100, le=10_000_000),
    period: str = Query("1y", pattern="^(6mo|1y|2y|5y)$"),
    strategies: str = Query(
        "unhedged,protective_put,collar,stock_put_etf",
        description="Comma-separated list of strategy keys to include",
    ),
):
    """
    Advanced multi-leg hedging analysis.
    Returns equity curves, summary comparison table, and scenario payoff
    across Unhedged / Protective Put / Collar / Put+Inverse ETF strategies.
    """
    strategy_list = [s.strip() for s in strategies.split(",") if s.strip()]
    return compute_advanced_hedge(
        symbol=symbol.upper(),
        portfolio_value=portfolio_value,
        period=period,
        strategies=strategy_list,
    )


@router.get("/{symbol}/correlation")
async def hedge_correlation(
    symbol: str,
    period: str = Query("1y", pattern="^(6mo|1y|2y|5y)$"),
):
    """Lightweight endpoint returning only the correlation matrix."""
    result = compute_correlation_matrix(symbol=symbol.upper(), period=period)
    return result
