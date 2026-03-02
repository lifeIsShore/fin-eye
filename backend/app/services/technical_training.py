from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from app.services.technical_models import (
    Timeframe,
    ModelKind,
    TrainingWindow,
    ModelPerformance,
    generate_walk_forward_windows,
    compute_sharpe_ratio,
    pick_timeframe_winner,
)
from app.services.model_registry import ModelRegistry, record_winners
from app.services.feature_builder import FeatureBuilder, StubFeatureBuilder


@dataclass
class TrainingResult:
    timeframe: Timeframe
    performances: List[ModelPerformance]


def _prepare_walk_forward_splits(
    df: pd.DataFrame,
    timeframe: Timeframe,
) -> List[Tuple[TrainingWindow, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]]:
    """
    Create walk-forward train/validation splits for a given timeframe.

    Assumes df has a DateTimeIndex, feature columns, and a 'target' column with
    {-1, 0, 1} directional labels as described in the PRD.
    """
    if "target" not in df.columns:
        raise ValueError("Data frame must contain a 'target' column")

    windows = generate_walk_forward_windows(df.index)
    splits: List[
        Tuple[TrainingWindow, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]
    ] = []

    feature_cols = [c for c in df.columns if c != "target"]

    for window in windows:
        train_mask = (df.index >= window.train_start) & (df.index < window.train_end)
        valid_mask = (df.index >= window.valid_start) & (df.index < window.valid_end)

        X_train = df.loc[train_mask, feature_cols]
        y_train = df.loc[train_mask, "target"]
        X_valid = df.loc[valid_mask, feature_cols]
        y_valid = df.loc[valid_mask, "target"]

        if X_train.empty or X_valid.empty:
            continue

        splits.append((window, X_train, y_train, X_valid, y_valid))

    return splits


def train_logistic_baseline_for_timeframe(
    df: pd.DataFrame,
    timeframe: Timeframe,
    registry: ModelRegistry,
) -> TrainingResult:
    """
    Minimal training orchestration for MVP-TECH-01:

    - Uses a simple logistic regression baseline.
    - Runs walk-forward evaluation for the given timeframe.
    - Computes Sharpe ratio from directional returns.
    - Picks a winner (only one model kind for now) and records it in the registry.
    """
    splits = _prepare_walk_forward_splits(df, timeframe)
    performances: List[ModelPerformance] = []

    if not splits:
        return TrainingResult(timeframe=timeframe, performances=performances)

    # Aggregate returns across validation windows
    all_valid_returns: List[float] = []
    correct_predictions = 0
    total_predictions = 0

    for _window, X_train, y_train, X_valid, y_valid in splits:
        # For the baseline, treat positive class as +1 and negative as -1, ignoring 0 for Sharpe
        clf = LogisticRegression(max_iter=1000, multi_class="auto")
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_valid)
        # Convert directional predictions into simple returns proxy: +1, 0, -1
        # In a future iteration, this can be tied to actual price returns.
        returns = np.where(y_pred == y_valid.to_numpy(), 1.0, -1.0)

        all_valid_returns.extend(returns.tolist())

        correct_predictions += int((y_pred == y_valid.to_numpy()).sum())
        total_predictions += y_valid.shape[0]

    sharpe = compute_sharpe_ratio(np.array(all_valid_returns))
    accuracy = (correct_predictions / total_predictions) if total_predictions else 0.0

    perf = ModelPerformance(
        model_kind=ModelKind.LOGISTIC,
        timeframe=timeframe,
        sharpe_ratio=sharpe,
        accuracy=accuracy,
    )
    performances.append(perf)

    winner = pick_timeframe_winner(performances)
    if winner:
        record_winners(registry, [winner], notes="logistic baseline v1")

    return TrainingResult(timeframe=timeframe, performances=performances)


def train_xgboost_for_timeframe(
    df: pd.DataFrame,
    timeframe: Timeframe,
    registry: ModelRegistry,
) -> TrainingResult:
    """
    XGBoost-based training orchestration for a single timeframe.

    Mirrors the logistic baseline flow but uses a tree-based model that can
    capture non-linear relationships in the engineered features.
    """
    splits = _prepare_walk_forward_splits(df, timeframe)
    performances: List[ModelPerformance] = []

    if not splits:
        return TrainingResult(timeframe=timeframe, performances=performances)

    all_valid_returns: List[float] = []
    correct_predictions = 0
    total_predictions = 0

    for _window, X_train, y_train, X_valid, y_valid in splits:
        # XGBoost expects non-negative class labels; map {-1,0,1} -> {0,1,2}
        y_train_mapped = (y_train.to_numpy() + 1).astype(int)
        y_valid_mapped = (y_valid.to_numpy() + 1).astype(int)

        clf = XGBClassifier(
            max_depth=4,
            n_estimators=100,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softmax",
            num_class=3,
            eval_metric="mlogloss",
            n_jobs=1,
        )
        clf.fit(X_train, y_train_mapped)

        y_pred = clf.predict(X_valid)

        returns = np.where(y_pred == y_valid_mapped, 1.0, -1.0)
        all_valid_returns.extend(returns.tolist())

        correct_predictions += int((y_pred == y_valid_mapped).sum())
        total_predictions += y_valid_mapped.shape[0]

    sharpe = compute_sharpe_ratio(np.array(all_valid_returns))
    accuracy = (correct_predictions / total_predictions) if total_predictions else 0.0

    perf = ModelPerformance(
        model_kind=ModelKind.XGBOOST,
        timeframe=timeframe,
        sharpe_ratio=sharpe,
        accuracy=accuracy,
    )
    performances.append(perf)

    winner = pick_timeframe_winner(performances)
    if winner:
        record_winners(registry, [winner], notes="xgboost v1")

    return TrainingResult(timeframe=timeframe, performances=performances)


def train_all_models_for_timeframe(
    timeframe: Timeframe,
    registry: ModelRegistry,
    symbol: str,
    start: datetime,
    end: datetime,
    feature_builder: FeatureBuilder | None = None,
) -> TrainingResult:
    """
    Orchestrate training of all configured models for a single timeframe and
    record the best-performing winner by Sharpe ratio.

    Currently runs:
      - Logistic regression baseline
      - XGBoost classifier

    Future sessions can extend this to Prophet and LSTM without changing the
    external interface.
    """
    all_performances: List[ModelPerformance] = []

    builder = feature_builder or StubFeatureBuilder()
    df = builder.build_features(symbol=symbol, timeframe=timeframe, start=start, end=end)
    if df.empty:
        return TrainingResult(timeframe=timeframe, performances=all_performances)

    # Derive next-period direction target from return_1d (shifted by -1).
    # If return_1d at t is (close_t / close_{t-1}) - 1, then return_1d at t+1
    # approximates next day's return relative to t. This keeps the FeatureBuilder
    # contract stable while enabling end-to-end training.
    df = df.copy()
    next_ret = df["return_1d"].shift(-1).fillna(0.0)
    df["target"] = np.where(next_ret > 0, 1, np.where(next_ret < 0, -1, 0)).astype(int)

    # Train logistic baseline
    logistic_result = train_logistic_baseline_for_timeframe(df, timeframe, registry)
    all_performances.extend(logistic_result.performances)

    # Train XGBoost baseline
    xgb_result = train_xgboost_for_timeframe(df, timeframe, registry)
    all_performances.extend(xgb_result.performances)

    # Determine overall winner across all model kinds
    winner = pick_timeframe_winner(all_performances)
    if winner:
        # Record a consolidated winner entry
        record_winners(registry, [winner], notes="combined models v1")

    return TrainingResult(timeframe=timeframe, performances=all_performances)

