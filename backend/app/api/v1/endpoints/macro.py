from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.crud.macro import get_latest_macro_indicator
from app.services.macro_orchestrator import refresh_all_macro_indicators

router = APIRouter()

def interpret_cpi(current: float) -> str:
    if current > 3.0:
        return "Inflation elevated"
    elif current < 2.0:
        return "Inflation below target"
    return "Inflation stable"

def interpret_yield_spread(current: float) -> str:
    if current < 0:
        return "Yield curve inverted (Warning)"
    elif current < 0.2:
        return "Yield curve flat"
    return "Yield curve normal"

def interpret_fed_funds(current: float) -> str:
    if current > 4.0:
        return "Rates restrictive"
    return "Rates accommodative"

def interpret_vix(current: float) -> str:
    if current > 30:
        return "Market fear high"
    elif current > 20:
        return "Market fear elevated"
    return "Market calm"

def interpret_unemployment(current: float) -> str:
    if current > 5.0:
        return "Labor market weakening"
    elif current < 4.0:
        return "Labor market tight"
    return "Labor market balanced"


def compute_macro_score(indicators: Dict[str, float]) -> Dict[str, Any]:
    """
    Compute a simple 0–100 macro score and label from the latest indicators.

    Heuristic (MVP):
      - Start at 50 (neutral).
      - Penalise inverted yield curves and high VIX / unemployment / CPI.
      - Reward steep positive spreads, low VIX, and healthy labour market.
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


@router.get("/latest", response_model=Dict[str, Any])
def get_latest_macro_dashboard(db: Session = Depends(get_db)):
    """Get the latest dashboard values for macro indicators and macro score."""

    indicators = [
        ("fed_funds_rate", interpret_fed_funds),
        ("unemployment_rate", interpret_unemployment),
        ("yield_spread_10y_2y", interpret_yield_spread),
        ("cpi_yoy", interpret_cpi),
        ("vix", interpret_vix),
    ]

    response_data: Dict[str, Any] = {}

    for name, interpreter_func in indicators:
        record = get_latest_macro_indicator(db, name)
        if record:
            interpretation = interpreter_func(record.value)
            response_data[name] = {
                "value": record.value,
                "date": record.date.isoformat(),
                "interpretation": interpretation,
            }
        else:
            response_data[name] = {
                "value": None,
                "date": None,
                "interpretation": "Data unavailable",
            }

    # Derive macro score from numeric values (ignores missing ones gracefully)
    numeric_values = {
        key: val["value"]
        for key, val in response_data.items()
        if val.get("value") is not None
    }
    macro_score = compute_macro_score(numeric_values) if numeric_values else None

    return {"data": response_data, "macro_score": macro_score}

@router.post("/refresh")
async def refresh_macro_data(db: Session = Depends(get_db)):
    """Trigger a refresh of all macro data indicators."""
    await refresh_all_macro_indicators(db)
    return {"status": "success", "message": "Macro data refresh initiated"}

