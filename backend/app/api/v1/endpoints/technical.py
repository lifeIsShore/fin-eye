from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from app.services.technical_service import compute_technical_consensus, TIMEFRAMES
from app.services.ml_pipeline import run_training_pipeline
from app.services.market_data import OHLCVFetcher
import pandas as pd
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/train/{symbol}")
async def train_technical_models(symbol: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Triggers ML pipeline training for all timeframes for a given symbol.
    Runs in the background since training 5 models (Logistic, XGBoost, Prophet)
    can take some time.
    # NEW BUG FIX: was sync `def` which blocks the FastAPI event loop for the
    # duration of the background task dispatch. Changed to `async def`.
    """
    symbol = symbol.upper()

    def _run_training():
        for tf in TIMEFRAMES:
            try:
                # Fetch data (1h capped at 730d by YF)
                period = "730d" if tf == "1h" else "5y"
                records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=tf)
                if len(records) < 200:
                    logger.warning(f"Not enough data to train {symbol} {tf} (found {len(records)} rows)")
                    continue
                
                # Format to df matching ml_pipeline expectations
                df = pd.DataFrame([{"date": r.timestamp, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume} for r in records])
                df.set_index("date", inplace=True)
                df.sort_index(inplace=True)
                
                # Run pipeline
                run_training_pipeline(symbol, tf, df)
            except Exception as e:
                logger.error(f"Background training failed for {symbol} {tf}: {e}")

    background_tasks.add_task(_run_training)
    
    return {
        "message": f"Training pipeline initiated in background for {symbol} across {len(TIMEFRAMES)} timeframes.",
        "symbol": symbol,
        "status": "processing"
    }


@router.get("/{symbol}/latest")
async def get_latest_technical_consensus(symbol: str) -> Dict[str, Any]:
    """
    Return the live technical consensus and 0–100 technical confidence score
    for a symbol, based on the most recently trained winners per timeframe.
    # NEW BUG FIX: was sync `def` calling CPU-bound inference directly on the
    # event loop. Changed to async + run_in_executor to avoid blocking.
    """
    import asyncio  # noqa: PLC0415
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, compute_technical_consensus, symbol.upper())
        # To maintain API contract with the frontend existing type `TechnicalConsensusDto`
        # Map the output properly
        
        frontend_mapped = {
            "symbol": result["symbol"],
            "consensus": result["consensus_label"],
            "technical_confidence_score": result["consensus_score"],
            "summary": f"{result['consensus_label']} based on live ML inference",
            "signals": [
                {
                    "timeframe": s["timeframe"],
                    "direction": s["direction"],
                    "confidence": s["confidence"],
                    "sharpe_weight": s["validation_sharpe"],
                    "model_used": s["model_used"]
                }
                for s in result["signals"]
            ]
        }
        return frontend_mapped

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"Error computing technical consensus for {symbol}:\n{err_msg}")
        return {"error": str(e), "traceback": err_msg}
