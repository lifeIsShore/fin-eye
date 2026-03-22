"""
app/services/portfolio_performance.py

Sprint 15 P3-PORT-02 — Portfolio vs benchmark equity curve.

Computes normalised (start=100) daily equity curves for:
  - The portfolio: weighted sum of each constituent's daily returns
  - The benchmark: single-asset return series (default SPY)

Both are normalised to 100 at the first common date so they're directly comparable.

Returns a dict suitable for JSON serialisation:
{
  "dates":       ["2024-01-02", ...],
  "portfolio":   [100.0, 101.2, ...],
  "benchmark":   [100.0, 100.8, ...],
  "benchmark_symbol": "SPY",
  "period":      "1y",
  "portfolio_return_pct":  12.5,
  "benchmark_return_pct":  8.3,
  "alpha_pct":             4.2,
  "error": null,
}
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)

PERIOD_MAP = {
    "1mo": "1mo", "3mo": "3mo", "6mo": "6mo",
    "1y": "1y", "2y": "2y", "5y": "5y",
}


async def calculate_portfolio_performance(portfolio: Any, period: str = "1y") -> Dict[str, Any]:
    """
    Compute normalised portfolio vs benchmark equity curves.
    portfolio is a Portfolio ORM object with .items and .benchmark attributes.
    """
    period = PERIOD_MAP.get(period, "1y")
    benchmark_symbol = (portfolio.benchmark or "SPY").upper().strip()

    items = portfolio.items
    if not items:
        return {
            "dates": [], "portfolio": [], "benchmark": [],
            "benchmark_symbol": benchmark_symbol, "period": period,
            "portfolio_return_pct": 0.0, "benchmark_return_pct": 0.0, "alpha_pct": 0.0,
            "error": "Portfolio is empty.",
        }

    # Normalise weights
    total_w = sum(i.weight for i in items)
    if total_w == 0:
        return {"error": "All weights are zero.", "dates": [], "portfolio": [],
                "benchmark": [], "benchmark_symbol": benchmark_symbol, "period": period,
                "portfolio_return_pct": 0.0, "benchmark_return_pct": 0.0, "alpha_pct": 0.0}

    weights = {i.symbol: i.weight / total_w for i in items}
    symbols  = list(weights.keys())

    # ── Fetch price data ──────────────────────────────────────────────────────
    price_series: Dict[str, pd.Series] = {}
    all_symbols  = symbols + ([benchmark_symbol] if benchmark_symbol not in symbols else [])

    for sym in all_symbols:
        try:
            records = OHLCVFetcher.fetch_historical_data(sym, period=period, interval="1d")
            if records:
                s = pd.Series(
                    {r.timestamp.date(): r.close for r in records},
                    name=sym,
                ).sort_index()
                price_series[sym] = s
        except Exception as exc:
            logger.warning("Performance fetch failed for %s: %s", sym, exc)

    if not price_series:
        return {"error": "Could not fetch price data for any symbol.",
                "dates": [], "portfolio": [], "benchmark": [],
                "benchmark_symbol": benchmark_symbol, "period": period,
                "portfolio_return_pct": 0.0, "benchmark_return_pct": 0.0, "alpha_pct": 0.0}

    # ── Build daily returns matrix ─────────────────────────────────────────────
    price_df = pd.DataFrame({s: price_series[s] for s in price_series}).sort_index()
    price_df = price_df.dropna(how="all").ffill().bfill()
    returns  = price_df.pct_change().fillna(0)

    # ── Portfolio return = weighted sum of constituent returns ─────────────────
    port_return = pd.Series(0.0, index=returns.index)
    for sym, w in weights.items():
        if sym in returns.columns:
            port_return += returns[sym] * w

    # ── Normalise to 100 ───────────────────────────────────────────────────────
    port_equity  = (1 + port_return).cumprod() * 100
    bench_equity = None
    if benchmark_symbol in returns.columns:
        bench_equity = (1 + returns[benchmark_symbol]).cumprod() * 100

    # ── Align both series to common dates ─────────────────────────────────────
    if bench_equity is not None:
        combined     = pd.DataFrame({"portfolio": port_equity, "benchmark": bench_equity}).dropna()
    else:
        combined     = pd.DataFrame({"portfolio": port_equity}).dropna()
        combined["benchmark"] = None

    if combined.empty:
        return {"error": "No overlapping dates found.",
                "dates": [], "portfolio": [], "benchmark": [],
                "benchmark_symbol": benchmark_symbol, "period": period,
                "portfolio_return_pct": 0.0, "benchmark_return_pct": 0.0, "alpha_pct": 0.0}

    dates           = [str(d) for d in combined.index]
    port_vals       = [round(v, 4) for v in combined["portfolio"].tolist()]
    bench_vals      = [round(v, 4) if v is not None and pd.notna(v) else None
                       for v in combined["benchmark"].tolist()]

    # ── Summary stats ─────────────────────────────────────────────────────────
    port_ret   = round((port_vals[-1] / port_vals[0] - 1) * 100, 2) \
                 if port_vals and port_vals[0] and port_vals[0] != 0 else 0.0
    bench_ret  = round((bench_vals[-1] / bench_vals[0] - 1) * 100, 2) \
                 if bench_vals and bench_vals[-1] is not None and bench_vals[0] is not None and bench_vals[0] != 0 else 0.0
    alpha      = round(port_ret - bench_ret, 2)

    return {
        "dates":                 dates,
        "portfolio":             port_vals,
        "benchmark":             bench_vals,
        "benchmark_symbol":      benchmark_symbol,
        "period":                period,
        "portfolio_return_pct":  port_ret,
        "benchmark_return_pct":  bench_ret,
        "alpha_pct":             alpha,
        "error":                 None,
    }
