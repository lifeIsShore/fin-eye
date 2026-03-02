from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from app.db.database import Base

class StockOHLCV(Base):
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
