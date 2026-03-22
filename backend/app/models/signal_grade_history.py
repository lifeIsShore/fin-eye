"""
app/models/signal_grade_history.py  — Sprint 27

Logs every signal grade *change* per symbol so we can:
  - Render a 7-day grade sparkline on watchlist cards and the explore leaderboard
  - Detect grade degradation for rebalancing alerts (Phase 2D)
  - Power the AI allocation engine with time-series grade context

Design:
  - One row per (symbol, grade change event).
  - Records old_grade → new_grade transitions only (no-change events are not stored).
  - gas_score and component_scores at the time of the change are captured for context.
  - Indexed on (symbol, recorded_at) for fast time-range queries.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, JSON
from sqlalchemy.orm import Mapped

from app.db.database import Base


class SignalGradeHistory(Base):
    """One row = one grade change event for a symbol."""

    __tablename__ = "signal_grade_history"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = Column(String(20), nullable=False, index=True)

    # The new grade after this change
    grade: Mapped[str] = Column(String(10), nullable=False)

    # The grade that was active before this event (null for the very first record)
    prev_grade: Mapped[str] = Column(String(10), nullable=True)

    # Numeric grade score 0–100 at the time of the event
    grade_score: Mapped[int] = Column(Integer, nullable=True)

    # GAS composite score at the time
    gas_score: Mapped[float] = Column(Float, nullable=False)

    # Component breakdown snapshot {"technical": 70, "sentiment": 55, "macro": 48}
    component_scores: Mapped[dict] = Column(JSON, nullable=True)

    # Whether the grade is tradeable at this point
    tradeable: Mapped[bool] = Column(String(5), nullable=True)  # stored as "True"/"False" for SQLite compat

    # UTC timestamp of the grade change event
    recorded_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Composite index for fast per-symbol history queries
    __table_args__ = (
        Index("ix_grade_history_symbol_time", "symbol", "recorded_at"),
    )

    def to_dict(self) -> dict:
        return {
            "symbol":           self.symbol,
            "grade":            self.grade,
            "prev_grade":       self.prev_grade,
            "grade_score":      self.grade_score,
            "gas_score":        self.gas_score,
            "component_scores": self.component_scores,
            "tradeable":        self.tradeable,
            "recorded_at":      self.recorded_at.isoformat(),
        }
