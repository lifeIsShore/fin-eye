"""
tests/services/test_macro_scoring.py
Unit tests for the upgraded macro scoring engine (P2-MACRO-ADV-01).

All tests are pure-Python — no DB, no network.
"""
import pytest

from app.services.macro_scoring import (
    compute_macro_score,
    compute_macro_stress_index,
    compute_recession_risk,
    compute_yield_curve,
)


# ─────────────────────────────────────────────────────────────────────────────
# compute_macro_score
# ─────────────────────────────────────────────────────────────────────────────

class TestMacroScore:
    def test_neutral_baseline_with_no_data(self):
        result = compute_macro_score({})
        assert result.score == 50.0
        assert result.label == "Neutral"

    def test_ideal_conditions_score_above_70(self):
        result = compute_macro_score({
            "yield_spread_10y_2y": 1.8,   # steep → +7
            "unemployment_rate": 3.2,      # very low → +8
            "cpi_yoy": 2.0,                # target → +5
            "fed_funds_rate": 2.0,         # accommodative → +2
            "vix": 11.0,                   # very low → +6
        })
        assert result.score >= 70
        assert result.label == "Supportive"

    def test_stressed_conditions_score_below_40(self):
        result = compute_macro_score({
            "yield_spread_10y_2y": -0.8,  # deeply inverted → -20
            "unemployment_rate": 7.5,      # very high → -12
            "cpi_yoy": 7.0,                # very high → -15
            "fed_funds_rate": 5.8,         # very restrictive → -8
            "vix": 42.0,                   # extreme fear → -15
        })
        assert result.score < 40
        assert result.label == "Stressed"

    def test_score_clamped_to_0_100(self):
        # Pile on every possible negative
        result = compute_macro_score({
            "yield_spread_10y_2y": -2.0,
            "unemployment_rate": 12.0,
            "cpi_yoy": 10.0,
            "fed_funds_rate": 8.0,
            "vix": 80.0,
            "nonfarm_payrolls_mom": -500.0,
            "industrial_production_yoy": -8.0,
        })
        assert result.score >= 0.0

    def test_nfp_and_ip_inputs_affect_score(self):
        base = compute_macro_score({"yield_spread_10y_2y": 0.5})
        with_nfp = compute_macro_score({
            "yield_spread_10y_2y": 0.5,
            "nonfarm_payrolls_mom": 400.0,
            "industrial_production_yoy": 4.0,
        })
        assert with_nfp.score > base.score

    def test_missing_indicators_handled_gracefully(self):
        """Partial data should still return a valid score."""
        result = compute_macro_score({"vix": 22.0})
        assert 0 <= result.score <= 100
        assert result.label in ("Supportive", "Neutral", "Stressed")


# ─────────────────────────────────────────────────────────────────────────────
# compute_macro_stress_index
# ─────────────────────────────────────────────────────────────────────────────

class TestMacroStressIndex:
    def test_no_data_returns_zero_stress(self):
        result = compute_macro_stress_index({})
        assert result.index == 0.0
        assert result.label == "Low Stress"
        assert result.components == []

    def test_deeply_inverted_curve_high_stress(self):
        result = compute_macro_stress_index({
            "yield_spread_10y_2y": -0.9,
            "vix": 38.0,
            "cpi_yoy": 5.5,
            "unemployment_rate": 6.5,
            "fed_funds_rate": 5.6,
        })
        assert result.index >= 60
        assert result.label == "High Stress"

    def test_benign_conditions_low_stress(self):
        result = compute_macro_stress_index({
            "yield_spread_10y_2y": 1.5,
            "vix": 13.0,
            "cpi_yoy": 2.1,
            "unemployment_rate": 3.8,
            "fed_funds_rate": 2.5,
        })
        assert result.index < 15
        assert result.label == "Low Stress"

    def test_components_present_for_each_provided_indicator(self):
        result = compute_macro_stress_index({
            "yield_spread_10y_2y": -0.3,
            "vix": 25.0,
            "cpi_yoy": 3.5,
            "unemployment_rate": 5.2,
            "fed_funds_rate": 4.8,
        })
        names = {c.name for c in result.components}
        assert "Yield Curve" in names
        assert "Volatility (VIX)" in names
        assert "Inflation (CPI)" in names
        assert "Labour Market" in names
        assert "Fed Policy" in names

    def test_stress_index_clamped_to_100(self):
        result = compute_macro_stress_index({
            "yield_spread_10y_2y": -2.0,
            "vix": 90.0,
            "cpi_yoy": 12.0,
            "unemployment_rate": 15.0,
            "fed_funds_rate": 9.0,
        })
        assert result.index <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_recession_risk
