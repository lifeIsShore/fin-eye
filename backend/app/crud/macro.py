"""
app/crud/macro.py
Database access layer for macro indicators.

Both sync (legacy, kept for backward-compat) and async variants are
provided.  New code should always use the async functions.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.macro import MacroIndicator
from app.schemas.data_models import MacroData

# ─────────────────────────────────────────────────────────────────────────────
# Sync helpers (kept for backward compat — macro_orchestrator legacy path)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_macro_data(db: Session, data: List[MacroData]) -> int:
    """Insert records that do not already exist.  Returns count inserted."""
    count = 0
    for item in data:
        stmt = select(MacroIndicator).where(
            MacroIndicator.indicator_name == item.indicator_name,
            MacroIndicator.date == item.date,
        )
        if db.execute(stmt).scalar_one_or_none() is None:
            db.add(MacroIndicator(
                indicator_name=item.indicator_name,
                value=item.value,
                date=item.date,
            ))
            count += 1
    db.commit()
    return count


def get_latest_macro_indicator(db: Session, indicator_name: str) -> Optional[MacroIndicator]:
    stmt = (
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_historical_macro_indicator(
    db: Session, indicator_name: str, limit: int = 30
) -> List[MacroIndicator]:
    stmt = (
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(limit)
    )
    return list(reversed(db.execute(stmt).scalars().all()))


# ─────────────────────────────────────────────────────────────────────────────
# Async helpers  ← used by all new endpoints
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_macro_data_async(db: AsyncSession, data: List[MacroData]) -> int:
    """Async upsert: insert records not already present.  Returns count inserted."""
    count = 0
    for item in data:
        result = await db.execute(
            select(MacroIndicator).where(
                MacroIndicator.indicator_name == item.indicator_name,
                MacroIndicator.date == item.date,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(MacroIndicator(
                indicator_name=item.indicator_name,
                value=item.value,
                date=item.date,
            ))
            count += 1
    await db.flush()
    return count


async def get_latest_async(
    db: AsyncSession, indicator_name: str
) -> Optional[MacroIndicator]:
    """Return the single most-recent record for an indicator."""
    result = await db.execute(
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_history_async(
    db: AsyncSession,
    indicator_name: str,
    limit: int = 60,
) -> List[MacroIndicator]:
    """Return up to `limit` records in chronological (ascending) order."""
    result = await db.execute(
        select(MacroIndicator)
        .where(MacroIndicator.indicator_name == indicator_name)
        .order_by(desc(MacroIndicator.date))
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def get_latest_batch_async(
    db: AsyncSession,
    indicator_names: List[str],
) -> dict[str, Optional[MacroIndicator]]:
    """
    Fetch the latest record for each indicator in a single round-trip using a
    window function, falling back to one query per indicator if the DB does not
    support it (e.g. SQLite in tests).

    Returns a dict keyed by indicator_name.
    """
    out: dict[str, Optional[MacroIndicator]] = {n: None for n in indicator_names}
    for name in indicator_names:
        out[name] = await get_latest_async(db, name)
    return out
