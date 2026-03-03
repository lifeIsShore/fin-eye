"""
Machine Learning Pipeline for Technical Analysis (MVP-TECH-01)

Handles feature engineering, training competing models 
(XGBoost, Logistic Regression, Prophet), walk-forward validation 
by Sharpe Ratio, and persistence of the winning model.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

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


# ── Walk-Forward Evaluation ───────────────────────────────────────────────────

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, returns: np.ndarray) -> Dict[str, float]:
    """
    Computes strategy metrics (Sharpe ratio, Accuracy) based on signals.
    y_pred: 1 for long, 0 for cash
    """
    accuracy = float(np.mean(y_true == y_pred))
    
    # Strategy returns
    strat_ret = np.where(y_pred == 1, returns, 0)
    
    # Annualised mean & std (assuming daily or sub-daily scaled approximations)
    # Using 252 periods as standard normalisation for Sharpe here
    mean_ret = np.mean(strat_ret)
    std_ret = np.std(strat_ret)
    
    if std_ret < 1e-6:
        sharpe = 0.0
    else:
        sharpe = float((mean_ret / std_ret) * np.sqrt(252))
        
    return {
        "accuracy": accuracy,
        "sharpe_ratio": sharpe,
        "total_return": float(np.sum(strat_ret))
    }


# ── Model Wrappers ────────────────────────────────────────────────────────────

class BaseModelWrapper:
    def fit(self, X: pd.DataFrame, y: pd.Series):
        pass
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        # Should return array of shape (n_samples, 2) where col 1 is prob(class=1)
        pass


class LogisticWrapper(BaseModelWrapper):
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = LogisticRegression(class_weight="balanced", dual=False)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)


class XGBoostWrapper(BaseModelWrapper):
    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=100, 
            max_depth=3, 
            learning_rate=0.05,
            eval_metric="logloss"
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.model.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X)


class ProphetWrapper(BaseModelWrapper):
    """
    Prophet doesn't natively do classification on standard feature sets easily, 
    but we can run it on the price to predict the future price, and derive a signal.
    """
    def __init__(self):
        self.model = Prophet(daily_seasonality=False, yearly_seasonality=False)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        # We need the original dates and closes. 
        # For this wrapper we'll extract them if we pass the full dataframe.
        # Original dates must be timezone naive for Prophet
        df = pd.DataFrame({
            'ds': pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values,
            'y': X['close_raw'] # Requires 'close_raw' injection
        })
        self.model.fit(df)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        df = pd.DataFrame({'ds': pd.Series(pd.to_datetime(X.index)).dt.tz_localize(None).values})
        forecast = self.model.predict(df)
        
        # Determine 1 or 0 based on predicted yhat slope
        pred_diff = forecast['yhat'].diff().fillna(0).values
        # Output shape (n, 2). Col 1 is probability. We'll binarize it.
        probs = np.where(pred_diff > 0, 0.8, 0.2)
        out = np.zeros((len(X), 2))
        out[:, 1] = probs
        out[:, 0] = 1 - probs
        return out


# ── Training Pipeline ─────────────────────────────────────────────────────────

def run_training_pipeline(symbol: str, timeframe: str, df_history: pd.DataFrame) -> Dict[str, Any]:
    """
    End-to-end pipeline: engineers features, trains XGB/Logistic/Prophet,
    evaluates on validation set via Sharpe ratio, and saves the winner.
    """
    logger.info(f"Running ML pipeline for {symbol} ({timeframe}). Data size: {len(df_history)}")
    
    if len(df_history) < 200:
        raise ValueError("Insufficient data to train ML pipeline (requires > 200 rows).")

    df = engineer_features(df_history)
    df['close_raw'] = df_history['close'] # For Prophet
    
    if len(df) < 100:
        raise ValueError("Insufficient data after feature engineering.")

    # Time-series split (80% train, 20% validation)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    X_train = train_df[FEATURES + ['close_raw']]
    y_train = train_df["target"]
    
    X_val = val_df[FEATURES + ['close_raw']]
    y_val = val_df["target"].values
    
    # We use subsequent 1-period forward return for Sharpe evaluation
    # so we know what happens in reality when we hold the position
    returns_val = val_df["target_ret_5"].values

    models = {
        "logistic": LogisticWrapper(),
        "xgboost": XGBoostWrapper(),
        "prophet": ProphetWrapper()
    }

    results = {}
    best_sharpe = -999.0
    best_model_name = None
    best_model_obj = None

    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            probs = model.predict_proba(X_val)[:, 1]
            preds = (probs > 0.5).astype(int)
            
            metrics = evaluate_predictions(y_val, preds, returns_val)
            results[name] = metrics
            
            logger.info(f"Model {name} Sharpe: {metrics['sharpe_ratio']:.3f}, Acc: {metrics['accuracy']:.3f}")
            
            if metrics["sharpe_ratio"] > best_sharpe:
                best_sharpe = metrics["sharpe_ratio"]
                best_model_name = name
                best_model_obj = model
        except Exception as e:
            logger.error(f"Error training {name}: {str(e)}")
            results[name] = {"accuracy": 0.0, "sharpe_ratio": -99.0}

    # If all fail, default to logistic
    if not best_model_name:
        best_model_name = "logistic"
        best_model_obj = models["logistic"]
        best_model_obj.fit(X_train, y_train)

    # ── Persistence ───────────────────────────────────────────────────────────
    timestamp = datetime.utcnow().isoformat()
    artifact_name = f"{symbol}_{timeframe}_winner.joblib"
    artifact_path = os.path.join(ARTIFACT_DIR, artifact_name)
    
    # Strip close_raw before saving model object logic? Not necessary but good practice.
    joblib.dump(best_model_obj, artifact_path)

    # Update Registry
    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "model_name": best_model_name,
        "trained_at": timestamp,
        "artifact_file": artifact_name,
        "validation_sharpe": best_sharpe,
        "metrics": results
    }

    with open(REGISTRY_FILE, "a") as f:
        f.write(json.dumps(metadata) + "\n")

    logger.info(f"Winning model for {symbol} {timeframe}: {best_model_name} (Sharpe {best_sharpe:.3f})")
    
    return metadata
