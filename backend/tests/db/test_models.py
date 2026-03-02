import pytest
from datetime import datetime, date, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.database import Base
from app.models.market import StockOHLCV
from app.models.macro import MacroIndicator

# Use an in-memory SQLite database for testing models
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_create_stock_ohlcv(db_session):
    record = StockOHLCV(
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        open=150.0,
        high=155.0,
        low=149.0,
        close=154.0,
        volume=1000000
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    assert record.id is not None
    assert record.symbol == "AAPL"

def test_unique_constraint_stock_ohlcv(db_session):
    test_time = datetime.now(timezone.utc)
    record1 = StockOHLCV(
        symbol="TSLA",
        timestamp=test_time,
        open=100.0, high=110.0, low=90.0, close=105.0, volume=500000
    )
    db_session.add(record1)
    db_session.commit()

    record2 = StockOHLCV(
        symbol="TSLA",
        timestamp=test_time,
        open=101.0, high=111.0, low=91.0, close=106.0, volume=500000
    )
    db_session.add(record2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_create_macro_indicator(db_session):
    record = MacroIndicator(
        indicator_name="fed_funds_rate",
        value=5.25,
        date=date(2023, 10, 1)
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    
    assert record.id is not None
    assert record.indicator_name == "fed_funds_rate"
    assert record.value == 5.25
