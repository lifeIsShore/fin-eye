"""
app/models/external_signal.py
Generic key-value store for external data signals (Sprint 40).

Captures values from:
  - CNN Fear & Greed Index
  - Crypto Fear & Greed Index
  - Google Trends search interest
  - Reddit sentiment/mentions
  - Wikipedia pageviews
  - (and any future external source added in Sprint 42+)

Each row = one signal reading for one source+symbol combination at a point in time.
"""
from sqlalchemy import (
    BigInteger, Column, Float, Index, JSON, String, DateTime, func,
)
from app.db.database import Base


class ExternalSignal(Base):
    __tablename__ = "external_signals"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    source      = Column(String(30),  nullable=False, index=True)   # e.g. "cnn_fear_greed"
    symbol      = Column(String(20),  nullable=True,  index=True)   # NULL for market-wide signals
    signal_name = Column(String(50),  nullable=False, index=True)   # e.g. "fear_greed_score"
    value       = Column(Float,       nullable=False)
    raw_json    = Column(JSON,        nullable=True)                 # full API response if useful
    fetched_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_ext_sig_symbol_name_time", "symbol", "signal_name", "fetched_at"),
        Index("idx_ext_sig_source_time",      "source",  "fetched_at"),
    )
