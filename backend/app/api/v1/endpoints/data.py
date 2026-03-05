"""
app/api/v1/data.py
Data-pipeline trigger endpoints (admin/internal use).
Allows manually triggering fetchers for dev and ops purposes.

FIXES:
  BUG-001: cache.set_macro_score() -> cache.set_macro() (method did not exist)
  BUG-002: Removed BackgroundTasks = BackgroundTasks() default (orphaned instance
           that FastAPI never managed; fetcher is awaited directly so param removed)
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.ohlcv_fetcher import OHLCVFetcher
from app.services.macro_data import MacroFetcher
from app.services.news_data import NewsFetcher
from app.services.cache import get_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["Data Pipelines"])


@router.post("/fetch/ohlcv", summary="Trigger OHLCV daily fetch")
async def trigger_ohlcv_fetch(
    symbols: Optional[List[str]] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually trigger an OHLCV daily fetch for the given symbols
    (or all default symbols if none specified).
    """
    fetcher = OHLCVFetcher()
    try:
        results = await fetcher.fetch_and_store_daily(db, symbols=symbols)
        return {"status": "ok", "results": results}
    except Exception as exc:
        logger.exception("OHLCV fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fetch/macro", summary="Trigger macro data fetch")
async def trigger_macro_fetch(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger a FRED macro fetch and score recomputation."""
    fetcher = MacroFetcher()
    cache = get_cache()
    try:
        await fetcher.fetch_and_store(db)
        score_data = await fetcher.compute_and_store_score(db)
        if score_data:
            # FIX BUG-001: was cache.set_macro_score() — method does not exist
            await cache.set_macro(score_data)
        return {"status": "ok", "score": score_data}
    except Exception as exc:
        logger.exception("Macro fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fetch/news", summary="Trigger news fetch")
async def trigger_news_fetch(
    symbols: Optional[List[str]] = Query(default=None),
    lookback_days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger a Finnhub news fetch for the given symbols."""
    fetcher = NewsFetcher()
    try:
        results = await fetcher.fetch_and_store(db, symbols=symbols, lookback_days=lookback_days)
        return {"status": "ok", "results": results}
    except Exception as exc:
        logger.exception("News fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cache/status", summary="Cache status")
async def cache_status() -> dict:
    """Check if Redis cache is reachable and return sample keys."""
    cache = get_cache()
    alive = await cache.ping()
    return {"redis_alive": alive}