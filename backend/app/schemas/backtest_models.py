from pydantic import BaseModel, Field
from datetime import datetime
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

class BacktestStats(BaseModel):
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int

class EquityPoint(BaseModel):
    date: str
    equity: float

class BacktestResponse(BaseModel):
    request: BacktestRequest
    stats: BacktestStats
    equity_curve: List[EquityPoint]
    assumptions_applied: str = "Applied initial capital and slippage model."
