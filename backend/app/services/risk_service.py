"""
app/services/risk_service.py

P3-RISK-01 — Scenario & Stress Testing engine.

Features:
  - Historical scenario library (2008 GFC, 2020 COVID, 2022 rate shock, dot-com, etc.)
  - Hypothetical shock scenarios (custom %-move on each asset)
  - Single-stock and portfolio-level stress computation
  - VaR / CVaR (95 & 99) from historical simulation
  - Max drawdown, beta-adjusted impact, recovery time estimate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ─── Scenario library ─────────────────────────────────────────────────────────

@dataclass
class Scenario:
    id: str
    name: str
    description: str
    category: str          # "historical" | "hypothetical" | "macro"
    # Market shocks: ticker -> % change (e.g. {"SPY": -0.55})
    market_shocks: dict[str, float]
    # Macro shocks (qualitative context)
    macro_notes: str = ""
    # Historical date range for context
    start_date: Optional[str] = None
    end_date: Optional[str] = None


SCENARIO_LIBRARY: list[Scenario] = [
    # ── Historical ────────────────────────────────────────────────────────────
    Scenario(
        id="gfc_2008",
        name="2008 Global Financial Crisis",
        category="historical",
        description=(
            "Lehman Brothers collapse triggered a systemic freeze in credit markets. "
            "S&P 500 fell ~57% peak-to-trough from Oct 2007 to Mar 2009."
        ),
        market_shocks={"SPY": -0.55, "QQQ": -0.52, "TLT": 0.26, "GLD": 0.05, "VIX_PROXY": 3.0},
        macro_notes="Fed Funds cut to 0–0.25%. TARP bailout. Unemployment peaked at 10%.",
        start_date="2008-09-01",
        end_date="2009-03-31",
    ),
    Scenario(
        id="covid_2020",
        name="2020 COVID-19 Crash",
        category="historical",
        description=(
            "Fastest bear market in history. S&P 500 fell ~34% in 33 days "
            "(Feb 19 – Mar 23, 2020), followed by an equally historic V-shaped recovery."
        ),
        market_shocks={"SPY": -0.34, "QQQ": -0.29, "TLT": 0.22, "GLD": -0.03, "VIX_PROXY": 4.5},
        macro_notes="Emergency Fed rate cut to 0%. $2.2T CARES Act. Global lockdowns.",
        start_date="2020-02-19",
        end_date="2020-03-23",
    ),
    Scenario(
        id="rate_shock_2022",
        name="2022 Rate Shock",
        category="historical",
        description=(
            "The Fed hiked rates 425bp in one year — the fastest tightening cycle since 1981. "
            "S&P 500 fell ~25%, bonds collapsed simultaneously (worst 60/40 year in decades)."
        ),
        market_shocks={"SPY": -0.25, "QQQ": -0.35, "TLT": -0.31, "GLD": -0.02, "VIX_PROXY": 1.5},
        macro_notes="CPI peaked at 9.1%. Fed hiked from 0.25% to 4.50%.",
        start_date="2022-01-01",
        end_date="2022-12-31",
    ),
    Scenario(
        id="dotcom_2000",
        name="Dot-Com Bust (2000–2002)",
        category="historical",
        description=(
            "Nasdaq fell ~78% peak-to-trough. S&P 500 lost ~49%. "
            "Tech valuations collapsed as the internet bubble burst."
        ),
        market_shocks={"SPY": -0.49, "QQQ": -0.78, "TLT": 0.33, "GLD": 0.12, "VIX_PROXY": 2.0},
        macro_notes="Fed cut rates from 6.5% to 1.75%. Widespread corporate scandals (Enron, WorldCom).",
        start_date="2000-03-10",
        end_date="2002-10-09",
    ),
    Scenario(
        id="black_monday_1987",
        name="Black Monday (Oct 1987)",
        category="historical",
        description=(
            "Dow Jones fell 22.6% in a single day — the largest one-day percentage drop in history. "
            "Caused by portfolio insurance feedback loops and overvaluation."
        ),
        market_shocks={"SPY": -0.34, "QQQ": -0.32, "TLT": 0.08, "GLD": 0.07, "VIX_PROXY": 5.0},
        macro_notes="Program trading and portfolio insurance amplified the crash.",
        start_date="1987-10-14",
        end_date="1987-10-19",
    ),
    # ── Hypothetical ─────────────────────────────────────────────────────────
    Scenario(
        id="mild_recession",
        name="Mild Recession",
        category="hypothetical",
        description=(
            "A garden-variety recession: GDP contracts 2 quarters, unemployment rises 2pp. "
            "Equities decline ~20%, investment-grade bonds hold up."
        ),
        market_shocks={"SPY": -0.20, "QQQ": -0.25, "TLT": 0.10, "GLD": 0.05, "VIX_PROXY": 1.8},
        macro_notes="Fed pauses, then cuts 100bp over 12 months.",
    ),
    Scenario(
        id="severe_recession",
        name="Severe Recession / Depression",
        category="hypothetical",
        description=(
            "A deep contraction comparable to 2008–2009. GDP falls 5%, "
            "unemployment spikes to 10%+, credit markets seize."
        ),
        market_shocks={"SPY": -0.50, "QQQ": -0.55, "TLT": 0.25, "GLD": 0.10, "VIX_PROXY": 3.5},
        macro_notes="Emergency Fed action. Possible fiscal stimulus. Credit spreads blow out.",
    ),
    Scenario(
        id="flash_crash",
        name="Flash Crash / Liquidity Crisis",
        category="hypothetical",
        description=(
            "A sudden, sharp market dislocation (similar to May 2010 flash crash or Aug 2015 China shock). "
            "Fast drop followed by partial recovery within days."
        ),
        market_shocks={"SPY": -0.10, "QQQ": -0.12, "TLT": 0.05, "GLD": 0.02, "VIX_PROXY": 2.5},
        macro_notes="Typically exogenous trigger (algo malfunction, geopolitical surprise).",
    ),
    Scenario(
        id="inflation_spike",
        name="Persistent Inflation Spike",
        category="macro",
        description=(
            "CPI remains above 6% for 12+ months, forcing the Fed to keep rates high. "
            "Growth stocks and long-duration bonds suffer most."
        ),
        market_shocks={"SPY": -0.15, "QQQ": -0.28, "TLT": -0.20, "GLD": 0.15, "VIX_PROXY": 1.2},
        macro_notes="Value / energy / commodities outperform. Duration risk is key.",
    ),
    Scenario(
        id="soft_landing",
        name="Soft Landing / Rally",
        category="hypothetical",
        description=(
            "Fed achieves a controlled disinflation without recession. "
            "Risk assets rally broadly. This is the bullish base case."
        ),
        market_shocks={"SPY": 0.15, "QQQ": 0.20, "TLT": 0.08, "GLD": -0.05, "VIX_PROXY": -0.3},
        macro_notes="Rate cuts begin, unemployment stays low, earnings grow.",
    ),
]

SCENARIO_MAP: dict[str, Scenario] = {s.id: s for s in SCENARIO_LIBRARY}


# ─── VaR / CVaR helpers ───────────────────────────────────────────────────────

def _fetch_returns(symbol: str, period: str = "5y") -> pd.Series:
    """Download daily returns for a symbol. Returns empty Series on failure."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval="1d")
        if hist.empty:
            return pd.Series(dtype=float)
        closes = hist["Close"].dropna()
        return closes.pct_change().dropna()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch returns for %s: %s", symbol, exc)
        return pd.Series(dtype=float)


