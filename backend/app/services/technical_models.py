from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np
import pandas as pd


class Timeframe(str, Enum):
    ONE_HOUR  = "1h"
    FOUR_HOUR = "4h"
    ONE_DAY   = "1d"
    ONE_WEEK  = "1wk"   # fixed: was "1w", ml_pipeline uses "1wk"
    ONE_MONTH = "1mo"   # fixed: was "1m", ml_pipeline uses "1mo"


class ModelKind(str, Enum):
    LOGISTIC       = "logistic"
    XGBOOST        = "xgboost"
    LIGHTGBM       = "lightgbm"    # Sprint 3 addition
    ENSEMBLE       = "ensemble"    # Sprint 3 addition
    PROPHET        = "prophet"     # kept for backwards compat (removed from competition)
    LSTM_ATTENTION = "lstm_attention"


class TechnicalModel(Protocol):
    kind: ModelKind

    def fit(self, features: pd.DataFrame, targets: pd.Series) -> None: ...
    def predict(self, features: pd.DataFrame) -> np.ndarray: ...


@dataclass
class TrainingWindow:
    train_start: pd.Timestamp
    train_end:   pd.Timestamp
    valid_start: pd.Timestamp
    valid_end:   pd.Timestamp


@dataclass
class ModelPerformance:
    model_kind:  ModelKind
    timeframe:   Timeframe
    sharpe_ratio: float
    accuracy:    float


@dataclass
class TimeframeWinner:
    timeframe:    Timeframe
    model_kind:   ModelKind
    sharpe_ratio: float
    accuracy:     float


def compute_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    if returns.size == 0:
        return 0.0
    excess = returns - risk_free_rate
    std = np.std(excess)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std)


def generate_walk_forward_windows(
    index: pd.DatetimeIndex,
    train_years: int = 3,
    valid_months: int = 6,
) -> List[TrainingWindow]:
    if index.empty:
        return []
    windows: List[TrainingWindow] = []
    start = index.min()
    while True:
        train_end = start + pd.DateOffset(years=train_years)
        valid_end = train_end + pd.DateOffset(months=valid_months)
        if valid_end > index.max():
            break
        windows.append(TrainingWindow(
            train_start=start, train_end=train_end,
            valid_start=train_end, valid_end=valid_end,
        ))
        start = valid_end
    return windows


def pick_timeframe_winner(
    performances: List[ModelPerformance],
) -> Optional[TimeframeWinner]:
    if not performances:
        return None
    best = max(performances, key=lambda p: p.sharpe_ratio)
    return TimeframeWinner(
        timeframe=best.timeframe, model_kind=best.model_kind,
        sharpe_ratio=best.sharpe_ratio, accuracy=best.accuracy,
    )


def summarise_winners_by_timeframe(
    winners: List[TimeframeWinner],
) -> Dict[Timeframe, TimeframeWinner]:
    return {w.timeframe: w for w in winners}
