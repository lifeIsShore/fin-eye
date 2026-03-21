"""
app/api/v1/endpoints/admin_bulk.py
════════════════════════════════════════════════════════════════════════════
Admin bulk pipeline endpoints (todos-v4.md Phases 3–5, 7–8).

TWO routers are exported so main.py can mount them at different prefixes:
  router       → mounted at /api/v1/admin/bulk  (bulk job endpoints)
  router_admin → mounted at /api/v1/admin        (single-ticker + universe endpoints)

Routes under /api/v1/admin/bulk:
  POST /run-seed          — seed OHLCV for all tickers (fire-and-forget)
  GET  /seed-status       — live seed progress
  POST /run-train         — train ML for seeded tickers (fire-and-forget)
  GET  /train-status      — live train progress
  POST /run-news-seed     — bulk news fetch + score
  GET  /news-status       — news job progress
  GET  /pipeline-overview — full pipeline snapshot

Routes under /api/v1/admin:
  GET  /tickers-universe          — paginated ticker list
  POST /seed/{symbol}             — single-symbol seed
  GET  /seed-status/{symbol}      — per-symbol seed status
  GET  /ticker-status/{symbol}    — OHLCV + model + news stats per ticker
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, AsyncSessionLocal
from app.models.bulk_ops import BulkJobRun, TickerUniverse
from app.models.market import OHLCVDaily, OHLCVIntraday
from app.models.sentiment import NewsArticle
from app.services.auth import require_admin
from app.services.bulk_seed_service import seed_symbol_incremental

# Two separate routers — different URL prefixes
router       = APIRouter()   # /api/v1/admin/bulk  (bulk jobs)
router_admin = APIRouter()   # /api/v1/admin        (single + universe)

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
# admin_bulk.py  →  endpoints/ → v1/ → api/ → app/ → backend/
_BACKEND_DIR   = Path(__file__).parent.parent.parent.parent.parent
_DATA_DIR      = _BACKEND_DIR / "data"
_TICKER_JSON   = _DATA_DIR / "tickers_predefined.json"
_ARTIFACT_DIR  = _DATA_DIR / "models"
_REGISTRY_FILE = _ARTIFACT_DIR / "model_registry.jsonl"

# ── In-process job state ──────────────────────────────────────────────────────
_active_jobs: Dict[str, bool] = {"seeding": False, "training": False, "news": False}

_seed_progress: Dict[str, Any] = {
    "total": 0, "done": 0, "failed": 0, "skipped": 0,
    "running": False, "recent": [], "started_at": None,
}
_train_progress: Dict[str, Any] = {
    "total": 0, "done": 0, "failed": 0, "running": False,
    "current_symbol": None, "current_timeframe": None,
    "recent": [], "started_at": None,
}
_news_progress: Dict[str, Any] = {
    "total": 0, "done": 0, "failed": 0, "running": False, "recent": [],
}


# ── Private helpers ────────────────────────────────────────────────────────────

def _read_registry() -> list[dict]:
    if not _REGISTRY_FILE.exists():
        return []
    records: list[dict] = []
    with open(_REGISTRY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


async def _get_valid_tickers(db: AsyncSession, scope: str = "missing_only") -> list[str]:
    """Return symbols from tickers_universe that are not explicitly invalid."""
    result = await db.execute(
        select(TickerUniverse.symbol)
        .where(
            TickerUniverse.is_active == True,       # noqa: E712
            TickerUniverse.yf_valid.isnot(False),   # NULL means unvalidated — include it
        )
        .order_by(TickerUniverse.tr_rank.nullslast())
    )
    all_syms = [row[0] for row in result.fetchall()]

    if scope == "missing_only":
        seeded = await db.execute(
            select(OHLCVDaily.symbol).distinct().where(OHLCVDaily.symbol.in_(all_syms))
        )
        seeded_set = {r[0] for r in seeded.fetchall()}
        return [s for s in all_syms if s not in seeded_set]

    return all_syms


# ══════════════════════════════════════════════════════════════════════════════
# router_admin  →  mounted at /api/v1/admin
# ══════════════════════════════════════════════════════════════════════════════

@router_admin.get(
    "/tickers-universe",
    dependencies=[Depends(require_admin)],
    summary="List predefined ticker universe (paginated)",
)
async def list_tickers_universe(
    page:        int            = Query(1, ge=1),
    page_size:   int            = Query(50, ge=1, le=200),
    asset_class: Optional[str]  = Query(None),
    yf_valid:    Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    q = select(TickerUniverse).order_by(TickerUniverse.tr_rank.nullslast())
    if asset_class:
        q = q.where(TickerUniverse.asset_class == asset_class)
    if yf_valid is not None:
        q = q.where(TickerUniverse.yf_valid == yf_valid)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tickers": [
            {
                "symbol":      t.symbol,
                "name":        t.name,
                "asset_class": t.asset_class,
                "tr_rank":     t.tr_rank,
                "exchange":    t.exchange,
                "yf_valid":    t.yf_valid,
                "is_active":   t.is_active,
            }
            for t in rows
        ],
    }


@router_admin.post(
    "/seed/{symbol}",
    dependencies=[Depends(require_admin)],
    summary="Seed OHLCV for a single symbol (background)",
)
async def seed_single_symbol(
    symbol: str,
    background_tasks: BackgroundTasks,  # injected by FastAPI — no default
) -> Dict[str, Any]:
    sym = symbol.upper()

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            await seed_symbol_incremental(session, sym)

    background_tasks.add_task(_run)
    return {"symbol": sym, "status": "started", "message": f"Seed started for {sym}"}


@router_admin.get(
    "/seed-status/{symbol}",
    dependencies=[Depends(require_admin)],
    summary="Get latest seed status for a single symbol",
)
async def get_seed_status_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    sym    = symbol.upper()
    result = await db.execute(
        select(BulkJobRun)
        .where(BulkJobRun.symbol == sym, BulkJobRun.job_type == "seed")
        .order_by(BulkJobRun.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        return {"symbol": sym, "status": "never_seeded", "rows_added": 0}
    return {
        "symbol":       sym,
        "status":       job.status,
        "reason":       job.reason,
        "rows_added":   job.rows_added,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router_admin.get(
    "/ticker-status/{symbol}",
    dependencies=[Depends(require_admin)],
    summary="OHLCV + model + news stats for a single ticker",
)
async def get_ticker_status(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    sym = symbol.upper()

    # OHLCV counts
    daily_count  = (await db.execute(
        select(func.count()).select_from(OHLCVDaily).where(OHLCVDaily.symbol == sym)
    )).scalar_one()
    hourly_count = (await db.execute(
        select(func.count()).select_from(OHLCVIntraday)
        .where(OHLCVIntraday.symbol == sym, OHLCVIntraday.interval == "1h")
    )).scalar_one()
    last_date_r  = (await db.execute(
        select(func.max(OHLCVDaily.trade_date)).where(OHLCVDaily.symbol == sym)
    )).scalar_one()
    first_date_r = (await db.execute(
        select(func.min(OHLCVDaily.trade_date)).where(OHLCVDaily.symbol == sym)
    )).scalar_one()

    # Training — read from JSONL registry + check artifact files exist on disk
    records     = _read_registry()
    sym_records = [r for r in records if r.get("symbol", "").upper() == sym]
    trained_tfs: list[dict] = []
    best_sharpe: Optional[float] = None
    best_model:  Optional[str]   = None
    last_trained: Optional[str]  = None

    for rec in sym_records:
        artifact = rec.get("artifact_file", "")
        path = _ARTIFACT_DIR / artifact if artifact else None
        if path and path.exists():
            tf = rec.get("timeframe")
            sh = rec.get("validation_sharpe")
            trained_tfs.append({
                "timeframe":  tf,
                "model":      rec.get("model_name"),
                "sharpe":     sh,
                "trained_at": rec.get("trained_at"),
            })
            t = rec.get("trained_at")
            if t and (last_trained is None or t > last_trained):
                last_trained = t
            if sh is not None and (best_sharpe is None or sh > best_sharpe):
                best_sharpe = sh
                best_model  = rec.get("model_name")

    train_status = "trained" if trained_tfs else ("no_artifacts" if sym_records else "not_started")

    # News stats
    news_count  = (await db.execute(
        select(func.count()).select_from(NewsArticle).where(NewsArticle.symbol == sym)
    )).scalar_one()
    news_oldest = (await db.execute(
        select(func.min(NewsArticle.published_at)).where(NewsArticle.symbol == sym)
    )).scalar_one()
    news_newest = (await db.execute(
        select(func.max(NewsArticle.published_at)).where(NewsArticle.symbol == sym)
    )).scalar_one()
    news_last_f = (await db.execute(
        select(func.max(NewsArticle.last_fetched_at)).where(NewsArticle.symbol == sym)
    )).scalar_one()

    return {
        "symbol": sym,
        "ohlcv": {
            "daily_bars":  daily_count,
            "hourly_bars": hourly_count,
            "last_date":   last_date_r.isoformat()  if last_date_r  else None,
            "first_date":  first_date_r.isoformat() if first_date_r else None,
            "is_seeded":   daily_count >= 200,
        },
        "training": {
            "status":             train_status,
            "timeframes_trained": len(trained_tfs),
            "best_sharpe":        best_sharpe,
            "best_model":         best_model,
            "trained_at":         last_trained,
            "timeframes":         trained_tfs,
        },
        "news": {
            "article_count":   news_count,
            "oldest":          news_oldest.date().isoformat() if news_oldest else None,
            "newest":          news_newest.date().isoformat() if news_newest else None,
            "last_fetched_at": news_last_f.isoformat()        if news_last_f else None,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# router  →  mounted at /api/v1/admin/bulk
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/run-seed",
    dependencies=[Depends(require_admin)],
    summary="Seed OHLCV for all tickers (fire-and-forget)",
)
async def run_bulk_seed(
    scope: str = "missing_only",
    background_tasks: BackgroundTasks = BackgroundTasks(),  # FastAPI injects regardless of default
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if _active_jobs["seeding"]:
        return {"status": "already_running", "message": "A seed job is already in progress."}

    symbols = await _get_valid_tickers(db, scope=scope)
    if not symbols:
        return {"status": "nothing_to_do", "total_tickers": 0, "message": "No tickers to seed."}

    _seed_progress.update({
        "total": len(symbols), "done": 0, "failed": 0, "skipped": 0,
        "running": True, "recent": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    async def _run_batch() -> None:
        _active_jobs["seeding"] = True
        try:
            batch_size = 10
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i: i + batch_size]
                await asyncio.gather(*[_seed_one(s) for s in batch], return_exceptions=True)
                await asyncio.sleep(1.0)  # yfinance courtesy pause
        finally:
            _active_jobs["seeding"] = False
            _seed_progress["running"] = False

    async def _seed_one(sym: str) -> None:
        async with AsyncSessionLocal() as session:
            result = await seed_symbol_incremental(session, sym)
        if result.status == "done":
            _seed_progress["done"] += 1
        elif result.status == "skipped":
            _seed_progress["skipped"] += 1
        else:
            _seed_progress["failed"] += 1
        _seed_progress["recent"] = (
            [{"symbol": sym, "status": result.status,
              "reason": result.reason, "rows_added": result.rows_added}]
            + _seed_progress["recent"]
        )[:50]

    background_tasks.add_task(_run_batch)
    return {
        "status":        "started",
        "total_tickers": len(symbols),
        "scope":         scope,
        "message":       f"Bulk seed started for {len(symbols)} tickers in the background.",
    }


@router.get(
    "/seed-status",
    dependencies=[Depends(require_admin)],
    summary="Live bulk seed job progress",
)
async def get_bulk_seed_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    p     = _seed_progress
    total = p["total"]
    done  = p["done"] + p["failed"] + p["skipped"]
    pct   = round(done / total * 100, 1) if total else 0

    agg = await db.execute(
        select(BulkJobRun.status, func.count().label("n"))
        .where(BulkJobRun.job_type == "seed")
        .group_by(BulkJobRun.status)
    )
    db_counts: dict[str, int] = {r[0]: r[1] for r in agg.fetchall()}

    return {
        "total":        total or sum(db_counts.values()),
        "done":         p["done"],
        "failed":       p["failed"],
        "skipped":      p["skipped"],
        "running":      p["running"],
        "pct_complete": pct,
        "started_at":   p["started_at"],
        "recent":       p["recent"][:20],
        "db_totals":    db_counts,
    }


@router.post(
    "/run-train",
    dependencies=[Depends(require_admin)],
    summary="Train ML models for all seeded tickers (fire-and-forget, sequential)",
)
async def run_bulk_train(
    scope: str = "untrained_only",
    background_tasks: BackgroundTasks = BackgroundTasks(),  # FastAPI injects regardless of default
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if _active_jobs["training"]:
        return {"status": "already_running", "message": "A training job is already in progress."}

    result = await db.execute(
        select(OHLCVDaily.symbol, func.count().label("bar_count"))
        .group_by(OHLCVDaily.symbol)
        .having(func.count() >= 200)
    )
    seeded_symbols = [r[0] for r in result.fetchall()]

    if scope == "untrained_only":
        registry    = _read_registry()
        trained_set = {r.get("symbol", "").upper() for r in registry}
        symbols     = [s for s in seeded_symbols if s.upper() not in trained_set]
    else:
        symbols = seeded_symbols

    if not symbols:
        return {"status": "nothing_to_do", "total_tickers": 0}

    _train_progress.update({
        "total": len(symbols), "done": 0, "failed": 0,
        "running": True, "current_symbol": None, "current_timeframe": None,
        "recent": [], "started_at": datetime.now(timezone.utc).isoformat(),
    })

    async def _run_train() -> None:
        from app.services.ml_pipeline import run_training_pipeline, TIMEFRAME_HORIZON  # noqa: PLC0415
        from app.services.market_data import OHLCVFetcher  # noqa: PLC0415

        _active_jobs["training"] = True
        timeframes = list(TIMEFRAME_HORIZON.keys())
        loop = asyncio.get_running_loop()
        try:
            for sym in symbols:
                _train_progress["current_symbol"] = sym
                for tf in timeframes:
                    _train_progress["current_timeframe"] = tf
                    try:
                        period  = "730d" if tf == "1h" else "5y"
                        records = OHLCVFetcher.fetch_historical_data(sym, period=period, interval=tf)
                        if len(records) < 200:
                            continue
                        df = pd.DataFrame([
                            {"date": r.timestamp, "open": r.open, "high": r.high,
                             "low": r.low, "close": r.close, "volume": r.volume}
                            for r in records
                        ]).set_index("date").sort_index()
                        # run_training_pipeline is CPU-bound — use executor
                        meta = await loop.run_in_executor(
                            None, run_training_pipeline, sym, tf, df
                        )
                        _train_progress["recent"] = (
                            [{"symbol": sym, "timeframe": tf,
                              "sharpe": meta.get("validation_sharpe"), "status": "done"}]
                            + _train_progress["recent"]
                        )[:50]
                    except Exception as exc:
                        logger.warning("Train failed %s/%s: %s", sym, tf, exc)
                        _train_progress["recent"] = (
                            [{"symbol": sym, "timeframe": tf,
                              "status": "failed", "reason": str(exc)[:200]}]
                            + _train_progress["recent"]
                        )[:50]
                        _train_progress["failed"] += 1
                _train_progress["done"] += 1
        finally:
            _active_jobs["training"] = False
            _train_progress["running"] = False
            _train_progress["current_symbol"] = None
            _train_progress["current_timeframe"] = None

    background_tasks.add_task(_run_train)
    return {
        "status":        "started",
        "total_tickers": len(symbols),
        "scope":         scope,
        "message":       f"Bulk training started for {len(symbols)} tickers (sequential).",
    }


@router.get(
    "/train-status",
    dependencies=[Depends(require_admin)],
    summary="Live bulk training job progress",
)
async def get_bulk_train_status() -> Dict[str, Any]:
    p     = _train_progress
    total = p["total"]
    done  = p["done"]
    pct   = round(done / total * 100, 1) if total else 0
    sharpe_vals = [
        r["sharpe"] for r in p["recent"]
        if r.get("status") == "done" and r.get("sharpe") is not None
    ]
    avg_sharpe = round(sum(sharpe_vals) / len(sharpe_vals), 3) if sharpe_vals else None
    return {
        "total":             total,
        "done":              done,
        "failed":            p["failed"],
        "running":           p["running"],
        "pct_complete":      pct,
        "current_symbol":    p["current_symbol"],
        "current_timeframe": p["current_timeframe"],
        "avg_sharpe":        avg_sharpe,
        "recent":            p["recent"][:20],
        "started_at":        p["started_at"],
    }


@router.post(
    "/run-news-seed",
    dependencies=[Depends(require_admin)],
    summary="Bulk fetch + score news for all active tickers",
)
async def run_bulk_news_seed(
    lookback_days: int = 7,
    background_tasks: BackgroundTasks = BackgroundTasks(),  # FastAPI injects regardless of default
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if _active_jobs["news"]:
        return {"status": "already_running"}

    result = await db.execute(
        select(TickerUniverse.symbol)
        .where(
            TickerUniverse.is_active == True,      # noqa: E712
            TickerUniverse.yf_valid.isnot(False),
        )
        .order_by(TickerUniverse.tr_rank.nullslast())
    )
    symbols = [r[0] for r in result.fetchall()]
    if not symbols:
        return {"status": "nothing_to_do"}

    _news_progress.update({"total": len(symbols), "done": 0, "failed": 0, "running": True, "recent": []})

    async def _run_news() -> None:
        from app.services.news_data import NewsFetcher  # noqa: PLC0415

        _active_jobs["news"] = True
        fetcher = NewsFetcher()
        try:
            for sym in symbols:
                try:
                    async with AsyncSessionLocal() as session:
                        counts = await fetcher.fetch_and_store(
                            session, symbols=[sym], lookback_days=lookback_days
                        )
                    _news_progress["done"] += 1
                    _news_progress["recent"] = (
                        [{"symbol": sym, "articles": counts.get(sym, 0), "status": "done"}]
                        + _news_progress["recent"]
                    )[:50]
                except Exception as exc:
                    _news_progress["failed"] += 1
                    _news_progress["recent"] = (
                        [{"symbol": sym, "status": "failed", "reason": str(exc)[:200]}]
                        + _news_progress["recent"]
                    )[:50]
                await asyncio.sleep(1.0)  # Finnhub free tier courtesy pause
        finally:
            _active_jobs["news"] = False
            _news_progress["running"] = False

    background_tasks.add_task(_run_news)
    return {"status": "started", "total_tickers": len(symbols), "lookback_days": lookback_days}


@router.get(
    "/news-status",
    dependencies=[Depends(require_admin)],
    summary="Live news seed job progress",
)
async def get_bulk_news_status() -> Dict[str, Any]:
    p     = _news_progress
    total = p["total"]
    done  = p["done"]
    pct   = round(done / total * 100, 1) if total else 0
    return {
        "total": total, "done": done, "failed": p["failed"],
        "running": p["running"], "pct_complete": pct,
        "recent": p["recent"][:20],
    }


@router.get(
    "/pipeline-overview",
    dependencies=[Depends(require_admin)],
    summary="Full snapshot of the entire data pipeline state",
)
async def get_pipeline_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:

    # ── Ticker universe ───────────────────────────────────────────────────────
    univ_total = (await db.execute(select(func.count()).select_from(TickerUniverse))).scalar_one()
    univ_valid = (await db.execute(
        select(func.count()).select_from(TickerUniverse)
        .where(TickerUniverse.yf_valid == True)  # noqa: E712
    )).scalar_one()
    class_rows = await db.execute(
        select(TickerUniverse.asset_class, func.count().label("n"))
        .where(TickerUniverse.is_active == True)  # noqa: E712
        .group_by(TickerUniverse.asset_class)
    )
    by_class = {r[0] or "unknown": r[1] for r in class_rows.fetchall()}

    # ── Seeding ───────────────────────────────────────────────────────────────
    seeded_count = (await db.execute(
        select(func.count(func.distinct(OHLCVDaily.symbol)))
    )).scalar_one()

    # Get the latest status per symbol — window function CTE to avoid showing
    # stale historical failures for symbols that were later successfully seeded.
    latest_seed_cte = (
        select(
            BulkJobRun.symbol,
            BulkJobRun.status,
            BulkJobRun.reason,
            func.row_number().over(
                partition_by=BulkJobRun.symbol,
                order_by=BulkJobRun.created_at.desc(),
            ).label("rn"),
        )
        .where(BulkJobRun.job_type == "seed", BulkJobRun.symbol.isnot(None))
        .cte("latest_seed")
    )
    latest_seed_rows = (await db.execute(
        select(latest_seed_cte.c.symbol, latest_seed_cte.c.status, latest_seed_cte.c.reason)
        .where(latest_seed_cte.c.rn == 1)
    )).fetchall()

    failed_tickers  = [{"symbol": r[0], "reason": r[2]} for r in latest_seed_rows if r[1] == "failed"][:50]
    skipped_tickers = [{"symbol": r[0], "reason": r[2]} for r in latest_seed_rows if r[1] == "skipped"][:50]
    last_seed = (await db.execute(
        select(func.max(BulkJobRun.completed_at)).where(BulkJobRun.job_type == "seed")
    )).scalar_one()

    # ── Training ──────────────────────────────────────────────────────────────
    registry = _read_registry()
    trained_symbols: set[str] = set()
    sharpe_vals: list[float] = []
    quality_pass = 0
    for rec in registry:
        sym = rec.get("symbol", "").upper()
        trained_symbols.add(sym)
        s = rec.get("validation_sharpe")
        if s is not None:
            sharpe_vals.append(s)
        if rec.get("quality_gate"):
            quality_pass += 1
    avg_sharpe   = round(sum(sharpe_vals) / len(sharpe_vals), 3) if sharpe_vals else None
    gate_pct     = round(quality_pass / len(registry) * 100, 1) if registry else 0
    train_failed = (await db.execute(
        select(func.count()).select_from(BulkJobRun)
        .where(BulkJobRun.job_type == "train", BulkJobRun.status == "failed")
    )).scalar_one()
    last_train = (await db.execute(
        select(func.max(BulkJobRun.completed_at)).where(BulkJobRun.job_type == "train")
    )).scalar_one()

    # ── News ──────────────────────────────────────────────────────────────────
    news_total  = (await db.execute(select(func.count()).select_from(NewsArticle))).scalar_one()
    news_oldest = (await db.execute(select(func.min(NewsArticle.published_at)))).scalar_one()
    news_last_f = (await db.execute(select(func.max(NewsArticle.last_fetched_at)))).scalar_one()

    return {
        "ticker_universe": {"total": univ_total, "yf_valid": univ_valid, "by_class": by_class},
        "seeding": {
            "seeded":          seeded_count,
            "failed":          len(failed_tickers),
            "skipped":         len(skipped_tickers),
            "missing":         max(0, (univ_valid or 0) - seeded_count),
            "last_run_at":     last_seed.isoformat() if last_seed else None,
            "failed_tickers":  failed_tickers,
            "skipped_tickers": skipped_tickers,
        },
        "training": {
            "trained":          len(trained_symbols),
            "failed":           train_failed,
            "untrained":        max(0, seeded_count - len(trained_symbols)),
            "avg_sharpe":       avg_sharpe,
            "quality_gate_pct": gate_pct,
            "last_run_at":      last_train.isoformat() if last_train else None,
        },
        "news": {
            "total_articles": news_total,
            "oldest_article": news_oldest.date().isoformat() if news_oldest else None,
            "last_fetch_at":  news_last_f.isoformat() if news_last_f else None,
        },
        "active_jobs": {k: v for k, v in _active_jobs.items()},
    }
