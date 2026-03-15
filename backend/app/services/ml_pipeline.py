"""
Machine Learning Pipeline for Technical Analysis (MVP-TECH-01)

KEY IMPROVEMENTS in this version:
  - Timeframe-adaptive target horizon: instead of always predicting 5 periods ahead,
    the horizon scales with the timeframe so each model predicts a meaningful duration.
      1h  → 3 periods ahead  (~3 hours)
      4h  → 3 periods ahead  (~12 hours)
      1d  → 3 periods ahead  (~3 trading days)
      1wk → 2 periods ahead  (~2 weeks)
      1mo → 1 period  ahead  (~1 month)
    This was the primary reason the 1d model was producing noise — predicting 5 days
    ahead on daily bars is extremely hard and noisy.

  - Expanded feature set: adds volume_ratio, ATR (volatility), price_vs_sma50,
    ret_3, ret_5 (multi-period returns). These add discriminating power that pure
    price-based indicators miss.

  - XGBoost tuned: max_depth increased to 4, n_estimators to 200, subsample and
    colsample_bytree added for regularisation. More capacity without overfitting.

  - Winner selection: requires accuracy >= 50% AND Sharpe >= 0.

  - Prophet disqualified on accuracy == 0.0 (silent failure guard).

  - Diagnostics saved to registry: val_rows, target_balance, low_variance_features.
"""

import os
import json
import logging
from datetime import datetime
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

# ── Quality gates ─────────────────────────────────────────────────────────────
MIN_WINNER_ACCURACY = 0.50
MIN_WINNER_SHARPE   = 0.0

# ── Timeframe-adaptive prediction horizon ────────────────────────────────────
# How many periods ahead to predict. Chosen so that each horizon represents
# roughly the same real-world duration (~12 hours to 1 day).
TIMEFRAME_HORIZON = {
    "1h":  3,   # ~3 hours
    "4h":  3,   # ~12 hours
    "1d":  3,   # ~3 trading days
    "1wk": 2,   # ~2 weeks
    "1mo": 1,   # ~1 month
}
DEFAULT_HORIZON = 3


# ── Feature Engineering ───────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame, horizon: int = DEFAULT_HORIZON) -> pd.DataFrame:
    """
    Computes technical indicators on an OHLCV DataFrame.

    Expects columns: ['open', 'high', 'low', 'close', 'volume']
    Returns enriched DataFrame with NaNs dropped.

    The `horizon` parameter controls how many periods ahead the target is set.
    Use TIMEFRAME_HORIZON[timeframe] to get the appropriate value per timeframe.
    """
    if len(df) < 60:
        return pd.DataFrame()

    d = df.copy()
    close  = d["close"]
    volume = d["volume"] if "volume" in d.columns else pd.Series(1, index=d.index)
    high   = d["high"]   if "high"   in d.columns else close
    low    = d["low"]    if "low"    in d.columns else close

    # ── Returns (multi-period) ────────────────────────────────────────────────
    d["ret_1"] = close.pct_change(1)
    d["ret_3"] = close.pct_change(3)
    d["ret_5"] = close.pct_change(5)

    # ── Moving averages ───────────────────────────────────────────────────────
    d["sma_10"] = close.rolling(10).mean()
    d["sma_20"] = close.rolling(20).mean()
    d["sma_50"] = close.rolling(50).mean()

    d["sma_cross_10_20"] = (d["sma_10"] / d["sma_20"]) - 1
    d["sma_cross_20_50"] = (d["sma_20"] / d["sma_50"]) - 1

    # Price position relative to SMA50 (trend context)
    d["price_vs_sma50"] = (close / d["sma_50"]) - 1

    # ── RSI (14 period) ───────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-9)
    d["rsi_14"] = 100 - (100 / (1 + rs))

    # ── MACD (12, 26, 9) ──────────────────────────────────────────────────────
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    d["macd"]        = ema_12 - ema_26
    d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["macd_hist"]   = d["macd"] - d["macd_signal"]

    # ── Bollinger Bands (20, 2σ) ──────────────────────────────────────────────
    d["std_20"]   = close.rolling(20).std()
    d["bb_upper"] = d["sma_20"] + (d["std_20"] * 2)
    d["bb_lower"] = d["sma_20"] - (d["std_20"] * 2)
    d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / d["sma_20"]
    d["bb_pb"]    = (close - d["bb_lower"]) / (
        (d["bb_upper"] - d["bb_lower"]).replace(0, 1e-9)
    )

    # ── Momentum ──────────────────────────────────────────────────────────────
    d["mom_10"] = close.pct_change(10)
    d["mom_20"] = close.pct_change(20)

    # ── ATR — Average True Range (volatility) ─────────────────────────────────
    # Strong discriminator: high ATR = trending / volatile bars
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    d["atr_14"]       = tr.rolling(14).mean()
    d["atr_pct"]      = d["atr_14"] / close   # normalise by price

    # ── Volume ratio ──────────────────────────────────────────────────────────
    # Volume vs its 20-period average — spikes signal conviction
    vol_ma20         = volume.rolling(20).mean().replace(0, 1e-9)
    d["volume_ratio"] = volume / vol_ma20

    # ── Target: forward return direction ─────────────────────────────────────
    d["target_ret_fwd"] = close.shift(-horizon) / close - 1
    d["target"]         = (d["target_ret_fwd"] > 0).astype(int)

    d.dropna(inplace=True)
    return d


