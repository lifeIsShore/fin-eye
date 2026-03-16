"""app/models/portfolio.py"""
from datetime import datetime

from sqlalchemy import Column, Float, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), index=True, nullable=False)
    description = Column(String(512), nullable=True)

    # Extended metadata fields
    strategy_tag    = Column(String(32),  nullable=True)   # Growth | Income | Hedge | Speculative | Index | Crypto | Mixed
    risk_tolerance  = Column(String(16),  nullable=True)   # Conservative | Moderate | Aggressive
    base_currency   = Column(String(8),   nullable=True, default="USD")
    horizon         = Column(String(16),  nullable=True)   # Short | Medium | Long
    notes           = Column(Text,        nullable=True)   # freeform thesis/scratchpad
    target_return   = Column(Float,       nullable=True)   # annual % target e.g. 15.0
    benchmark       = Column(String(20),  nullable=True)   # e.g. SPY, QQQ, BTC-USD

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="portfolios")
    items = relationship("PortfolioItem", back_populates="portfolio", cascade="all, delete-orphan")
    positions = relationship("PortfolioPosition", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioItem(Base):
    """Lightweight watchlist-style portfolio entry (symbol + weight)."""
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    weight = Column(Float, nullable=False, default=0.0)
    added_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="items")


class PortfolioPosition(Base):
    """Full position entry with quantity, cost basis, and currency."""
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    average_cost = Column(Float, nullable=True)  # cost basis per unit
    currency = Column(String(10), nullable=False, default="USD")
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")
