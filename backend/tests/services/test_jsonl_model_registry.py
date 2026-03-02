from datetime import datetime
from pathlib import Path

from app.services.model_registry import JsonlFileModelRegistry, ModelRecord
from app.services.technical_models import Timeframe, ModelKind


def test_jsonl_registry_round_trip(tmp_path: Path):
    path = tmp_path / "registry.jsonl"
    registry = JsonlFileModelRegistry(path)

    record = ModelRecord(
        symbol="AAPL",
        timeframe=Timeframe.ONE_DAY,
        model_kind=ModelKind.LOGISTIC,
        sharpe_ratio=0.5,
        accuracy=0.6,
        trained_at=datetime.utcnow(),
        notes="test",
        artifact_path="model_store/artifacts/AAPL/1d/logistic.joblib",
    )

    registry.save_winner(record)

    records = registry.list_winners()
    assert len(records) == 1
    assert records[0].symbol == "AAPL"

    latest = registry.get_latest_for_timeframe(Timeframe.ONE_DAY, symbol="AAPL")
    assert latest is not None
    assert latest.model_kind == ModelKind.LOGISTIC

