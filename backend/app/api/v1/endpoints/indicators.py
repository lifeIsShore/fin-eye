"""
app/api/v1/endpoints/indicators.py
─────────────────────────────────────────────────────────────────────────────
P3-ANALYTICS-01 — No-Code Indicator Builder endpoints

Routes (all auth-protected):
  POST   /indicators/evaluate          — evaluate a formula (no save)
  POST   /indicators/validate          — validate formula without evaluating
  POST   /indicators                   — save a named custom indicator
  GET    /indicators                   — list user's saved indicators
  GET    /indicators/{id}              — get one indicator
  PUT    /indicators/{id}              — update name/description/formula
  DELETE /indicators/{id}              — delete
  GET    /indicators/{id}/evaluate     — evaluate a saved indicator
  GET    /indicators/catalog           — list available functions & their params
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.custom_indicator import CustomIndicator
from app.models.user import User
from app.services.indicator_service import evaluate, validate_formula

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    symbol: str    = Field(..., min_length=1, max_length=20)
    timeframe: str = Field(default="1d", pattern="^(1d|1h|1wk|1mo)$")
    periods:  int  = Field(default=300, ge=50, le=500)
    formula:  Dict[str, Any]


class ValidateRequest(BaseModel):
    formula: Dict[str, Any]


class IndicatorCreate(BaseModel):
    name:        str              = Field(..., min_length=1, max_length=80)
    description: Optional[str]   = Field(None, max_length=255)
    formula:     Dict[str, Any]


class IndicatorUpdate(BaseModel):
    name:        Optional[str]   = Field(None, min_length=1, max_length=80)
    description: Optional[str]   = Field(None, max_length=255)
    formula:     Optional[Dict[str, Any]] = None


class IndicatorResponse(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    formula:     Dict[str, Any]
    created_at:  datetime
    updated_at:  datetime
    model_config = {"from_attributes": True}


class EvaluateResponse(BaseModel):
    dates:   List[str]
    values:  List[Optional[float]]
    type:    str
    summary: Dict[str, Optional[float]]


class ValidateResponse(BaseModel):
    valid:  bool
    errors: List[str]


# ─── Catalog of available functions ──────────────────────────────────────────

FUNCTION_CATALOG = [
    {
        "fn": "SMA", "label": "Simple Moving Average", "category": "Trend",
        "params": [{"name": "period", "default": 20, "min": 2, "max": 200, "type": "int"}],
        "outputs": [], "description": "Average closing price over N periods.",
        "example": {"type": "indicator", "fn": "SMA", "params": {"period": 20}},
    },
    {
        "fn": "EMA", "label": "Exponential Moving Average", "category": "Trend",
        "params": [{"name": "period", "default": 20, "min": 2, "max": 200, "type": "int"}],
        "outputs": [], "description": "Exponentially weighted average — reacts faster to recent prices.",
        "example": {"type": "indicator", "fn": "EMA", "params": {"period": 20}},
    },
    {
        "fn": "RSI", "label": "Relative Strength Index", "category": "Momentum",
        "params": [{"name": "period", "default": 14, "min": 2, "max": 50, "type": "int"}],
        "outputs": [], "description": "Momentum oscillator 0–100. Above 70 = overbought, below 30 = oversold.",
        "example": {"type": "indicator", "fn": "RSI", "params": {"period": 14}},
    },
    {
        "fn": "MACD", "label": "MACD", "category": "Momentum",
        "params": [
            {"name": "fast",   "default": 12, "min": 2,  "max": 50, "type": "int"},
            {"name": "slow",   "default": 26, "min": 5,  "max": 100, "type": "int"},
            {"name": "signal", "default": 9,  "min": 2,  "max": 30, "type": "int"},
        ],
        "outputs": ["macd", "signal", "hist"],
        "description": "Moving Average Convergence Divergence. Select output: macd line, signal line, or histogram.",
        "example": {"type": "indicator", "fn": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "output": "macd"},
    },
    {
        "fn": "BB", "label": "Bollinger Bands", "category": "Volatility",
        "params": [
            {"name": "period", "default": 20, "min": 5,   "max": 100, "type": "int"},
            {"name": "std",    "default": 2.0, "min": 0.5, "max": 4.0, "type": "float"},
        ],
        "outputs": ["upper", "lower", "mid", "width", "pb"],
        "description": "Volatility bands around SMA. pb = percent bandwidth (0=lower band, 1=upper band).",
        "example": {"type": "indicator", "fn": "BB", "params": {"period": 20, "std": 2.0}, "output": "pb"},
    },
    {
        "fn": "ATR", "label": "Average True Range", "category": "Volatility",
        "params": [{"name": "period", "default": 14, "min": 2, "max": 50, "type": "int"}],
        "outputs": [], "description": "Measures market volatility — average of true range over N periods.",
        "example": {"type": "indicator", "fn": "ATR", "params": {"period": 14}},
    },
    {
        "fn": "STOCH", "label": "Stochastic Oscillator", "category": "Momentum",
        "params": [
            {"name": "k", "default": 14, "min": 3, "max": 50, "type": "int"},
            {"name": "d", "default": 3,  "min": 1, "max": 10, "type": "int"},
        ],
        "outputs": ["k", "d"],
        "description": "%K and %D stochastic lines (0–100). Above 80 = overbought, below 20 = oversold.",
        "example": {"type": "indicator", "fn": "STOCH", "params": {"k": 14, "d": 3}, "output": "k"},
    },
    {
        "fn": "OBV", "label": "On-Balance Volume", "category": "Volume",
        "params": [], "outputs": [],
        "description": "Cumulative volume indicator — rises on up days, falls on down days.",
        "example": {"type": "indicator", "fn": "OBV", "params": {}},
    },
    {
        "fn": "ROC", "label": "Rate of Change", "category": "Momentum",
        "params": [{"name": "period", "default": 10, "min": 1, "max": 50, "type": "int"}],
        "outputs": [], "description": "Percentage price change over N periods.",
        "example": {"type": "indicator", "fn": "ROC", "params": {"period": 10}},
    },
    {
        "fn": "CCI", "label": "Commodity Channel Index", "category": "Momentum",
        "params": [{"name": "period", "default": 20, "min": 5, "max": 100, "type": "int"}],
        "outputs": [], "description": "Oscillator comparing typical price to its mean. ±100 are key levels.",
        "example": {"type": "indicator", "fn": "CCI", "params": {"period": 20}},
    },
    {
        "fn": "VWAP", "label": "VWAP (20-period)", "category": "Volume",
        "params": [], "outputs": [],
        "description": "Volume-weighted average price over a 20-bar rolling window.",
        "example": {"type": "indicator", "fn": "VWAP", "params": {}},
    },
    {
        "fn": "CLOSE", "label": "Close Price", "category": "Price",
        "params": [], "outputs": [],
        "description": "Raw closing price series.",
        "example": {"type": "indicator", "fn": "CLOSE", "params": {}},
    },
]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/catalog", summary="List all available indicator functions and their parameters")
async def get_catalog() -> List[dict]:
    """Returns the full function catalog — no auth required for this route."""
    return FUNCTION_CATALOG


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate a formula tree without evaluating it",
)
async def validate(body: ValidateRequest) -> ValidateResponse:
    errors = validate_formula(body.formula)
    return ValidateResponse(valid=(len(errors) == 0), errors=errors)


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate a formula against live market data (not saved)",
)
async def evaluate_formula(
    body: EvaluateRequest,
    current_user: User = Depends(get_current_user),
) -> EvaluateResponse:
    # Validate first
    errors = validate_formula(body.formula)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, evaluate, body.formula, body.symbol.upper(), body.timeframe, body.periods
        )
        return EvaluateResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Indicator evaluation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Evaluation failed: {exc}") from exc


@router.post(
    "",
    response_model=IndicatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a named custom indicator",
)
async def create_indicator(
    body: IndicatorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IndicatorResponse:
    errors = validate_formula(body.formula)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )
    ind = CustomIndicator(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        formula=body.formula,
    )
    db.add(ind)
    await db.flush()
    await db.refresh(ind)
    await db.commit()
    return ind


@router.get(
    "",
    response_model=List[IndicatorResponse],
    summary="List saved custom indicators for the authenticated user",
)
async def list_indicators(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[IndicatorResponse]:
    result = await db.execute(
        select(CustomIndicator)
        .where(CustomIndicator.user_id == current_user.id)
        .order_by(CustomIndicator.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/{indicator_id}",
    response_model=IndicatorResponse,
    summary="Get a saved indicator by ID",
)
async def get_indicator(
    indicator_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IndicatorResponse:
    result = await db.execute(
        select(CustomIndicator).where(
            CustomIndicator.id == indicator_id,
            CustomIndicator.user_id == current_user.id,
        )
    )
    ind = result.scalar_one_or_none()
    if not ind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")
    return ind


@router.put(
    "/{indicator_id}",
    response_model=IndicatorResponse,
    summary="Update a saved custom indicator",
)
async def update_indicator(
    indicator_id: int,
    body: IndicatorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IndicatorResponse:
    result = await db.execute(
        select(CustomIndicator).where(
            CustomIndicator.id == indicator_id,
            CustomIndicator.user_id == current_user.id,
        )
    )
    ind = result.scalar_one_or_none()
    if not ind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")

    if body.name is not None:        ind.name        = body.name
    if body.description is not None: ind.description = body.description
    if body.formula is not None:
        errors = validate_formula(body.formula)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"validation_errors": errors},
            )
        ind.formula = body.formula
    ind.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(ind)
    await db.commit()
    return ind


@router.delete(
    "/{indicator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved custom indicator",
)
async def delete_indicator(
    indicator_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(CustomIndicator).where(
            CustomIndicator.id == indicator_id,
            CustomIndicator.user_id == current_user.id,
        )
    )
    ind = result.scalar_one_or_none()
    if not ind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")
    await db.delete(ind)
    await db.commit()


@router.get(
    "/{indicator_id}/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate a saved indicator against live data",
)
async def evaluate_saved(
    indicator_id: int,
    symbol:    str = "AAPL",
    timeframe: str = "1d",
    periods:   int = 300,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluateResponse:
    result = await db.execute(
        select(CustomIndicator).where(
            CustomIndicator.id == indicator_id,
            CustomIndicator.user_id == current_user.id,
        )
    )
    ind = result.scalar_one_or_none()
    if not ind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")

    try:
        loop = asyncio.get_running_loop()
        eval_result = await loop.run_in_executor(
            None, evaluate, ind.formula, symbol.upper(), timeframe, min(max(50, periods), 500)
        )
        return EvaluateResponse(**eval_result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Saved indicator evaluation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Evaluation failed: {exc}") from exc