# ─────────────────────────────────────────────────────────────────────────────

class TestRecessionRisk:
    def test_nber_recession_flag_returns_95_probability(self):
        result = compute_recession_risk({"recession_indicator": 1.0})
        assert result.probability_pct >= 95.0
        assert result.nber_in_recession is True
        assert result.label == "High"

    def test_no_signals_returns_low_probability(self):
        result = compute_recession_risk({})
        assert result.probability_pct < 30
        assert result.label == "Low"

    def test_deeply_inverted_curve_elevated_risk(self):
        result = compute_recession_risk({
            "yield_spread_10y_2y": -1.0,
            "unemployment_rate": 6.8,
        })
        assert result.probability_pct >= 60
        assert result.label == "High"

    def test_flat_curve_alone_is_elevated_not_high(self):
        result = compute_recession_risk({"yield_spread_10y_2y": 0.1})
        assert 10 <= result.probability_pct < 60

    def test_probability_never_reaches_100(self):
        result = compute_recession_risk({
            "yield_spread_10y_2y": -2.0,
            "unemployment_rate": 10.0,
            "industrial_production_yoy": -5.0,
            "vix": 50.0,
        })
        assert result.probability_pct < 100.0

    def test_drivers_list_non_empty(self):
        result = compute_recession_risk({"yield_spread_10y_2y": -0.5})
        assert len(result.drivers) > 0


# ─────────────────────────────────────────────────────────────────────────────
# compute_yield_curve
# ─────────────────────────────────────────────────────────────────────────────

class TestYieldCurve:
    def test_normal_upward_sloping_curve(self):
        result = compute_yield_curve({
            "treasury_2y": 4.0,
            "treasury_5y": 4.3,
            "treasury_10y": 4.6,
            "treasury_30y": 4.9,
        })
        assert result.shape == "Normal"
        assert result.spread_10y_2y == pytest.approx(0.6, abs=0.01)

    def test_inverted_curve_detected(self):
        result = compute_yield_curve({
            "treasury_2y": 5.1,
            "treasury_5y": 4.8,
            "treasury_10y": 4.5,
            "treasury_30y": 4.4,
        })
        assert result.shape == "Inverted"
        assert result.spread_10y_2y < 0

    def test_flat_curve_detected(self):
        result = compute_yield_curve({
            "treasury_2y": 4.5,
            "treasury_5y": 4.5,
            "treasury_10y": 4.55,
            "treasury_30y": 4.6,
        })
        assert result.shape == "Flat"

    def test_steep_curve_detected(self):
        result = compute_yield_curve({
            "treasury_2y": 2.0,
            "treasury_5y": 3.0,
            "treasury_10y": 4.2,
            "treasury_30y": 4.8,
        })
        assert result.shape == "Steep"

    def test_unavailable_when_no_data(self):
        result = compute_yield_curve({})
        assert result.shape == "Unavailable"
        assert result.spread_10y_2y is None

    def test_four_tenor_points_always_present(self):
        result = compute_yield_curve({})
        assert len(result.points) == 4
        tenors = {p.tenor for p in result.points}
        assert tenors == {"2Y", "5Y", "10Y", "30Y"}

    def test_30y_2y_spread_computed(self):
        result = compute_yield_curve({
            "treasury_2y": 3.5,
            "treasury_10y": 4.2,
            "treasury_30y": 4.8,
        })
        assert result.spread_30y_2y == pytest.approx(1.3, abs=0.01)
