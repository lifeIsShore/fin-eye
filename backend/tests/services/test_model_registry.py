from datetime import datetime, timedelta

from app.services.technical_models import Timeframe, ModelKind, TimeframeWinner
from app.services.model_registry import (
    ModelRecord,
    InMemoryModelRegistry,
    record_winners,
)


def test_in_memory_model_registry_basic():
    registry = InMemoryModelRegistry()

    now = datetime.utcnow()
    record = ModelRecord(
        symbol="AAPL",
        timeframe=Timeframe.ONE_DAY,
        model_kind=ModelKind.XGBOOST,
        sharpe_ratio=1.2,
        accuracy=0.65,
        trained_at=now,
        notes="initial test run",
    )

    registry.save_winner(record)

    all_records = registry.list_winners()
    assert len(all_records) == 1
    assert all_records[0].model_kind == ModelKind.XGBOOST

    latest = registry.get_latest_for_timeframe(Timeframe.ONE_DAY)
    assert latest is not None
    assert latest.sharpe_ratio == 1.2


def test_record_winners_helper():
    registry = InMemoryModelRegistry()
    winners = [
        TimeframeWinner(
            timeframe=Timeframe.ONE_DAY,
            model_kind=ModelKind.LOGISTIC,
            sharpe_ratio=0.8,
            accuracy=0.6,
        ),
        TimeframeWinner(
            timeframe=Timeframe.ONE_WEEK,
            model_kind=ModelKind.XGBOOST,
            sharpe_ratio=1.1,
            accuracy=0.62,
        ),
    ]

    when = datetime.utcnow() - timedelta(days=1)
    record_winners(registry, winners, symbol="AAPL", trained_at=when, notes="walk-forward v1")

    all_records = registry.list_winners()
    assert len(all_records) == 2
    assert {r.timeframe for r in all_records} == {
        Timeframe.ONE_DAY,
        Timeframe.ONE_WEEK,
    }
    assert all(r.trained_at == when for r in all_records)
    assert all(r.notes == "walk-forward v1" for r in all_records)
    assert all(r.symbol == "AAPL" for r in all_records)

