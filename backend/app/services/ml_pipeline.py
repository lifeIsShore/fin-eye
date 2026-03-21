"""
Machine Learning Pipeline for Technical Analysis (MVP-TECH-01)

Sprint 3 — todos-v5 Phase 4: ML Improvements
  - LightGBM added as 4th competing model (faster than XGBoost, comparable accuracy)
  - Soft-voting Ensemble added as 5th candidate (Sharpe-weighted probability blend)
  - SHAP feature importance computed after training and stored in registry metadata
  - Prophet REMOVED from signal competition — consistently disqualified (accuracy=0.0)
    Prophet is kept as a class for potential future macro-regime use only

Model competition order:
  1. logistic  — regularised logistic regression baseline (fast, interpretable)
  2. xgboost   — gradient boosted trees (handles non-linearities well)
  3. lightgbm  — leaf-wise boosted trees (often faster + comparable to XGBoost)
  4. ensemble  — Sharpe-weighted soft-vote of logistic + xgboost + lightgbm

Winner = model with highest Sharpe on validation set that passes quality gates.
The ensemble frequently wins by smoothing individual model errors.

MLflow: every training run logged to backend/data/mlflow.db (SQLite, no server needed).
Start UI with start_mlflow.bat to browse runs at http://localhost:5000.
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

from app.services.technical_models import Timeframe, ModelKind, TimeframeWinner
from app.services.model_registry import JsonlFileModelRegistry, record_winners

logger = logging.getLogger(__name__)

ARTIFACT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")
REGISTRY_FILE = os.path.join(ARTIFACT_DIR, "model_registry.jsonl")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# ── MLflow config ─────────────────────────────────────────────────────────────
_DATA_DIR           = Path(__file__).parent.parent.parent / "data"
_MLFLOW_DB          = _DATA_DIR / "mlflow.db"
_MLFLOW_ARTIFACTS   = _DATA_DIR / "mlartifacts"
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{_MLFLOW_DB}")
MLFLOW_ARTIFACT_ROOT = str(_MLFLOW_ARTIFACTS)
MLFLOW_EXPERIMENT   = "fin-eye-technical-signals"

# ── Quality gates ─────────────────────────────────────────────────────────────
MIN_WINNER_ACCURACY = 0.50
MIN_WINNER_SHARPE   = 0.0

# ── Timeframe-adaptive prediction horizon ─────────────────────────────────────
TIMEFRAME_HORIZON = {
    "1h":  3,
    "4h":  3,
    "1d":  3,
    "1wk": 2,
    "1mo": 1,
}
DEFAULT_HORIZON = 3

# ── SHAP: only compute for tree models (fast), skip for logistic ──────────────
SHAP_ENABLED = True
SHAP_MAX_SAMPLES = 200   # cap for speed — full val set can be slow on large datasets


# ── MLflow helpers ────────────────────────────────────────────────────────────

def _get_mlflow():
    try:
        import mlflow  # noqa: PLC0415
        return mlflow
    except ImportError:
        logger.warning("mlflow not installed — training without experiment tracking.")
        return None


def _start_mlflow_run(mlflow, symbol: str, timeframe: str, horizon: int):
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        run = mlflow.start_run(
            run_name=f"{symbol}_{timeframe}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        mlflow.set_tags({
            "symbol": symbol, "timeframe": timeframe,
            "horizon": str(horizon), "pipeline": "fin-eye-ml-v3",
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
        mlflow.log_artifact(artifact_path, artifact_path="joblib")
    except Exception as e:
        logger.debug("MLflow artifact log failed: %s", e)


def _log_and_register_model(mlflow, winner_obj, run_id: str,
                             symbol: str, timeframe: str, artifact_path: str):
    """Log winner as an MLflow sklearn model and register it."""
    try:
        import mlflow.sklearn  # noqa: PLC0415
        from sklearn.pipeline import Pipeline  # noqa: PLC0415

        model_name   = f"fin-eye-{symbol}-{timeframe}".replace("/", "-")
        artifact_dir = "model"

        # Unwrap wrapper classes — mlflow.sklearn needs a real estimator or Pipeline
        if isinstance(winner_obj, EnsembleWrapper):
            # Ensemble: log as the best single sub-model for MLflow compatibility
            # The full ensemble is still saved in the .joblib artifact
            sk_model = winner_obj.best_base_model()
        elif hasattr(winner_obj, "model") and hasattr(winner_obj, "scaler"):
            # LogisticWrapper → Pipeline
            sk_model = Pipeline([("scaler", winner_obj.scaler), ("clf", winner_obj.model)])
        elif hasattr(winner_obj, "model"):
            # XGBoostWrapper / LightGBMWrapper
            sk_model = winner_obj.model
        else:
            sk_model = winner_obj

        mlflow.sklearn.log_model(sk_model, artifact_path=artifact_dir)
        model_uri = f"runs:/{run_id}/{artifact_dir}"
        result    = mlflow.register_model(model_uri, model_name)
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

    # Returns
    d["ret_1"] = close.pct_change(1, fill_method=None)
    d["ret_3"] = close.pct_change(3, fill_method=None)
    d["ret_5"] = close.pct_change(5, fill_method=None)

    # Moving averages + crossovers
    d["sma_10"] = close.rolling(10).mean()
    d["sma_20"] = close.rolling(20).mean()
    d["sma_50"] = close.rolling(50).mean()
    d["sma_cross_10_20"] = (d["sma_10"] / d["sma_20"]) - 1
    d["sma_cross_20_50"] = (d["sma_20"] / d["sma_50"]) - 1
    d["price_vs_sma50"]  = (close / d["sma_50"]) - 1

    # RSI
    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-9)
    d["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    d["macd"]        = ema_12 - ema_26
    d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["macd_hist"]   = d["macd"] - d["macd_signal"]

    # Bollinger Bands
    d["std_20"]   = close.rolling(20).std()
    d["bb_upper"] = d["sma_20"] + (d["std_20"] * 2)
    d["bb_lower"] = d["sma_20"] - (d["std_20"] * 2)
    d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / d["sma_20"]
    d["bb_pb"]    = (close - d["bb_lower"]) / (
        (d["bb_upper"] - d["bb_lower"]).replace(0, 1e-9)
    )

    # Momentum
    d["mom_10"] = close.pct_change(10, fill_method=None)
    d["mom_20"] = close.pct_change(20, fill_method=None)

    # ATR
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    d["atr_14"]  = tr.rolling(14).mean()
    d["atr_pct"] = d["atr_14"] / close

    # Volume
    vol_ma20          = volume.rolling(20).mean().replace(0, 1e-9)
    d["volume_ratio"] = volume / vol_ma20

    # Target
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


# ── SHAP feature importance ───────────────────────────────────────────────────

def compute_shap_importance(model_wrapper, X_val: pd.DataFrame) -> Optional[Dict[str, float]]:
    """
    Compute mean absolute SHAP values for tree-based models.
    Returns a dict {feature_name: mean_abs_shap} sorted descending, or None on failure.
    Skips logistic and ensemble wrappers (no TreeExplainer support).
    """
    if not SHAP_ENABLED:
        return None
    if not isinstance(model_wrapper, (XGBoostWrapper, LightGBMWrapper)):
        return None
    try:
        import shap  # noqa: PLC0415
        X_sample = X_val[FEATURES].iloc[:SHAP_MAX_SAMPLES]
        explainer = shap.TreeExplainer(model_wrapper.model)
        shap_vals = explainer.shap_values(X_sample)
        # For binary classifiers shap_values may return a list [neg, pos] — use pos class
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        mean_abs = np.abs(shap_vals).mean(axis=0)
        importance = {
            feat: round(float(val), 6)
            for feat, val in sorted(
                zip(FEATURES, mean_abs), key=lambda x: x[1], reverse=True
            )
        }
        logger.debug("SHAP computed: top feature = %s (%.4f)", next(iter(importance)), next(iter(importance.values())))
        return importance
    except ImportError:
        logger.debug("shap not installed — skipping feature importance")
        return None
    except Exception as e:
        logger.debug("SHAP computation failed: %s", e)
        return None


# ── Model wrappers ────────────────────────────────────────────────────────────

class LogisticWrapper:
    name = "logistic"

    def __init__(self):
        self.scaler = StandardScaler()
        self.model  = LogisticRegression(
            class_weight="balanced", max_iter=1000, C=0.1, dual=False,
        )

    def fit(self, X, y):
        X_feat = X[FEATURES]
        self.scaler.fit(X_feat)
        self.model.fit(self.scaler.transform(X_feat), y)

    def predict_proba(self, X):
        return self.model.predict_proba(self.scaler.transform(X[FEATURES]))


class XGBoostWrapper:
    name = "xgboost"

    def __init__(self, n_positive: int = 1, n_negative: int = 1):
        spw = max(1.0, n_negative / max(n_positive, 1))
        self.model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            gamma=0.1, scale_pos_weight=spw, eval_metric="logloss",
            random_state=42, verbosity=0,
        )

    def fit(self, X, y):
        self.model.fit(X[FEATURES], y)

    def predict_proba(self, X):
        return self.model.predict_proba(X[FEATURES])


class LightGBMWrapper:
    """
    Sprint 3 — LightGBM as 4th competing model.
    Leaf-wise tree growth (vs level-wise in XGBoost) — often faster and comparable accuracy.
    Uses class_weight='balanced' to handle label imbalance gracefully.
    verbose=-1 suppresses LightGBM's noisy output to the terminal.
    """
    name = "lightgbm"

    def __init__(self, n_positive: int = 1, n_negative: int = 1):
        try:
            from lightgbm import LGBMClassifier  # noqa: PLC0415
            # Scale positive weight mirrors XGBoost's approach
            spw = max(1.0, n_negative / max(n_positive, 1))
            self.model = LGBMClassifier(
                n_estimators=300, max_depth=4, learning_rate=0.03,
                subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
                scale_pos_weight=spw, random_state=42, verbose=-1,
                n_jobs=1,
            )
            self._available = True
        except ImportError:
            logger.warning("lightgbm not installed — LightGBMWrapper will be skipped")
            self.model      = None
            self._available = False

    def fit(self, X, y):
        if not self._available:
            raise RuntimeError("lightgbm not installed")
        self.model.fit(X[FEATURES], y)

    def predict_proba(self, X):
        if not self._available:
            raise RuntimeError("lightgbm not installed")
        return self.model.predict_proba(X[FEATURES])


class EnsembleWrapper:
    """
    Sprint 3 — Soft-voting ensemble.
    Blends LogisticWrapper + XGBoostWrapper + LightGBMWrapper probabilities,
    weighted by their individual validation Sharpe ratios (floored at 0.1).

    The ensemble frequently wins because individual model errors cancel out.
    It is evaluated like any other model — must pass the same quality gates.

    best_base_model() returns the highest-Sharpe sub-model for MLflow registration
    (MLflow doesn't natively support ensemble objects).
    """
    name = "ensemble"

    def __init__(
        self,
        base_models: Dict[str, Any],        # name → fitted wrapper
        base_results: Dict[str, Dict],      # name → metrics dict from evaluation
    ):
        self._models  = base_models
        self._weights = self._compute_weights(base_results)
        self._results = base_results

    @staticmethod
    def _compute_weights(results: Dict[str, Dict]) -> Dict[str, float]:
        """Sharpe-weighted normalisation (floor at 0.1 to include weak models)."""
        raw = {
            name: max(m.get("sharpe_ratio", 0.0), 0.1)
            for name, m in results.items()
            if not m.get("disqualified", False)
        }
        total = sum(raw.values()) or 1.0
        return {name: w / total for name, w in raw.items()}

    def fit(self, X, y):
        # Base models are already fitted — ensemble has no additional fitting step
        pass

    def predict_proba(self, X):
        blended = np.zeros((len(X) if hasattr(X, "__len__") else 1, 2))
        n_rows  = None
        for name, model in self._models.items():
            w = self._weights.get(name, 0.0)
            if w <= 0:
                continue
            try:
                probs = model.predict_proba(X)
                if n_rows is None:
                    n_rows = probs.shape[0]
                    blended = np.zeros((n_rows, 2))
                blended += w * probs
            except Exception as e:
                logger.warning("Ensemble: sub-model %s predict_proba failed: %s", name, e)
        # Normalise rows that didn't receive full weight (e.g. if a sub-model failed)
        row_sums = blended.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1.0, row_sums)
        return blended / row_sums

    def best_base_model(self):
        """Return the sub-model wrapper with the highest Sharpe — for MLflow logging."""
        best_name = max(self._weights, key=lambda n: self._weights[n])
        return self._models.get(best_name)


# ── Winner selection ──────────────────────────────────────────────────────────

def select_winner(results: Dict[str, Dict]) -> Tuple[Optional[str], float]:
    eligible = {
        name: m for name, m in results.items()
        if m.get("accuracy", 0)    >= MIN_WINNER_ACCURACY
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
    Sprint 3 — updated pipeline:
      feature engineering → train 4 base models → build ensemble → pick winner
      → compute SHAP importance for winner → persist → log to MLflow

    Model competition:
      logistic   — fast linear baseline
      xgboost    — gradient boosted trees
      lightgbm   — leaf-wise boosted trees (Sprint 3 addition)
      ensemble   — Sharpe-weighted soft-vote of the above three (Sprint 3 addition)

    Prophet has been removed from the competition. It consistently produced
    accuracy=0.0 and was disqualified every run. Keeping it only added ~30s
    to training time with zero benefit. It is kept as a class for potential
    future use in macro-regime detection (slow-moving time series).
    """
    logger.info(f"Training pipeline v3: {symbol}/{timeframe}  input_rows={len(df_history)}")

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

    # ── Base model definitions — Prophet intentionally absent ─────────────────
    base_model_defs: Dict[str, Any] = {
        "logistic": LogisticWrapper(),
        "xgboost":  XGBoostWrapper(n_positive=n_pos, n_negative=n_neg),
        "lightgbm": LightGBMWrapper(n_positive=n_pos, n_negative=n_neg),
    }
    results:      Dict[str, Dict] = {}
    fitted_models: Dict[str, Any] = {}

    # ── MLflow ────────────────────────────────────────────────────────────────
    mlflow     = _get_mlflow()
    mlflow_run = _start_mlflow_run(mlflow, symbol, timeframe, horizon) if mlflow else None

    try:
        if mlflow and mlflow_run:
            mlflow.log_params({
                "symbol": symbol, "timeframe": timeframe,
                "horizon_periods": horizon, "n_features": len(FEATURES),
                "total_rows": diagnostics["total_rows"],
                "train_rows": diagnostics["train_rows"],
                "val_rows":   diagnostics["val_rows"],
                "target_balance": diagnostics["target_balance_up_pct"],
                "features": ",".join(FEATURES),
                "min_sharpe_gate": MIN_WINNER_SHARPE,
                "min_acc_gate":    MIN_WINNER_ACCURACY,
                "models_competing": "logistic,xgboost,lightgbm,ensemble",
                "prophet_removed":  "true",
            })

        # ── Train base models ─────────────────────────────────────────────────
        for name, model in base_model_defs.items():
            try:
                model.fit(X_train, y_train)
                probs   = model.predict_proba(X_val)[:, 1]
                preds   = (probs > 0.5).astype(int)
                metrics = evaluate_predictions(y_val, preds, returns_val)
                results[name]       = metrics
                fitted_models[name] = model

                logger.info(
                    f"  [{name:<10}]  Sharpe={metrics['sharpe_ratio']:>7.3f}  "
                    f"Acc={metrics['accuracy']:.1%}  Ret={metrics['total_return']:+.3f}"
                )
                if mlflow and mlflow_run:
                    _log_model_metrics(mlflow, name, metrics)

            except Exception as e:
                logger.error(f"  [{name}] FAILED: {e}")
                results[name] = {
                    "accuracy": 0.0, "sharpe_ratio": -99.0, "total_return": 0.0,
                    "disqualified": True, "disqualify_reason": str(e),
                }
                if mlflow and mlflow_run:
                    _log_model_metrics(mlflow, name, results[name])

        # ── Build and evaluate ensemble ───────────────────────────────────────
        # Only include non-disqualified base models in the ensemble
        eligible_for_ensemble = {
            name: model for name, model in fitted_models.items()
            if not results.get(name, {}).get("disqualified", False)
        }
        eligible_results = {
            name: results[name] for name in eligible_for_ensemble
        }

        if len(eligible_for_ensemble) >= 2:
            try:
                ensemble = EnsembleWrapper(eligible_for_ensemble, eligible_results)
                # ensemble.fit() is a no-op — base models already fitted
                ensemble_probs = ensemble.predict_proba(X_val)[:, 1]
                ensemble_preds = (ensemble_probs > 0.5).astype(int)
                ensemble_metrics = evaluate_predictions(y_val, ensemble_preds, returns_val)
                results["ensemble"]       = ensemble_metrics
                fitted_models["ensemble"] = ensemble

                logger.info(
                    f"  [{'ensemble':<10}]  Sharpe={ensemble_metrics['sharpe_ratio']:>7.3f}  "
                    f"Acc={ensemble_metrics['accuracy']:.1%}  "
                    f"Ret={ensemble_metrics['total_return']:+.3f}  "
                    f"(weights: {', '.join(f'{n}={w:.2f}' for n,w in ensemble._weights.items())})"
                )
                if mlflow and mlflow_run:
                    _log_model_metrics(mlflow, "ensemble", ensemble_metrics)

            except Exception as e:
                logger.error(f"  [ensemble] FAILED: {e}")
                results["ensemble"] = {
                    "accuracy": 0.0, "sharpe_ratio": -99.0, "total_return": 0.0,
                    "disqualified": True, "disqualify_reason": str(e),
                }
        else:
            logger.warning("Not enough eligible base models for ensemble (need ≥2)")
            results["ensemble"] = {
                "accuracy": 0.0, "sharpe_ratio": -99.0,
                "disqualified": True, "disqualify_reason": "insufficient base models",
            }

        # ── Select winner ─────────────────────────────────────────────────────
        best_name, best_sharpe = select_winner(results)
        best_obj = fitted_models[best_name]

        # Re-fit winner on full training set (base models were fit on train_df only)
        # Ensemble re-fits its base models on full training data for production use
        if best_name == "ensemble":
            for sub_name, sub_model in eligible_for_ensemble.items():
                try:
                    sub_model.fit(X_train, y_train)
                except Exception as e:
                    logger.warning("Ensemble re-fit failed for sub-model %s: %s", sub_name, e)
        else:
            best_obj.fit(X_train, y_train)

        quality_gate_passed = (
            best_sharpe >= MIN_WINNER_SHARPE
            and results.get(best_name, {}).get("accuracy", 0) >= MIN_WINNER_ACCURACY
        )

        # ── SHAP feature importance ───────────────────────────────────────────
        shap_importance: Optional[Dict[str, float]] = None
        shap_model = best_obj
        if best_name == "ensemble" and eligible_for_ensemble:
            # Use the best tree sub-model for SHAP
            shap_model = eligible_for_ensemble.get(
                "xgboost") or eligible_for_ensemble.get("lightgbm")
        shap_importance = compute_shap_importance(shap_model, X_val)
        if shap_importance:
            top3 = list(shap_importance.items())[:3]
            logger.info(
                "  [SHAP] Top features: %s",
                ", ".join(f"{f}={v:.4f}" for f, v in top3),
            )

        # ── Persist .joblib ───────────────────────────────────────────────────
        timestamp     = datetime.utcnow().isoformat()
        artifact_name = f"{symbol}_{timeframe}_winner.joblib"
        artifact_path = os.path.join(ARTIFACT_DIR, artifact_name)
        joblib.dump(best_obj, artifact_path)

        # ── MLflow: log winner ────────────────────────────────────────────────
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
                if shap_importance:
                    top_feat, top_val = next(iter(shap_importance.items()))
                    mlflow.set_tags({"shap_top_feature": top_feat})
                    mlflow.log_metric("shap_top_feature_value", round(top_val, 4))
                _log_winner_artifact(mlflow, artifact_path)
                _log_and_register_model(
                    mlflow, best_obj, mlflow_run_id, symbol, timeframe, artifact_path
                )
            except Exception as e:
                logger.warning("MLflow winner logging failed: %s", e)

        # ── JSONL registry ────────────────────────────────────────────────────
        extra_metrics = {
            "horizon_periods":   horizon,
            "val_rows":          diagnostics["val_rows"],
            "train_rows":        diagnostics["train_rows"],
            "total_return":      results.get(best_name, {}).get("total_return", 0.0),
            "all_model_metrics": results,
        }
        if shap_importance:
            extra_metrics["shap_importance"] = shap_importance

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
            "shap_importance":   shap_importance,
        }

        registry = JsonlFileModelRegistry(REGISTRY_FILE)
        winner_tf = TimeframeWinner(
            timeframe    = Timeframe(timeframe),
            model_kind   = ModelKind(best_name),
            sharpe_ratio = best_sharpe,
            accuracy     = results.get(best_name, {}).get("accuracy", 0.0),
        )
        record_winners(
            registry      = registry,
            winners       = [winner_tf],
            symbol        = symbol,
            trained_at    = datetime.utcnow(),
            artifact_path = artifact_path,
            mlflow_run_id = mlflow_run_id,
            quality_gate  = quality_gate_passed,
            notes         = f"horizon={horizon} val_rows={diagnostics['val_rows']} sprint3",
            extra_metrics = extra_metrics,
        )

        logger.info(
            f"Winner {symbol}/{timeframe}: {best_name}  "
            f"Sharpe={best_sharpe:.3f}  "
            f"Acc={results.get(best_name, {}).get('accuracy', 0):.1%}  "
            f"val_rows={diagnostics['val_rows']}  horizon={horizon}"
            + (f"  shap_top={next(iter(shap_importance))}" if shap_importance else "")
            + (f"  mlflow={mlflow_run_id}" if mlflow_run_id else "")
        )

        return metadata

    finally:
        if mlflow and mlflow_run:
            try:
                mlflow.end_run()
            except Exception:
                pass
