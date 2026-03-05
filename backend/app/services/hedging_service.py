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

# ── Advanced multi-leg strategy definitions ───────────────────────────────────
# annual_cost_pct: total annual drag of holding the hedge (premiums + carry)
# put_cost_pct:    annual cost of the protective put leg
# call_credit_pct: annual premium received from the short call leg (collar)
# etf_cost_pct:    expense ratio of inverse ETF leg
ADV_STRATEGIES: Dict[str, Dict] = {
    "unhedged": {
        "label": "Unhedged",
        "description": "No hedge — full exposure to the underlying.",
        "annual_cost_pct": 0.0,
    },
    "protective_put": {
        "label": "Protective Put",
        "description": "Buy an ATM put for downside protection. ~2% annual premium drag.",
        "annual_cost_pct": 0.02,
        "put_cost_pct": 0.02,
    },
    "collar": {
        "label": "Collar",
        "description": (
            "Long stock + long OTM put (5% below spot) + short OTM call (5% above spot). "
            "Put premium partially offset by call premium received. ~1% net cost."
        ),
        "annual_cost_pct": 0.01,   # net: put ~2% minus call credit ~1%
        "put_cost_pct": 0.02,
        "call_credit_pct": 0.01,
        "put_strike_pct": 0.95,    # 5% OTM put
        "call_strike_pct": 1.05,   # 5% OTM call (caps upside)
    },
    "stock_put_etf": {
        "label": "Put + Inverse ETF",
        "description": (
            "Dual-layer hedge: protective put for tail risk + 25% allocation to SH "
            "(inverse ETF) for continuous beta offset. ~3% total annual drag."
        ),
        "annual_cost_pct": 0.03,
        "put_cost_pct": 0.02,
        "etf_cost_pct": 0.0089,
        "etf_weight": 0.25,        # fraction of portfolio in inverse ETF
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
    symbol_or_list: str,
    benchmarks: Optional[List[str]] = None,
    period: str = "1y",
) -> Dict:
    """
    Pearson correlation of daily returns between input and each benchmark.
    *symbol_or_list* can be a single symbol "AAPL" or a comma-separated list "AAPL,MSFT".

    Returns
    -------
    {
        "symbol": "AAPL,MSFT",
        "period": "1y",
        "correlations": {"SPY": 0.82, "QQQ": 0.88, ...}
    }
    """
    benchmarks = benchmarks or BENCHMARKS
    symbols = [s.strip().upper() for s in symbol_or_list.split(",") if s.strip()]
    
    if len(symbols) == 1:
        closes = _fetch_closes(symbols[0], period)
    else:
        # Simple equal-weighted portfolio returns
        all_returns = []
        for s in symbols:
            s_closes = _fetch_closes(s, period)
            if not s_closes.empty:
                all_returns.append(_daily_returns(s_closes))
        
        if not all_returns:
            return {"symbol": symbol_or_list, "period": period, "correlations": {}}
            
        combined_returns = pd.concat(all_returns, axis=1).dropna()
        closes = combined_returns.mean(axis=1) # Treat mean returns as portfolio returns proxy

    if closes.empty:
        return {"symbol": symbol_or_list, "period": period, "correlations": {}}

    input_ret = closes if len(symbols) > 1 else _daily_returns(closes)
    correlations: Dict[str, float] = {}

    for bm in benchmarks:
        bm_closes = _fetch_closes(bm, period)
        if bm_closes.empty:
            correlations[bm] = 0.0
            continue
        bm_ret = _daily_returns(bm_closes)
        # Align on common dates
        combined = pd.DataFrame({"inp": input_ret, "bm": bm_ret}).dropna()
        if len(combined) < 20:
            correlations[bm] = 0.0
            continue
        correlations[bm] = float(combined["inp"].corr(combined["bm"]))

    return {"symbol": symbol_or_list, "period": period, "correlations": correlations}


def compute_portfolio_beta(
    symbols: List[str],
    benchmark: str = "SPY",
    period: str = "1y",
) -> Dict:
    """
    Aggregates beta for a basket of symbols (equal-weighted).
    """
    betas = []
    for s in symbols:
        res = compute_beta(s, benchmark, period)
        betas.append(res["beta"])
    
    avg_beta = float(np.mean(betas)) if betas else 1.0
    return {
        "symbols": symbols,
        "benchmark": benchmark,
        "beta": round(avg_beta, 4),
        "individual_betas": {s: b for s, b in zip(symbols, betas)},
        "period": period
    }


def compute_intra_portfolio_correlation(
    symbols: List[str],
    period: str = "1y",
) -> Dict:
    """
    Returns a correlation matrix between all symbols in the list.
    Used to detect over-concentration/clusters.
    """
    if len(symbols) < 2:
        return {"matrix": {}, "symbols": symbols}
    
    returns_map = {}
    for s in symbols:
        closes = _fetch_closes(s, period)
        if not closes.empty:
            returns_map[s] = _daily_returns(closes)
            
    if not returns_map:
        return {"matrix": {}, "symbols": symbols}
        
    df = pd.DataFrame(returns_map).dropna()
    if df.empty:
        return {"matrix": {}, "symbols": symbols}
        
    matrix = df.corr().to_dict()
    return {
        "matrix": matrix,
        "symbols": list(returns_map.keys()),
        "period": period
    }


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
    Orchestrator that returns the complete hedging analysis payload.
    Supports comma-separated symbols for portfolio analysis.
    """
    symbols = [s.strip().upper() for s in symbol.split(",") if s.strip()]
    is_portfolio = len(symbols) > 1

    # 1. Correlation matrix (vs benchmarks)
    corr = compute_correlation_matrix(symbol, period=period)
    
    # 1b. Intra-portfolio correlation
    intra_corr = None
    if is_portfolio:
        intra_corr = compute_intra_portfolio_correlation(symbols, period)

    # 2. Beta vs SPY
    if is_portfolio:
        beta_data = compute_portfolio_beta(symbols, "SPY", period)
    else:
        beta_data = compute_beta(symbols[0], "SPY", period)
    
    beta_val = beta_data["beta"]

    # 3. Hedge ratio
    spy_closes = _fetch_closes("SPY", "5d")
    hedge_price = float(spy_closes.iloc[-1]) if not spy_closes.empty else 450.0
    ratio = compute_hedge_ratio(beta_val, portfolio_value, hedge_price)

    # 4. Payoff scenarios
    payoff = compute_payoff(portfolio_value, hedge_type, beta_val)

    # 5. Cost estimate
    cost = estimate_hedge_cost(hedge_type, portfolio_value)

    return {
        "symbol": symbol,
        "is_portfolio": is_portfolio,
        "symbols": symbols,
        "hedge_type": hedge_type,
        "portfolio_value": portfolio_value,
        "period": period,
        "correlation": corr,
        "intra_portfolio_correlation": intra_corr,
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


# ── Advanced Multi-Leg Hedging (P2-HEDGE-ADV-01) ──────────────────────────────

def _simulate_strategy_equity_curve(
    stock_returns: pd.Series,
    spy_returns: pd.Series,
    strategy_key: str,
    initial_capital: float,
    beta: float,
) -> pd.Series:
    """
    Simulate a daily equity curve for one strategy given realised daily returns.
    Returns a Series indexed by date with portfolio value.
    """
    cfg = ADV_STRATEGIES.get(strategy_key, ADV_STRATEGIES["unhedged"])
    daily_cost = cfg["annual_cost_pct"] / 252

    aligned = pd.DataFrame({"stock": stock_returns, "spy": spy_returns}).dropna()
    portfolio_value = initial_capital
    curve: List[Dict] = []

    for date, row in aligned.iterrows():
        r = float(row["stock"])
        spy_r = float(row["spy"])

        if strategy_key == "unhedged":
            daily_return = r

        elif strategy_key == "protective_put":
            # Put absorbs ~80% of downside; full upside minus daily premium drag
            if r < 0:
                daily_return = r * 0.20  # put absorbs ~80% of losses
            else:
                daily_return = r
            daily_return -= daily_cost

        elif strategy_key == "collar":
            put_strike_pct = cfg.get("put_strike_pct", 0.95)  # 5% OTM
            call_strike_pct = cfg.get("call_strike_pct", 1.05)  # 5% OTM
            # Put protection: kicks in below ~5% loss threshold
            if r < -(1 - put_strike_pct):
                protected_r = -(1 - put_strike_pct)
            else:
                protected_r = r
            # Call cap: surrenders upside above ~5% gain
            if protected_r > (call_strike_pct - 1):
                daily_return = (call_strike_pct - 1)
            else:
                daily_return = protected_r
            daily_return -= daily_cost

        elif strategy_key == "stock_put_etf":
            etf_w = cfg.get("etf_weight", 0.25)
            stock_w = 1.0 - etf_w
            # ETF leg provides inverse SPY return scaled by weight
            etf_r = -spy_r * abs(beta)  # simplified inverse ETF return
            # Put leg absorbs residual tail: ~60% of downside after ETF
            if r < 0:
                stock_leg = r * 0.40  # put absorbs ~60% after ETF offset
            else:
                stock_leg = r
            daily_return = stock_w * stock_leg + etf_w * etf_r
            daily_return -= daily_cost

        else:
            daily_return = r

        portfolio_value *= (1 + daily_return)
        portfolio_value = max(portfolio_value, 0.0)
        curve.append({"date": str(date.date()), "value": round(portfolio_value, 2)})

    return curve


def _compute_drawdown_stats(curve: List[Dict]) -> Dict:
    """Compute max drawdown and total return from an equity curve list."""
    if not curve:
        return {"max_drawdown_pct": 0.0, "total_return_pct": 0.0}

    values = [c["value"] for c in curve]
    initial = values[0]
    final = values[-1]
    total_return_pct = round((final / initial - 1) * 100, 2) if initial > 0 else 0.0

    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return {
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_return_pct": total_return_pct,
    }


def compute_advanced_hedge(
    symbol: str,
    portfolio_value: float = 10_000,
    period: str = "1y",
    strategies: Optional[List[str]] = None,
) -> Dict:
    """
    Multi-leg hedging analysis (P2-HEDGE-ADV-01).

    Runs all requested strategies over actual historical returns and returns:
    - Equity curves for each strategy
    - Summary comparison table (max drawdown, total return, cost)
    - Payoff table across scenario returns
    """
    if strategies is None:
        strategies = ["unhedged", "protective_put", "collar", "stock_put_etf"]

    symbol = symbol.upper()
    stock_closes = _fetch_closes(symbol, period)
    spy_closes = _fetch_closes("SPY", period)

    if stock_closes.empty:
        return {
            "symbol": symbol,
            "error": f"No price data found for {symbol}.",
        }

    stock_ret = _daily_returns(stock_closes)
    spy_ret = _daily_returns(spy_closes) if not spy_closes.empty else pd.Series(0.0, index=stock_ret.index)

    # Beta
    beta_data = compute_beta(symbol, "SPY", period)
    beta = beta_data["beta"]

    # Run each strategy
    equity_curves: Dict[str, List] = {}
    summary_rows: List[Dict] = []

    for strat_key in strategies:
        if strat_key not in ADV_STRATEGIES:
            continue
        cfg = ADV_STRATEGIES[strat_key]
        curve = _simulate_strategy_equity_curve(
            stock_ret, spy_ret, strat_key, portfolio_value, beta
        )
        equity_curves[strat_key] = curve
        stats = _compute_drawdown_stats(curve)
        annual_cost_pct = cfg["annual_cost_pct"]
        summary_rows.append({
            "strategy": strat_key,
            "label": cfg["label"],
            "description": cfg["description"],
            "total_return_pct": stats["total_return_pct"],
            "max_drawdown_pct": stats["max_drawdown_pct"],
            "annual_cost_pct": round(annual_cost_pct * 100, 2),
            "annual_cost_usd": round(portfolio_value * annual_cost_pct, 2),
        })

    # Scenario payoff comparison (static scenarios across strategies)
    scenario_returns = [r / 100 for r in range(-40, 45, 5)]
    payoff_comparison: List[Dict] = []
    for ret in scenario_returns:
        row: Dict = {"return_pct": round(ret * 100, 1)}
        for strat_key in strategies:
            if strat_key not in ADV_STRATEGIES:
                continue
            cfg = ADV_STRATEGIES[strat_key]
            cost = cfg["annual_cost_pct"]
            if strat_key == "unhedged":
                final = portfolio_value * (1 + ret)
            elif strat_key == "protective_put":
                if ret < 0:
                    final = portfolio_value * (1 + ret * 0.20) - portfolio_value * cost
                else:
                    final = portfolio_value * (1 + ret) - portfolio_value * cost
            elif strat_key == "collar":
                put_floor = -(1 - cfg.get("put_strike_pct", 0.95))
                call_cap = cfg.get("call_strike_pct", 1.05) - 1
                capped_ret = min(max(ret, put_floor), call_cap)
                final = portfolio_value * (1 + capped_ret) - portfolio_value * cost
            elif strat_key == "stock_put_etf":
                etf_w = cfg.get("etf_weight", 0.25)
                stock_w = 1.0 - etf_w
                etf_r = -ret * abs(beta)
                if ret < 0:
                    stock_leg = ret * 0.40
                else:
                    stock_leg = ret
                final = portfolio_value * (stock_w * (1 + stock_leg) + etf_w * (1 + etf_r)) - portfolio_value * cost
            else:
                final = portfolio_value * (1 + ret)
            row[strat_key] = round(max(final, 0), 2)
        payoff_comparison.append(row)

    return {
        "symbol": symbol,
        "portfolio_value": portfolio_value,
        "period": period,
        "beta": beta_data,
        "strategies": strategies,
        "strategy_definitions": [
            {
                "key": k,
                "label": ADV_STRATEGIES[k]["label"],
                "description": ADV_STRATEGIES[k]["description"],
                "annual_cost_pct": round(ADV_STRATEGIES[k]["annual_cost_pct"] * 100, 2),
            }
            for k in strategies if k in ADV_STRATEGIES
        ],
        "equity_curves": equity_curves,
        "summary": summary_rows,
        "payoff_comparison": payoff_comparison,
        "disclaimer": (
            "Educational simulation only. Multi-leg options pricing is simplified and "
            "does not reflect real bid-ask spreads, liquidity, margin requirements, or "
            "assignment risk. Consult a licensed advisor before implementing any hedge."
        ),
    }
