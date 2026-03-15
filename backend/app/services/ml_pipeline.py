"""
Machine Learning Pipeline for Technical Analysis (MVP-TECH-01)

MLflow integration: every training run is now logged to the local MLflow
tracking server in addition to the existing model_registry.jsonl.

MLflow gives you:
  - A UI at http://localhost:5000 to browse all training runs
  - Per-run metrics (Sharpe, accuracy, return) for all 3 competing models
  - Artifact storage of the winning .joblib file
  - Model staging: Staging → Production → Archived
  - One-click revert to any previous run's artifact

The JSONL registry is kept unchanged — it is still the fast runtime path
used by technical_service.py for inference. MLflow is the management layer.

MLflow is optional: if it is not installed or not running, the pipeline
logs a warning and continues without it. Nothing breaks.

BACKEND: SQLite (backend/data/mlflow.db)
  - No deprecation warnings (filesystem store deprecated Feb 2026)
  - Works even when the UI server is not running
  - Start the UI with: start_mlflow.bat
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from prophet import Prophet

logger = logging.getLogger(__name__)

ARTIFACT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")
REGISTRY_FILE = os.path.join(ARTIFACT_DIR, "model_registry.jsonl")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# ── MLflow config ─────────────────────────────────────────────────────────────
# Default: SQLite database in backend/data/mlflow.db
#   - No UI server required to log runs — writes directly to the DB file
#   - No deprecation warnings (filesystem store deprecated in MLflow Feb 2026)
#   - Start UI with start_mlflow.bat to browse runs at http://localhost:5000
#
# Override with MLFLOW_TRACKING_URI env var to point at a remote server:
#   set MLFLOW_TRACKING_URI=http://my-mlflow-server:5000

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_MLFLOW_DB = _DATA_DIR / "mlflow.db"
_MLFLOW_ARTIFACTS = _DATA_DIR / "mlartifacts"

MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{_MLFLOW_DB}",
)
MLFLOW_ARTIFACT_ROOT = str(_MLFLOW_ARTIFACTS)
MLFLOW_EXPERIMENT    = "fin-eye-technical-signals"

# ── Quality gates ─────────────────────────────────────────────────────────────
MIN_WINNER_ACCURACY = 0.50
MIN_WINNER_SHARPE   = 0.0

# ── Timeframe-adaptive prediction horizon ────────────────────────────────────
TIMEFRAME_HORIZON = {
    "1h":  3,
    "4h":  3,
    "1d":  3,
    "1wk": 2,
    "1mo": 1,
}
DEFAULT_HORIZON = 3


# ── MLflow helpers ────────────────────────────────────────────────────────────

def _get_mlflow():
    """Lazily import mlflow. Returns module or None if unavailable."""
    try:
        import mlflow  # noqa: PLC0415
        return mlflow
    except ImportError:
        logger.warning(
            "mlflow not installed — training will proceed without experiment tracking. "
            "Install with: pip install mlflow"
        )
        return None


def _start_mlflow_run(mlflow, symbol: str, timeframe: str, horizon: int):
    """Set tracking URI, ensure experiment exists, start and return a run."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        run = mlflow.start_run(
            run_name=f"{symbol}_{timeframe}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        mlflow.set_tags({
            "symbol":    symbol,
            "timeframe": timeframe,
            "horizon":   str(horizon),
            "pipeline":  "fin-eye-ml-v2",
        })
        return run
    except Exception as e:
        logger.warning("MLflow run start failed: %s — continuing without tracking", e)
        return None


def _log_model_metrics(mlflow, model_name: str, metrics: dict):
    try:
        mlflow.log_metrics({
            f"{model_name}.sharpe_ratio": round(metrics.get("sharpe_ratio", -99), 4),
            f"{model_name}.accuracy":     round(metrics.get("accuracy", 0), 4),
            f"{model_name}.total_return": round(metrics.get("total_return", 0), 4),
        })
    except Exception as e:
        logger.debug("MLflow metric log failed: %s", e)


def _log_winner_artifact(mlflow, artifact_path: str):
    try:
        mlflow.log_artifact(artifact_path, artifact_path="model")
    except Exception as e:
        logger.debug("MLflow artifact log failed: %s", e)


def _register_model_in_mlflow(mlflow, run_id: str, symbol: str,
                               timeframe: str, artifact_path: str):
    try:
        model_name = f"fin-eye-{symbol}-{timeframe}".replace("/", "-")
        model_uri  = f"runs:/{run_id}/model/{os.path.basename(artifact_path)}"
        result     = mlflow.register_model(model_uri, model_name)
        logger.info("MLflow: registered '%s' version %s", model_name, result.version)
        return result
    except Exception as e:
        logger.warning("MLflow model registration failed: %s", e)
        return None


