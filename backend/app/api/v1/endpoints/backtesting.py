from fastapi import APIRouter, HTTPException, Depends
from typing import Any
import logging

from app.schemas.backtest_models import BacktestRequest, BacktestResponse, WalkForwardRequest, WalkForwardResponse
from app.services.backtesting_service import BacktestingEngine, WalkForwardEngine

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=BacktestResponse, summary="Run a historical backtest")
async def run_backtest(request: BacktestRequest) -> Any:
    """
    Run a strategy backtest based on the request parameters.
    
    * **symbol**: Ticker symbol to test (e.g. AAPL)
    * **strategy**: Strategy name (e.g. "momentum")
    * **parameters**: Strategy-specific params like sma_fast, sma_slow, rsi_threshold
    * **start_date / end_date**: Optional YYYY-MM-DD bounds
    """
    try:
        engine = BacktestingEngine(request)
        response = engine.run()
        return response
    except ValueError as e:
        logger.error(f"Validation error in backtest: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in backtest: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while running the backtest.")


@router.post(
    "/walk-forward",
    response_model=WalkForwardResponse,
    summary="Walk-forward out-of-sample validation",
    description=(
        "Runs a time-series walk-forward validation to estimate out-of-sample "
        "performance. Splits the full history into N anchored IS/OOS windows, "
        "runs the strategy on each, and returns per-fold stats plus a stitched "
        "OOS equity curve. High IS→OOS Sharpe degradation indicates overfitting."
    ),
)
async def run_walk_forward(request: WalkForwardRequest) -> Any:
    try:
        engine = WalkForwardEngine(request)
        return engine.run()
    except ValueError as e:
        logger.error(f"Walk-forward validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in walk-forward: {str(e)}")
        raise HTTPException(status_code=500, detail="Walk-forward validation failed.")
