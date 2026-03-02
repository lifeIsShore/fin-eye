from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from app.db.database import Base

class MacroIndicator(Base):
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, index=True)
    indicator_name = Column(String, index=True, nullable=False) # e.g. 'fed_funds_rate', 'cpi'
    value = Column(Float, nullable=False)
    date = Column(Date, index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint('indicator_name', 'date', name='_indicator_date_uc'),
    )
