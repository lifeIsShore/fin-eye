from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Protocol

from app.services.technical_models import Timeframe, ModelKind, TimeframeWinner


@dataclass
class ModelRecord:
    """Metadata for a trained model winner."""

    timeframe: Timeframe
    model_kind: ModelKind
    sharpe_ratio: float
    accuracy: float
    trained_at: datetime
    notes: str = ""


class ModelRegistry(Protocol):
    """Abstract interface for persisting model metadata."""

    def save_winner(self, record: ModelRecord) -> None:
        ...

    def list_winners(self) -> List[ModelRecord]:
        ...

    def get_latest_for_timeframe(self, timeframe: Timeframe) -> Optional[ModelRecord]:
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

    def get_latest_for_timeframe(self, timeframe: Timeframe) -> Optional[ModelRecord]:
        for record in reversed(self._records):
            if record.timeframe == timeframe:
                return record
        return None


def record_winners(
    registry: ModelRegistry,
    winners: List[TimeframeWinner],
    trained_at: Optional[datetime] = None,
    notes: str = "",
) -> None:
    """
    Convenience helper to convert TimeframeWinner objects into ModelRecord
    entries in the registry.
    """
    when = trained_at or datetime.utcnow()
    for winner in winners:
        registry.save_winner(
            ModelRecord(
                timeframe=winner.timeframe,
                model_kind=winner.model_kind,
                sharpe_ratio=winner.sharpe_ratio,
                accuracy=winner.accuracy,
                trained_at=when,
                notes=notes,
            )
        )

