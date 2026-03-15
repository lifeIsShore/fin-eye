"""
Service layer for ML-driven Technical Consensus (MVP-TECH-02).

BUG-003 RESOLUTION:
  Original bug: TIMEFRAMES listed ["1h", "4h"] only because 1d/1wk/1mo models
  had not been trained yet. A later change added all 5 timeframes to the list
  without training those models, causing silent skips on every consensus call.

  Fix applied here:
    1. TIMEFRAMES is now derived dynamically from the model registry — only
       timeframes that have a trained artifact on disk are included. No more
       hardcoded list that drifts out of sync with what is actually trained.

    2. engineer_features() is called with the horizon from the registry record
       so inference uses the same feature construction as training.

    3. Data fetching uses the updated OHLCVFetcher which handles chunked
       intraday fetching internally — period arg is only passed for daily+.

    4. If no models exist at all, compute_technical_consensus raises a clear
       error rather than silently returning a neutral score.
"""

import os
import json
import logging
import joblib

import pandas as pd
import numpy as np

from app.services.market_data import OHLCVFetcher
from app.services.ml_pipeline import (
    engineer_features,
    FEATURES,
    ARTIFACT_DIR,
    REGISTRY_FILE,
    TIMEFRAME_HORIZON,
    DEFAULT_HORIZON,
)

logger = logging.getLogger(__name__)


# ── Registry helpers ──────────────────────────────────────────────────────────

def get_latest_model_metadata(symbol: str, timeframe: str) -> dict:
    """
    Reads the JSONL registry and returns the most recent record for the given
    symbol + timeframe combination. Returns {} if nothing found.
    """
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
                    latest = record   # last entry wins
    except Exception as e:
        logger.error(f"Error reading model registry: {e}")

    return latest


