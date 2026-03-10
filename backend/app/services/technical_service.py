"""
Service layer for ML-driven Technical Consensus (MVP-TECH-02).
"""

import os
import json
import logging
import joblib

import pandas as pd
import numpy as np

from app.services.market_data import OHLCVFetcher
from app.services.ml_pipeline import (
    engineer_features, FEATURES, ARTIFACT_DIR, REGISTRY_FILE
)

logger = logging.getLogger(__name__)

# Supported timeframes that compose the consensus (YF compatible)
# BUG-003 FIX: Must match the timeframes the ML pipeline actually trains.
# ml_pipeline.py trains "1h" and "4h" — do NOT add 1d/1wk/1mo until training produces them.
TIMEFRAMES = ["1h", "4h"]

def get_latest_model_metadata(symbol: str, timeframe: str) -> dict:
    """Reads the JSONL registry to find the most recently trained model metadata."""
    if not os.path.exists(REGISTRY_FILE):
        return {}
        
    latest = {}
    try:
        with open(REGISTRY_FILE, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("symbol") == symbol and record.get("timeframe") == timeframe:
                    # Overwrites prior so we end up with the last (most recent) one
                    latest = record
    except Exception as e:
        logger.error(f"Error reading model registry: {e}")
        
    return latest


def load_model_instance(artifact_file: str):
    path = os.path.join(ARTIFACT_DIR, artifact_file)
    if not os.path.exists(path):
        return None
    return joblib.load(path)


def generate_timeframe_signal(symbol: str, timeframe: str) -> dict:
    """
    Returns prediction for a specific timeframe.
    Output: {
        "timeframe": "1d",
        "direction": "Bullish",
        "signal_raw": 0.8,
        "confidence": 80.0,
        "validation_sharpe": 1.5,
        "model_used": "xgboost"
    }
    """
    meta = get_latest_model_metadata(symbol, timeframe)
    if not meta:
        raise ValueError(f"No trained model found for {symbol} {timeframe}")
        
    model = load_model_instance(meta["artifact_file"])
    if not model:
        raise ValueError(f"Model artifact {meta['artifact_file']} missing")

    # Fetch recent data to construct features.
    # yfinance intraday data limits:
    #   1h  → max 730 days
    #   4h  → resampled from 1h, so also capped at 730 days
    # NEW BUG FIX: previously used "5y" for 4h which yfinance rejects silently,
    # returning an empty DataFrame and causing inference to fail.
    period = "730d" if timeframe in ("1h", "4h") else "5y"
    # yfinance does NOT have a native 4h interval — must fetch 1h and resample.
    # NEW BUG FIX: previously passed interval="4h" to yfinance which silently
    # returned empty data, causing inference to fail for the 4h timeframe.
    fetch_interval = "1h" if timeframe == "4h" else timeframe
    records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=fetch_interval)
    if len(records) < 50:
        raise ValueError(f"Not enough data to run inference on {timeframe}")

    df = pd.DataFrame([{"date": r.timestamp, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume} for r in records])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)

    # Resample 1h → 4h if needed (mirrors what the training pipeline does)
    if timeframe == "4h":
        df = df.resample("4h", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()

    # Engineer
    df_feat = engineer_features(df)
    if df_feat.empty:
        raise ValueError("Feature engineering resulted in empty dataframe.")

    # Get the latest row for inference
    latest_row = df_feat.iloc[-1:]
    
    # Needs close_raw for Prophet wrappers
    latest_row_copy = latest_row.copy()
    latest_row_copy['close_raw'] = df['close'].iloc[-1]
    
    X = latest_row_copy[FEATURES + ['close_raw']]
    
    probs = model.predict_proba(X)
    prob_up = float(probs[0, 1])  # Class 1 probability
    
    direction_val = 1 if prob_up > 0.5 else -1
    confidence = max(prob_up, 1 - prob_up) * 100
    signal_raw = direction_val * (confidence / 100.0)

    return {
        "timeframe": timeframe,
        "direction": "Bullish" if direction_val > 0 else "Bearish",
        "signal_raw": signal_raw,
        "confidence": round(confidence, 1),
        "validation_sharpe": meta.get("validation_sharpe", 0.0),
        "model_used": meta.get("model_name", "unknown")
    }


def compute_technical_consensus(symbol: str) -> dict:
    """
    Agregates 5 timeframe signals into a single 0-100 score.
    Maps RAW (-1 to +1) to SCORE (0 to 100).
    """
    signals = []
    
    # We gracefully skip ones that fail (e.g. no data or no model)
    for tf in TIMEFRAMES:
        try:
            sig = generate_timeframe_signal(symbol, tf)
            signals.append(sig)
        except Exception as e:
            logger.warning(f"Failed to generate signal for {symbol} {tf}: {e}")

    if not signals:
        raise ValueError(f"Failed to generate technical consensus for {symbol}: no timeframe models available. Try training first.")

    # Weighted sum based on Historical Validation Sharpe (min bounded at 0.1 to avoid negatives)
    total_weight = 0.0
    weighted_signal = 0.0

    for s in signals:
        w = max(s["validation_sharpe"], 0.1)
        weighted_signal += s["signal_raw"] * w
        total_weight += w

    # -1 to +1
    consensus_raw = weighted_signal / total_weight if total_weight > 0 else 0.0

    # Map -1..+1 to 0..100
    # Equation: Score = (Raw + 1) / 2 * 100
    score_0_100 = round((consensus_raw + 1) / 2 * 100, 1)

    if score_0_100 >= 80:
        label = "Strong Bullish"
    elif score_0_100 >= 60:
        label = "Bullish Focus"
    elif score_0_100 >= 40:
        label = "Mixed / Neutral"
    elif score_0_100 >= 20:
        label = "Bearish Focus"
    else:
        label = "Strong Bearish"

    return {
        "symbol": symbol,
        "consensus_score": score_0_100,
        "consensus_label": label,
        "signals": signals,
        "generated_at": pd.Timestamp.utcnow().isoformat()
    }
