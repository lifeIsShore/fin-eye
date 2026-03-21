"""
New models for todos-v4.md implementation:
  - TickerUniverse  — the 1000-ticker predefined list
  - BulkJobRun      — tracks every seed/train/news job result
"""

from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Text, Index, UniqueConstraint,
)
from sqlalchemy.sql import func
from app.db.database import Base


class TickerUniverse(Base):
    """
    Predefined universe of tickers used by all bulk seed/train operations.
    Populated by scripts/seed_ticker_universe.py from data/tickers_predefined.json.
    """
    __tablename__ = "tickers_universe"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(20), nullable=False, index=True)
    name        = Column(String(200), nullable=True)
    asset_class = Column(String(20), nullable=True)   # 'stock','etf','crypto','commodity','forex'
    tr_rank     = Column(Integer, nullable=True)       # popularity rank on Trade Republic DE
    exchange    = Column(String(20), nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    # NULL = not yet validated; True = yfinance resolves OK; False = invalid
    yf_valid    = Column(Boolean, nullable=True)
    added_at    = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Explicit name used by seed_ticker_universe.py on_conflict_do_update()
        # and admin_bulk.py upserts. Must match exactly.
        UniqueConstraint("symbol", name="uq_ticker_universe_symbol"),
    )


class BulkJobRun(Base):
    """
    Tracks the result of every bulk seed/train/news operation per ticker.
    Used by the Settings pipeline panel to show progress and failure lists.
    """
    __tablename__ = "bulk_job_runs"

    id           = Column(Integer, primary_key=True, index=True)
    # 'seed', 'train', 'news'
    job_type     = Column(String(20), nullable=False)
    # 'bulk' (triggered by Settings) or 'single' (triggered by ticker page)
    scope        = Column(String(20), nullable=False)
    symbol       = Column(String(20), nullable=True, index=True)
    # 'queued', 'running', 'done', 'failed', 'skipped'
    status       = Column(String(20), nullable=False)
    # e.g. 'insufficient_data (87 rows)', 'yfinance timeout', etc.
    reason       = Column(Text, nullable=True)
    rows_added   = Column(Integer, nullable=False, default=0)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_bulk_job_symbol",  "symbol"),
        Index("idx_bulk_job_status",  "status"),
        Index("idx_bulk_job_type_ts", "job_type", "created_at"),
    )
