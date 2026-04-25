from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Any, Dict
import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so `import app` works when running as a script.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal
from app.services.feature_builder import DbFeatureBuilder
from app.services.model_registry import JsonlFileModelRegistry
from app.services.technical_models import Timeframe
from app.services.technical_training import train_all_models_for_timeframe
from app.services.model_artifacts import ModelArtifactStore


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MVP-TECH-01 training")
    # Support both --symbol and --symbols for flexibility
    parser.add_argument("--symbol", help="Single ticker symbol, e.g. AAPL")
    parser.add_argument("--symbols", help="Comma-separated ticker symbols, e.g. AAPL,MSFT,SPY")
    parser.add_argument(
        "--start", 
        help="Start datetime (ISO), defaults to 5 years ago. E.g. 2018-01-01T00:00:00"
    )
    parser.add_argument(
        "--end", 
        help="End datetime (ISO), defaults to now. E.g. 2024-01-01T00:00:00"
    )
    parser.add_argument(
        "--timeframe",
        default="1d",
        choices=["1h", "4h", "1d", "1wk", "1mo", "all"],
        help="Timeframe to train (choices: 1h, 4h, 1d, 1wk, 1mo, all)",
    )
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        parser.error("Either --symbol or --symbols must be provided")

    # Defaults: 5 years of data up to now
    end = parse_dt(args.end) if args.end else datetime.now()
    start = parse_dt(args.start) if args.start else end - timedelta(days=5 * 365)
    
    timeframes_to_run = []
    if args.timeframe == "all":
        timeframes_to_run = [
            Timeframe.ONE_HOUR,
            Timeframe.FOUR_HOUR,
            Timeframe.ONE_DAY,
            Timeframe.ONE_WEEK,
            Timeframe.ONE_MONTH,
        ]
    else:
        timeframes_to_run = [Timeframe(args.timeframe)]

    db = SessionLocal()
    try:
        registry = JsonlFileModelRegistry("model_store/registry.jsonl")
        store = ModelArtifactStore("model_store/artifacts")
        builder = DbFeatureBuilder(db=db)

        for symbol in symbols:
            print(f"\n========================================")
            print(f"TRAINING SYMBOL: {symbol}")
            print(f"========================================")
            
            for tf in timeframes_to_run:
                print(f"\n--- Training for Timeframe: {tf.value} ---")
                result = train_all_models_for_timeframe(
                    timeframe=tf,
                    registry=registry,
                    symbol=symbol,
                    start=start,
                    end=end,
                    feature_builder=builder,
                    artifact_store=store,
                )

                print(f"Symbol: {symbol}  Timeframe: {tf.value}")
                if not result.performances:
                    print("No performances produced (insufficient data?)")
                    continue

                for perf in result.performances:
                    print(
                        f"- {perf.model_kind.value}: sharpe={perf.sharpe_ratio:.3f}  acc={perf.accuracy:.3f}"
                    )

                latest = registry.get_latest_for_timeframe(tf, symbol=symbol)
                if latest:
                    print(
                        f"Winner: {latest.model_kind.value}  sharpe={latest.sharpe_ratio:.3f}  acc={latest.accuracy:.3f}"
                    )
                    if latest.artifact_path:
                        print(f"Artifact: {latest.artifact_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
