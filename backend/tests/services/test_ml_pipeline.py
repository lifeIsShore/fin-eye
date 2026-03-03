"""
Tests for ML-driven Technical Pipeline (MVP-TECH-01 & 02).
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from app.services.ml_pipeline import (
    engineer_features,
    evaluate_predictions,
    LogisticWrapper,
    XGBoostWrapper,
    run_training_pipeline,
    FEATURES
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _generate_synthetic_ohlcv(n=300, seed=42):
    """Generates synthetic price data for testing feature engineering & models."""
    rng = np.random.RandomState(seed)
    returns = rng.normal(0.0005, 0.015, n)
    
    # Start price
    price = 100.0
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    
    data = []
    for d, r in zip(dates, returns):
        open_p = price
        high_p = price * (1 + abs(rng.normal(0, 0.01)))
        low_p = price * (1 - abs(rng.normal(0, 0.01)))
        close_p = price * (1 + r)
        volume = rng.randint(1_000_000, 5_000_000)
        
        data.append({
            "date": d,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume
        })
        price = close_p
        
    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)
    return df


# ── Tests ────────────────────────────────────────────────────────────────────

def test_feature_engineering_shape():
    df = _generate_synthetic_ohlcv(300)
    df_feat = engineer_features(df)
    
    # 50 rows dropped from rolling max window, plus 5 shifted back
    assert len(df_feat) > 200
    
    # Check that all requested features are built
    for feature in FEATURES:
        assert feature in df_feat.columns
        
    # Check target
    assert "target" in df_feat.columns
    # Target should be 1 or 0
    assert set(df_feat["target"].unique()).issubset({0, 1})
    # Target should not be NaN
    assert not df_feat["target"].isnull().any()


def test_evaluate_predictions_logic():
    y_true = np.array([1, 0, 1, 1, 0])
    y_pred = np.array([1, 0, 1, 0, 1])
    returns = np.array([0.05, -0.02, 0.03, 0.04, -0.01])
    
    metrics = evaluate_predictions(y_true, y_pred, returns)
    
    assert metrics["accuracy"] == 0.6  # 3/5
    
    # Strategy returns:
    # idx0: pred=1, ret = 0.05
    # idx1: pred=0, ret = 0.0
    # idx2: pred=1, ret = 0.03
    # idx3: pred=0, ret = 0.0
    # idx4: pred=1, ret = -0.01
    # total_strat_ret = 0.05 + 0 + 0.03 + 0 - 0.01 = 0.07
    
    assert np.isclose(metrics["total_return"], 0.07)
    
    # Sharpe ratio computation:
    # strat returns: [0.05, 0.0, 0.03, 0.0, -0.01]
    # mean = 0.014
    # std = approx 0.0224
    # sharpe approx 9.9
    assert metrics["sharpe_ratio"] > 0


def test_logistic_wrapper_fit_predict():
    df = _generate_synthetic_ohlcv(200)
    df_feat = engineer_features(df)
    
    X = df_feat[FEATURES]
    y = df_feat["target"]
    
    wrapper = LogisticWrapper()
    wrapper.fit(X, y)
    
    probs = wrapper.predict_proba(X)
    assert probs.shape == (len(X), 2)
    assert np.all(probs >= 0) and np.all(probs <= 1)


def test_xgboost_wrapper_fit_predict():
    df = _generate_synthetic_ohlcv(200)
    df_feat = engineer_features(df)
    
    X = df_feat[FEATURES]
    y = df_feat["target"]
    
    wrapper = XGBoostWrapper()
    wrapper.fit(X, y)
    
    probs = wrapper.predict_proba(X)
    assert probs.shape == (len(X), 2)
    assert np.all(probs >= 0) and np.all(probs <= 1)


@patch("app.services.ml_pipeline.joblib.dump")
def test_run_training_pipeline(mock_dump):
    """
    End-to-end pipeline test on synthetic data avoiding joblib IO and Prophet
    to keep test fast.
    """
    df = _generate_synthetic_ohlcv(500)
    
    # We patch out Prophet locally here because Prophet takes ~2-5s to train 
    # which is slow for unit tests, so we replace it with a dummy wrapper.
    class DummyProphet(LogisticWrapper):
        pass
        
    with patch.dict("app.services.ml_pipeline.run_training_pipeline.__globals__", 
                    {"ProphetWrapper": DummyProphet}):
        metadata = run_training_pipeline("TEST_SYM", "1d", df)
        
    assert metadata["symbol"] == "TEST_SYM"
    assert metadata["timeframe"] == "1d"
    assert "metrics" in metadata
    assert "model_name" in metadata
    
    # Assert model was attempted to save
    mock_dump.assert_called_once()