# ── Feature Engineering ───────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame, horizon: int = DEFAULT_HORIZON) -> pd.DataFrame:
    if len(df) < 60:
        return pd.DataFrame()

    d = df.copy()
    close  = d["close"]
    volume = d["volume"] if "volume" in d.columns else pd.Series(1, index=d.index)
    high   = d["high"]   if "high"   in d.columns else close
    low    = d["low"]    if "low"    in d.columns else close

    d["ret_1"] = close.pct_change(1)
    d["ret_3"] = close.pct_change(3)
    d["ret_5"] = close.pct_change(5)

    d["sma_10"] = close.rolling(10).mean()
    d["sma_20"] = close.rolling(20).mean()
    d["sma_50"] = close.rolling(50).mean()
    d["sma_cross_10_20"] = (d["sma_10"] / d["sma_20"]) - 1
    d["sma_cross_20_50"] = (d["sma_20"] / d["sma_50"]) - 1
    d["price_vs_sma50"]  = (close / d["sma_50"]) - 1

    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-9)
    d["rsi_14"] = 100 - (100 / (1 + rs))

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    d["macd"]        = ema_12 - ema_26
    d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["macd_hist"]   = d["macd"] - d["macd_signal"]

    d["std_20"]   = close.rolling(20).std()
    d["bb_upper"] = d["sma_20"] + (d["std_20"] * 2)
    d["bb_lower"] = d["sma_20"] - (d["std_20"] * 2)
    d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / d["sma_20"]
    d["bb_pb"]    = (close - d["bb_lower"]) / (
        (d["bb_upper"] - d["bb_lower"]).replace(0, 1e-9)
    )

    d["mom_10"] = close.pct_change(10)
    d["mom_20"] = close.pct_change(20)

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    d["atr_14"]  = tr.rolling(14).mean()
    d["atr_pct"] = d["atr_14"] / close

    vol_ma20          = volume.rolling(20).mean().replace(0, 1e-9)
    d["volume_ratio"] = volume / vol_ma20

    d["target_ret_fwd"] = close.shift(-horizon) / close - 1
    d["target"]         = (d["target_ret_fwd"] > 0).astype(int)

    d.dropna(inplace=True)
    return d


FEATURES = [
    "ret_1", "ret_3", "ret_5",
    "sma_cross_10_20", "sma_cross_20_50", "price_vs_sma50",
    "rsi_14", "macd", "macd_hist",
    "bb_width", "bb_pb", "atr_pct",
    "mom_10", "mom_20",
    "volume_ratio",
]


# ── Diagnostics ───────────────────────────────────────────────────────────────

def log_training_diagnostics(
    symbol: str, timeframe: str,
    df: pd.DataFrame, train_df: pd.DataFrame, val_df: pd.DataFrame,
) -> dict:
    total_rows     = len(df)
    train_rows     = len(train_df)
    val_rows       = len(val_df)
    target_counts  = df["target"].value_counts().to_dict()
    n_positive     = int(target_counts.get(1, 0))
    target_balance = round(n_positive / total_rows, 3) if total_rows else 0.5
    feature_std    = df[FEATURES].std()
    low_var        = feature_std[feature_std < 1e-6].index.tolist()

    logger.info(
        f"[{symbol}/{timeframe}] rows={total_rows}  train={train_rows}  "
        f"val={val_rows}  target_up={target_balance:.1%}  low_var={low_var or 'none'}"
    )
    if val_rows < 50:
        logger.warning(f"[{symbol}/{timeframe}] Only {val_rows} val rows.")
    if abs(target_balance - 0.5) > 0.15:
        logger.warning(f"[{symbol}/{timeframe}] Imbalanced: {target_balance:.1%} UP.")
    if low_var:
        logger.warning(f"[{symbol}/{timeframe}] Low-variance features: {low_var}")

    return {
        "train_rows":            train_rows,
        "val_rows":              val_rows,
        "total_rows":            total_rows,
        "target_balance_up_pct": round(target_balance * 100, 1),
        "low_variance_features": low_var,
        "n_features":            len(FEATURES),
    }


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_predictions(y_true, y_pred, returns) -> Dict[str, float]:
    accuracy  = float(np.mean(y_true == y_pred))
    strat_ret = np.where(y_pred == 1, returns, 0)
    mean_ret  = np.mean(strat_ret)
    std_ret   = np.std(strat_ret)
    sharpe    = 0.0 if std_ret < 1e-6 else float((mean_ret / std_ret) * np.sqrt(252))
    return {
        "accuracy":     accuracy,
        "sharpe_ratio": sharpe,
        "total_return": float(np.sum(strat_ret)),
    }