def get_trained_timeframes(symbol: str) -> list[str]:
    """
    BUG-003 FIX: Derive the active timeframe list from the registry + disk.

    A timeframe is considered active only when ALL of these are true:
      1. A registry entry exists for (symbol, timeframe)
      2. The artifact file referenced in the registry exists on disk
      3. The recorded validation_sharpe is > 0 (not a known-bad fallback)

    This replaces the hardcoded TIMEFRAMES list that was the root of BUG-003.
    """
    if not os.path.exists(REGISTRY_FILE):
        return []

    # Collect latest record per timeframe (last entry in registry wins)
    latest_per_tf: dict[str, dict] = {}
    try:
        with open(REGISTRY_FILE, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("symbol") == symbol:
                    tf = record.get("timeframe", "")
                    if tf:
                        latest_per_tf[tf] = record
    except Exception as e:
        logger.error(f"Error scanning registry for {symbol}: {e}")
        return []

    active = []
    for tf, record in latest_per_tf.items():
        artifact_file = record.get("artifact_file", "")
        artifact_path = os.path.join(ARTIFACT_DIR, artifact_file)
        sharpe        = record.get("validation_sharpe", -99)

        if not artifact_file:
            logger.debug("Skipping %s/%s — no artifact_file in registry", symbol, tf)
            continue
        if not os.path.exists(artifact_path):
            logger.debug("Skipping %s/%s — artifact missing: %s", symbol, tf, artifact_path)
            continue
        if sharpe <= 0:
            logger.debug(
                "Skipping %s/%s — Sharpe=%.3f (non-positive, model not trusted)",
                symbol, tf, sharpe
            )
            continue

        active.append(tf)
        logger.debug("Active timeframe: %s/%s  Sharpe=%.3f", symbol, tf, sharpe)

    logger.info("Active trained timeframes for %s: %s", symbol, active or "none")
    return active


def load_model_instance(artifact_file: str):
    path = os.path.join(ARTIFACT_DIR, artifact_file)
    if not os.path.exists(path):
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        logger.error(f"Failed to load model artifact {artifact_file}: {e}")
        return None


# ── Signal generation ─────────────────────────────────────────────────────────

def generate_timeframe_signal(symbol: str, timeframe: str) -> dict:
    """
    Runs inference for a single timeframe and returns a signal dict:
    {
        "timeframe":        "4h",
        "direction":        "Bullish",
        "signal_raw":       0.8,        # in [-1, +1]
        "confidence":       80.0,       # in [50, 100]
        "validation_sharpe": 1.85,
        "model_used":       "xgboost",
        "horizon_periods":  3,
    }
    """
    meta = get_latest_model_metadata(symbol, timeframe)
    if not meta:
        raise ValueError(f"No trained model found for {symbol}/{timeframe}")

    model = load_model_instance(meta["artifact_file"])
    if model is None:
        raise ValueError(f"Model artifact missing for {symbol}/{timeframe}: {meta['artifact_file']}")

    # ── Fetch OHLCV data for inference ────────────────────────────────────────
    # OHLCVFetcher handles chunked intraday fetching internally.
    # For intraday (1h/4h): period is ignored, chunked fetch up to 730 days.
    # For daily+: use 5y to match the training window.
    if timeframe in ("1h", "4h"):
        # period is ignored for intraday — chunked fetcher always gets max data
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5y", interval="1h")
    else:
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5y", interval=timeframe)

    if len(records) < 60:
        raise ValueError(
            f"Not enough data for inference on {symbol}/{timeframe}: "
            f"got {len(records)} bars (need ≥ 60)"
        )

    df = pd.DataFrame([
        {
            "date":   r.timestamp,
            "open":   r.open,
            "high":   r.high,
            "low":    r.low,
            "close":  r.close,
            "volume": r.volume,
        }
        for r in records
    ])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)

    # Resample 1h → 4h for the 4h timeframe (yfinance has no native 4h)
    if timeframe == "4h":
        df = df.resample("4h", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna()

    # ── Feature engineering ───────────────────────────────────────────────────
    # Use the same horizon that was used during training so the feature
    # construction is identical between train time and inference time.
    horizon = meta.get("horizon_periods", TIMEFRAME_HORIZON.get(timeframe, DEFAULT_HORIZON))

    df_feat = engineer_features(df, horizon=horizon)
    if df_feat.empty:
        raise ValueError(
            f"Feature engineering returned empty DataFrame for {symbol}/{timeframe}. "
            f"Check OHLCV data quality."
        )

    # ── Inference on the most recent bar ─────────────────────────────────────
    latest = df_feat.iloc[-1:].copy()
    latest["close_raw"] = float(df["close"].iloc[-1])

    # Guard: ensure all expected features are present
    missing = [f for f in FEATURES if f not in latest.columns]
    if missing:
        raise ValueError(
            f"Missing features for inference on {symbol}/{timeframe}: {missing}. "
            f"Re-train the model after adding new features."
        )

    X = latest[FEATURES + ["close_raw"]]

    probs     = model.predict_proba(X)
    prob_up   = float(probs[0, 1])

    direction_val = 1 if prob_up > 0.5 else -1
    confidence    = max(prob_up, 1.0 - prob_up) * 100.0
    signal_raw    = direction_val * (confidence / 100.0)

    return {
        "timeframe":         timeframe,
        "direction":         "Bullish" if direction_val > 0 else "Bearish",
        "signal_raw":        round(signal_raw, 4),
        "confidence":        round(confidence, 1),
        "validation_sharpe": meta.get("validation_sharpe", 0.0),
        "model_used":        meta.get("model_name", "unknown"),
        "horizon_periods":   horizon,
    }


# ── Consensus aggregation ─────────────────────────────────────────────────────

def compute_technical_consensus(symbol: str) -> dict:
    """
    Aggregates signals across all trained timeframes into a single 0–100 score.

    Only timeframes with a trained artifact AND positive Sharpe are included
    (see get_trained_timeframes). The score is a Sharpe-weighted average of the
    per-timeframe raw signals, mapped from [-1, +1] to [0, 100].

    Raises ValueError if no valid models exist for the symbol.
    """
    active_timeframes = get_trained_timeframes(symbol)

    if not active_timeframes:
        raise ValueError(
            f"No trained models found for {symbol}. "
            f"Run the training pipeline first: POST /api/v1/admin/ml/train?symbol={symbol}"
        )

    signals = []
    skipped = []

    for tf in active_timeframes:
        try:
            sig = generate_timeframe_signal(symbol, tf)
            signals.append(sig)
            logger.info(
                "Signal %s/%s: %s  conf=%.1f%%  Sharpe=%.3f",
                symbol, tf,
                sig["direction"],
                sig["confidence"],
                sig["validation_sharpe"],
            )
        except Exception as e:
            skipped.append(tf)
            logger.warning("Skipped signal for %s/%s: %s", symbol, tf, e)

    if not signals:
        raise ValueError(
            f"All timeframe signals failed for {symbol}. "
            f"Tried: {active_timeframes}. Check model artifacts and OHLCV data."
        )

    if skipped:
        logger.warning(
            "Partial consensus for %s — %d/%d timeframes succeeded. Skipped: %s",
            symbol, len(signals), len(active_timeframes), skipped,
        )

    # Sharpe-weighted consensus (floor weight at 0.1 to avoid zero-weight signals)
    total_weight    = 0.0
    weighted_signal = 0.0

    for s in signals:
        w = max(s["validation_sharpe"], 0.1)
        weighted_signal += s["signal_raw"] * w
        total_weight    += w

    consensus_raw = weighted_signal / total_weight if total_weight > 0 else 0.0

    # Map [-1, +1] → [0, 100]
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
        "symbol":            symbol,
        "consensus_score":   score_0_100,
        "consensus_label":   label,
        "signals":           signals,
        "timeframes_used":   [s["timeframe"] for s in signals],
        "timeframes_skipped": skipped,
        "generated_at":      pd.Timestamp.utcnow().isoformat(),
    }
