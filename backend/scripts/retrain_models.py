import sys
import os

# Add backend directory to sys.path so 'app' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from app.services.ml_pipeline import run_training_pipeline
from app.services.technical_service import TIMEFRAMES
from app.services.market_data import OHLCVFetcher

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(symbol: str):
    logger.info(f"Starting retraining for symbol: {symbol}")
    for tf in TIMEFRAMES:
        logger.info(f"--- Training {symbol} on timeframe {tf} ---")
        try:
            period = "730d" if tf in ("1h", "4h") else "max"
            fetch_interval = "1h" if tf == "4h" else tf
            records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=fetch_interval)
            
            if len(records) < 200:
                logger.warning(f"Not enough data to train {symbol} {tf} (found {len(records)} rows)")
                continue

            df = pd.DataFrame([{
                "date": r.timestamp, 
                "open": r.open, 
                "high": r.high, 
                "low": r.low, 
                "close": r.close, 
                "volume": r.volume
            } for r in records])
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)
            
            if tf == "4h":
                df = df.resample("4h", label="left", closed="left").agg(
                    {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
                ).dropna()

            if len(df) < 200:
                logger.warning(f"Not enough data for {symbol} {tf} after feature engineering/resampling (found {len(df)} rows)")
                continue

            run_training_pipeline(symbol, tf, df)
            logger.info(f"Successfully finished training {symbol} on {tf}")
            
        except Exception as e:
            logger.error(f"Failed to train {symbol} on {tf}: {e}")

if __name__ == "__main__":
    # Default to main pair if none provided
    symbols = ["BTC-USD"]
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
    
    for sym in symbols:
        main(sym)
