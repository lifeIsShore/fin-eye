from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from random import Random
import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so `import app` works when running as a script.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal
from app.models.market import StockOHLCV
from app.models.macro import MacroIndicator
from app.models.sentiment import SentimentAggregate, NewsArticle


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed DB with synthetic training data")
    parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    parser.add_argument("--start", required=True, help="Start datetime (ISO)")
    parser.add_argument("--end", required=True, help="End datetime (ISO)")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    start = parse_dt(args.start)
    end = parse_dt(args.end)
    rng = Random(args.seed)

    db = SessionLocal()
    try:
        # OHLCV: daily bars
        days = (end.date() - start.date()).days
        if days <= 0:
            raise ValueError("end must be after start")

        base_price = 100.0
        price = base_price

        for i in range(days + 1):
            ts = start + timedelta(days=i)

            # simple drift + small noise
            drift = 0.03
            shock = rng.uniform(-0.5, 0.5)
            price = max(1.0, price + drift + shock)

            open_ = price + rng.uniform(-0.2, 0.2)
            close = price
            high = max(open_, close) + rng.uniform(0.0, 0.3)
            low = min(open_, close) - rng.uniform(0.0, 0.3)
            volume = 1_000_000.0 + rng.uniform(-50_000, 50_000)

            db.add(
                StockOHLCV(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=float(volume),
                )
            )

            # Daily sentiment aggregate (news)
            sent = rng.uniform(-0.2, 0.2)
            db.add(
                SentimentAggregate(
                    symbol=symbol,
                    date=ts.date(),
                    mentions=10,
                    sentiment_score=float(sent),
                    source_type="news",
                )
            )

            # A couple of articles on some days for source diversity
            if i % 3 == 0:
                db.add(
                    NewsArticle(
                        symbol=symbol,
                        title=f"{symbol} headline {i} A",
                        source="Reuters",
                        published_at=ts.replace(hour=12, minute=0, second=0, microsecond=0),
                        sentiment_score=float(sent),
                    )
                )
                db.add(
                    NewsArticle(
                        symbol=symbol,
                        title=f"{symbol} headline {i} B",
                        source="Bloomberg",
                        published_at=ts.replace(hour=13, minute=0, second=0, microsecond=0),
                        sentiment_score=float(-sent),
                    )
                )

            # Macro indicators: seed weekly (ffill will carry)
            if i % 7 == 0:
                d = ts.date()
                db.add(MacroIndicator(indicator_name="vix", value=18.0 + rng.uniform(-2, 2), date=d))
                db.add(
                    MacroIndicator(
                        indicator_name="yield_spread_10y_2y",
                        value=0.5 + rng.uniform(-0.2, 0.2),
                        date=d,
                    )
                )
                db.add(MacroIndicator(indicator_name="fed_funds_rate", value=5.0, date=d))
                db.add(MacroIndicator(indicator_name="unemployment_rate", value=4.0, date=d))
                db.add(MacroIndicator(indicator_name="cpi_yoy", value=3.0, date=d))

        db.commit()
        print(f"Seeded synthetic data for {symbol} from {start.date()} to {end.date()}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

