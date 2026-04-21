"""
app/models/bot.py
─────────────────────────────────────────────────────────────────────────────
Sprint 47 — Paper Trading Bot tables

Three tables:
  bot_configs    — one row per user, their bot settings + kill switch
  bot_positions  — open and closed paper positions
  bot_audit_log  — immutable log of every decision the bot made
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base


class BotConfig(Base):
    __tablename__ = "bot_configs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    is_enabled       = Column(Boolean, default=False, nullable=False)
    mode             = Column(String(10), default="paper", nullable=False)   # 'paper' | 'live' (live locked)
    strategy         = Column(String(20), default="balanced", nullable=False) # 'aggressive'|'balanced'|'conservative'
    min_grade        = Column(String(3), default="B", nullable=False)         # minimum grade to trade
    max_position_pct = Column(Float, default=0.20, nullable=False)            # max % per symbol
    max_total_pct    = Column(Float, default=0.80, nullable=False)            # max % total deployed
    max_sector_pct   = Column(Float, default=0.40, nullable=False)            # max % in one sector
    daily_loss_limit = Column(Float, default=0.03, nullable=False)            # pause if daily PnL < -3%
    verbose_logging  = Column(Boolean, default=False, nullable=False)         # log SKIP/HOLD actions (noisy)
    portfolio_value  = Column(Float, default=10000.0, nullable=False)         # starting paper value
    halt_flag        = Column(Boolean, default=False, nullable=False)         # kill switch

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class BotPosition(Base):
    __tablename__ = "bot_positions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol        = Column(String(20), nullable=False, index=True)
    entry_price   = Column(Float, nullable=False)
    entry_grade   = Column(String(3), nullable=False)
    entry_gas     = Column(Float, nullable=False)
    size_units    = Column(Float, nullable=False)
    size_usd      = Column(Float, nullable=False)
    position_pct  = Column(Float, nullable=False)
    opened_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at     = Column(DateTime(timezone=True), nullable=True)
    close_price   = Column(Float, nullable=True)
    close_reason  = Column(String(50), nullable=True)   # 'grade_drop'|'stop_loss'|'manual'|'daily_limit'
    pnl_usd       = Column(Float, nullable=True)
    pnl_pct       = Column(Float, nullable=True)
    is_open       = Column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        # One open position per symbol per user
        Index("idx_bot_pos_user_symbol_open", "user_id", "symbol", "is_open"),
    )


class BotAuditLog(Base):
    __tablename__ = "bot_audit_log"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    logged_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    symbol      = Column(String(20), nullable=True)
    action      = Column(String(20), nullable=False)   # EVALUATE|BUY|SELL|HOLD|SKIP|HALT|RESUME
    grade       = Column(String(3), nullable=True)
    gas_score   = Column(Float, nullable=True)
    confidence  = Column(Float, nullable=True)
    price       = Column(Float, nullable=True)
    size_usd    = Column(Float, nullable=True)
    reason      = Column(Text, nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey("bot_positions.id"), nullable=True)
    regime      = Column(String(30), nullable=True)
    macro_score = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_bot_log_user_time", "user_id", "logged_at"),
        Index("idx_bot_log_symbol",    "symbol",  "logged_at"),
    )
