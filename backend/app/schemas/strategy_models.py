"""
app/schemas/strategy_models.py
Pydantic schemas for the Strategy Library (P2-STRAT-01).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class StrategySaveRequest(BaseModel):
    """Payload to save a strategy — includes the backtest config and optional results."""

    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)

    # The BacktestRequest fields, mirrored here so we don't need a circular import
    symbol: str = Field(..., min_length=1, max_length=20)
    strategy: str = Field(default="momentum")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    initial_capital: float = Field(default=10_000.0, gt=0)
    slippage_pct: float = Field(default=0.001, ge=0)

    # Optional — filled from backtest results if saving after a run
    total_return_pct: Optional[float] = None
    annualized_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    win_rate_pct: Optional[float] = None
    total_trades: Optional[int] = None

    is_public: bool = False

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    symbol: str
    strategy: str
    parameters: Dict[str, Any]
    initial_capital: float
    slippage_pct: float
    start_date: Optional[str]
    end_date: Optional[str]

    # Metrics
    total_return_pct: Optional[float]
    annualized_return_pct: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    win_rate_pct: Optional[float]
    total_trades: Optional[int]

    is_public: bool
    is_mine: bool = True  # set at serialisation time
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class StrategyListResponse(BaseModel):
    strategies: List[StrategyResponse]
    total: int


class StrategyUpdateRequest(BaseModel):
    """Partial update — only fields the user wants to change."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    is_public: Optional[bool] = None