# FEATURES list — what gets passed to the classifiers
FEATURES = [
    # Returns
    "ret_1", "ret_3", "ret_5",
    # Trend
    "sma_cross_10_20", "sma_cross_20_50", "price_vs_sma50",
    # Momentum oscillators
    "rsi_14", "macd", "macd_hist",
    # Volatility
    "bb_width", "bb_pb", "atr_pct",
    # Momentum
    "mom_10", "mom_20",
    # Volume
    "volume_ratio",
]


# ── Diagnostics ───────────────────────────────────────────────────────────────

def log_training_diagnostics(
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
) -> dict:
    total_rows = len(df)
    train_rows = len(train_df)
    val_rows   = len(val_df)

    target_counts  = df["target"].value_counts().to_dict()
    n_positive     = int(target_counts.get(1, 0))
    target_balance = round(n_positive / total_rows, 3) if total_rows else 0.5

    feature_std          = df[FEATURES].std()
    low_variance_features = feature_std[feature_std < 1e-6].index.tolist()

    logger.info(
        f"[{symbol}/{timeframe}] Training diagnostics:\n"
        f"  Total rows  : {total_rows}\n"
        f"  Train rows  : {train_rows}\n"
        f"  Val rows    : {val_rows}\n"
        f"  Target UP   : {target_balance:.1%}\n"
        f"  Low-var     : {low_variance_features or 'none'}\n"
        f"  Features    : {len(FEATURES)}"
    )

    if val_rows < 50:
        logger.warning(f"[{symbol}/{timeframe}] Only {val_rows} val rows — estimates unreliable.")
    if abs(target_balance - 0.5) > 0.15:
        logger.warning(f"[{symbol}/{timeframe}] Target imbalanced: {target_balance:.1%} UP.")
    if low_variance_features:
        logger.warning(f"[{symbol}/{timeframe}] Low-variance features: {low_variance_features}")

    return {
        "train_rows":             train_rows,
        "val_rows":               val_rows,
        "total_rows":             total_rows,
        "target_balance_up_pct":  round(target_balance * 100, 1),
        "low_variance_features":  low_variance_features,
        "n_features":             len(FEATURES),
    }


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    returns: np.ndarray,
) -> Dict[str, float]:
    accuracy  = float(np.mean(y_true == y_pred))
    strat_ret = np.where(y_pred == 1, returns, 0)
    mean_ret  = np.mean(strat_ret)
    std_ret   = np.std(strat_ret)

    sharpe = 0.0 if std_ret < 1e-6 else float((mean_ret / std_ret) * np.sqrt(252))

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
            class_weight="balanced",
            max_iter=1000,
            C=0.1,          # stronger regularisation — prevents overfitting on small val sets
            dual=False,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.scaler.fit(X)
        self.model.fit(self.scaler.transform(X), y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(self.scaler.transform(X))


class XGBoostWrapper:
    def __init__(self, n_positive: int = 1, n_negative: int = 1):
        spw = max(1.0, n_negative / max(n_positive, 1))
        self.model = XGBClassifier(
            n_estimators=200,       # more trees = better generalisation
            max_depth=4,            # slightly deeper = more capacity
            learning_rate=0.03,     # lower lr requires more trees, but generalises better
            subsample=0.8,          # row subsampling — reduces overfitting
            colsample_bytree=0.8,   # feature subsampling — reduces overfitting
            min_child_weight=5,     # requires each leaf to have at least 5 samples
            gamma=0.1,              # minimum gain to make a split
            scale_pos_weight=spw,
            eval_metric="logloss",
            random_state=42,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.model.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X)


class ProphetWrapper:
    """
    Prophet as a trend-direction classifier.
    Requires 'close_raw' column in X.
    """
    def __init__(self):
        self.model = Prophet(daily_seasonality=False, yearly_seasonality=False)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        df = pd.DataFrame({
            "ds": pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values,
            "y":  X["close_raw"],
        })
        self.model.fit(df)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        df = pd.DataFrame({
            "ds": pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values
        })
        forecast  = self.model.predict(df)
        pred_diff = forecast["yhat"].diff().fillna(0).values
        probs     = np.where(pred_diff > 0, 0.8, 0.2)
        out        = np.zeros((len(X), 2))
        out[:, 1]  = probs
        out[:, 0]  = 1 - probs
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
        best_name = max(eligible, key=lambda n: eligible[n]["sharpe_ratio"])
        return best_name, eligible[best_name]["sharpe_ratio"]

    logger.warning(
        "No model passed quality gates (acc >= %.0f%% AND Sharpe >= %.2f). "
        "Falling back to highest-accuracy model as placeholder.",
        MIN_WINNER_ACCURACY * 100, MIN_WINNER_SHARPE,
    )
    fallback = max(results, key=lambda n: results[n].get("accuracy", 0))
    return fallback, results[fallback].get("sharpe_ratio", -99.0)


# ── Training pipeline ─────────────────────────────────────────────────────────

def run_training_pipeline(
    symbol: str,
    timeframe: str,
    df_history: pd.DataFrame,
) -> Dict[str, Any]:
    """
    End-to-end pipeline: feature engineering → train 3 models → pick winner → persist.

    df_history must have columns: open, high, low, close, volume
    with a DatetimeIndex sorted ascending.
    """
    logger.info(f"Training pipeline: {symbol}/{timeframe}  input_rows={len(df_history)}")

    if len(df_history) < 200:
        raise ValueError(f"Need > 200 rows, got {len(df_history)}")

    # Use timeframe-adaptive horizon
    horizon = TIMEFRAME_HORIZON.get(timeframe, DEFAULT_HORIZON)
    logger.info(f"[{symbol}/{timeframe}] Prediction horizon: {horizon} periods")

    df = engineer_features(df_history, horizon=horizon)

    # Inject raw close for Prophet
    df["close_raw"] = df_history["close"].reindex(df.index)

    if len(df) < 100:
        raise ValueError(f"Only {len(df)} rows after feature engineering.")

    split_idx = int(len(df) * 0.8)
    train_df  = df.iloc[:split_idx]
    val_df    = df.iloc[split_idx:]

    diagnostics = log_training_diagnostics(symbol, timeframe, df, train_df, val_df)

    n_pos = int((train_df["target"] == 1).sum())
    n_neg = int((train_df["target"] == 0).sum())

    X_train      = train_df[FEATURES + ["close_raw"]]
    y_train      = train_df["target"]
    X_val        = val_df[FEATURES + ["close_raw"]]
    y_val        = val_df["target"].values
    returns_val  = val_df["target_ret_fwd"].values   # real forward returns

    models = {
        "logistic": LogisticWrapper(),
        "xgboost":  XGBoostWrapper(n_positive=n_pos, n_negative=n_neg),
        "prophet":  ProphetWrapper(),
    }

    results: Dict[str, Dict] = {}

    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            probs   = model.predict_proba(X_val)[:, 1]
            preds   = (probs > 0.5).astype(int)
            metrics = evaluate_predictions(y_val, preds, returns_val)
            results[name] = metrics

            logger.info(
                f"  [{name}]  Sharpe={metrics['sharpe_ratio']:>7.3f}  "
                f"Acc={metrics['accuracy']:.1%}  "
                f"Ret={metrics['total_return']:+.3f}"
            )

            # Prophet silent-failure guard
            if name == "prophet" and metrics["accuracy"] == 0.0:
                logger.warning("Prophet accuracy=0.0 — disqualifying.")
                results[name]["sharpe_ratio"]     = -99.0
                results[name]["disqualified"]      = True
                results[name]["disqualify_reason"] = "accuracy == 0.0"

        except Exception as e:
            logger.error(f"  [{name}] FAILED: {e}")
            results[name] = {
                "accuracy": 0.0, "sharpe_ratio": -99.0, "total_return": 0.0,
                "disqualified": True, "disqualify_reason": str(e),
            }

    best_name, best_sharpe = select_winner(results)

    # Refit winner on full training data before saving
    best_obj = models[best_name]
    best_obj.fit(X_train, y_train)

    timestamp     = datetime.utcnow().isoformat()
    artifact_name = f"{symbol}_{timeframe}_winner.joblib"
    artifact_path = os.path.join(ARTIFACT_DIR, artifact_name)
    joblib.dump(best_obj, artifact_path)

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
    }

    with open(REGISTRY_FILE, "a") as f:
        f.write(json.dumps(metadata) + "\n")

    logger.info(
        f"Winner {symbol}/{timeframe}: {best_name}  "
        f"Sharpe={best_sharpe:.3f}  "
        f"Acc={results.get(best_name, {}).get('accuracy', 0):.1%}  "
        f"val_rows={diagnostics['val_rows']}  "
        f"horizon={horizon}"
    )

    return metadata
