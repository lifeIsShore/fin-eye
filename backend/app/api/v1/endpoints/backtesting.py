from fastapi import APIRouter, HTTPException, Depends
from typing import Any
import logging

from app.schemas.backtest_models import BacktestRequest, BacktestResponse
from app.services.backtesting_service import BacktestingEngine

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
