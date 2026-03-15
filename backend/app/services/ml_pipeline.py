"""
Machine Learning Pipeline for Technical Analysis (MVP-TECH-01)

Handles feature engineering, training competing models 
(XGBoost, Logistic Regression, Prophet), walk-forward validation 
by Sharpe Ratio, and persistence of the winning model.

CHANGES vs original:
  - Winner selection now requires accuracy >= 50% in addition to highest Sharpe.
    A model cannot win on Sharpe alone if it is worse than random.
  - Prophet is disqualified if it returns accuracy == 0.0 (silent training failure).
  - Registry now records train_rows, val_rows, target_balance, and feature_count
    so inspect_models.py can report on data quality alongside model quality.
  - Diagnostic logging added: target distribution, feature variance warnings,
    validation set size — printed at INFO level on every training run.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from prophet import Prophet

logger = logging.getLogger(__name__)

# Paths for persisting models
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")
REGISTRY_FILE = os.path.join(ARTIFACT_DIR, "model_registry.jsonl")

os.makedirs(ARTIFACT_DIR, exist_ok=True)

# ── Quality gates applied at winner selection ─────────────────────────────────
# A model must pass BOTH to be eligible as winner.
MIN_WINNER_ACCURACY = 0.50   # must beat random
MIN_WINNER_SHARPE   = 0.0    # must not destroy value (hard floor — 0.30 is recommended floor)


# ── Feature Engineering ───────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes technical indicators on OHLCV DataFrame.
    Expects df with columns: ['open', 'high', 'low', 'close', 'volume']
    Returns df with NaN dropped and feature columns added.
    """
    if len(df) < 50:
        return pd.DataFrame()

    d = df.copy()

    # Returns
    d["ret_1"] = d["close"].pct_change(1)

    # Simple Moving Averages
    d["sma_10"] = d["close"].rolling(10).mean()
    d["sma_20"] = d["close"].rolling(20).mean()
    d["sma_50"] = d["close"].rolling(50).mean()
    d["sma_cross_10_20"] = (d["sma_10"] / d["sma_20"]) - 1
    d["sma_cross_20_50"] = (d["sma_20"] / d["sma_50"]) - 1

    # RSI (14 period)
    delta = d["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(int(14)).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(int(14)).mean()
    rs = gain / loss.replace(0, 1e-9)
    d["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema_12 = d["close"].ewm(span=12, adjust=False).mean()
    ema_26 = d["close"].ewm(span=26, adjust=False).mean()
    d["macd"] = ema_12 - ema_26
    d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["macd_hist"] = d["macd"] - d["macd_signal"]

    # Volatility / Bollinger Bands (20, 2)
    d["std_20"] = d["close"].rolling(20).std()
    d["bb_upper"] = d["sma_20"] + (d["std_20"] * 2)
    d["bb_lower"] = d["sma_20"] - (d["std_20"] * 2)
    d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / d["sma_20"]
    d["bb_pb"] = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"]).replace(0, 1e-9)

    # Momentum
    d["mom_10"] = d["close"].pct_change(10)
    d["mom_20"] = d["close"].pct_change(20)

    # Target: Predict next 5-period return direction
    d["target_ret_5"] = d["close"].shift(-5) / d["close"] - 1
    # 1 if positive return, 0 if negative
    d["target"] = (d["target_ret_5"] > 0).astype(int)

    d.dropna(inplace=True)
    return d


FEATURES = [
    "ret_1", "sma_cross_10_20", "sma_cross_20_50",
    "rsi_14", "macd", "macd_hist", "bb_width", "bb_pb",
    "mom_10", "mom_20"
]


# ── Diagnostics ───────────────────────────────────────────────────────────────

def log_training_diagnostics(
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
) -> dict:
    """
    Logs and returns a diagnostics dict that is saved into the registry.
    Covers target balance, validation set size, and feature variance.
    These are the three most common silent reasons for bad model quality.
    """
    total_rows = len(df)
    train_rows = len(train_df)
    val_rows   = len(val_df)

    # Target balance: how many 1s vs 0s
    target_counts = df["target"].value_counts().to_dict()
    n_positive = int(target_counts.get(1, 0))
    n_negative = int(target_counts.get(0, 0))
    target_balance = round(n_positive / total_rows, 3) if total_rows else 0.5

    # Feature variance: any features near-zero variance are useless
    feature_std = df[FEATURES].std()
    low_variance_features = feature_std[feature_std < 1e-6].index.tolist()

    logger.info(
        f"[{symbol}/{timeframe}] Training diagnostics:\n"
        f"  Total rows after feature engineering : {total_rows}\n"
        f"  Train rows (80%%)                    : {train_rows}\n"
        f"  Validation rows (20%%)               : {val_rows}\n"
        f"  Target balance (fraction up)          : {target_balance:.1%} up / {1-target_balance:.1%} down\n"
        f"  Low-variance features (useless)       : {low_variance_features if low_variance_features else 'none'}"
    )

    if val_rows < 50:
        logger.warning(
            f"[{symbol}/{timeframe}] Validation set has only {val_rows} rows. "
            f"Sharpe and accuracy estimates will be unreliable. "
            f"Collect more data before trusting this training run."
        )

    if abs(target_balance - 0.5) > 0.15:
        logger.warning(
            f"[{symbol}/{timeframe}] Target is imbalanced: {target_balance:.1%} positive. "
            f"Models may be biased toward the majority class. "
            f"Consider using class_weight='balanced' (already set on Logistic) "
            f"and scale_pos_weight on XGBoost."
        )

    if low_variance_features:
        logger.warning(
            f"[{symbol}/{timeframe}] These features have near-zero variance and "
            f"will not help the model: {low_variance_features}. "
            f"Check your OHLCV data — this often means repeated prices."
        )

    return {
        "train_rows": train_rows,
        "val_rows": val_rows,
        "total_rows": total_rows,
        "target_balance_up_pct": round(target_balance * 100, 1),
        "low_variance_features": low_variance_features,
    }


# ── Walk-Forward Evaluation ───────────────────────────────────────────────────

def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    returns: np.ndarray,
) -> Dict[str, float]:
    """
    Computes strategy metrics (Sharpe ratio, Accuracy) based on signals.
    y_pred: 1 for long, 0 for cash
    """
    accuracy = float(np.mean(y_true == y_pred))

    # Strategy returns: hold when model says 1, cash when model says 0
    strat_ret = np.where(y_pred == 1, returns, 0)

    mean_ret = np.mean(strat_ret)
    std_ret  = np.std(strat_ret)

    if std_ret < 1e-6:
        sharpe = 0.0
    else:
        sharpe = float((mean_ret / std_ret) * np.sqrt(252))

    return {
        "accuracy":     accuracy,
        "sharpe_ratio": sharpe,
        "total_return": float(np.sum(strat_ret)),
    }


# ── Model Wrappers ────────────────────────────────────────────────────────────

class BaseModelWrapper:
    def fit(self, X: pd.DataFrame, y: pd.Series):
        pass

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        pass


class LogisticWrapper(BaseModelWrapper):
    def __init__(self):
        self.scaler = StandardScaler()
        self.model  = LogisticRegression(class_weight="balanced", dual=False)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)


