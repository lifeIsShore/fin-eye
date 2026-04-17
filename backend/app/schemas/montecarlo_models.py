from pydantic import BaseModel
from typing import List, Optional

class MCAssetParams(BaseModel):
    symbol: str
    starting_value: float = 10000.0
    mu: float            # Annualized expected return (drift)
    sigma: float         # Annualized volatility
    years: int = 5       # Time horizon in years
    paths: int = 10000   # Number of simulation paths
    steps_per_year: int = 252 # Trading days per year
    model_type: str = "GBM" # "GBM", "JUMP_DIFFUSION"
    
    # Jump Diffusion params (optional)
    jump_intensity: float = 0.0 # Lambda: expected jumps per year
    jump_mean: float = 0.0      # Average jump size (log return)
    jump_std: float = 0.0       # Volatility of jump size

class MCPercentileResult(BaseModel):
    step: int
    day: int
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float

class MCSimulationResult(BaseModel):
    symbol: str
    final_median: float
    final_p5: float
    final_p95: float
    max_drawdown_p95: float
    cvar_95: float        # Conditional VaR at 95% confidence over the horizon
    paths_generated: int
    trajectory: List[MCPercentileResult]

class MCPortfolioParams(BaseModel):
    assets: List[MCAssetParams]
    correlation_matrix: Optional[List[List[float]]] = None # NxN matrix
    starting_capital: float = 10000.0
    monthly_contribution: float = 0.0  # Positive for adding, negative for withdrawing
    years: int = 30
    paths: int = 10000
    steps_per_year: int = 12 # Monthly steps for long term retirement

class MCPortfolioResult(BaseModel):
    final_median: float
    final_p5: float
    final_p95: float
    success_rate: float # Percentage of paths where final capital > 0 (for retirement)
    trajectory: List[MCPercentileResult]
