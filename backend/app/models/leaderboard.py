"""
app/models/leaderboard.py
Sprint 44 — ORM model for public_backtest_runs (community strategy leaderboard).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base


class PublicBacktestRun(Base):
    __tablename__ = "public_backtest_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    strategy_name    = Column(String(80),  nullable=False)
    symbol           = Column(String(20),  nullable=False, index=True)
    strategy         = Column(String(40),  nullable=False)
    start_date       = Column(String(10),  nullable=True)
    end_date         = Column(String(10),  nullable=True)

    sharpe_ratio     = Column(Float,   nullable=False)
    total_return_pct = Column(Float,   nullable=False)
    max_drawdown_pct = Column(Float,   nullable=False)
    total_trades     = Column(Integer, nullable=False)

    # Soft-delete: set to False when the weekly leaderboard resets
    is_active    = Column(Boolean, nullable=False, default=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
