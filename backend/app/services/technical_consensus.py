from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.model_registry import ModelRecord, ModelRegistry
from app.services.model_artifacts import ModelArtifactStore
from app.services.technical_models import Timeframe, ModelKind
from app.services.feature_builder import FeatureBuilder, DbFeatureBuilder


@dataclass
class TimeframeSignal:
    timeframe: Timeframe
    direction: int  # -1 = bearish/sell, 0 = neutral, +1 = bullish/buy
    confidence: float  # 0..1
    sharpe_weight: float


@dataclass
class TechnicalConsensus:
    consensus: float  # -1..+1
    technical_confidence_score: float  # 0..100
    summary: str
    signals: List[TimeframeSignal]


def consensus_to_score(consensus: float) -> float:
    """
    Map consensus in [-1, +1] to a 0–100 score.
    """
    c = max(-1.0, min(1.0, float(consensus)))
    return round(((c + 1.0) / 2.0) * 100.0, 1)


def score_summary(score: float) -> str:
    if score >= 70:
        return "Mostly bullish"
    if score <= 30:
        return "Mostly bearish"
    if 45 <= score <= 55:
        return "Neutral / mixed"
    return "Mixed"


def compute_consensus(signals: List[TimeframeSignal]) -> TechnicalConsensus:
    """
    Combine timeframe signals using Sharpe-based weights.

    We weight by (abs(sharpe) * confidence) so high-confidence signals from
    strong models contribute more. Consensus stays within [-1, +1].
    """
    if not signals:
        return TechnicalConsensus(
            consensus=0.0,
            technical_confidence_score=50.0,
            summary="No signals",
            signals=[],
        )

    weights = np.array(
        [max(0.0, abs(s.sharpe_weight)) * max(0.0, min(1.0, s.confidence)) for s in signals],
        dtype=float,
    )
    dirs = np.array([float(s.direction) for s in signals], dtype=float)

    if float(weights.sum()) == 0.0:
        consensus = float(np.mean(dirs))
    else:
        consensus = float(np.dot(dirs, weights) / weights.sum())

    consensus = max(-1.0, min(1.0, consensus))
    score = consensus_to_score(consensus)
    return TechnicalConsensus(
        consensus=round(consensus, 3),
        technical_confidence_score=score,
        summary=score_summary(score),
        signals=signals,
    )


def _predict_direction_and_confidence(
    model: any,
    model_kind: ModelKind,
    features_row: pd.DataFrame,
) -> Tuple[int, float]:
    """
    Predict direction {-1,0,1} and confidence 0..1 from a single-row feature frame.
    """
    # LogisticRegression supports predict_proba on original labels.
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features_row)[0]
        classes = getattr(model, "classes_", None)
        if classes is not None:
            # classes_ may be [-1,0,1] for logistic; for XGBoost we trained mapped labels.
            best_idx = int(np.argmax(proba))
            pred_class = int(classes[best_idx])
            conf = float(proba[best_idx])
            if model_kind == ModelKind.XGBOOST:
                # Map {0,1,2} back to {-1,0,1}
                pred_class = pred_class - 1
            return pred_class, conf

    # Fallback: use predict only, confidence unknown -> 1.0
    pred = int(model.predict(features_row)[0])
    if model_kind == ModelKind.XGBOOST:
        pred = pred - 1
    return pred, 1.0


def build_consensus_for_symbol(
    *,
    symbol: str,
    registry: ModelRegistry,
    artifact_store: ModelArtifactStore,
    feature_builder: FeatureBuilder,
    timeframes: List[Timeframe],
    end: datetime,
    lookback_days: int = 365 * 5,
) -> TechnicalConsensus:
    """
    High-level helper for MVP-TECH-02:
      - For each timeframe, load latest winner record for symbol
      - Load the model artifact
      - Build latest feature row
      - Predict direction + confidence
      - Combine signals into a technical confidence score

    Note: This will naturally produce partial consensus if only some timeframes
    have trained winners.
    """
    start = end - timedelta(days=lookback_days)

    signals: List[TimeframeSignal] = []
    for tf in timeframes:
        record = registry.get_latest_for_timeframe(tf, symbol=symbol)
        if record is None or not record.artifact_path:
            continue

        model = artifact_store.load(artifact_path=record.artifact_path, model_kind=record.model_kind)
        df = feature_builder.build_features(symbol=symbol, timeframe=tf, start=start, end=end)
        if df.empty:
            continue

        # Use the most recent feature row
        latest_row = df.tail(1).drop(columns=["symbol", "timestamp"], errors="ignore")
        direction, conf = _predict_direction_and_confidence(model, record.model_kind, latest_row)

        signals.append(
            TimeframeSignal(
                timeframe=tf,
                direction=direction,
                confidence=conf,
                sharpe_weight=record.sharpe_ratio,
            )
        )

    return compute_consensus(signals)

