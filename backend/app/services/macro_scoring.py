"""
app/services/macro_scoring.py
Macro scoring engine — upgraded for P2-MACRO-ADV-01.

Exports:
  compute_macro_score()      — 0-100 environment score  (lower = worse)
  compute_macro_stress_index() — 0-100 stress index     (higher = worse)
  compute_recession_risk()   — structured recession gauge
  compute_yield_curve()      — shape + spreads from individual tenor yields
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.schemas.macro_models import (
    MacroScoreDto,
    MacroStressIndexDto,
    RecessionDto,
    StressComponentDto,
    YieldCurveDto,
    YieldCurvePoint,
)

logger = logging.getLogger(__name__)

# ─── Type alias used internally ───────────────────────────────────────────────
Indicators = Dict[str, Optional[float]]


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Core macro score  (MVP-compatible, enhanced inputs)
# ─────────────────────────────────────────────────────────────────────────────

def compute_macro_score(indicators: Indicators) -> MacroScoreDto:
    """
    Return a 0–100 environment score.
    100 = ideal macro backdrop.  0 = maximum stress.

    Scoring starts at 50 (neutral) and adjusts for each known signal.
    Missing values are skipped gracefully — the score is still valid.
    """
    score = 50.0
    components: list[tuple[str, float]] = []

    def _adj(name: str, delta: float) -> None:
        nonlocal score
        score += delta
        components.append((name, delta))

    # ── Yield curve (strongest recession signal) ──────────────────────────
    spread = indicators.get("yield_spread_10y_2y")
    if spread is not None:
        if spread < -0.5:
            _adj("yield_curve_deeply_inverted", -20.0)
        elif spread < 0:
            _adj("yield_curve_inverted", -12.0)
        elif spread < 0.25:
            _adj("yield_curve_flat", -5.0)
        elif spread > 1.5:
            _adj("yield_curve_steep", +7.0)
        elif spread > 0.5:
            _adj("yield_curve_normal", +3.0)

    # ── Labour market ──────────────────────────────────────────────────────
    unemp = indicators.get("unemployment_rate")
    if unemp is not None:
        if unemp > 7.0:
            _adj("unemployment_very_high", -12.0)
        elif unemp > 6.0:
            _adj("unemployment_high", -8.0)
        elif unemp > 5.0:
            _adj("unemployment_elevated", -4.0)
        elif unemp < 3.5:
            _adj("unemployment_very_low", +8.0)
        elif unemp < 4.5:
            _adj("unemployment_low", +5.0)

    # ── Inflation ──────────────────────────────────────────────────────────
    cpi = indicators.get("cpi_yoy")
    if cpi is not None:
        if cpi > 6.0:
            _adj("inflation_very_high", -15.0)
        elif cpi > 4.0:
            _adj("inflation_high", -10.0)
        elif cpi > 3.0:
            _adj("inflation_elevated", -5.0)
        elif 1.5 <= cpi <= 2.5:
            _adj("inflation_target", +5.0)
        elif cpi < 0:
            _adj("deflation_risk", -8.0)

    # ── Fed policy stance ──────────────────────────────────────────────────
    fed = indicators.get("fed_funds_rate")
    if fed is not None:
        if fed > 5.5:
            _adj("rates_very_restrictive", -8.0)
        elif fed > 4.5:
            _adj("rates_restrictive", -4.0)
        elif fed < 1.0:
            _adj("rates_very_accommodative", +3.0)
        elif fed < 2.5:
            _adj("rates_accommodative", +2.0)

    # ── Volatility regime ──────────────────────────────────────────────────
    vix = indicators.get("vix")
    if vix is not None:
        if vix > 40:
            _adj("vix_extreme_fear", -15.0)
        elif vix > 30:
            _adj("vix_high_fear", -10.0)
        elif vix > 20:
            _adj("vix_elevated", -4.0)
        elif vix < 12:
            _adj("vix_very_low", +6.0)
        elif vix < 15:
            _adj("vix_low", +4.0)

    # ── NFP momentum (if available) ────────────────────────────────────────
    nfp_mom = indicators.get("nonfarm_payrolls_mom")
    if nfp_mom is not None:
        if nfp_mom > 300:
            _adj("nfp_very_strong", +4.0)
        elif nfp_mom > 150:
            _adj("nfp_solid", +2.0)
        elif nfp_mom < -100:
            _adj("nfp_contraction", -8.0)
        elif nfp_mom < 50:
            _adj("nfp_weak", -3.0)

    # ── Industrial production ──────────────────────────────────────────────
    ip_yoy = indicators.get("industrial_production_yoy")
    if ip_yoy is not None:
        if ip_yoy < -3.0:
            _adj("ip_contraction", -5.0)
        elif ip_yoy < 0:
            _adj("ip_slowing", -2.0)
        elif ip_yoy > 3.0:
            _adj("ip_strong", +3.0)

    score = max(0.0, min(100.0, score))

    if score >= 70:
        label = "Supportive"
    elif score >= 40:
        label = "Neutral"
    else:
        label = "Stressed"

    logger.debug("Macro score %.1f (%s).  Components: %s", score, label, components)
    return MacroScoreDto(score=round(score, 1), label=label)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Macro Stress Index  (P2-MACRO-ADV-01 — inverse framing)
# ─────────────────────────────────────────────────────────────────────────────

def compute_macro_stress_index(indicators: Indicators) -> MacroStressIndexDto:
    """
    A 0–100 stress index where 100 = maximum market stress.
    Methodologically this is the complement of compute_macro_score, but
    decomposed into named, explainable components for the UI.
    """
    comps: list[StressComponentDto] = []

    def _comp(name: str, contrib: float, desc: str) -> None:
        comps.append(StressComponentDto(name=name, contribution=round(contrib, 1), description=desc))

    raw_stress = 0.0

    # ── Yield curve inversion (0–25 pts) ──────────────────────────────────
    spread = indicators.get("yield_spread_10y_2y")
    if spread is not None:
        if spread < -0.75:
            s = 25.0
            _comp("Yield Curve", s, "Deeply inverted — historically strong recession signal")
        elif spread < -0.25:
            s = 18.0
            _comp("Yield Curve", s, "Inverted yield curve — recession risk elevated")
        elif spread < 0.25:
            s = 10.0
            _comp("Yield Curve", s, "Flat yield curve — growth concerns")
        else:
            s = 0.0
            _comp("Yield Curve", s, "Normal upward slope — benign signal")
        raw_stress += s

    # ── VIX / volatility (0–20 pts) ───────────────────────────────────────
    vix = indicators.get("vix")
    if vix is not None:
        if vix > 40:
            s = 20.0
            _comp("Volatility (VIX)", s, f"VIX {vix:.1f} — extreme fear regime")
        elif vix > 30:
            s = 15.0
            _comp("Volatility (VIX)", s, f"VIX {vix:.1f} — elevated fear")
        elif vix > 20:
            s = 8.0
            _comp("Volatility (VIX)", s, f"VIX {vix:.1f} — mildly elevated")
        else:
            s = 0.0
            _comp("Volatility (VIX)", s, f"VIX {vix:.1f} — calm markets")
        raw_stress += s

    # ── Inflation (0–20 pts) ───────────────────────────────────────────────
    cpi = indicators.get("cpi_yoy")
    if cpi is not None:
        if cpi > 6.0:
            s = 20.0
            _comp("Inflation (CPI)", s, f"CPI {cpi:.1f}% — persistently elevated, policy risk")
        elif cpi > 4.0:
            s = 12.0
            _comp("Inflation (CPI)", s, f"CPI {cpi:.1f}% — above target, restrictive policy likely")
        elif cpi > 3.0:
            s = 6.0
            _comp("Inflation (CPI)", s, f"CPI {cpi:.1f}% — slightly above target")
        elif cpi < 0:
            s = 10.0
            _comp("Inflation (CPI)", s, f"CPI {cpi:.1f}% — deflation risk")
        else:
            s = 0.0
            _comp("Inflation (CPI)", s, f"CPI {cpi:.1f}% — near target")
        raw_stress += s

    # ── Labour market (0–20 pts) ───────────────────────────────────────────
    unemp = indicators.get("unemployment_rate")
    if unemp is not None:
        if unemp > 7.0:
            s = 20.0
            _comp("Labour Market", s, f"Unemployment {unemp:.1f}% — significant job losses")
        elif unemp > 6.0:
            s = 12.0
            _comp("Labour Market", s, f"Unemployment {unemp:.1f}% — weakening labour market")
        elif unemp > 5.0:
            s = 6.0
            _comp("Labour Market", s, f"Unemployment {unemp:.1f}% — softening")
        else:
            s = 0.0
            _comp("Labour Market", s, f"Unemployment {unemp:.1f}% — healthy labour market")
        raw_stress += s

    # ── Fed policy (0–15 pts) ──────────────────────────────────────────────
    fed = indicators.get("fed_funds_rate")
    if fed is not None:
        if fed > 5.5:
            s = 15.0
            _comp("Fed Policy", s, f"Fed rate {fed:.2f}% — highly restrictive, growth headwind")
        elif fed > 4.5:
            s = 8.0
            _comp("Fed Policy", s, f"Fed rate {fed:.2f}% — restrictive territory")
        elif fed > 3.0:
            s = 3.0
            _comp("Fed Policy", s, f"Fed rate {fed:.2f}% — moderately tight")
        else:
            s = 0.0
            _comp("Fed Policy", s, f"Fed rate {fed:.2f}% — accommodative stance")
        raw_stress += s

    stress = max(0.0, min(100.0, raw_stress))

    if stress >= 60:
        label = "High Stress"
    elif stress >= 35:
        label = "Elevated"
    elif stress >= 15:
        label = "Moderate"
    else:
        label = "Low Stress"

    return MacroStressIndexDto(
        index=round(stress, 1),
        label=label,
        components=comps,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Recession risk gauge
# ─────────────────────────────────────────────────────────────────────────────

def compute_recession_risk(indicators: Indicators) -> RecessionDto:
    """
    Estimate recession probability (0–100 %) using a rule-based model that
    mirrors the classic Estrella/Mishkin yield-curve approach combined with
    labour-market and industrial production signals.

    This is explicitly an educational estimate, not an econometric model.
    """
    prob = 5.0  # base rate (US has been in recession ~15 % of months historically)
    drivers: list[str] = []
    nber_in_recession = False

    # ── NBER official indicator (most authoritative) ───────────────────────
    usrec = indicators.get("recession_indicator")
    if usrec is not None and usrec >= 0.5:
        nber_in_recession = True
        prob = 95.0
        drivers.append("NBER: Currently in an official recession (USREC = 1)")
        return RecessionDto(
            probability_pct=round(prob, 1),
            label="High",
            nber_in_recession=True,
            drivers=drivers,
        )

    # ── Yield curve (historically most predictive, 12-month horizon) ──────
    spread = indicators.get("yield_spread_10y_2y")
    if spread is not None:
        if spread < -0.75:
            prob += 45.0
            drivers.append(f"Yield curve deeply inverted (10Y–2Y = {spread:.2f}%)")
        elif spread < -0.25:
            prob += 30.0
            drivers.append(f"Yield curve inverted (10Y–2Y = {spread:.2f}%)")
        elif spread < 0.25:
            prob += 12.0
            drivers.append(f"Yield curve flat (10Y–2Y = {spread:.2f}%)")
        else:
            drivers.append(f"Yield curve normal — no inversion signal")

    # ── Unemployment (lagging but confirming signal) ───────────────────────
    unemp = indicators.get("unemployment_rate")
    if unemp is not None:
        if unemp > 6.5:
            prob += 20.0
            drivers.append(f"Unemployment high at {unemp:.1f}%")
        elif unemp > 5.5:
            prob += 8.0
            drivers.append(f"Unemployment rising — {unemp:.1f}%")

    # ── Industrial production contraction ─────────────────────────────────
    ip_yoy = indicators.get("industrial_production_yoy")
    if ip_yoy is not None and ip_yoy < -2.0:
        prob += 10.0
        drivers.append(f"Industrial production contracting ({ip_yoy:.1f}% YoY)")

    # ── VIX credit-stress proxy ────────────────────────────────────────────
    vix = indicators.get("vix")
    if vix is not None and vix > 35:
        prob += 8.0
        drivers.append(f"VIX {vix:.0f} — financial stress elevated")

    prob = max(0.0, min(99.0, prob))  # never report 0% or 100%

    if prob >= 60:
        label = "High"
    elif prob >= 30:
        label = "Elevated"
    else:
        label = "Low"

    if not drivers:
        drivers.append("No major recession signals detected")

    return RecessionDto(
        probability_pct=round(prob, 1),
        label=label,
        nber_in_recession=nber_in_recession,
        drivers=drivers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Yield curve shape
# ─────────────────────────────────────────────────────────────────────────────

_TENORS = [
    ("2Y",  2,  "treasury_2y"),
    ("5Y",  5,  "treasury_5y"),
    ("10Y", 10, "treasury_10y"),
    ("30Y", 30, "treasury_30y"),
]


def compute_yield_curve(indicators: Indicators, dates: dict[str, Optional[str]] = {}) -> YieldCurveDto:
    """
    Build a YieldCurveDto from individual tenor yields.
    `dates` maps indicator_name → ISO date string of the observation.
    """
    points: list[YieldCurvePoint] = []
    for label, years, key in _TENORS:
        points.append(YieldCurvePoint(
            tenor=label,
            tenor_years=years,
            yield_pct=indicators.get(key),
            date=dates.get(key),
        ))

    # Determine shape from 2Y and 10Y (most commonly watched pair)
    y2 = indicators.get("treasury_2y")
    y10 = indicators.get("treasury_10y")
    y30 = indicators.get("treasury_30y")

    spread_10_2 = (y10 - y2) if (y10 is not None and y2 is not None) else None
    spread_30_2 = (y30 - y2) if (y30 is not None and y2 is not None) else None

    if spread_10_2 is None:
        shape = "Unavailable"
        desc = "Yield curve data not yet available — run a macro refresh."
    elif spread_10_2 < -0.5:
        shape = "Inverted"
        desc = "Short-term yields exceed long-term yields — historically a leading recession indicator."
    elif spread_10_2 < 0.1:
        shape = "Flat"
        desc = "Very little difference between short and long yields — signals growth uncertainty."
    elif spread_10_2 > 2.0:
        shape = "Steep"
        desc = "Long yields well above short yields — typically signals strong growth expectations."
    else:
        shape = "Normal"
        desc = "Upward sloping curve — the baseline healthy shape."

    return YieldCurveDto(
        points=points,
        shape=shape,
        shape_description=desc,
        spread_10y_2y=round(spread_10_2, 3) if spread_10_2 is not None else None,
        spread_30y_2y=round(spread_30_2, 3) if spread_30_2 is not None else None,
    )
