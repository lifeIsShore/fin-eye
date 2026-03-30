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
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.market import OHLCVDaily, OHLCVIntraday
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


@router.get("/ohlcv/{symbol}", summary="Read OHLCV price history for a symbol")
async def get_ohlcv(
    symbol: str,
    interval: str = Query(default="1d", description="Bar interval: '1d', '1h', or '4h'"),
    limit: int = Query(default=365, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return OHLCV bars for a symbol, used by the DCA simulator and other frontend pages.

    - interval=1d  → ohlcv_daily  (trade_date)
    - interval=1h  → ohlcv_intraday filtered by interval
    - interval=4h  → ohlcv_intraday filtered by interval
    """
    sym = symbol.upper()

    if interval == "1d":
        result = await db.execute(
            select(OHLCVDaily)
            .where(OHLCVDaily.symbol == sym)
            .order_by(desc(OHLCVDaily.trade_date))
            .limit(limit)
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail=f"No daily OHLCV data found for {sym}")
        # Return oldest-first so the DCA page gets an ascending time series
        bars = [
            {
                "date": str(r.trade_date),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.adj_close,  # DCA calculations use adj_close
                "volume": r.volume,
            }
            for r in reversed(rows)
        ]
    elif interval in ("1h", "4h"):
        result = await db.execute(
            select(OHLCVIntraday)
            .where(OHLCVIntraday.symbol == sym, OHLCVIntraday.interval == interval)
            .order_by(desc(OHLCVIntraday.bar_time))
            .limit(limit)
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail=f"No {interval} OHLCV data found for {sym}")
        bars = [
            {
                "date": r.bar_time.isoformat(),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in reversed(rows)
        ]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval '{interval}'. Use '1d', '1h', or '4h'.",
        )

    return {"symbol": sym, "interval": interval, "count": len(bars), "bars": bars}


@router.get("/cache/status", summary="Cache status")
async def cache_status() -> dict:
    """Check if Redis cache is reachable and return sample keys."""
    cache = get_cache()
    alive = await cache.ping()
    return {"redis_alive": alive}