import numpy as np
import pandas as pd

from app.services.technical_models import (
    Timeframe,
    ModelKind,
    TrainingWindow,
    ModelPerformance,
    compute_sharpe_ratio,
    generate_walk_forward_windows,
    pick_timeframe_winner,
    summarise_winners_by_timeframe,
)


def test_compute_sharpe_ratio_basic():
    returns = np.array([0.01, 0.02, -0.005, 0.015])
    sharpe = compute_sharpe_ratio(returns)
    assert isinstance(sharpe, float)
    # It should be positive for mostly positive returns
    assert sharpe > 0


def test_compute_sharpe_ratio_zero_std():
    returns = np.array([0.0, 0.0, 0.0])
    sharpe = compute_sharpe_ratio(returns)
    assert sharpe == 0.0


def test_generate_walk_forward_windows_empty_index():
    idx = pd.DatetimeIndex([])
    windows = generate_walk_forward_windows(idx)
    assert windows == []


def test_generate_walk_forward_windows_creates_windows():
    # 5 years of daily data
    idx = pd.date_range("2015-01-01", periods=365 * 5, freq="D")
    windows = generate_walk_forward_windows(idx, train_years=3, valid_months=6)
    # We expect at least one window
    assert len(windows) >= 1
    for w in windows:
        assert isinstance(w, TrainingWindow)
        assert w.train_start < w.train_end < w.valid_end


def test_pick_timeframe_winner_and_summary():
    performances = [
        ModelPerformance(
            model_kind=ModelKind.LOGISTIC,
            timeframe=Timeframe.ONE_DAY,
            sharpe_ratio=0.5,
            accuracy=0.6,
        ),
        ModelPerformance(
            model_kind=ModelKind.XGBOOST,
            timeframe=Timeframe.ONE_DAY,
            sharpe_ratio=1.0,
            accuracy=0.65,
        ),
    ]
    winner = pick_timeframe_winner(performances)
    assert winner is not None
    assert winner.model_kind == ModelKind.XGBOOST

    summary = summarise_winners_by_timeframe([winner])
    assert Timeframe.ONE_DAY in summary
    assert summary[Timeframe.ONE_DAY].model_kind == ModelKind.XGBOOST

