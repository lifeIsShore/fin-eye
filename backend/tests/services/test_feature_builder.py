from datetime import datetime, timedelta

import numpy as np

from app.services.feature_builder import DbFeatureBuilder
from app.services.technical_models import Timeframe
from app.models.market import StockOHLCV
from app.models.macro import MacroIndicator
from app.models.sentiment import SentimentAggregate, NewsArticle


def test_db_feature_builder_builds_1d_features(test_db):
    symbol = "AAPL"
    start = datetime(2020, 1, 1)
    end = datetime(2020, 3, 31)

    # Seed OHLCV with a gently increasing close to produce non-zero MACD values
    ts_list = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    for i, ts in enumerate(ts_list):
        close = 100.0 + i * 0.5
        test_db.add(
            StockOHLCV(
                symbol=symbol,
                timestamp=ts,
                open=close - 0.2,
                high=close + 0.3,
                low=close - 0.4,
                close=close,
                volume=1_000_000.0,
            )
        )

    # Seed macro indicators (date-based)
    for d in {t.date() for t in ts_list}:
        test_db.add(MacroIndicator(indicator_name="vix", value=18.0, date=d))
        test_db.add(
            MacroIndicator(
                indicator_name="yield_spread_10y_2y",
                value=0.5,
                date=d,
            )
        )
        test_db.add(MacroIndicator(indicator_name="fed_funds_rate", value=5.0, date=d))
        test_db.add(MacroIndicator(indicator_name="unemployment_rate", value=6.5, date=d))
        test_db.add(MacroIndicator(indicator_name="cpi_yoy", value=4.5, date=d))

        # Seed daily sentiment aggregate
        test_db.add(
            SentimentAggregate(
                symbol=symbol,
                date=d,
                mentions=10,
                sentiment_score=0.6,
                source_type="news",
            )
        )

        # Seed a couple of news articles with distinct sources (for diversity)
        test_db.add(
            NewsArticle(
                symbol=symbol,
                title=f"News {d} A",
                source="Reuters",
                published_at=datetime(d.year, d.month, d.day, 12, 0, 0),
                sentiment_score=0.6,
            )
        )
        test_db.add(
            NewsArticle(
                symbol=symbol,
                title=f"News {d} B",
                source="Bloomberg",
                published_at=datetime(d.year, d.month, d.day, 13, 0, 0),
                sentiment_score=-0.2,
            )
        )

    test_db.commit()

    builder = DbFeatureBuilder(db=test_db)
    df = builder.build_features(
        symbol=symbol,
        timeframe=Timeframe.ONE_DAY,
        start=start,
        end=end,
    )

    assert not df.empty
    # Ensure key computed columns exist
    for col in [
        "return_1d",
        "return_5d",
        "volatility_20d",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "vix_level",
        "yield_spread_10y_2y",
    ]:
        assert col in df.columns

    # MACD should not be all zeros for trending prices
    assert not np.allclose(df["macd"].to_numpy(), 0.0)

    # Macro joins should be present and constant given our seed data
    assert float(df["vix_level"].iloc[-1]) == 18.0
    assert float(df["yield_spread_10y_2y"].iloc[-1]) == 0.5

    # Sentiment should be joined
    assert float(df["news_sentiment_1d"].iloc[-1]) == 0.6
    assert float(df["news_source_diversity_30d"].iloc[-1]) >= 2.0

    # Macro score should reflect the "stressed" seeded environment (should be < 50)
    assert float(df["macro_score"].iloc[-1]) < 50.0


def test_db_feature_builder_builds_1w_features(test_db):
    symbol = "AAPL"
    start = datetime(2020, 1, 1)
    end = datetime(2020, 3, 31)

    # Seed daily OHLCV (enough to resample into multiple weeks)
    ts_list = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    for i, ts in enumerate(ts_list):
        close = 100.0 + i * 0.3
        test_db.add(
            StockOHLCV(
                symbol=symbol,
                timestamp=ts,
                open=close - 0.2,
                high=close + 0.3,
                low=close - 0.4,
                close=close,
                volume=1_000_000.0,
            )
        )

    for d in {t.date() for t in ts_list}:
        test_db.add(MacroIndicator(indicator_name="vix", value=18.0, date=d))
        test_db.add(MacroIndicator(indicator_name="yield_spread_10y_2y", value=0.5, date=d))
        test_db.add(MacroIndicator(indicator_name="fed_funds_rate", value=5.0, date=d))
        test_db.add(MacroIndicator(indicator_name="unemployment_rate", value=6.5, date=d))
        test_db.add(MacroIndicator(indicator_name="cpi_yoy", value=4.5, date=d))
        test_db.add(
            SentimentAggregate(
                symbol=symbol,
                date=d,
                mentions=10,
                sentiment_score=0.2,
                source_type="news",
            )
        )

    test_db.commit()

    builder = DbFeatureBuilder(db=test_db)
    df = builder.build_features(
        symbol=symbol,
        timeframe=Timeframe.ONE_WEEK,
        start=start,
        end=end,
    )

    assert not df.empty
    # Weekly resample should have fewer rows than daily range
    assert len(df) < len(ts_list)
    assert "macd" in df.columns
    assert "macro_score" in df.columns

