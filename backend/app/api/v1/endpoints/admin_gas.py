"""
app/api/v1/endpoints/admin_gas.py
─────────────────────────────────────────────────────────────────────────────
Admin endpoints for EXP-PERF-01 GAS pre-computation.

Routes (all admin-only except /snapshots/{symbol} and /history/{symbol}):
  POST /api/v1/admin/gas/precompute          — trigger a full batch now
  POST /api/v1/admin/gas/precompute/{symbol} — trigger for one symbol
  GET  /api/v1/admin/gas/snapshots           — list latest snapshot per symbol
  GET  /api/v1/admin/gas/snapshots/{symbol}  — get latest snapshot for one symbol
  GET  /api/v1/admin/gas/history/{symbol}    — last N snapshots (sparkline data)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud.gas_snapshot import get_latest, get_latest_batch
from app.db.database import get_db
from app.api.v1.deps import require_admin
from app.models.gas_snapshot import GasSnapshot
from app.services.gas_precompute import (
    DEFAULT_SYMBOLS,
    compute_gas_for_symbol,
    run_gas_precompute_batch,
)

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Schemas (inline) ────────────────────────────────────────────────────────

def _snap_response(snap_dict: dict) -> dict:
    return snap_dict


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/precompute",
    dependencies=[Depends(require_admin)],
    summary="Trigger full GAS pre-compute batch (all default symbols)",
)
async def trigger_full_precompute(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    async def _run() -> None:
        try:
            from app.db.database import AsyncSessionLocal  # noqa: PLC0415
            async with AsyncSessionLocal() as session:
                await run_gas_precompute_batch(session)
        except Exception as exc:
            logger.error("Background GAS precompute failed: %s", exc)

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": f"GAS precompute triggered for {len(DEFAULT_SYMBOLS)} symbols. "
                   "Check GET /snapshots for results.",
        "symbols": DEFAULT_SYMBOLS,
    }


@router.post(
    "/precompute/{symbol}",
    dependencies=[Depends(require_admin)],
    summary="Trigger GAS pre-compute for a single symbol",
)
async def trigger_symbol_precompute(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    sym = symbol.upper()
    try:
        snap = await compute_gas_for_symbol(sym, db)
        await db.commit()
        return {"status": "ok", "snapshot": _snap_response(snap)}
    except Exception as exc:
        logger.error("Single-symbol precompute failed for %s: %s", sym, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Precompute failed for {sym}: {exc}",
        ) from exc


@router.get(
    "/snapshots",
    dependencies=[Depends(require_admin)],
    summary="List latest GAS snapshot for all default symbols",
)
async def list_snapshots(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    batch = await get_latest_batch(db, DEFAULT_SYMBOLS)
    return [_snap_response(snap.to_dict()) for snap in batch.values()]


@router.get(
    "/snapshots/{symbol}",
    summary="Get latest GAS snapshot for a single symbol (public read path)",
)
async def get_snapshot(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.gas_precompute import get_snapshot_cached  # noqa: PLC0415

    sym = symbol.upper()
    snap = await get_snapshot_cached(sym, db)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No GAS snapshot available for {sym}. "
                   "Ensure models are trained and the pre-compute job has run.",
        )
    return _snap_response(snap)


@router.get(
    "/history/{symbol}",
    summary="Get last N GAS snapshots for a symbol (sparkline / trend data)",
)
async def get_gas_history(
    symbol: str,
    limit: int = Query(default=7, ge=1, le=90, description="Number of snapshots to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns the last `limit` GAS snapshots for a symbol ordered oldest-first,
    so the frontend can render a sparkline showing the 7-day GAS trend.

    Public endpoint — no auth required (data is already shown on dashboard).
    Default: last 7 snapshots (one per daily compute run = 7-day sparkline).
    Max: 90 (for longer trend charts).
    """
    sym = symbol.upper()
    result = await db.execute(
        select(GasSnapshot)
        .where(GasSnapshot.symbol == sym)
        .order_by(GasSnapshot.computed_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    if not rows:
        return []

    # Return oldest-first so frontend can render left→right chronologically
    rows_asc = list(reversed(rows))
    return [
        {
            "computed_at": row.computed_at.isoformat(),
            "gas_score":   round(row.gas_score, 1),
            "weather_label": row.weather_label,
            "regime":        row.regime,
            "component_scores": row.component_scores,
        }
        for row in rows_asc
    ]
