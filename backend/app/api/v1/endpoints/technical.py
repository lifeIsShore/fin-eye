from typing import Any, Dict

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.services.model_registry import JsonlFileModelRegistry
from app.services.model_artifacts import ModelArtifactStore
from app.services.feature_builder import DbFeatureBuilder
from app.services.technical_models import Timeframe
from app.services.technical_consensus import build_consensus_for_symbol


router = APIRouter()


@router.get("/{symbol}/latest")
def get_latest_technical_consensus(
    symbol: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return the latest technical consensus and 0–100 technical confidence score
    for a symbol, based on the most recently trained winners per timeframe.

    Notes:
      - If only some timeframes have trained winners, this returns a partial consensus.
      - For now, feature engineering is only implemented for the 1d timeframe in DbFeatureBuilder.
    """
    symbol = symbol.upper()

    registry_path = f"{settings.model_store_dir}/registry.jsonl"
    artifacts_dir = f"{settings.model_store_dir}/artifacts"

    registry = JsonlFileModelRegistry(registry_path)
    store = ModelArtifactStore(artifacts_dir)
    builder = DbFeatureBuilder(db=db)

    consensus = build_consensus_for_symbol(
        symbol=symbol,
        registry=registry,
        artifact_store=store,
        feature_builder=builder,
        timeframes=[
            Timeframe.ONE_HOUR,
            Timeframe.FOUR_HOUR,
            Timeframe.ONE_DAY,
            Timeframe.ONE_WEEK,
            Timeframe.ONE_MONTH,
        ],
        end=datetime.now(timezone.utc),
    )

    return {
        "symbol": symbol,
        "consensus": consensus.consensus,
        "technical_confidence_score": consensus.technical_confidence_score,
        "summary": consensus.summary,
        "signals": [
            {
                "timeframe": s.timeframe.value,
                "direction": s.direction,
                "confidence": s.confidence,
                "sharpe_weight": s.sharpe_weight,
            }
            for s in consensus.signals
        ],
    }

