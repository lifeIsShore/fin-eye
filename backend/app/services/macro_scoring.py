from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class MacroScore(TypedDict):
    score: float
    label: str


def compute_macro_score(indicators: Dict[str, Optional[float]]) -> MacroScore:
    """
    Compute a simple 0–100 macro score and label from the latest indicators.

    This mirrors the MVP heuristic used by the macro API so scoring is consistent
    across endpoints and feature engineering.
    """
    score = 50.0

    fed = indicators.get("fed_funds_rate")
    unemp = indicators.get("unemployment_rate")
    spread = indicators.get("yield_spread_10y_2y")
    cpi = indicators.get("cpi_yoy")
    vix = indicators.get("vix")

    # Yield curve: strong signal
    if spread is not None:
        if spread < 0:
            score -= 15.0
        elif spread < 0.2:
            score -= 5.0
        elif spread > 1.0:
            score += 5.0

    # Labour market
    if unemp is not None:
        if unemp > 6.0:
            score -= 10.0
        elif unemp > 5.0:
            score -= 5.0
        elif unemp < 4.0:
            score += 5.0

    # Inflation
    if cpi is not None:
        if cpi > 4.0:
            score -= 10.0
        elif cpi > 3.0:
            score -= 5.0
        elif cpi < 2.0:
            score += 5.0

    # Policy stance (very rough)
    if fed is not None:
        if fed > 4.5:
            score -= 5.0
        elif fed < 2.0:
            score += 2.0

    # Volatility regime
    if vix is not None:
        if vix > 30:
            score -= 10.0
        elif vix > 20:
            score -= 5.0
        elif vix < 15:
            score += 5.0

    # Clamp to 0–100
    score = max(0.0, min(100.0, score))

    if score >= 70:
        label = "Supportive"
    elif score >= 40:
        label = "Neutral"
    else:
        label = "Stressed"

    return {"score": round(score, 1), "label": label}