# ── Model wrappers ────────────────────────────────────────────────────────────

class LogisticWrapper:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model  = LogisticRegression(
            class_weight="balanced", max_iter=1000, C=0.1, dual=False,
        )
    def fit(self, X, y):
        self.scaler.fit(X)
        self.model.fit(self.scaler.transform(X), y)
    def predict_proba(self, X):
        return self.model.predict_proba(self.scaler.transform(X))


class XGBoostWrapper:
    def __init__(self, n_positive: int = 1, n_negative: int = 1):
        spw = max(1.0, n_negative / max(n_positive, 1))
        self.model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            gamma=0.1, scale_pos_weight=spw, eval_metric="logloss", random_state=42,
        )
    def fit(self, X, y):           self.model.fit(X, y)
    def predict_proba(self, X):    return self.model.predict_proba(X)


class ProphetWrapper:
    def __init__(self):
        self.model = Prophet(daily_seasonality=False, yearly_seasonality=False)
    def fit(self, X, y):
        df = pd.DataFrame({
            "ds": pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values,
            "y":  X["close_raw"],
        })
        self.model.fit(df)
    def predict_proba(self, X):
        df       = pd.DataFrame({"ds": pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values})
        forecast = self.model.predict(df)
        diff     = forecast["yhat"].diff().fillna(0).values
        probs    = np.where(diff > 0, 0.8, 0.2)
        out      = np.zeros((len(X), 2))
        out[:, 1] = probs
        out[:, 0] = 1 - probs
        return out


# ── Winner selection ──────────────────────────────────────────────────────────

def select_winner(results: Dict[str, Dict]) -> Tuple[Optional[str], float]:
    eligible = {
        name: m for name, m in results.items()
        if m.get("accuracy", 0) >= MIN_WINNER_ACCURACY
        and m.get("sharpe_ratio", -99) >= MIN_WINNER_SHARPE
        and not m.get("disqualified", False)
    }
    if eligible:
        best = max(eligible, key=lambda n: eligible[n]["sharpe_ratio"])
        return best, eligible[best]["sharpe_ratio"]

    logger.warning("No model passed quality gates — falling back to highest-accuracy.")
    fallback = max(results, key=lambda n: results[n].get("accuracy", 0))
    return fallback, results[fallback].get("sharpe_ratio", -99.0)


# ── Training pipeline ─────────────────────────────────────────────────────────

