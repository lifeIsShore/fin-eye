"""
app/api/v1/endpoints/sectors.py
─────────────────────────────────────────────────────────────────────────────
EXP-SECT-01 — Sector Rotation Heatmap endpoints

Routes:
  GET /sectors/rotation      — full rotation data (all sectors + cycle analysis)
  GET /sectors/heatmap       — lightweight heatmap-only payload (returns grid)
  GET /sectors/rrg           — RRG scatter data (RS + momentum per sector)

No auth required. All CPU-bound work offloaded to thread pool.
Results cached 15 min in-process inside sector_service.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.sector_service import SectorRotationData, SectorData, fetch_sector_rotation

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response schemas ─────────────────────────────────────────────────────────

class SectorDto(BaseModel):
    ticker: str
    name: str
    cycle_phase: str
    return_1w: Optional[float]
    return_1m: Optional[float]
    return_3m: Optional[float]
    rs_1w: Optional[float]
    rs_1m: Optional[float]
    rs_3m: Optional[float]
    rs_score: float          # 0–100 normalised; 50 = SPY parity
    momentum: Optional[float]
    rrg_quadrant: str        # Leading | Weakening | Lagging | Improving
    last_price: Optional[float]


class SectorRotationDto(BaseModel):
    sectors: List[SectorDto]
    spy_return_1w: Optional[float]
    spy_return_1m: Optional[float]
    spy_return_3m: Optional[float]
    dominant_cycle_phase: str
    dominant_cycle_description: str
    cycle_phase_scores: Dict[str, float]
    disclaimer: str


class HeatmapCellDto(BaseModel):
    ticker: str
    name: str
    cycle_phase: str
    return_1w: Optional[float]
    return_1m: Optional[float]
    return_3m: Optional[float]
    rs_score: float
    rrg_quadrant: str


class RRGPointDto(BaseModel):
    ticker: str
    name: str
    cycle_phase: str
    rs_1m: Optional[float]   # x-axis: relative strength vs SPY (1.0 = parity)
    momentum: Optional[float]  # y-axis: RS momentum (positive = accelerating)
    rrg_quadrant: str
    return_1m: Optional[float]
    rs_score: float


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _get_data() -> SectorRotationData:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, fetch_sector_rotation)
    except Exception as exc:
        logger.error("Sector rotation fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sector data temporarily unavailable: {exc}",
        ) from exc


def _to_dto(s: SectorData) -> SectorDto:
    return SectorDto(
        ticker=s.ticker,
        name=s.name,
        cycle_phase=s.cycle_phase,
        return_1w=s.return_1w,
        return_1m=s.return_1m,
        return_3m=s.return_3m,
        rs_1w=s.rs_1w,
        rs_1m=s.rs_1m,
        rs_3m=s.rs_3m,
        rs_score=s.rs_score,
        momentum=s.momentum,
        rrg_quadrant=s.rrg_quadrant,
        last_price=s.last_price,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/rotation",
    response_model=SectorRotationDto,
    summary="Full sector rotation analysis — heatmap + RRG + cycle phase",
)
async def get_sector_rotation() -> SectorRotationDto:
    """
    Returns the full sector rotation dataset:
    - 11 SPDR Sector ETF performance (1W / 1M / 3M)
    - Relative Strength vs SPY per period
    - RS normalised score (0–100, 50 = SPY parity)
    - Momentum (RS rate-of-change)
    - RRG quadrant (Leading / Weakening / Lagging / Improving)
    - Economic cycle phase per sector
    - Dominant cycle phase currently in favour
    - SPY benchmark returns

    Data is sourced from yfinance (15-min delayed) and cached 15 minutes.
    """
    data = await _get_data()
    return SectorRotationDto(
        sectors=[_to_dto(s) for s in data.sectors],
        spy_return_1w=data.spy_return_1w,
        spy_return_1m=data.spy_return_1m,
        spy_return_3m=data.spy_return_3m,
        dominant_cycle_phase=data.dominant_cycle_phase,
        dominant_cycle_description=data.dominant_cycle_description,
        cycle_phase_scores=data.cycle_phase_scores,
        disclaimer=data.disclaimer,
    )


@router.get(
    "/heatmap",
    response_model=List[HeatmapCellDto],
    summary="Lightweight heatmap grid — returns + RS score per sector",
)
async def get_sector_heatmap() -> List[HeatmapCellDto]:
    """
    Lightweight endpoint for rendering the heatmap grid only.
    Returns one cell per sector with returns and colour-scale score.
    Sorted by 1-month RS score descending (best first).
    """
    data = await _get_data()
    cells = [
        HeatmapCellDto(
            ticker=s.ticker,
            name=s.name,
            cycle_phase=s.cycle_phase,
            return_1w=s.return_1w,
            return_1m=s.return_1m,
            return_3m=s.return_3m,
            rs_score=s.rs_score,
            rrg_quadrant=s.rrg_quadrant,
        )
        for s in data.sectors
    ]
    cells.sort(key=lambda c: c.rs_score, reverse=True)
    return cells


@router.get(
    "/rrg",
    response_model=List[RRGPointDto],
    summary="RRG scatter data — relative strength vs momentum per sector",
)
async def get_sector_rrg() -> List[RRGPointDto]:
    """
    Returns the data needed to render a Relative Rotation Graph (RRG):
    - x-axis: relative strength vs SPY (rs_1m, where 1.0 = parity)
    - y-axis: momentum (positive = RS is improving)
    - quadrant label

    Sectors are sorted Leading → Improving → Weakening → Lagging.
    """
    data = await _get_data()
    order = {"Leading": 0, "Improving": 1, "Weakening": 2, "Lagging": 3}
    points = [
        RRGPointDto(
            ticker=s.ticker,
            name=s.name,
            cycle_phase=s.cycle_phase,
            rs_1m=s.rs_1m,
            momentum=s.momentum,
            rrg_quadrant=s.rrg_quadrant,
            return_1m=s.return_1m,
            rs_score=s.rs_score,
        )
        for s in data.sectors
    ]
    points.sort(key=lambda p: order.get(p.rrg_quadrant, 9))
    return points
