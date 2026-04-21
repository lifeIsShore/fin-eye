"""
app/models/gas_snapshot.py
─────────────────────────────────────────────────────────────────────────────
Persists pre-computed GAS (Global Alignment Score) results so the dashboard
can serve cached data instantly without triggering live ML inference.

Design:
  - One row per (symbol, computed_at).
  - Unique constraint on symbol keeps only the latest snapshot per symbol when
    using upsert — the table stays small and bounded.
  - `component_scores` stores the three sub-scores as a JSON column so the
    frontend can show the breakdown without extra round-trips.
  - `ttl_seconds` is advisory metadata — the actual cache expiry is enforced
    in Redis; the DB row is the durable fallback.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, JSON, Boolean
from sqlalchemy.orm import Mapped

from app.db.database import Base


class GasSnapshot(Base):
    """
    A point-in-time GAS snapshot for a single symbol.
    """

    __tablename__ = "gas_snapshots"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)

    # ── Core fields ────────────────────────────────────────────────────────
    symbol: Mapped[str] = Column(String(20), nullable=False, index=True)

    # 0–100 composite score
    gas_score: Mapped[float] = Column(Float, nullable=False)

    # "Mild Support" | "Mixed Signals" | "Headwind" | "High Instability"
    weather_label: Mapped[str] = Column(String(40), nullable=False)

    # "Risk-On" | "Transitional" | "Risk-Off"
    regime: Mapped[str] = Column(String(30), nullable=False)

    # Three sub-scores as a flat dict:
    # {"technical": 68.5, "sentiment": 52.0, "macro": 44.0}
    component_scores: Mapped[dict] = Column(JSON, nullable=False, default=dict)

    # Full signal breakdown for the technical layer (timeframe signals list)
    technical_signals: Mapped[list] = Column(JSON, nullable=True)

    # ISO-8601 timestamp of when this snapshot was computed
    computed_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Source of data: "live" (fresh inference) | "cache" (served from Redis)
    source: Mapped[str] = Column(String(10), nullable=False, default="live")

    # ── Signal Grade (Phase 2D) ────────────────────────────────────────────
    # Letter grade: "A+" | "A" | "B" | "C" | "D" | "F"
    signal_grade: Mapped[str] = Column(String(10), nullable=True)

    # 0–100 quality score for the decision
    signal_grade_score: Mapped[int] = Column(Integer, nullable=True)

    # Boolean flag for trade execution
    signal_tradeable: Mapped[bool] = Column(Boolean, nullable=True)

    # Human-readable summary
    signal_grade_desc: Mapped[str] = Column(String(255), nullable=True)

    # List of reasons [ "GAS 82 — strong tailwind", ... ]
    signal_grade_reasons: Mapped[list] = Column(JSON, nullable=True)

    # Sector for the symbol (e.g. "Technology", "Healthcare") — used by bot sector gate
    sector: Mapped[str] = Column(String(60), nullable=True)

    # ── Composite index: fast lookup by symbol, most recent first ──────────
    __table_args__ = (
        Index("ix_gas_snapshots_symbol_computed", "symbol", "computed_at"),
    )

    def to_dict(self) -> dict:
        return {
            "symbol":           self.symbol,
            "gas_score":        self.gas_score,
            "weather_label":    self.weather_label,
            "regime":           self.regime,
            "component_scores": self.component_scores,
            "technical_signals": self.technical_signals,
            "computed_at":      self.computed_at.isoformat(),
            "source":           self.source,
            "signal_grade":     self.signal_grade,
            "signal_grade_score": self.signal_grade_score,
            "signal_tradeable":   self.signal_tradeable,
            "signal_grade_desc":  self.signal_grade_desc,
            "signal_grade_reasons": self.signal_grade_reasons,
            "sector":           self.sector,
        }

    def __repr__(self) -> str:
        return (
            f"<GasSnapshot symbol={self.symbol!r} "
            f"gas={self.gas_score} regime={self.regime!r} "
            f"at={self.computed_at.isoformat()}>"
        )
