from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.crud.macro import get_latest_macro_indicator
from app.services.macro_orchestrator import refresh_all_macro_indicators
from app.services.macro_scoring import compute_macro_score

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

