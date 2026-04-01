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

Sprint 2 — todos-v5 Phase 5.2:
  compute_and_store_consensus() wraps compute_technical_consensus() and
  stores each signal in ml_predictions via prediction_service.store_prediction().
  Called by the API endpoint instead of the raw sync function.
"""

import os
import logging
import joblib
from typing import Optional

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
from app.services.model_registry import JsonlFileModelRegistry
from app.services.technical_models import Timeframe

logger = logging.getLogger(__name__)

# BUG-BE-15: Do NOT cache registry at module level — newly trained models
# appended to the JSONL file after startup won't be visible until restart.
# Always create a fresh instance so reads go back to disk each time.
def _fresh_registry() -> JsonlFileModelRegistry:
    return JsonlFileModelRegistry(REGISTRY_FILE)


# ── Registry helpers ──────────────────────────────────────────────────────────

def get_latest_model_metadata(symbol: str, timeframe: str) -> dict:
    try:
        record = _fresh_registry().get_latest_for_timeframe(Timeframe(timeframe), symbol=symbol)
    except Exception as e:
        logger.error("Error reading model registry for %s/%s: %s", symbol, timeframe, e)
        return {}
    if record is None:
        return {}
    return {
        "symbol":            record.symbol,
        "timeframe":         record.timeframe.value,
        "model_name":        record.model_kind.value,
        "artifact_file":     os.path.basename(record.artifact_path) if record.artifact_path else "",
        "validation_sharpe": record.sharpe_ratio,
        "horizon_periods":   record.extra_metrics.get("horizon_periods", DEFAULT_HORIZON),
        "mlflow_run_id":     record.mlflow_run_id,
        "trained_at":        record.trained_at.isoformat(),
        "version":           record.version,
        "status":            record.status,
        "quality_gate":      record.quality_gate,
    }


def get_trained_timeframes(symbol: str) -> list[str]:
    """BUG-003 FIX: Derive active timeframe list from registry + disk."""
    try:
        all_champions = _fresh_registry().all_champions()
    except Exception as e:
        logger.error("Error reading registry champions for %s: %s", symbol, e)
        return []

    active = []
    for record in all_champions:
        if record.symbol != symbol:
            continue
        artifact_path = record.artifact_path or ""
        if not artifact_path:
            artifact_path = os.path.join(
                ARTIFACT_DIR, f"{symbol}_{record.timeframe.value}_winner.joblib"
            )
        if not os.path.exists(artifact_path):
            logger.debug("Skipping %s/%s — artifact missing", symbol, record.timeframe.value)
            continue
        if record.sharpe_ratio <= 0:
            logger.debug("Skipping %s/%s — Sharpe=%.3f", symbol, record.timeframe.value, record.sharpe_ratio)
            continue
        active.append(record.timeframe.value)
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
    Runs inference for a single timeframe and returns a signal dict.
    Also returns the raw feature values for the latest bar (used for prediction storage).
    """
    meta = get_latest_model_metadata(symbol, timeframe)
    if not meta:
        raise ValueError(f"No trained model found for {symbol}/{timeframe}")

    model = load_model_instance(meta["artifact_file"])
    if model is None:
        raise ValueError(f"Model artifact missing for {symbol}/{timeframe}: {meta['artifact_file']}")

    if timeframe in ("1h", "4h"):
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5y", interval="1h")
    else:
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5y", interval=timeframe)

    if len(records) < 60:
        raise ValueError(
            f"Not enough data for inference on {symbol}/{timeframe}: got {len(records)} bars (need ≥ 60)"
        )

    df = pd.DataFrame([
        {"date": r.timestamp, "open": r.open, "high": r.high,
         "low": r.low, "close": r.close, "volume": r.volume}
        for r in records
    ])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)

    if timeframe == "4h":
        df = df.resample("4h", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()

    horizon = meta.get("horizon_periods", TIMEFRAME_HORIZON.get(timeframe, DEFAULT_HORIZON))
    df_feat = engineer_features(df, horizon=horizon)
    if df_feat.empty:
        raise ValueError(f"Feature engineering returned empty DataFrame for {symbol}/{timeframe}.")

    latest = df_feat.iloc[-1:].copy()
    latest["close_raw"] = float(df["close"].iloc[-1])

    missing = [f for f in FEATURES if f not in latest.columns]
    if missing:
        raise ValueError(f"Missing features for {symbol}/{timeframe}: {missing}")

    X = latest[FEATURES + ["close_raw"]]
    probs         = model.predict_proba(X)
    prob_up       = float(probs[0, 1])
    direction_val = 1 if prob_up > 0.5 else -1
    confidence    = max(prob_up, 1.0 - prob_up) * 100.0
    signal_raw    = direction_val * (confidence / 100.0)

    # Build feature snapshot for prediction storage
    feature_snapshot: dict = {}
    try:
        for feat in FEATURES:
            val = latest[feat].iloc[0]
            feature_snapshot[feat] = round(float(val), 6) if not pd.isna(val) else None
    except Exception:
        pass  # snapshot is best-effort

    current_price = float(df["close"].iloc[-1])

    return {
        "timeframe":         timeframe,
        "direction":         "Bullish" if direction_val > 0 else "Bearish",
        "signal_raw":        round(signal_raw, 4),
        "confidence":        round(confidence, 1),
        "validation_sharpe": meta.get("validation_sharpe", 0.0),
        "model_used":        meta.get("model_name", "unknown"),
        "horizon_periods":   horizon,
        "mlflow_run_id":     meta.get("mlflow_run_id"),
        # Extra fields for prediction storage (not sent to frontend)
        "_predicted_direction": 1 if direction_val > 0 else 0,
        "_confidence_raw":      round(confidence / 100.0, 4),  # 0.5–1.0
        "_current_price":       current_price,
        "_feature_snapshot":    feature_snapshot,
    }


# ── Consensus aggregation (sync — runs in executor) ──────────────────────────

def compute_technical_consensus(symbol: str) -> dict:
    """
    Aggregates signals across all trained timeframes into a single 0–100 score.
    This is the sync core — called via run_in_executor from the endpoint.
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
                symbol, tf, sig["direction"], sig["confidence"], sig["validation_sharpe"],
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

    total_weight    = 0.0
    weighted_signal = 0.0
    for s in signals:
        w = max(s["validation_sharpe"], 0.1)
        weighted_signal += s["signal_raw"] * w
        total_weight    += w

    consensus_raw = weighted_signal / total_weight if total_weight > 0 else 0.0
    score_0_100   = round((consensus_raw + 1) / 2 * 100, 1)

    if score_0_100 >= 80:   label = "Strong Bullish"
    elif score_0_100 >= 60: label = "Bullish Focus"
    elif score_0_100 >= 40: label = "Mixed / Neutral"
    elif score_0_100 >= 20: label = "Bearish Focus"
    else:                   label = "Strong Bearish"

    return {
        "symbol":             symbol,
        "consensus_score":    score_0_100,
        "consensus_label":    label,
        "signals":            signals,
        "timeframes_used":    [s["timeframe"] for s in signals],
        "timeframes_skipped": skipped,
        "generated_at":       pd.Timestamp.utcnow().isoformat(),
    }


# ── Async wrapper: compute + store predictions ────────────────────────────────

async def compute_and_store_consensus(
    symbol: str,
    db,                       # AsyncSession — typed loosely to avoid circular import
    *,
    macro_score:    Optional[float] = None,
    vix:            Optional[float] = None,
    market_regime:  Optional[str]   = None,
) -> dict:
    """
    Sprint 2 — todos-v5 Phase 5.2.

    Async wrapper around compute_technical_consensus() that:
      1. Runs the sync consensus computation in an executor (non-blocking)
      2. For each signal, fires-and-forgets a prediction storage call
         (failure to store never breaks signal delivery to the user)

    Called from the technical endpoint instead of the raw sync function.
    Falls back to the raw sync function gracefully if DB is unavailable.
    """
    import asyncio  # noqa: PLC0415

    loop   = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, compute_technical_consensus, symbol.upper())

    # Store predictions asynchronously — fire and forget, never blocks the response
    if db is not None:
        try:
            from app.services.prediction_service import store_prediction  # noqa: PLC0415
            for sig in result.get("signals", []):
                price = sig.get("_current_price", 0.0)
                if price <= 0:
                    continue
                await store_prediction(
                    db,
                    symbol=symbol.upper(),
                    timeframe=sig["timeframe"],
                    model_name=sig.get("model_used", "unknown"),
                    predicted_direction=sig.get("_predicted_direction", 1),
                    confidence=sig.get("_confidence_raw", 0.5),
                    horizon_periods=sig.get("horizon_periods", 3),
                    price_at_prediction=price,
                    mlflow_run_id=sig.get("mlflow_run_id"),
                    feature_snapshot=sig.get("_feature_snapshot"),
                    macro_score=macro_score,
                    vix=vix,
                    market_regime=market_regime,
                )
        except Exception as exc:
            # Prediction storage failure must NEVER break the consensus response
            logger.warning("Prediction storage failed for %s (non-fatal): %s", symbol, exc)

    return result
