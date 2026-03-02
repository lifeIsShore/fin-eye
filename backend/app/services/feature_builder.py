from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.services.technical_models import Timeframe
from app.schemas.data_models import TechnicalFeatureRow
from app.models.market import StockOHLCV
from app.models.macro import MacroIndicator
from app.models.sentiment import SentimentAggregate, NewsArticle
from app.services.macro_scoring import compute_macro_score


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


class DbFeatureBuilder:
    """
    DB-backed FeatureBuilder for daily (1d) timeframe.

    Currently implements:
      - OHLCV-based price features (returns, volatility, RSI-14, Bollinger bands)
      - Macro backdrop (VIX level) and placeholder Macro Score
      - Synthetic defaults for sentiment-related fields
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_features(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        if timeframe is not Timeframe.ONE_DAY:
            # Narrow slice for now; other timeframes can be added later.
            return pd.DataFrame()

        # 1. Load OHLCV from DB
        rows = (
            self.db.query(StockOHLCV)
            .filter(
                StockOHLCV.symbol == symbol,
                StockOHLCV.timestamp >= start,
                StockOHLCV.timestamp <= end,
            )
            .order_by(StockOHLCV.timestamp.asc())
            .all()
        )
        if not rows:
            return pd.DataFrame()

        ohlcv_df = pd.DataFrame(
            [
                {
                    "symbol": r.symbol,
                    "timestamp": r.timestamp,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        )
        ohlcv_df = ohlcv_df.set_index("timestamp").sort_index()

        close = ohlcv_df["close"]

        # 2. Basic technical indicators
        return_1d = close.pct_change(1).fillna(0.0)
        return_5d = close.pct_change(5).fillna(0.0)
        volatility_20d = close.pct_change(1).rolling(20).std().fillna(0.0)

        # RSI-14 (Wilder's smoothing)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        roll_up = gain.rolling(14).mean()
        roll_down = loss.rolling(14).mean()
        rs = roll_up / (roll_down.replace(0, np.nan))
        rsi_14 = 100 - (100 / (1 + rs))
        rsi_14 = rsi_14.fillna(50.0)

        # Bollinger Bands (20-day, 2 std)
        rolling_mean = close.rolling(20).mean()
        rolling_std = close.rolling(20).std()
        bb_middle = rolling_mean.fillna(close)
        bb_upper = (rolling_mean + 2 * rolling_std).fillna(close)
        bb_lower = (rolling_mean - 2 * rolling_std).fillna(close)

        # MACD (12, 26, 9) on close
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd = (ema_12 - ema_26).fillna(0.0)
        macd_signal = macd.ewm(span=9, adjust=False).mean().fillna(0.0)
        macd_hist = (macd - macd_signal).fillna(0.0)

        # 3. Macro indicators per date (simple join) -> macro_score series
        dates = ohlcv_df.index.normalize().unique()
        macro_rows = (
            self.db.query(MacroIndicator)
            .filter(
                MacroIndicator.indicator_name.in_(
                    [
                        "vix",
                        "yield_spread_10y_2y",
                        "fed_funds_rate",
                        "unemployment_rate",
                        "cpi_yoy",
                    ]
                ),
                MacroIndicator.date >= dates.min().date(),
                MacroIndicator.date <= dates.max().date(),
            )
            .order_by(MacroIndicator.date.asc())
            .all()
        )
        macro_df = (
            pd.DataFrame(
                [
                    {
                        "date": r.date,
                        "indicator_name": r.indicator_name,
                        "value": r.value,
                    }
                    for r in macro_rows
                ]
            )
            if macro_rows
            else pd.DataFrame(columns=["date", "indicator_name", "value"])
        )

        if not macro_df.empty:
            wide = (
                macro_df.pivot(index="date", columns="indicator_name", values="value")
                .sort_index()
                .ffill()
            )
            wide = wide.reindex(dates, method="ffill")
        else:
            wide = pd.DataFrame(index=dates)

        vix_series = wide.get("vix", pd.Series(20.0, index=wide.index)).fillna(20.0)
        yield_series = wide.get(
            "yield_spread_10y_2y", pd.Series(0.0, index=wide.index)
        ).fillna(0.0)

        # Compute macro score per date using the shared heuristic
        macro_scores = []
        for d in wide.index:
            indicators = {
                "fed_funds_rate": float(wide.at[d, "fed_funds_rate"])
                if "fed_funds_rate" in wide.columns and pd.notna(wide.at[d, "fed_funds_rate"])
                else None,
                "unemployment_rate": float(wide.at[d, "unemployment_rate"])
                if "unemployment_rate" in wide.columns and pd.notna(wide.at[d, "unemployment_rate"])
                else None,
                "yield_spread_10y_2y": float(wide.at[d, "yield_spread_10y_2y"])
                if "yield_spread_10y_2y" in wide.columns and pd.notna(wide.at[d, "yield_spread_10y_2y"])
                else None,
                "cpi_yoy": float(wide.at[d, "cpi_yoy"])
                if "cpi_yoy" in wide.columns and pd.notna(wide.at[d, "cpi_yoy"])
                else None,
                "vix": float(wide.at[d, "vix"])
                if "vix" in wide.columns and pd.notna(wide.at[d, "vix"])
                else None,
            }
            macro_scores.append(compute_macro_score(indicators)["score"])
        macro_score_by_date = pd.Series(macro_scores, index=wide.index).fillna(50.0)

        # Map date-indexed macro series back to timestamp index (same order as ohlcv_df)
        vix_aligned = pd.Series(vix_series.values, index=ohlcv_df.index)
        yield_aligned = pd.Series(yield_series.values, index=ohlcv_df.index)
        macro_score = pd.Series(macro_score_by_date.values, index=ohlcv_df.index)

        # 4. Sentiment aggregates (news) + source diversity
        start_date = dates.min().date()
        end_date = dates.max().date()

        sent_rows = (
            self.db.query(SentimentAggregate)
            .filter(
                SentimentAggregate.symbol == symbol,
                SentimentAggregate.source_type == "news",
                SentimentAggregate.date >= start_date,
                SentimentAggregate.date <= end_date,
            )
            .order_by(SentimentAggregate.date.asc())
            .all()
        )
        sent_df = (
            pd.DataFrame(
                [
                    {
                        "date": r.date,
                        "mentions": int(r.mentions or 0),
                        "score": float(r.sentiment_score or 0.0),
                    }
                    for r in sent_rows
                ]
            ).set_index("date")
            if sent_rows
            else pd.DataFrame(columns=["mentions", "score"], index=pd.Index([], name="date"))
        )

        sent_df = sent_df.reindex(wide.index).fillna({"mentions": 0, "score": 0.0})
        num = (sent_df["score"] * sent_df["mentions"]).astype(float)
        den = sent_df["mentions"].astype(float)

        def weighted_roll(window: int) -> pd.Series:
            n = num.rolling(window).sum()
            d = den.rolling(window).sum()
            return (n / d.replace(0, np.nan)).fillna(0.0)

        news_1d = weighted_roll(1)
        news_7d = weighted_roll(7)
        news_30d = weighted_roll(30)

        # Source diversity: distinct news sources observed over last 30 days (uses NewsArticle)
        article_rows = (
            self.db.query(NewsArticle)
            .filter(
                NewsArticle.symbol == symbol,
                NewsArticle.published_at >= start - pd.Timedelta(days=30),
                NewsArticle.published_at <= end,
            )
            .all()
        )
        sources_by_date: dict = {}
        for a in article_rows:
            d = a.published_at.date()
            sources_by_date.setdefault(d, set()).add(a.source or "Unknown")

        # Sliding window distinct count
        from collections import Counter, deque
        window = deque()
        counts: Counter = Counter()
        diversity_values = []
        for d in wide.index:
            cur = d.date()
            # add current date sources
            todays = sources_by_date.get(cur, set())
            window.append((cur, todays))
            for s in todays:
                counts[s] += 1
            # drop older than 30 days window (inclusive)
            cutoff = (cur - pd.Timedelta(days=29)).date()
            while window and window[0][0] < cutoff:
                old_date, old_sources = window.popleft()
                for s in old_sources:
                    counts[s] -= 1
                    if counts[s] <= 0:
                        del counts[s]
            diversity_values.append(float(len(counts)))
        source_div_30d_by_date = pd.Series(diversity_values, index=wide.index).replace(0.0, 1.0)

        # 5. Assemble feature DataFrame
        df = pd.DataFrame(
            {
                "symbol": symbol,
                "timestamp": ohlcv_df.index,
                "return_1d": return_1d,
                "return_5d": return_5d,
                "volatility_20d": volatility_20d,
                "rsi_14": rsi_14,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                # Sentiment (news)
                "news_sentiment_1d": pd.Series(news_1d.values, index=ohlcv_df.index),
                "news_sentiment_7d": pd.Series(news_7d.values, index=ohlcv_df.index),
                "news_sentiment_30d": pd.Series(news_30d.values, index=ohlcv_df.index),
                "news_source_diversity_30d": pd.Series(
                    source_div_30d_by_date.values, index=ohlcv_df.index
                ),
                # Macro backdrop
                "macro_score": macro_score,
                "vix_level": vix_aligned,
                "yield_spread_10y_2y": yield_aligned,
                # Temporal
                "day_of_week": [ts.weekday() for ts in ohlcv_df.index],
                "month": [ts.month for ts in ohlcv_df.index],
                "hour_of_day": [ts.hour for ts in ohlcv_df.index],
            },
            index=ohlcv_df.index,
        )

        # Validate against TechnicalFeatureRow schema for early mismatch detection
        for row in df.head(5).to_dict(orient="records"):
            TechnicalFeatureRow(**row)

        return df


