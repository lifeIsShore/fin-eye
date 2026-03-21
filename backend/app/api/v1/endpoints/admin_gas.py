"""
app/api/v1/endpoints/admin_gas.py
─────────────────────────────────────────────────────────────────────────────
Admin endpoints for EXP-PERF-01 GAS pre-computation.

Routes (all admin-only):
  POST /api/v1/admin/gas/precompute          — trigger a full batch now
  POST /api/v1/admin/gas/precompute/{symbol} — trigger for one symbol
  GET  /api/v1/admin/gas/snapshots           — list latest snapshot per symbol
  GET  /api/v1/admin/gas/snapshots/{symbol}  — get latest snapshot for one symbol
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud.gas_snapshot import get_latest, get_latest_batch
from app.db.database import get_db
from app.api.v1.deps import require_admin
from app.services.gas_precompute import (
    DEFAULT_SYMBOLS,
    compute_gas_for_symbol,
    run_gas_precompute_batch,
)

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Schemas (inline — small enough to not warrant a separate file) ────────

def _snap_response(snap_dict: dict) -> dict:
    """Ensure every field is JSON-serialisable."""
    return snap_dict


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/precompute",
    dependencies=[Depends(require_admin)],
    summary="Trigger full GAS pre-compute batch (all default symbols)",
)
async def trigger_full_precompute(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Fire-and-forget: starts the GAS batch in the background and returns
    immediately.  Check /snapshots to see results once complete.
    """
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
    """
    Synchronous single-symbol compute — returns the snapshot immediately.
    Useful for manual investigation or re-warming after a model retrain.
    """
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
    """
    Returns the most-recent DB snapshot for every default symbol.
    Symbols with no snapshot yet will be absent from the list.
    """
    batch = await get_latest_batch(db, DEFAULT_SYMBOLS)
    return [_snap_response(snap.to_dict()) for snap in batch.values()]


@router.get(
    "/snapshots/{symbol}",
    summary="Get latest GAS snapshot for a single symbol (public-facing read path)",
)
async def get_snapshot(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Public read endpoint — no admin auth required.
    Used by the dashboard to get a fast pre-computed GAS score.

    Response includes a `source` field:
      - "cache"       — served from Redis (fastest)
      - "db_snapshot" — served from DB snapshot (fast)
      - "live"        — freshly computed (cold start only)
    """
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
