"""
app/services/portfolio_correlation.py

Sprint 19 -- Pairwise Pearson correlation matrix for portfolio positions.

Fetches `period` of daily closing prices for each symbol using the existing
OHLCVFetcher, aligns them on a common date index (inner join), and computes
the full correlation matrix.

Returns:
{
  "symbols": ["AAPL", "MSFT", "TSLA"],
  "matrix":  [[1.0, 0.82, 0.61], [0.82, 1.0, 0.55], [0.61, 0.55, 1.0]],
  "period":  "6mo",
  "error":   null   # or a string if something went wrong
}
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)

# Map period strings to yfinance period codes
_PERIOD_MAP: dict[str, str] = {
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y":  "1y",
    "2y":  "2y",
}


async def calculate_portfolio_correlation(
    portfolio: Any,
    period: str = "6mo",
) -> Dict[str, Any]:
    """Compute pairwise Pearson correlation matrix for all portfolio symbols."""

    items = portfolio.items or []
    symbols = [i.symbol for i in items]

    if len(symbols) < 2:
        return {
            "symbols": symbols,
            "matrix": [[1.0]] if len(symbols) == 1 else [],
            "period": period,
            "error": "Need at least 2 symbols for a correlation matrix.",
        }

    yf_period = _PERIOD_MAP.get(period, "6mo")

    close_series: dict[str, pd.Series] = {}
    for sym in symbols:
        try:
            rows = OHLCVFetcher.fetch_historical_data(sym, period=yf_period, interval="1d")
            if rows:
                s = pd.Series(
                    {r.timestamp.date(): r.close for r in rows},
                    name=sym,
                )
                close_series[sym] = s
        except Exception as exc:
            logger.warning("Correlation: could not fetch %s: %s", sym, exc)

    valid_symbols = [s for s in symbols if s in close_series]

    if len(valid_symbols) < 2:
        return {
            "symbols": valid_symbols,
            "matrix": [],
            "period": period,
            "error": f"Price data unavailable for most symbols in the {period} window.",
        }

    # Align on common dates (inner join of all series)
    df = pd.DataFrame({sym: close_series[sym] for sym in valid_symbols})
    df = df.dropna()  # keep only rows where ALL symbols have data

    if len(df) < 10:
        return {
            "symbols": valid_symbols,
            "matrix": [],
            "period": period,
            "error": f"Not enough overlapping trading days ({len(df)}) across all symbols.",
        }

    corr = df.corr(method="pearson")

    matrix = [
        [round(float(corr.loc[s1, s2]), 4) for s2 in valid_symbols]
        for s1 in valid_symbols
    ]

    return {
        "symbols": valid_symbols,
        "matrix": matrix,
        "period": period,
        "n_days": len(df),
        "error": None,
    }
