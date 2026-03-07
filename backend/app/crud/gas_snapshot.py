"""
app/crud/gas_snapshot.py
─────────────────────────────────────────────────────────────────────────────
Database helpers for the gas_snapshots table.

All functions are async-first and accept an AsyncSession.

Design:
  - upsert_snapshot():  write a new snapshot row, then prune so we keep only
    the last MAX_ROWS_PER_SYMBOL rows per symbol (prevents unbounded growth).
  - get_latest():       return the most-recent snapshot for a symbol (or None).
  - get_latest_batch(): return the most-recent snapshot for a list of symbols
    in a single query — used by the dashboard multi-symbol endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gas_snapshot import GasSnapshot

logger = logging.getLogger(__name__)

# Keep the last N snapshots per symbol — prevents the table from growing
# unboundedly while still allowing us to show recent trend data if needed.
MAX_ROWS_PER_SYMBOL = 48  # ~12h of 15-min snapshots


async def upsert_snapshot(
    db: AsyncSession,
    *,
    symbol: str,
    gas_score: float,
    weather_label: str,
    regime: str,
    component_scores: dict,
    technical_signals: Optional[list] = None,
    source: str = "live",
) -> GasSnapshot:
    """
    Insert a new GasSnapshot row, then trim old rows for that symbol so we
    never exceed MAX_ROWS_PER_SYMBOL.

    Returns the newly created snapshot (not yet committed — caller must commit).
    """
    snap = GasSnapshot(
        symbol=symbol.upper(),
        gas_score=round(gas_score, 2),
        weather_label=weather_label,
        regime=regime,
        component_scores=component_scores,
        technical_signals=technical_signals,
        computed_at=datetime.now(timezone.utc),
        source=source,
    )
    db.add(snap)
    await db.flush()  # get the id so the trim query works correctly

    # ── Trim: delete oldest rows beyond the cap ────────────────────────────
    # Subquery: the id of the (MAX_ROWS_PER_SYMBOL)th most recent row
    subq = (
        select(GasSnapshot.id)
        .where(GasSnapshot.symbol == symbol.upper())
        .order_by(GasSnapshot.computed_at.desc())
        .offset(MAX_ROWS_PER_SYMBOL)
        .limit(1)
        .scalar_subquery()
    )
    # Delete all rows older than that cutoff id
    cutoff_stmt = select(GasSnapshot.id).where(
        GasSnapshot.symbol == symbol.upper(),
        GasSnapshot.computed_at
        < select(GasSnapshot.computed_at)
        .where(GasSnapshot.id == subq)
        .scalar_subquery(),
    )
    ids_to_delete = (await db.execute(cutoff_stmt)).scalars().all()
    if ids_to_delete:
        await db.execute(
            delete(GasSnapshot).where(GasSnapshot.id.in_(ids_to_delete))
        )
        logger.debug(
            "gas_snapshots: trimmed %d old rows for %s", len(ids_to_delete), symbol
        )

    return snap


async def get_latest(
    db: AsyncSession,
    symbol: str,
) -> Optional[GasSnapshot]:
    """Return the most-recent snapshot for a symbol, or None if none exist."""
    result = await db.execute(
        select(GasSnapshot)
        .where(GasSnapshot.symbol == symbol.upper())
        .order_by(GasSnapshot.computed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_batch(
    db: AsyncSession,
    symbols: list[str],
) -> dict[str, GasSnapshot]:
    """
    Return a mapping of symbol → latest GasSnapshot for each requested symbol.
    Symbols with no snapshot are omitted from the result.

    Uses a single efficient query with a window function to avoid N+1 selects.
    """
    if not symbols:
        return {}

    upper_symbols = [s.upper() for s in symbols]

    # CTE: rank rows per symbol by computed_at desc, pick rank = 1
    ranked = (
        select(
            GasSnapshot,
            func.row_number()
            .over(
                partition_by=GasSnapshot.symbol,
                order_by=GasSnapshot.computed_at.desc(),
            )
            .label("rn"),
        )
        .where(GasSnapshot.symbol.in_(upper_symbols))
        .subquery()
    )

    stmt = (
        select(GasSnapshot)
        .join(ranked, GasSnapshot.id == ranked.c.id)
        .where(ranked.c.rn == 1)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {row.symbol: row for row in rows}
