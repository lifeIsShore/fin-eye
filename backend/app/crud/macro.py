from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from datetime import date

from app.models.macro import MacroIndicator
from app.schemas.data_models import MacroData

def upsert_macro_data(db: Session, data: List[MacroData]) -> int:
    """
    Upsert macro data records. Returns the number of newly added records.
    (In a real production app we'd use dialact-specific insert on conflict do nothing,
    but checking existence is fine for MVP)
    """
    count = 0
    for item in data:
        # Check if exists
        stmt = select(MacroIndicator).where(
            MacroIndicator.indicator_name == item.indicator_name,
            MacroIndicator.date == item.date
        )
        existing = db.execute(stmt).scalar_one_or_none()
        
        if not existing:
            new_record = MacroIndicator(
                indicator_name=item.indicator_name,
                value=item.value,
                date=item.date
            )
            db.add(new_record)
            count += 1
            
    db.commit()
    return count

def get_latest_macro_indicator(db: Session, indicator_name: str) -> Optional[MacroIndicator]:
    """Get the most recent value for a specific macro indicator."""
    stmt = (
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()

def get_historical_macro_indicator(db: Session, indicator_name: str, limit: int = 30) -> List[MacroIndicator]:
    """Get historical values for a specific macro indicator."""
    stmt = (
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(limit)
    )
    results = db.execute(stmt).scalars().all()
    # Return chronologically
    return list(reversed(results))
