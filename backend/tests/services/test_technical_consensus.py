from app.services.technical_consensus import (
    TimeframeSignal,
    compute_consensus,
    consensus_to_score,
)
from app.services.technical_models import Timeframe


def test_consensus_to_score_bounds():
    assert consensus_to_score(-1.0) == 0.0
    assert consensus_to_score(0.0) == 50.0
    assert consensus_to_score(1.0) == 100.0


def test_compute_consensus_weighted():
    signals = [
        TimeframeSignal(
            timeframe=Timeframe.ONE_DAY,
            direction=1,
            confidence=1.0,
            sharpe_weight=1.5,
        ),
        TimeframeSignal(
            timeframe=Timeframe.ONE_WEEK,
            direction=-1,
            confidence=1.0,
            sharpe_weight=0.5,
        ),
    ]
    consensus = compute_consensus(signals)
    # Weighted toward the stronger sharpe signal -> bullish
    assert consensus.consensus > 0
    assert consensus.technical_confidence_score > 50

