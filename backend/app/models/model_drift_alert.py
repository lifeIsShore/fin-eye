"""
app/models/model_drift_alert.py

Sprint 6 — todos-v5 Phase 5.5

Stores model drift alerts — detected when a symbol/timeframe's live accuracy
drops more than DRIFT_THRESHOLD_PP percentage points below its training accuracy
over a rolling 30-day window.

One row per symbol/timeframe per detection event.
Auto-retrain is flagged here; the scheduler picks it up.
"""

from sqlalchemy import (
    Column, BigInteger, Integer, String, Float, Boolean,
    DateTime, Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.db.database import Base

DRIFT_THRESHOLD_PP = 10.0   # alert if live_acc < val_acc - 10pp


class ModelDriftAlert(Base):
    __tablename__ = "model_drift_alerts"

    id = Column(BigInteger, primary_key=True, index=True)

    symbol    = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)

    # Accuracy figures at detection time
    val_accuracy_pct    = Column(Float, nullable=False)   # training/validation accuracy (%)
    live_accuracy_pct   = Column(Float, nullable=False)   # rolling 30-day live accuracy (%)
    delta_pp            = Column(Float, nullable=False)   # val - live (positive = degraded)
    n_live_predictions  = Column(Integer, nullable=False) # how many resolved predictions used

    # Response
    severity     = Column(String(10), nullable=False, default="warning")  # "warning" | "critical"
    auto_retrain = Column(Boolean, nullable=False, default=False)
    retrained_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged = Column(Boolean, nullable=False, default=False)
    ack_at       = Column(DateTime(timezone=True), nullable=True)

    detected_at  = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at  = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # No unique constraint — can have multiple alerts per symbol/tf over time
        Index("idx_drift_symbol_tf",   "symbol", "timeframe"),
        Index("idx_drift_unacked",     "acknowledged", "detected_at"),
        Index("idx_drift_severity",    "severity"),
    )
