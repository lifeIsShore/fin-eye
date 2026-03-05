"""
app/models/strategy.py
Saved strategy model for P2-STRAT-01 — Strategy Library.

A saved strategy is a named snapshot of a BacktestRequest + its
key result metrics. Users can reload it into the backtester at any
time, and optionally mark it public so others can browse it.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func

from app.db.database import Base


class SavedStrategy(Base):
    __tablename__ = "saved_strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)

    # The full BacktestRequest as JSON (symbol, strategy, params, dates, capital, slippage)
    request_snapshot = Column(JSON, nullable=False)

    # Key result metrics snapshot (null if strategy hasn't been run yet)
    total_return_pct = Column(Float, nullable=True)
    annualized_return_pct = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    win_rate_pct = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)

    # Visibility
    is_public = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    owner = relationship("User")
