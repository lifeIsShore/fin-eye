"""
Tests for Technical Consensus service (MVP-TECH-02).
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.technical_service import compute_technical_consensus

@patch("app.services.technical_service.generate_timeframe_signal")
def test_compute_technical_consensus_bullish(mock_generate):
    """
    Test when signals are mostly bullish, consensus score should be high > 50.
    """
    # Mocking generate_timeframe_signal to return predefined signals
    
    mock_generate.side_effect = [
        {"timeframe": "1h", "direction": "Bullish", "signal_raw": 0.8, "confidence": 80.0, "validation_sharpe": 1.5, "model_used": "xgboost"},
        {"timeframe": "1d", "direction": "Bullish", "signal_raw": 0.6, "confidence": 60.0, "validation_sharpe": 1.2, "model_used": "logistic"},
        {"timeframe": "1wk", "direction": "Bearish", "signal_raw": -0.5, "confidence": 50.0, "validation_sharpe": 0.5, "model_used": "xgboost"},
        {"timeframe": "1mo", "direction": "Bullish", "signal_raw": 0.9, "confidence": 90.0, "validation_sharpe": 2.0, "model_used": "logistic"}
    ]
    
    result = compute_technical_consensus("AAPL")
    
    # Weights used (from Sharpe): 1.5, 1.2, 0.5, 2.0
    # Weighted Signal: (0.8*1.5) + (0.6*1.2) + (-0.5*0.5) + (0.9*2.0) = 1.2 + 0.72 - 0.25 + 1.8 = 3.47
    # Total Weight: 1.5 + 1.2 + 0.5 + 2.0 = 5.2
    # Consensus Raw: 3.47 / 5.2 = 0.667
    # Score 0-100: (0.667 + 1) / 2 * 100 = 83.35 -> rounded to 83.4
    
    assert result["symbol"] == "AAPL"
    assert result["consensus_score"] >= 83.0 and result["consensus_score"] <= 84.0
    assert result["consensus_label"] == "Strong Bullish"
    assert len(result["signals"]) == 4


@patch("app.services.technical_service.generate_timeframe_signal")
def test_compute_technical_consensus_bearish(mock_generate):
    """
    Test when signals are mostly bearish, consensus score should be low < 50.
    """
    
    mock_generate.side_effect = [
        {"timeframe": "1h", "direction": "Bearish", "signal_raw": -0.8, "confidence": 80.0, "validation_sharpe": 1.5, "model_used": "xgboost"},
        {"timeframe": "1d", "direction": "Bearish", "signal_raw": -0.6, "confidence": 60.0, "validation_sharpe": 1.2, "model_used": "logistic"},
        {"timeframe": "1wk", "direction": "Bearish", "signal_raw": -0.5, "confidence": 50.0, "validation_sharpe": 0.5, "model_used": "xgboost"},
        {"timeframe": "1mo", "direction": "Bearish", "signal_raw": -0.9, "confidence": 90.0, "validation_sharpe": 2.0, "model_used": "logistic"}
    ]
    
    result = compute_technical_consensus("AAPL")
    
    # Weighted Signal: (-0.8*1.5) + (-0.6*1.2) + (-0.5*0.5) + (-0.9*2.0) = -1.2 - 0.72 - 0.25 - 1.8 = -3.97
    # Total Weight: 5.2
    # Consensus Raw: -3.97 / 5.2 = -0.763
    # Score 0-100: (-0.763 + 1) / 2 * 100 = 11.85 -> rounded to 11.8
    # 0-20 label is Strong Bearish
    
    assert result["consensus_score"] >= 11.0 and result["consensus_score"] <= 12.0
    assert result["consensus_label"] == "Strong Bearish"
