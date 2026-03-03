"""
Hedging Analysis Service (MVP-HEDGE-01)

Pure-Python functions for computing correlation, beta, hedge ratios,
payoff scenarios, and cost estimates.  Uses daily close prices from
Yahoo Finance via the existing OHLCVFetcher.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)

# ── Default benchmarks & hedge instruments ────────────────────────────────────

BENCHMARKS = ["SPY", "QQQ", "GLD", "TLT"]
HEDGE_INSTRUMENTS = {
    "protective_put": {
        "description": "Protective Put (synthetic – modelled as insurance)",
        "annual_cost_pct": 0.02,          # ~2% of notional per year
    },
    "inverse_etf": {
        "instrument": "SH",               # ProShares Short S&P 500
        "description": "Short Inverse ETF (SH)",
        "annual_cost_pct": 0.0089,         # 0.89% expense ratio
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fetch_closes(symbol: str, period: str = "1y") -> pd.Series:
    """Return a DatetimeIndex → Close Series for *symbol*."""
    records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval="1d")
    if not records:
        return pd.Series(dtype=float)
    df = pd.DataFrame([{"date": r.timestamp, "close": r.close} for r in records])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df["close"]


def _daily_returns(closes: pd.Series) -> pd.Series:
    return closes.pct_change().dropna()


# ── Public API ───────────────────────────────────────────────────────────────

def compute_correlation_matrix(
    symbol: str,
    benchmarks: Optional[List[str]] = None,
    period: str = "1y",
) -> Dict:
    """
    Pearson correlation of daily returns between *symbol* and each benchmark.

    Returns
    -------
    {
        "symbol": "AAPL",
        "period": "1y",
        "correlations": {"SPY": 0.82, "QQQ": 0.88, ...}
    }
    """
    benchmarks = benchmarks or BENCHMARKS
    symbol_closes = _fetch_closes(symbol, period)
    if symbol_closes.empty:
        return {"symbol": symbol, "period": period, "correlations": {}}

    sym_ret = _daily_returns(symbol_closes)
    correlations: Dict[str, float] = {}

    for bm in benchmarks:
        bm_closes = _fetch_closes(bm, period)
        if bm_closes.empty:
            correlations[bm] = 0.0
            continue
        bm_ret = _daily_returns(bm_closes)
        # Align on common dates
        combined = pd.DataFrame({"sym": sym_ret, "bm": bm_ret}).dropna()
        if len(combined) < 20:
            correlations[bm] = 0.0
            continue
        correlations[bm] = float(combined["sym"].corr(combined["bm"]))

    return {"symbol": symbol, "period": period, "correlations": correlations}


def compute_beta(
    symbol: str,
    benchmark: str = "SPY",
    period: str = "1y",
) -> Dict:
    """
    OLS beta of *symbol* vs *benchmark*.

    Returns
    -------
    {"symbol", "benchmark", "beta", "r_squared", "data_points"}
    """
    sym_closes = _fetch_closes(symbol, period)
    bm_closes = _fetch_closes(benchmark, period)
    if sym_closes.empty or bm_closes.empty:
        return {"symbol": symbol, "benchmark": benchmark, "beta": 1.0, "r_squared": 0.0, "data_points": 0}

    sym_ret = _daily_returns(sym_closes)
    bm_ret = _daily_returns(bm_closes)
    combined = pd.DataFrame({"sym": sym_ret, "bm": bm_ret}).dropna()

    if len(combined) < 20:
        return {"symbol": symbol, "benchmark": benchmark, "beta": 1.0, "r_squared": 0.0, "data_points": len(combined)}

    cov = np.cov(combined["sym"], combined["bm"])
    beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] != 0 else 1.0
    corr = float(combined["sym"].corr(combined["bm"]))
    r_squared = corr ** 2

    return {
        "symbol": symbol,
        "benchmark": benchmark,
        "beta": round(beta, 4),
        "r_squared": round(r_squared, 4),
        "data_points": len(combined),
    }


def compute_hedge_ratio(
    beta: float,
    portfolio_value: float,
    hedge_price: float,
) -> Dict:
    """
    Number of hedge instrument shares needed to neutralise beta exposure.

    hedge_units = (beta × portfolio_value) / hedge_price
    """
    if hedge_price <= 0:
        return {"hedge_units": 0, "notional": 0.0}
    units = round((abs(beta) * portfolio_value) / hedge_price)
    notional = round(units * hedge_price, 2)
    return {"hedge_units": units, "notional": notional}


def compute_payoff(
    portfolio_value: float,
    hedge_type: str,
    beta: float,
    scenarios: Optional[List[float]] = None,
) -> Dict:
    """
    Unhedged vs hedged portfolio value across a range of return scenarios.

    Parameters
    ----------
    scenarios : list of floats, e.g. [-0.30, -0.20, ..., 0.30]
    hedge_type : 'protective_put' or 'inverse_etf'
    beta : the symbol's beta vs SPY

    Returns
    -------
    {
        "scenarios": [
            {"return_pct": -30, "unhedged": 7000, "hedged": 8400},
            ...
        ]
    }
    """
    if scenarios is None:
        scenarios = [x / 100 for x in range(-30, 35, 5)]

    cost_pct = HEDGE_INSTRUMENTS.get(hedge_type, {}).get("annual_cost_pct", 0.02)
    hedge_cost = portfolio_value * cost_pct

    rows = []
    for ret in scenarios:
        unhedged = round(portfolio_value * (1 + ret), 2)

        if hedge_type == "protective_put":
            # Put limits downside: max loss = premium paid
            if ret < 0:
                hedged_gain = portfolio_value * ret * (1 - abs(beta) * 0.8)
            else:
                hedged_gain = portfolio_value * ret
            hedged = round(portfolio_value + hedged_gain - hedge_cost, 2)
        else:
            # Inverse ETF gains when market falls
            hedge_return = -ret * abs(beta)
            hedge_gain = portfolio_value * abs(beta) * hedge_return
            # Weight hedge at beta-adjusted ratio
            hedged = round(
                portfolio_value * (1 + ret) + hedge_gain * 0.5 - hedge_cost,
                2,
            )

        rows.append({
            "return_pct": round(ret * 100, 1),
            "unhedged": unhedged,
            "hedged": max(hedged, 0),
        })

    return {"scenarios": rows}


def estimate_hedge_cost(
    hedge_type: str,
    portfolio_value: float,
) -> Dict:
    """Approximate annual cost of the selected hedge strategy."""
    info = HEDGE_INSTRUMENTS.get(hedge_type)
    if not info:
        return {
            "hedge_type": hedge_type,
            "annual_cost_pct": 0.0,
            "annual_cost_usd": 0.0,
            "description": "Unknown hedge type",
        }
    cost_pct = info["annual_cost_pct"]
    return {
        "hedge_type": hedge_type,
        "annual_cost_pct": round(cost_pct * 100, 2),
        "annual_cost_usd": round(portfolio_value * cost_pct, 2),
        "description": info["description"],
    }


def get_full_hedge_analysis(
    symbol: str,
    hedge_type: str = "protective_put",
    portfolio_value: float = 10_000,
    period: str = "1y",
) -> Dict:
    """
    Orchestrator that returns the complete hedging analysis payload
    consumed by the `/hedge/{symbol}/analysis` endpoint.
    """
    # 1. Correlation matrix
    corr = compute_correlation_matrix(symbol, period=period)

    # 2. Beta vs SPY
    beta_data = compute_beta(symbol, "SPY", period)
    beta_val = beta_data["beta"]

    # 3. Hedge ratio (use SPY price as proxy for inverse-ETF price)
    spy_closes = _fetch_closes("SPY", "5d")
    hedge_price = float(spy_closes.iloc[-1]) if not spy_closes.empty else 450.0
    ratio = compute_hedge_ratio(beta_val, portfolio_value, hedge_price)

    # 4. Payoff scenarios
    payoff = compute_payoff(portfolio_value, hedge_type, beta_val)

    # 5. Cost estimate
    cost = estimate_hedge_cost(hedge_type, portfolio_value)

    return {
        "symbol": symbol,
        "hedge_type": hedge_type,
        "portfolio_value": portfolio_value,
        "period": period,
        "correlation": corr,
        "beta": beta_data,
        "hedge_ratio": ratio,
        "payoff": payoff,
        "cost": cost,
        "disclaimer": (
            "This is a simplified educational simulation, not investment advice. "
            "Actual hedging costs, slippage, and instrument behaviour may differ. "
            "Always consult a qualified advisor before implementing hedging strategies."
        ),
    }
