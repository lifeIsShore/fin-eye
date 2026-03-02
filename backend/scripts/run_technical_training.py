from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any, Dict

from app.db.database import SessionLocal
from app.services.feature_builder import DbFeatureBuilder
from app.services.model_registry import InMemoryModelRegistry
from app.services.technical_models import Timeframe
from app.services.technical_training import train_all_models_for_timeframe


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MVP-TECH-01 training (1d)")
    parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    parser.add_argument("--start", required=True, help="Start datetime (ISO), e.g. 2018-01-01T00:00:00")
    parser.add_argument("--end", required=True, help="End datetime (ISO), e.g. 2024-01-01T00:00:00")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    start = parse_dt(args.start)
    end = parse_dt(args.end)

    db = SessionLocal()
    try:
        builder = DbFeatureBuilder(db=db)
        registry = InMemoryModelRegistry()

        result = train_all_models_for_timeframe(
            timeframe=Timeframe.ONE_DAY,
            registry=registry,
            symbol=symbol,
            start=start,
            end=end,
            feature_builder=builder,
        )

        print(f"Symbol: {symbol}  Timeframe: 1d")
        if not result.performances:
            print("No performances produced (insufficient data?)")
            return

        for perf in result.performances:
            print(
                f"- {perf.model_kind.value}: sharpe={perf.sharpe_ratio:.3f}  acc={perf.accuracy:.3f}"
            )

        latest = registry.get_latest_for_timeframe(Timeframe.ONE_DAY)
        if latest:
            print(
                f"Winner: {latest.model_kind.value}  sharpe={latest.sharpe_ratio:.3f}  acc={latest.accuracy:.3f}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()

