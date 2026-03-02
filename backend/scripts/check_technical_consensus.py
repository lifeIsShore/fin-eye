from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so `import app` works when running as a script.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.database import SessionLocal
from app.services.feature_builder import DbFeatureBuilder
from app.services.model_artifacts import ModelArtifactStore
from app.services.model_registry import JsonlFileModelRegistry
from app.services.technical_consensus import build_consensus_for_symbol
from app.services.technical_models import Timeframe


def main() -> None:
    parser = argparse.ArgumentParser(description="Check MVP-TECH-02 consensus output")
    parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    args = parser.parse_args()

    symbol = args.symbol.upper()

    registry = JsonlFileModelRegistry(f"{settings.model_store_dir}/registry.jsonl")
    store = ModelArtifactStore(f"{settings.model_store_dir}/artifacts")

    db = SessionLocal()
    try:
        builder = DbFeatureBuilder(db=db)
        consensus = build_consensus_for_symbol(
            symbol=symbol,
            registry=registry,
            artifact_store=store,
            feature_builder=builder,
            timeframes=[
                Timeframe.ONE_DAY,
                Timeframe.ONE_WEEK,
            ],
            end=datetime.now(timezone.utc),
        )

        print(f"Symbol: {symbol}")
        print(f"Consensus: {consensus.consensus}")
        print(f"Score: {consensus.technical_confidence_score} ({consensus.summary})")
        print("Signals:")
        for s in consensus.signals:
            print(
                f"- {s.timeframe.value}: dir={s.direction} conf={s.confidence:.3f} sharpe={s.sharpe_weight:.3f}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()

