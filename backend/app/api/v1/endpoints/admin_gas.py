"""
app/api/v1/endpoints/admin_gas.py
─────────────────────────────────────────────────────────────────────────────
Admin endpoints for EXP-PERF-01 GAS pre-computation.

Routes (all admin-only except /snapshots/{symbol}, /history/{symbol}, /snapshots/batch):
  POST /api/v1/admin/gas/precompute          — trigger a full batch now
  POST /api/v1/admin/gas/precompute/{symbol} — trigger for one symbol
  GET  /api/v1/admin/gas/snapshots           — list latest snapshot per symbol
  GET  /api/v1/admin/gas/snapshots/{symbol}  — get latest snapshot for one symbol
  POST /api/v1/admin/gas/snapshots/batch     — batch lookup (What Changed Today)
  GET  /api/v1/admin/gas/history/{symbol}    — last N snapshots (sparkline data)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import Response as FastAPIResponse
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

# Prevents concurrent full-batch runs from stacking up
_batch_running = False


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
    global _batch_running
    if _batch_running:
        return {
            "status": "already_running",
            "message": "A batch precompute is already in progress. Wait for it to finish.",
            "symbols": DEFAULT_SYMBOLS,
        }

    async def _run() -> None:
        global _batch_running
        _batch_running = True
        try:
            from app.db.database import AsyncSessionLocal  # noqa: PLC0415
            async with AsyncSessionLocal() as session:
                await run_gas_precompute_batch(session)
        except Exception as exc:
            logger.error("Background GAS precompute failed: %s", exc)
        finally:
            _batch_running = False

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


@router.post(
    "/snapshots/batch",
    summary="Get latest GAS snapshot for multiple symbols at once (public)",
)
async def get_snapshots_batch(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Accepts { "symbols": ["AAPL", "TSLA", ...] } (max 30).
    Returns the most-recent GAS snapshot for each symbol that has one.
    Also returns the previous snapshot score so the frontend can show
    delta arrows (↑ / ↓ / →).

    Used by the 'What Changed Today' widget and Watchlist Overview page.
    Public endpoint — no admin auth required.
    """
    from app.services.gas_precompute import get_snapshot_cached  # noqa: PLC0415

    symbols_raw = body.get("symbols", [])
    if not isinstance(symbols_raw, list):
        return []
    symbols = [str(s).upper() for s in symbols_raw[:30]]

    results: List[Dict[str, Any]] = []
    for sym in symbols:
        try:
            snap_data = await get_snapshot_cached(sym, db)
            if snap_data is None:
                continue

            # Normalise — get_snapshot_cached can return a dict or a GasSnapshot
            if isinstance(snap_data, dict):
                gas_score    = snap_data.get("gas_score", 50)
                weather      = snap_data.get("weather_label", "")
                regime       = snap_data.get("regime", "")
                comp_scores  = snap_data.get("component_scores", {})
                computed_at  = snap_data.get("computed_at", "")
            else:
                gas_score    = snap_data.gas_score
                weather      = snap_data.weather_label
                regime       = snap_data.regime
                comp_scores  = snap_data.component_scores
                computed_at  = snap_data.computed_at.isoformat()

            # Fetch the previous snapshot for delta computation
            prev_result = await db.execute(
                select(GasSnapshot)
                .where(GasSnapshot.symbol == sym)
                .order_by(GasSnapshot.computed_at.desc())
                .offset(1)
                .limit(1)
            )
            prev = prev_result.scalar_one_or_none()

            # Grade fields — present in both dict and ORM paths
            if isinstance(snap_data, dict):
                sig_grade     = snap_data.get("signal_grade")
                sig_grade_sc  = snap_data.get("signal_grade_score")
                sig_tradeable = snap_data.get("signal_tradeable")
            else:
                sig_grade     = getattr(snap_data, "signal_grade", None)
                sig_grade_sc  = getattr(snap_data, "signal_grade_score", None)
                sig_tradeable = getattr(snap_data, "signal_tradeable", None)

            results.append({
                "symbol":             sym,
                "gas_score":          round(gas_score, 1),
                "weather_label":      weather,
                "regime":             regime,
                "component_scores":   comp_scores,
                "computed_at":        computed_at,
                "prev_gas_score":     round(prev.gas_score, 1) if prev else None,
                "delta":              round(gas_score - prev.gas_score, 1) if prev else None,
                # Sprint 27 — grade fields for watchlist sidebar + overview cards
                "signal_grade":       sig_grade,
                "signal_grade_score": sig_grade_sc,
                "signal_tradeable":   sig_tradeable,
            })
        except Exception as exc:
            logger.debug("Batch snapshot failed for %s: %s", sym, exc)
            continue

    return results


@router.get(
    "/snapshots/{symbol}",
    summary="Get latest GAS snapshot for a single symbol (public read path)",
)
async def get_snapshot(
    symbol: str,
    response: FastAPIResponse,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Sprint 29 — GAS snapshots are recomputed every 15 min; short cache is fine
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
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
    "/grade-history/{symbol}",
    summary="Sprint 27 — Grade change history for a symbol (last N events)",
)
async def get_grade_history(
    symbol: str,
    limit: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns the last `limit` grade change events for a symbol ordered
    oldest-first.  Used by the grade sparkline on watchlist cards and
    the explore leaderboard, and by the rebalancing alert engine.
    """
    from app.models.signal_grade_history import SignalGradeHistory  # noqa: PLC0415

    sym = symbol.upper()
    result = await db.execute(
        select(SignalGradeHistory)
        .where(SignalGradeHistory.symbol == sym)
        .order_by(SignalGradeHistory.recorded_at.desc())
        .limit(limit)
    )
    rows = list(reversed(result.scalars().all()))
    return [r.to_dict() for r in rows]


@router.get(
    "/history/{symbol}",
    summary="Get last N GAS snapshots for a symbol (sparkline / trend data)",
)
async def get_gas_history(
    symbol: str,
    limit: int = Query(default=7, ge=1, le=90, description="Number of snapshots to return"),
    response: FastAPIResponse = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    # Sprint 29 — sparkline data; 5-min cache is safe
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    """
    Returns the last `limit` GAS snapshots for a symbol ordered oldest-first,
    so the frontend can render a sparkline showing the 7-day GAS trend.

    Public endpoint — no auth required.
    Default: last 7 snapshots. Max: 90.
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

    rows_asc = list(reversed(rows))
    return [
        {
            "computed_at":      row.computed_at.isoformat(),
            "gas_score":        round(row.gas_score, 1),
            "weather_label":    row.weather_label,
            "regime":           row.regime,
            "component_scores": row.component_scores,
        }
        for row in rows_asc
    ]