class XGBoostWrapper(BaseModelWrapper):
    def __init__(self, n_positive: int = 1, n_negative: int = 1):
        # scale_pos_weight corrects for class imbalance in XGBoost
        # ratio = count(negative) / count(positive)
        spw = max(1.0, n_negative / max(n_positive, 1))
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            scale_pos_weight=spw,
            eval_metric="logloss",
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.model.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X)


class ProphetWrapper(BaseModelWrapper):
    """
    Prophet predicts future price trend slope and converts to a binary signal.
    Requires 'close_raw' column in X (injected by the training pipeline).
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

def select_winner(
    results: Dict[str, Dict],
) -> Tuple[Optional[str], float]:
    """
    Selects the best model name and its Sharpe from the results dict.

    Rules (applied in order):
      1. Disqualify any model with accuracy < MIN_WINNER_ACCURACY (below random).
      2. Disqualify any model with Sharpe < MIN_WINNER_SHARPE (destroys value).
      3. From eligible models, pick highest Sharpe.
      4. If NO model passes the gates, pick the one with the highest accuracy
         (least-bad fallback) and log a warning — but do NOT silently use it
         as if it were a good model.

    Returns (model_name, sharpe).
    """
    eligible = {
        name: m for name, m in results.items()
        if m.get("accuracy", 0) >= MIN_WINNER_ACCURACY
        and m.get("sharpe_ratio", -99) >= MIN_WINNER_SHARPE
    }

    if eligible:
        best_name = max(eligible, key=lambda n: eligible[n]["sharpe_ratio"])
        return best_name, eligible[best_name]["sharpe_ratio"]

    # No model passed — fall back to least-bad by accuracy, but flag it
    logger.warning(
        "No model passed quality gates (accuracy >= %.0f%% AND Sharpe >= %.2f). "
        "All models failed on this training run. "
        "Falling back to highest-accuracy model as a placeholder — "
        "this model should NOT be used in production until retraining improves results.",
        MIN_WINNER_ACCURACY * 100,
        MIN_WINNER_SHARPE,
    )
    fallback_name = max(results, key=lambda n: results[n].get("accuracy", 0))
    return fallback_name, results[fallback_name].get("sharpe_ratio", -99.0)


# ── Training Pipeline ─────────────────────────────────────────────────────────

def run_training_pipeline(
    symbol: str,
    timeframe: str,
    df_history: pd.DataFrame,
) -> Dict[str, Any]:
    """
    End-to-end pipeline: engineers features, trains XGB/Logistic/Prophet,
    evaluates on validation set via Sharpe ratio, and saves the winner.

    Returns the full metadata dict that was written to the registry,
    including diagnostics so the caller can inspect what happened.
    """
    logger.info(
        f"Running ML pipeline for {symbol} ({timeframe}). "
        f"Input rows: {len(df_history)}"
    )

    if len(df_history) < 200:
        raise ValueError(
            f"Insufficient data: {len(df_history)} rows. "
            f"ML pipeline requires > 200 rows."
        )

    df = engineer_features(df_history)

    # Inject raw close for Prophet (must be done before split)
    df["close_raw"] = df_history["close"].reindex(df.index)

    if len(df) < 100:
        raise ValueError(
            f"Only {len(df)} rows remain after feature engineering. "
            f"Check for data gaps or insufficient history."
        )

    # Time-series split (80% train, 20% validation — no shuffling, ever)
    split_idx = int(len(df) * 0.8)
    train_df  = df.iloc[:split_idx]
    val_df    = df.iloc[split_idx:]

    # Log and capture diagnostics
    diagnostics = log_training_diagnostics(symbol, timeframe, df, train_df, val_df)

    # Class counts for XGBoost scale_pos_weight
    n_pos = int((train_df["target"] == 1).sum())
    n_neg = int((train_df["target"] == 0).sum())

    X_train = train_df[FEATURES + ["close_raw"]]
    y_train = train_df["target"]
    X_val   = val_df[FEATURES + ["close_raw"]]
    y_val   = val_df["target"].values

    # Real forward returns for Sharpe calculation (not a proxy)
    returns_val = val_df["target_ret_5"].values

    models = {
        "logistic": LogisticWrapper(),
        "xgboost":  XGBoostWrapper(n_positive=n_pos, n_negative=n_neg),
        "prophet":  ProphetWrapper(),
    }

    results: Dict[str, Dict] = {}

    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            probs = model.predict_proba(X_val)[:, 1]
            preds = (probs > 0.5).astype(int)
            metrics = evaluate_predictions(y_val, preds, returns_val)
            results[name] = metrics

            logger.info(
                f"  [{name}] Sharpe: {metrics['sharpe_ratio']:>7.3f}  "
                f"Acc: {metrics['accuracy']:.1%}  "
                f"Return: {metrics['total_return']:+.3f}"
            )

            # Disqualify Prophet if it silently failed (accuracy == 0)
            if name == "prophet" and metrics["accuracy"] == 0.0:
                logger.warning(
                    "Prophet returned accuracy 0.0 — training likely failed "
                    "(close_raw injection issue or insufficient data). "
                    "Marking Prophet as disqualified for winner selection."
                )
                results[name]["sharpe_ratio"]  = -99.0
                results[name]["disqualified"]  = True
                results[name]["disqualify_reason"] = "accuracy == 0.0 (silent failure)"

        except Exception as e:
            logger.error(f"  [{name}] Training failed: {e}")
            results[name] = {
                "accuracy":          0.0,
                "sharpe_ratio":     -99.0,
                "total_return":      0.0,
                "disqualified":      True,
                "disqualify_reason": str(e),
            }

    # ── Select winner ─────────────────────────────────────────────────────────
    best_model_name, best_sharpe = select_winner(results)

    # Refit winner on full training set before saving
    best_model_obj = models.get(best_model_name)
    if best_model_obj is None:
        # Edge case: winner name from results has no corresponding model object
        best_model_name = "logistic"
        best_model_obj  = LogisticWrapper()

    best_model_obj.fit(X_train, y_train)

    # ── Persist artifact ──────────────────────────────────────────────────────
    timestamp     = datetime.utcnow().isoformat()
    artifact_name = f"{symbol}_{timeframe}_winner.joblib"
    artifact_path = os.path.join(ARTIFACT_DIR, artifact_name)
    joblib.dump(best_model_obj, artifact_path)

    # ── Write registry entry ──────────────────────────────────────────────────
    metadata = {
        "symbol":           symbol,
        "timeframe":        timeframe,
        "model_name":       best_model_name,
        "trained_at":       timestamp,
        "artifact_file":    artifact_name,
        "validation_sharpe": best_sharpe,
        "metrics":          results,
        # Diagnostics — used by inspect_models.py and ml_output_evaluator.py
        "diagnostics":      diagnostics,
    }

    with open(REGISTRY_FILE, "a") as f:
        f.write(json.dumps(metadata) + "\n")

    logger.info(
        f"Winner for {symbol}/{timeframe}: {best_model_name} "
        f"(Sharpe={best_sharpe:.3f}, "
        f"Acc={results.get(best_model_name, {}).get('accuracy', 0):.1%}, "
        f"val_rows={diagnostics['val_rows']})"
    )

    return metadata
