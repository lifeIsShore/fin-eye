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
    # Sprint 25 — benchmark comparison toggle
    benchmark: str = Field(default="", description="Benchmark ticker for buy-and-hold comparison (e.g. SPY, QQQ, BTC-USD). Empty = same symbol.")

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

# Sprint 25 — Trade Log
class TradeRecord(BaseModel):
    entry_date:     str
    exit_date:      str
    entry_price:    float
    exit_price:     float
    return_pct:     float        # net return % for this trade
    holding_days:   int
    side:           str = "long" # currently all trades are long

class BacktestResponse(BaseModel):
    request: BacktestRequest
    stats: BacktestStats
    equity_curve: List[EquityPoint]
    trade_log: List[TradeRecord] = Field(default_factory=list)  # Sprint 25
    assumptions_applied: str = "Applied initial capital and slippage model."
    overfitting_warning: bool = False  # True when Sharpe > 1.2
    benchmark_label: str = "Buy & Hold"  # Sprint 25 — display name of benchmark


# ── Walk-Forward Validation ──────────────────────────────────────────────────

class WalkForwardRequest(BaseModel):
    symbol: str
    strategy: str = "momentum"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    initial_capital: float = 10000.0
    slippage_pct: float = 0.001
    # Walk-forward split config
    n_splits: int = Field(default=5, ge=2, le=10, description="Number of in-sample/out-of-sample splits")
    train_pct: float = Field(default=0.7, ge=0.5, le=0.9, description="Fraction of each window used for in-sample")


class WalkForwardFold(BaseModel):
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    # In-sample (training window) stats
    in_sample_stats: BacktestStats
    in_sample_equity: List[EquityPoint]
    # Out-of-sample (test window) stats
    out_of_sample_stats: BacktestStats
    out_of_sample_equity: List[EquityPoint]


class WalkForwardResponse(BaseModel):
    request: WalkForwardRequest
    folds: List[WalkForwardFold]
    # Aggregated out-of-sample stats across all folds
    oos_total_return_pct: float
    oos_avg_sharpe: float
    oos_avg_win_rate: float
    oos_max_drawdown_pct: float
    # Degradation: IS Sharpe - OOS Sharpe (positive = overfit signal)
    avg_sharpe_degradation: float
    # Combined OOS equity curve (folds stitched together)
    combined_oos_equity: List[EquityPoint]
    overfitting_warning: bool
