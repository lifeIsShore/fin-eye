from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

import pandas as pd

from app.services.technical_models import Timeframe
from app.schemas.data_models import TechnicalFeatureRow


class FeatureBuilder(Protocol):
    """
    Abstract interface for building model-ready feature matrices.

    Implementations are responsible for:
      - Pulling OHLCV data
      - Joining macro indicators and sentiment aggregates
      - Computing technical indicators
      - Aligning everything on a common time index
    """

    def build_features(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        ...


class StubFeatureBuilder:
    """
    Minimal placeholder implementation of FeatureBuilder.

    This returns a synthetic DataFrame whose columns match TechnicalFeatureRow
    so that training code can be developed and tested in isolation. A future
    session will replace this with a real implementation wired to the DB and
    indicator calculations.
    """

    def build_features(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        index = pd.date_range(start, end, freq="D")
        if index.empty:
            return pd.DataFrame()

        data = {
            "symbol": [symbol] * len(index),
            "timestamp": index,
            # Simple synthetic values; real implementation will use actual indicators
            "return_1d": 0.0,
            "return_5d": 0.0,
            "volatility_20d": 0.1,
            "rsi_14": 50.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "bb_upper": 1.0,
            "bb_middle": 0.0,
            "bb_lower": -1.0,
            "news_sentiment_1d": 0.0,
            "news_sentiment_7d": 0.0,
            "news_sentiment_30d": 0.0,
            "news_source_diversity_30d": 1.0,
            "macro_score": 50.0,
            "vix_level": 20.0,
            "yield_spread_10y_2y": 0.0,
            "day_of_week": [ts.weekday() for ts in index],
            "month": [ts.month for ts in index],
            "hour_of_day": [ts.hour for ts in index],
        }

        df = pd.DataFrame(data, index=index)
        # Validate against TechnicalFeatureRow schema for early mismatch detection
        for row in df.head(5).to_dict(orient="records"):
            TechnicalFeatureRow(**row)
        return df

