from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Protocol

import json

from app.services.technical_models import Timeframe, ModelKind, TimeframeWinner


@dataclass
class ModelRecord:
    """Metadata for a trained model winner."""

    symbol: str
    timeframe: Timeframe
    model_kind: ModelKind
    sharpe_ratio: float
    accuracy: float
    trained_at: datetime
    notes: str = ""
    artifact_path: Optional[str] = None


class ModelRegistry(Protocol):
    """Abstract interface for persisting model metadata."""

    def save_winner(self, record: ModelRecord) -> None:
        ...

    def list_winners(self) -> List[ModelRecord]:
        ...

    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]:
        ...


class InMemoryModelRegistry:
    """
    Simple in-memory implementation of ModelRegistry.

    This is suitable for development and tests. A future session can
    introduce a database-backed implementation without changing the
    public interface.
    """

    def __init__(self) -> None:
        self._records: List[ModelRecord] = []

    def save_winner(self, record: ModelRecord) -> None:
        self._records.append(record)

    def list_winners(self) -> List[ModelRecord]:
        # Return a copy to avoid external mutation
        return list(self._records)

    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]:
        for record in reversed(self._records):
            if record.timeframe != timeframe:
                continue
            if symbol is not None and record.symbol != symbol:
                continue
                return record
        return None


class JsonlFileModelRegistry:
    """
    File-backed registry storing ModelRecord entries in JSONL format.

    This is the smallest persistence layer: append-only writes and full reads
    when listing. A future DB-backed registry can reuse the same interface.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def save_winner(self, record: ModelRecord) -> None:
        payload = {
            "symbol": record.symbol,
            "timeframe": record.timeframe.value,
            "model_kind": record.model_kind.value,
            "sharpe_ratio": record.sharpe_ratio,
            "accuracy": record.accuracy,
            "trained_at": record.trained_at.isoformat(),
            "notes": record.notes,
            "artifact_path": record.artifact_path,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def list_winners(self) -> List[ModelRecord]:
        records: List[ModelRecord] = []
        if not self.path.exists():
            return records
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(
                ModelRecord(
                    symbol=payload["symbol"],
                    timeframe=Timeframe(payload["timeframe"]),
                    model_kind=ModelKind(payload["model_kind"]),
                    sharpe_ratio=float(payload["sharpe_ratio"]),
                    accuracy=float(payload["accuracy"]),
                    trained_at=datetime.fromisoformat(payload["trained_at"]),
                    notes=str(payload.get("notes", "")),
                    artifact_path=payload.get("artifact_path"),
                )
            )
        return records

    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]:
        records = self.list_winners()
        for record in reversed(records):
            if record.timeframe != timeframe:
                continue
            if symbol is not None and record.symbol != symbol:
                continue
            return record
        return None


def record_winners(
    registry: ModelRegistry,
    winners: List[TimeframeWinner],
    symbol: str,
    trained_at: Optional[datetime] = None,
    notes: str = "",
    artifact_path: Optional[str] = None,
) -> None:
    """
    Convenience helper to convert TimeframeWinner objects into ModelRecord
    entries in the registry.
    """
    when = trained_at or datetime.utcnow()
    for winner in winners:
        registry.save_winner(
            ModelRecord(
                symbol=symbol,
                timeframe=winner.timeframe,
                model_kind=winner.model_kind,
                sharpe_ratio=winner.sharpe_ratio,
                accuracy=winner.accuracy,
                trained_at=when,
                notes=notes,
                artifact_path=artifact_path,
            )
        )

