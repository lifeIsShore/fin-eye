"""
app/services/optuna_tuner.py

Sprint 6 — todos-v5 Phase 4.4

Optuna Bayesian hyperparameter tuning for XGBoost and LightGBM.

Design decisions (from todos-v5 brainstorm):
  - Gated behind ENABLE_HYPERTUNING env flag — never runs per-request
  - Runs as a nightly scheduler job, not during real-time inference
  - Best params stored in a JSON sidecar alongside the .joblib artifact
  - Training pipeline reads best params file if it exists, overrides defaults
  - Optuna DB stored at backend/data/optuna/ (one study per symbol/timeframe)
  - Uses SQLite storage so studies survive restarts

Tuning budget per symbol/timeframe: 30 trials (~5-10 minutes for XGBoost,
  ~3-7 minutes for LightGBM). Total for 10 symbols × 5 timeframes = 2,500 trials,
  spread across overnight hours.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR    = Path(__file__).parent.parent.parent / "data"
_OPTUNA_DIR  = _DATA_DIR / "optuna"
_PARAMS_DIR  = _DATA_DIR / "models"

_OPTUNA_DIR.mkdir(parents=True, exist_ok=True)

N_TRIALS_DEFAULT   = 30
N_TRIALS_QUICK     = 15   # for low-data timeframes (1wk, 1mo)
MIN_ROWS_FOR_TUNING = 300  # don't bother tuning with fewer rows


def _params_file(symbol: str, timeframe: str, model_name: str) -> Path:
    return _PARAMS_DIR / f"{symbol}_{timeframe}_{model_name}_best_params.json"


def load_best_params(symbol: str, timeframe: str, model_name: str) -> Optional[Dict[str, Any]]:
    """
    Load pre-tuned hyperparameters from the sidecar JSON file.
    Returns None if no tuned params exist (fall back to ml_pipeline defaults).
    Called inside run_training_pipeline() before model construction.
    """
    p = _params_file(symbol, timeframe, model_name)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Loaded %s tuned params for %s/%s", model_name, symbol, timeframe)
        return data.get("best_params")
    except Exception as exc:
        logger.warning("Could not load best params for %s/%s/%s: %s", symbol, timeframe, model_name, exc)
        return None


def _save_best_params(
    symbol: str, timeframe: str, model_name: str,
    best_params: dict, best_value: float, n_trials: int,
) -> None:
    p = _params_file(symbol, timeframe, model_name)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({
                "symbol":      symbol,
                "timeframe":   timeframe,
                "model_name":  model_name,
                "best_params": best_params,
                "best_value":  round(best_value, 6),
                "n_trials":    n_trials,
                "tuned_at":    datetime.utcnow().isoformat(),
            }, f, indent=2)
        logger.info("Saved %s best params for %s/%s (val_acc=%.4f)", model_name, symbol, timeframe, best_value)
    except Exception as exc:
        logger.warning("Could not save best params: %s", exc)


# ── XGBoost tuning ────────────────────────────────────────────────────────────

def tune_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val:   pd.DataFrame,
    y_val:   np.ndarray,
    features: list[str],
    symbol:   str,
    timeframe: str,
    n_trials: int = N_TRIALS_DEFAULT,
    study_storage: Optional[str] = None,
) -> Tuple[dict, float]:
    """
    Tune XGBoost hyperparameters via Optuna.
    Returns (best_params, best_val_accuracy).
    """
    try:
        import optuna  # noqa: PLC0415
        from xgboost import XGBClassifier  # noqa: PLC0415
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError as e:
        logger.warning("Optuna/XGBoost not available: %s", e)
        return {}, 0.0

    storage = study_storage or f"sqlite:///{_OPTUNA_DIR / f'{symbol}_{timeframe}_xgboost.db'}"

    def objective(trial):
        params = {
            "n_estimators":     trial.suggest_int("n_estimators", 100, 600),
            "max_depth":        trial.suggest_int("max_depth", 3, 7),
            "learning_rate":    trial.suggest_float("learning_rate", 0.005, 0.15, log=True),
            "subsample":        trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 15),
            "gamma":            trial.suggest_float("gamma", 0.0, 0.5),
            "reg_alpha":        trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda":       trial.suggest_float("reg_lambda", 0.5, 3.0),
        }
        model = XGBClassifier(
            **params, eval_metric="logloss", random_state=42, verbosity=0,
        )
        model.fit(X_train[features], y_train)
        preds = model.predict(X_val[features])
        return float(np.mean(preds == y_val))

    try:
        study = optuna.create_study(
            direction="maximize",
            storage=storage,
            study_name=f"{symbol}_{timeframe}_xgboost",
            load_if_exists=True,
        )
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best_params = study.best_params
        best_val    = study.best_value
        _save_best_params(symbol, timeframe, "xgboost", best_params, best_val, n_trials)
        return best_params, best_val
    except Exception as exc:
        logger.error("XGBoost Optuna study failed for %s/%s: %s", symbol, timeframe, exc)
        return {}, 0.0


# ── LightGBM tuning ───────────────────────────────────────────────────────────

def tune_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val:   pd.DataFrame,
    y_val:   np.ndarray,
    features: list[str],
    symbol:   str,
    timeframe: str,
    n_trials: int = N_TRIALS_DEFAULT,
    study_storage: Optional[str] = None,
) -> Tuple[dict, float]:
    """
    Tune LightGBM hyperparameters via Optuna.
    Returns (best_params, best_val_accuracy).
    """
    try:
        import optuna  # noqa: PLC0415
        from lightgbm import LGBMClassifier  # noqa: PLC0415
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError as e:
        logger.warning("Optuna/LightGBM not available: %s", e)
        return {}, 0.0

    storage = study_storage or f"sqlite:///{_OPTUNA_DIR / f'{symbol}_{timeframe}_lightgbm.db'}"

    def objective(trial):
        params = {
            "n_estimators":      trial.suggest_int("n_estimators", 100, 700),
            "max_depth":         trial.suggest_int("max_depth", 3, 8),
            "learning_rate":     trial.suggest_float("learning_rate", 0.005, 0.15, log=True),
            "subsample":         trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "num_leaves":        trial.suggest_int("num_leaves", 15, 127),
            "reg_alpha":         trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda":        trial.suggest_float("reg_lambda", 0.0, 2.0),
        }
        model = LGBMClassifier(
            **params, random_state=42, verbose=-1, n_jobs=1,
        )
        model.fit(X_train[features], y_train)
        preds = model.predict(X_val[features])
        return float(np.mean(preds == y_val))

    try:
        study = optuna.create_study(
            direction="maximize",
            storage=storage,
            study_name=f"{symbol}_{timeframe}_lightgbm",
            load_if_exists=True,
        )
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best_params = study.best_params
        best_val    = study.best_value
        _save_best_params(symbol, timeframe, "lightgbm", best_params, best_val, n_trials)
        return best_params, best_val
    except Exception as exc:
        logger.error("LightGBM Optuna study failed for %s/%s: %s", symbol, timeframe, exc)
        return {}, 0.0


# ── Batch tuning job ──────────────────────────────────────────────────────────

def run_tuning_for_symbol(symbol: str, timeframe: str) -> dict:
    """
    Full tuning pass for one symbol/timeframe: fetch data, engineer features,
    tune XGBoost + LightGBM, save best params.

    Runs synchronously — call via run_in_executor from async scheduler.

    Returns summary dict: { symbol, timeframe, xgb_best, lgbm_best, status }
    """
    from app.services.market_data import OHLCVFetcher  # noqa: PLC0415
    from app.services.ml_pipeline import (  # noqa: PLC0415
        engineer_features, FEATURES, TIMEFRAME_HORIZON, DEFAULT_HORIZON,
    )

    logger.info("Optuna tuning: %s/%s", symbol, timeframe)

    try:
        period  = "730d" if timeframe == "1h" else "5y"
        records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=timeframe)

        if len(records) < MIN_ROWS_FOR_TUNING:
            return {"symbol": symbol, "timeframe": timeframe, "status": "skipped_insufficient_data", "rows": len(records)}

        df = pd.DataFrame([
            {"date": r.timestamp, "open": r.open, "high": r.high,
             "low": r.low, "close": r.close, "volume": r.volume}
            for r in records
        ]).set_index("date").sort_index()

        if timeframe == "4h":
            df = df.resample("4h", label="left", closed="left").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
            ).dropna()

        horizon  = TIMEFRAME_HORIZON.get(timeframe, DEFAULT_HORIZON)
        df_feat  = engineer_features(df, horizon=horizon)

        if len(df_feat) < 100:
            return {"symbol": symbol, "timeframe": timeframe, "status": "skipped_insufficient_features"}

        split_idx = int(len(df_feat) * 0.8)
        train_df  = df_feat.iloc[:split_idx]
        val_df    = df_feat.iloc[split_idx:]

        X_train = train_df[FEATURES + ["close_raw"]] if "close_raw" in train_df.columns else train_df[FEATURES]
        y_train = train_df["target"]
        X_val   = val_df[FEATURES + ["close_raw"]]   if "close_raw" in val_df.columns   else val_df[FEATURES]
        y_val   = val_df["target"].values

        # Use quick trials for long timeframes (less data) to avoid overfitting
        n_trials = N_TRIALS_QUICK if timeframe in ("1wk", "1mo") else N_TRIALS_DEFAULT

        xgb_params, xgb_acc  = tune_xgboost(X_train, y_train, X_val, y_val, FEATURES, symbol, timeframe, n_trials)
        lgbm_params, lgbm_acc = tune_lightgbm(X_train, y_train, X_val, y_val, FEATURES, symbol, timeframe, n_trials)

        return {
            "symbol":      symbol,
            "timeframe":   timeframe,
            "status":      "ok",
            "n_trials":    n_trials,
            "xgb_best_acc":  round(xgb_acc * 100, 2),
            "lgbm_best_acc": round(lgbm_acc * 100, 2),
        }

    except Exception as exc:
        logger.error("Tuning failed for %s/%s: %s", symbol, timeframe, exc)
        return {"symbol": symbol, "timeframe": timeframe, "status": "error", "error": str(exc)}