def compute_var_cvar(
    returns: pd.Series,
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
    portfolio_value: float = 10_000.0,
) -> dict:
    """
    Historical-simulation VaR and CVaR.
    Returns dict with var_95, var_99, cvar_95, cvar_99 as absolute $ amounts.
    """
    if returns.empty or len(returns) < 30:
        return {"var_95": None, "var_99": None, "cvar_95": None, "cvar_99": None}

    result = {}
    for cl in confidence_levels:
        key = str(int(cl * 100))
        percentile = np.percentile(returns, (1 - cl) * 100)
        cvar = returns[returns <= percentile].mean()
        result[f"var_{key}"] = round(float(percentile * portfolio_value), 2)
        result[f"cvar_{key}"] = round(float(cvar * portfolio_value), 2) if not np.isnan(cvar) else None
    return result


def compute_max_drawdown(returns: pd.Series) -> float:
    """Compute maximum drawdown from a daily return series."""
    if returns.empty:
        return 0.0
    cum = (1 + returns).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    return float(drawdown.min())


def _annualised_vol(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float(returns.std() * np.sqrt(252))


def _beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    """OLS beta of stock vs market."""
    aligned = pd.concat([stock_returns, market_returns], axis=1).dropna()
    if len(aligned) < 30:
        return 1.0
    cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    var = aligned.iloc[:, 1].var()
    return float(cov / var) if var != 0 else 1.0


# ─── Single-stock stress ──────────────────────────────────────────────────────

@dataclass
class StockStressResult:
    symbol: str
    scenario_id: str
    scenario_name: str
    # Estimated portfolio impact
    portfolio_value: float
    estimated_pnl: float          # $ change
    estimated_pnl_pct: float      # % change
    beta_adjusted_pnl: float      # beta-scaled estimate
    # Risk metrics (from historical data)
    var_95: Optional[float]
    var_99: Optional[float]
    cvar_95: Optional[float]
    cvar_99: Optional[float]
    max_drawdown_historical: float
    annualised_vol: float
    beta_vs_spy: float
    # Qualitative
    macro_notes: str
    recovery_estimate_days: Optional[int]


def stress_test_symbol(
    symbol: str,
    scenario_id: str,
    portfolio_value: float = 10_000.0,
) -> StockStressResult:
    """
    Apply a scenario shock to a single stock position.
    Uses beta-adjusted impact: stock_shock ≈ beta × SPY_shock + idiosyncratic.
    """
    scenario = SCENARIO_MAP.get(scenario_id)
    if not scenario:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    sym = symbol.upper()
    returns = _fetch_returns(sym, period="5y")
    spy_returns = _fetch_returns("SPY", period="5y")

    # Risk metrics from history
    var_cvar = compute_var_cvar(returns, portfolio_value=portfolio_value)
    mdd = compute_max_drawdown(returns)
    vol = _annualised_vol(returns)
    b = _beta(returns, spy_returns)

    # Estimate scenario impact
    spy_shock = scenario.market_shocks.get("SPY", 0.0)

    # If the symbol IS a benchmark, use direct shock; otherwise use beta scaling
    direct_shocks = {"SPY": "SPY", "QQQ": "QQQ", "TLT": "TLT", "GLD": "GLD"}
    if sym in direct_shocks and sym in scenario.market_shocks:
        estimated_pct = scenario.market_shocks[sym]
    else:
        # Beta-scaled: stock moves beta× the market shock, clipped at ±90%
        estimated_pct = float(np.clip(b * spy_shock, -0.90, 0.90))

    estimated_pnl = portfolio_value * estimated_pct
    beta_adjusted_pnl = portfolio_value * float(np.clip(b * spy_shock, -0.90, 0.90))

    # Rough recovery estimate: assume mean daily return × recovery needed / vol²
    recovery_days: Optional[int] = None
    if not returns.empty and estimated_pct < 0:
        mean_daily = float(returns.mean())
        if mean_daily > 0:
            # Approximate: days = |loss| / mean_daily_gain
            recovery_days = int(abs(estimated_pct) / mean_daily)
            recovery_days = min(recovery_days, 3650)  # cap at 10 years

    return StockStressResult(
        symbol=sym,
        scenario_id=scenario_id,
        scenario_name=scenario.name,
        portfolio_value=portfolio_value,
        estimated_pnl=round(estimated_pnl, 2),
        estimated_pnl_pct=round(estimated_pct * 100, 2),
        beta_adjusted_pnl=round(beta_adjusted_pnl, 2),
        var_95=var_cvar.get("var_95"),
        var_99=var_cvar.get("var_99"),
        cvar_95=var_cvar.get("cvar_95"),
        cvar_99=var_cvar.get("cvar_99"),
        max_drawdown_historical=round(mdd * 100, 2),
        annualised_vol=round(vol * 100, 2),
        beta_vs_spy=round(b, 3),
        macro_notes=scenario.macro_notes,
        recovery_estimate_days=recovery_days,
    )


# ─── Portfolio-level stress ───────────────────────────────────────────────────

@dataclass
class PositionInput:
    symbol: str
    weight: float      # 0–1, portfolio weight
    value: float       # $ value


@dataclass
class PortfolioStressResult:
    scenario_id: str
    scenario_name: str
    total_portfolio_value: float
    total_estimated_pnl: float
    total_estimated_pnl_pct: float
    # Per-position detail
    positions: list[dict] = field(default_factory=list)
    # Aggregate risk
    portfolio_var_95: Optional[float] = None
    portfolio_var_99: Optional[float] = None
    portfolio_cvar_95: Optional[float] = None
    # Top risks
    worst_position: Optional[str] = None
    best_position: Optional[str] = None
    macro_notes: str = ""


def stress_test_portfolio(
    positions: list[PositionInput],
    scenario_id: str,
) -> PortfolioStressResult:
    """
    Apply a scenario shock to a multi-position portfolio.
    Aggregates per-position impact into a portfolio-level summary.
    """
    scenario = SCENARIO_MAP.get(scenario_id)
    if not scenario:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    if not positions:
        raise ValueError("Portfolio must have at least one position.")

    spy_returns = _fetch_returns("SPY", period="5y")
    total_value = sum(p.value for p in positions)

    position_results = []
    weighted_returns_list: list[tuple[pd.Series, float]] = []

    for pos in positions:
        sym = pos.symbol.upper()
        try:
            ret = _fetch_returns(sym, period="5y")
        except Exception:  # noqa: BLE001
            ret = pd.Series(dtype=float)

        b = _beta(ret, spy_returns)
        spy_shock = scenario.market_shocks.get("SPY", 0.0)

        direct_shocks = {"SPY", "QQQ", "TLT", "GLD"}
        if sym in direct_shocks and sym in scenario.market_shocks:
            est_pct = scenario.market_shocks[sym]
        else:
            est_pct = float(np.clip(b * spy_shock, -0.90, 0.90))

        est_pnl = pos.value * est_pct
        position_results.append({
            "symbol": sym,
            "value": round(pos.value, 2),
            "weight_pct": round(pos.value / total_value * 100, 2) if total_value > 0 else 0.0,
            "estimated_pnl": round(est_pnl, 2),
            "estimated_pnl_pct": round(est_pct * 100, 2),
            "beta_vs_spy": round(b, 3),
        })

        if not ret.empty:
            weighted_returns_list.append((ret, pos.weight))

    total_pnl = sum(p["estimated_pnl"] for p in position_results)
    total_pct = total_pnl / total_value if total_value > 0 else 0.0

    # Aggregate portfolio return series (weighted)
    port_var_95 = port_var_99 = port_cvar_95 = None
    if weighted_returns_list:
        try:
            combined = pd.concat([r for r, _ in weighted_returns_list], axis=1).dropna()
            weights = np.array([w for _, w in weighted_returns_list])
            weights = weights[:combined.shape[1]]
            weights = weights / weights.sum()
            port_returns = combined.values @ weights
            port_series = pd.Series(port_returns)
            vc = compute_var_cvar(port_series, portfolio_value=total_value)
            port_var_95 = vc.get("var_95")
            port_var_99 = vc.get("var_99")
            port_cvar_95 = vc.get("cvar_95")
        except Exception:  # noqa: BLE001
            pass

    worst = min(position_results, key=lambda x: x["estimated_pnl_pct"])["symbol"] if position_results else None
    best = max(position_results, key=lambda x: x["estimated_pnl_pct"])["symbol"] if position_results else None

    return PortfolioStressResult(
        scenario_id=scenario_id,
        scenario_name=scenario.name,
        total_portfolio_value=round(total_value, 2),
        total_estimated_pnl=round(total_pnl, 2),
        total_estimated_pnl_pct=round(total_pct * 100, 2),
        positions=position_results,
        portfolio_var_95=port_var_95,
        portfolio_var_99=port_var_99,
        portfolio_cvar_95=port_cvar_95,
        worst_position=worst,
        best_position=best,
        macro_notes=scenario.macro_notes,
    )


# ─── Custom hypothetical shock ────────────────────────────────────────────────

def build_custom_scenario(
    shocks: dict[str, float],
    name: str = "Custom Scenario",
    description: str = "",
) -> Scenario:
    """Build a one-off scenario from user-defined per-asset shocks."""
    return Scenario(
        id="custom",
        name=name,
        description=description or "User-defined hypothetical shock.",
        category="hypothetical",
        market_shocks=shocks,
    )