def run_training_pipeline(
    symbol: str,
    timeframe: str,
    df_history: pd.DataFrame,
) -> Dict[str, Any]:
    """
    End-to-end pipeline: feature engineering → train 3 models → pick winner
    → persist to disk → log to MLflow SQLite (if available).

    MLflow logs directly to backend/data/mlflow.db — no UI server required.
    Start the UI separately with start_mlflow.bat to browse runs.
    """
    logger.info(f"Training pipeline: {symbol}/{timeframe}  input_rows={len(df_history)}")

    if len(df_history) < 200:
        raise ValueError(f"Need > 200 rows, got {len(df_history)}")

    horizon = TIMEFRAME_HORIZON.get(timeframe, DEFAULT_HORIZON)
    df      = engineer_features(df_history, horizon=horizon)
    df["close_raw"] = df_history["close"].reindex(df.index)

    if len(df) < 100:
        raise ValueError(f"Only {len(df)} rows after feature engineering.")

    split_idx   = int(len(df) * 0.8)
    train_df    = df.iloc[:split_idx]
    val_df      = df.iloc[split_idx:]
    diagnostics = log_training_diagnostics(symbol, timeframe, df, train_df, val_df)

    n_pos = int((train_df["target"] == 1).sum())
    n_neg = int((train_df["target"] == 0).sum())

    X_train     = train_df[FEATURES + ["close_raw"]]
    y_train     = train_df["target"]
    X_val       = val_df[FEATURES + ["close_raw"]]
    y_val       = val_df["target"].values
    returns_val = val_df["target_ret_fwd"].values

    models = {
        "logistic": LogisticWrapper(),
        "xgboost":  XGBoostWrapper(n_positive=n_pos, n_negative=n_neg),
        "prophet":  ProphetWrapper(),
    }
    results: Dict[str, Dict] = {}

    # ── MLflow: start run ─────────────────────────────────────────────────────
    mlflow     = _get_mlflow()
    mlflow_run = _start_mlflow_run(mlflow, symbol, timeframe, horizon) if mlflow else None

    try:
        if mlflow and mlflow_run:
            mlflow.log_params({
                "symbol":          symbol,
                "timeframe":       timeframe,
                "horizon_periods": horizon,
                "n_features":      len(FEATURES),
                "total_rows":      diagnostics["total_rows"],
                "train_rows":      diagnostics["train_rows"],
                "val_rows":        diagnostics["val_rows"],
                "target_balance":  diagnostics["target_balance_up_pct"],
                "features":        ",".join(FEATURES),
                "min_sharpe_gate": MIN_WINNER_SHARPE,
                "min_acc_gate":    MIN_WINNER_ACCURACY,
            })

        # ── Train all models ──────────────────────────────────────────────────
        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                probs   = model.predict_proba(X_val)[:, 1]
                preds   = (probs > 0.5).astype(int)
                metrics = evaluate_predictions(y_val, preds, returns_val)
                results[name] = metrics

                logger.info(
                    f"  [{name}]  Sharpe={metrics['sharpe_ratio']:>7.3f}  "
                    f"Acc={metrics['accuracy']:.1%}  Ret={metrics['total_return']:+.3f}"
                )

                if mlflow and mlflow_run:
                    _log_model_metrics(mlflow, name, metrics)

                if name == "prophet" and metrics["accuracy"] == 0.0:
                    logger.warning("Prophet accuracy=0.0 — disqualifying.")
                    results[name].update({
                        "sharpe_ratio": -99.0,
                        "disqualified": True,
                        "disqualify_reason": "accuracy == 0.0",
                    })

            except Exception as e:
                logger.error(f"  [{name}] FAILED: {e}")
                results[name] = {
                    "accuracy": 0.0, "sharpe_ratio": -99.0, "total_return": 0.0,
                    "disqualified": True, "disqualify_reason": str(e),
                }
                if mlflow and mlflow_run:
                    _log_model_metrics(mlflow, name, results[name])

        # ── Select winner ─────────────────────────────────────────────────────
        best_name, best_sharpe = select_winner(results)
        best_obj = models[best_name]
        best_obj.fit(X_train, y_train)

        quality_gate_passed = (
            best_sharpe >= MIN_WINNER_SHARPE
            and results.get(best_name, {}).get("accuracy", 0) >= MIN_WINNER_ACCURACY
        )

        # ── Persist .joblib ───────────────────────────────────────────────────
        timestamp     = datetime.utcnow().isoformat()
        artifact_name = f"{symbol}_{timeframe}_winner.joblib"
        artifact_path = os.path.join(ARTIFACT_DIR, artifact_name)
        joblib.dump(best_obj, artifact_path)

        # ── MLflow: log winner + register ─────────────────────────────────────
        mlflow_run_id = None
        if mlflow and mlflow_run:
            try:
                mlflow_run_id = mlflow_run.info.run_id
                mlflow.log_metrics({
                    "winner.sharpe_ratio": round(best_sharpe, 4),
                    "winner.accuracy":     round(results[best_name].get("accuracy", 0), 4),
                    "winner.total_return": round(results[best_name].get("total_return", 0), 4),
                })
                mlflow.set_tags({
                    "winner_model": best_name,
                    "quality_gate": "pass" if quality_gate_passed else "fallback",
                    "artifact_file": artifact_name,
                })
                _log_winner_artifact(mlflow, artifact_path)
                _register_model_in_mlflow(
                    mlflow, mlflow_run_id, symbol, timeframe, artifact_path
                )
            except Exception as e:
                logger.warning("MLflow winner logging failed: %s", e)

        # ── JSONL registry ────────────────────────────────────────────────────
        metadata = {
            "symbol":            symbol,
            "timeframe":         timeframe,
            "model_name":        best_name,
            "trained_at":        timestamp,
            "artifact_file":     artifact_name,
            "validation_sharpe": best_sharpe,
            "horizon_periods":   horizon,
            "metrics":           results,
            "diagnostics":       diagnostics,
            "mlflow_run_id":     mlflow_run_id,
        }

        with open(REGISTRY_FILE, "a") as f:
            f.write(json.dumps(metadata) + "\n")

        logger.info(
            f"Winner {symbol}/{timeframe}: {best_name}  "
            f"Sharpe={best_sharpe:.3f}  "
            f"Acc={results.get(best_name, {}).get('accuracy', 0):.1%}  "
            f"val_rows={diagnostics['val_rows']}  horizon={horizon}"
            + (f"  mlflow_run={mlflow_run_id}" if mlflow_run_id else "")
        )

        return metadata

    finally:
        if mlflow and mlflow_run:
            try:
                mlflow.end_run()
            except Exception:
                pass
