from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Date, UniqueConstraint
from app.db.database import Base

class StockOHLCV(Base):
    """Legacy table — consolidated OHLCV."""
    __tablename__ = "stock_ohlcv"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='_symbol_timestamp_uc'),
    )

class OHLCVDaily(Base):
    """Daily OHLCV bars (CORE-DATA-01)."""
    __tablename__ = "ohlcv_daily"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    data_source = Column(String, nullable=False, server_default="yahoo_finance")

    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date', name='uq_ohlcv_symbol_date'),
    )

class OHLCVIntraday(Base):
    """Intraday OHLCV bars (1h, 4h) (CORE-DATA-01)."""
    __tablename__ = "ohlcv_intraday"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    interval = Column(String, nullable=False)  # '1h', '4h'
    bar_time = Column(DateTime(timezone=True), index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    data_source = Column(String, nullable=False, server_default="yahoo_finance")

    __table_args__ = (
        UniqueConstraint('symbol', 'interval', 'bar_time', name='uq_ohlcv_intraday'),
    )
