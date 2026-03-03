"""
Unit tests for hedging_service.py (MVP-HEDGE-01)

Uses synthetic/mock price data so no network calls needed.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.services.hedging_service import (
    compute_correlation_matrix,
    compute_beta,
    compute_hedge_ratio,
    compute_payoff,
    estimate_hedge_cost,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_ohlcv(symbol: str, prices: list):
    """Create a list of mock OHLCVData-like objects from a price list."""
    base = datetime(2025, 1, 1)
    records = []
    for i, p in enumerate(prices):
        obj = MagicMock()
        obj.timestamp = base + timedelta(days=i)
        obj.close = float(p)
        records.append(obj)
    return records


def _synth_prices(n=252, start=100, seed=42):
    """Generate n days of synthetic prices with a fixed seed."""
    rng = np.random.RandomState(seed)
    returns = rng.normal(0.0005, 0.012, n)
    prices = [start]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return prices


# ── Tests ────────────────────────────────────────────────────────────────────

class TestComputeHedgeRatio:
    def test_basic_ratio(self):
        result = compute_hedge_ratio(beta=1.2, portfolio_value=10_000, hedge_price=500)
        assert result["hedge_units"] == 24       # round(1.2 * 10000 / 500)
        assert result["notional"] == 12_000.0

    def test_zero_hedge_price(self):
        result = compute_hedge_ratio(beta=1.0, portfolio_value=10_000, hedge_price=0)
        assert result["hedge_units"] == 0

    def test_fractional_beta(self):
        result = compute_hedge_ratio(beta=0.5, portfolio_value=20_000, hedge_price=100)
        assert result["hedge_units"] == 100      # round(0.5 * 20000 / 100)


class TestComputePayoff:
    def test_scenario_count(self):
        result = compute_payoff(10_000, "protective_put", 1.0)
        # Default scenarios: -30 to +30 step 5 → 13 scenarios
        assert len(result["scenarios"]) == 13

    def test_hedged_always_non_negative(self):
        result = compute_payoff(10_000, "protective_put", 1.5)
        for s in result["scenarios"]:
            assert s["hedged"] >= 0

    def test_unhedged_matches_simple_math(self):
        result = compute_payoff(10_000, "inverse_etf", 1.0)
        for s in result["scenarios"]:
            expected_unhedged = round(10_000 * (1 + s["return_pct"] / 100), 2)
            assert s["unhedged"] == expected_unhedged

    def test_custom_scenarios(self):
        result = compute_payoff(5_000, "protective_put", 1.0, scenarios=[-0.1, 0.0, 0.1])
        assert len(result["scenarios"]) == 3


class TestEstimateHedgeCost:
    def test_protective_put_cost(self):
        result = estimate_hedge_cost("protective_put", 10_000)
        assert result["annual_cost_pct"] == 2.0
        assert result["annual_cost_usd"] == 200.0

    def test_inverse_etf_cost(self):
        result = estimate_hedge_cost("inverse_etf", 10_000)
        assert result["annual_cost_pct"] == 0.89
        assert result["annual_cost_usd"] == 89.0

    def test_unknown_type(self):
        result = estimate_hedge_cost("unknown", 10_000)
        assert result["annual_cost_pct"] == 0.0


class TestComputeCorrelation:
    @patch("app.services.hedging_service.OHLCVFetcher.fetch_historical_data")
    def test_correlation_shape(self, mock_fetch):
        """Correlation dict should have one entry per benchmark."""
        prices_sym = _synth_prices(100, start=150, seed=1)
        prices_spy = _synth_prices(100, start=450, seed=2)
        prices_qqq = _synth_prices(100, start=380, seed=3)

        def side_effect(symbol, **kwargs):
            if symbol == "TEST":
                return _make_ohlcv("TEST", prices_sym)
            elif symbol == "SPY":
                return _make_ohlcv("SPY", prices_spy)
            elif symbol == "QQQ":
                return _make_ohlcv("QQQ", prices_qqq)
            return []

        mock_fetch.side_effect = side_effect

        result = compute_correlation_matrix("TEST", benchmarks=["SPY", "QQQ"])
        assert "SPY" in result["correlations"]
        assert "QQQ" in result["correlations"]
        for v in result["correlations"].values():
            assert -1.0 <= v <= 1.0


class TestComputeBeta:
    @patch("app.services.hedging_service.OHLCVFetcher.fetch_historical_data")
    def test_beta_within_range(self, mock_fetch):
        """Beta should be a finite number."""
        prices_sym = _synth_prices(100, start=150, seed=10)
        prices_spy = _synth_prices(100, start=450, seed=20)

        def side_effect(symbol, **kwargs):
            if symbol == "TEST":
                return _make_ohlcv("TEST", prices_sym)
            return _make_ohlcv("SPY", prices_spy)

        mock_fetch.side_effect = side_effect

        result = compute_beta("TEST", "SPY")
        assert -5 <= result["beta"] <= 5
        assert 0 <= result["r_squared"] <= 1
        assert result["data_points"] > 0
