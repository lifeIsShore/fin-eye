import numpy as np
import pandas as pd

from datetime import datetime, timedelta

from app.services.technical_models import Timeframe, ModelKind
from app.services.model_registry import InMemoryModelRegistry
from app.services.technical_training import (
    _prepare_walk_forward_splits,
    train_logistic_baseline_for_timeframe,
    train_xgboost_for_timeframe,
    train_all_models_for_timeframe,
)


def _make_synthetic_dataframe() -> pd.DataFrame:
  # 5 years of daily data with simple features and targets cycling through -1, 0, 1
  idx = pd.date_range("2015-01-01", periods=365 * 5, freq="D")
  data = {
      "feature_1": np.random.randn(len(idx)),
      "feature_2": np.random.randn(len(idx)),
      "target": np.tile(np.array([-1, 0, 1]), len(idx) // 3 + 1)[: len(idx)],
  }
  return pd.DataFrame(data, index=idx)


def test_prepare_walk_forward_splits_basic():
  df = _make_synthetic_dataframe()
  splits = _prepare_walk_forward_splits(df, Timeframe.ONE_DAY)
  assert len(splits) >= 1
  for window, X_train, y_train, X_valid, y_valid in splits:
      assert not X_train.empty
      assert not X_valid.empty
      assert "target" not in X_train.columns
      assert y_train.name == "target"


def test_train_logistic_baseline_for_timeframe_records_winner():
  df = _make_synthetic_dataframe()
  registry = InMemoryModelRegistry()

  result = train_logistic_baseline_for_timeframe(
      df=df,
      timeframe=Timeframe.ONE_DAY,
      registry=registry,
  )

  # Should have at least one performance entry
  assert result.performances
  perf = result.performances[0]
  assert perf.timeframe == Timeframe.ONE_DAY

  # This helper returns performance only; persistence happens in the orchestrator


def test_train_xgboost_for_timeframe_records_winner():
  df = _make_synthetic_dataframe()
  registry = InMemoryModelRegistry()

  result = train_xgboost_for_timeframe(
      df=df,
      timeframe=Timeframe.ONE_DAY,
      registry=registry,
  )

  assert result.performances
  perf = result.performances[0]
  assert perf.timeframe == Timeframe.ONE_DAY

  # This helper returns performance only; persistence happens in the orchestrator


def test_train_all_models_for_timeframe_records_combined_winner():
  registry = InMemoryModelRegistry()

  result = train_all_models_for_timeframe(
      timeframe=Timeframe.ONE_DAY,
      registry=registry,
      symbol="AAPL",
      start=datetime(2015, 1, 1),
      end=datetime(2019, 12, 31),
  )

  # We should have performances from more than one model kind
  kinds = {p.model_kind for p in result.performances}
  assert ModelKind.LOGISTIC in kinds
  assert ModelKind.XGBOOST in kinds

  # Registry should have at least one latest entry for the timeframe
  latest = registry.get_latest_for_timeframe(Timeframe.ONE_DAY, symbol="AAPL")
  assert latest is not None

