from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, date
from typing import List, Optional, Dict, Any

class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = Field(default="momentum", description="The strategy identifier, e.g. 'momentum'")
    start_date: Optional[str] = Field(default=None, description="Format YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="Format YYYY-MM-DD")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy specific parameters, e.g., {'sma_fast': 50, 'sma_slow': 200}"
    )
    initial_capital: float = Field(default=10000.0)
    slippage_pct: float = Field(default=0.001, description="Slippage percentage per trade (e.g. 0.001 = 0.1%)")

    # BUG-018 FIX: Server-side validation to prevent OOM, confusing empty results,
    # or pandas/SQLAlchemy errors from invalid date ranges.
    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            dt = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v!r}")
        if dt > date.today():
            raise ValueError(f"Date cannot be in the future: {v}")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "BacktestRequest":
        if self.start_date and self.end_date:
            start = datetime.strptime(self.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            if end <= start:
                raise ValueError("end_date must be after start_date")
            if (end - start).days < 365:
                raise ValueError("Date range must span at least 1 year for a reliable backtest")
            if (date.today() - start).days > 365 * 20:
                raise ValueError("start_date cannot be more than 20 years in the past")
        return self

class BacktestStats(BaseModel):
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    recovery_factor: float = 0.0  # total_return / abs(max_drawdown)

class EquityPoint(BaseModel):
    date: str
    equity: float
    benchmark_equity: Optional[float] = None  # Buy-and-hold comparison

class BacktestResponse(BaseModel):
    request: BacktestRequest
    stats: BacktestStats
    equity_curve: List[EquityPoint]
    assumptions_applied: str = "Applied initial capital and slippage model."
    overfitting_warning: bool = False  # True when Sharpe > 1.2
