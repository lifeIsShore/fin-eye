"""
app/services/gas_precompute.py

BUG FIX: _compute_technical_score and _compute_sentiment_score were called
sequentially with await despite the comment saying "run concurrently".
They now run with asyncio.gather() — saves ~1-2s per symbol per batch.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud.gas_snapshot import get_latest, upsert_snapshot
from app.services.cache import get_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_W_TECHNICAL = 0.40
_W_SENTIMENT = 0.30
_W_MACRO     = 0.30

_CACHE_TTL_S = 900

DEFAULT_SYMBOLS: list[str] = settings.ohlcv_symbols_default  # type: ignore[attr-defined]


def _gas_to_weather(score: float) -> str:
    if score >= 80:
        return "Strong Tailwind"
    if score >= 60:
        return "Mild Support"
    if score >= 40:
        return "Mixed Signals"
    if score >= 20:
        return "Headwind"
    return "High Instability"


def _technical_to_regime(technical_score: float) -> str:
    if technical_score >= 60:
        return "Risk-On"
    if technical_score <= 40:
        return "Risk-Off"
    return "Transitional"


async def _compute_technical_score(symbol: str) -> tuple[float, Optional[list]]:
    try:
        from app.services.technical_service import compute_technical_consensus  # noqa: PLC0415
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, compute_technical_consensus, symbol)
        score   = float(result.get("consensus_score", 50.0))
        signals = result.get("signals", [])
        logger.debug("Technical score for %s: %.1f", symbol, score)
        return score, signals
    except Exception as exc:
        logger.warning("Technical inference failed for %s: %s — using 50.0", symbol, exc)
        return 50.0, []


async def _compute_sentiment_score(symbol: str, db: AsyncSession) -> float:
    try:
        from sqlalchemy import select, func  # noqa: PLC0415
        from app.models.sentiment import SentimentAggregate  # noqa: PLC0415
        from datetime import timedelta  # noqa: PLC0415

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(func.avg(SentimentAggregate.sentiment_score))
            .where(
                SentimentAggregate.symbol == symbol.upper(),
                SentimentAggregate.date >= cutoff.date(),
            )
        )
        avg_raw: Optional[float] = result.scalar_one_or_none()
        if avg_raw is None:
            logger.debug("No sentiment data for %s — using 50.0", symbol)
            return 50.0
        score = ((float(avg_raw) + 1.0) / 2.0) * 100.0
        score = max(0.0, min(100.0, score))
        logger.debug("Sentiment score for %s: %.1f (raw=%.3f)", symbol, score, avg_raw)
        return round(score, 1)
    except Exception as exc:
        logger.warning("Sentiment score failed for %s: %s — using 50.0", symbol, exc)
        return 50.0


async def _compute_macro_score(db: AsyncSession) -> float:
    try:
        from app.crud.macro import get_latest_batch_async  # noqa: PLC0415
        from app.services.macro_scoring import compute_macro_score  # noqa: PLC0415

        indicator_names = [
            "fed_funds_rate", "unemployment_rate", "yield_spread_10y_2y",
            "cpi_yoy", "vix", "nonfarm_payrolls_mom", "industrial_production_yoy",
        ]
        rows = await get_latest_batch_async(db, indicator_names)
        indicators = {name: row.value if row else None for name, row in rows.items()}
        result = compute_macro_score(indicators)
        logger.debug("Macro score: %.1f (%s)", result.score, result.label)
        return float(result.score)
    except Exception as exc:
        logger.warning("Macro score computation failed: %s — using 50.0", exc)
        return 50.0


async def compute_gas_for_symbol(
    symbol: str,
    db: AsyncSession,
    macro_score: Optional[float] = None,
) -> dict:
    symbol = symbol.upper()

    # BUG FIX: run technical and sentiment concurrently, not sequentially.
    # Previously both were awaited in sequence despite the comment saying concurrent.
    (technical_score, technical_signals), sentiment_score = await asyncio.gather(
        _compute_technical_score(symbol),
        _compute_sentiment_score(symbol, db),
    )

    if macro_score is None:
        macro_score = await _compute_macro_score(db)

    gas_score = (
        technical_score * _W_TECHNICAL
        + sentiment_score * _W_SENTIMENT
        + macro_score    * _W_MACRO
    )
    gas_score = round(max(0.0, min(100.0, gas_score)), 2)

    weather_label = _gas_to_weather(gas_score)
    regime        = _technical_to_regime(technical_score)

    component_scores = {
        "technical": round(technical_score, 1),
        "sentiment": round(sentiment_score, 1),
        "macro":     round(macro_score, 1),
    }

    snap = await upsert_snapshot(
        db,
        symbol=symbol,
        gas_score=gas_score,
        weather_label=weather_label,
        regime=regime,
        component_scores=component_scores,
        technical_signals=technical_signals or [],
        source="live",
    )

    snap_dict = snap.to_dict()

    cache = get_cache()
    if cache:
        cache_key = f"gas:snapshot:{symbol}"
        await cache.set(cache_key, snap_dict, ttl=_CACHE_TTL_S)
        logger.debug("Cached gas:snapshot:%s (TTL=%ds)", symbol, _CACHE_TTL_S)

    return snap_dict


async def run_gas_precompute_batch(
    db: AsyncSession,
    symbols: Optional[list[str]] = None,
) -> dict:
    target_symbols = [s.upper() for s in (symbols or DEFAULT_SYMBOLS)]
    started_at     = datetime.now(timezone.utc)

    logger.info("GAS precompute batch started — %d symbols: %s", len(target_symbols), target_symbols)

    macro_score = await _compute_macro_score(db)
    logger.info("Shared macro score for this batch: %.1f", macro_score)

    results:  dict[str, dict] = {}
    failures: list[str]       = []

    for symbol in target_symbols:
        try:
            snap = await compute_gas_for_symbol(symbol, db, macro_score=macro_score)
            results[symbol] = snap
            logger.info(
                "  ✓ %s  GAS=%.1f  weather=%s  regime=%s",
                symbol, snap["gas_score"], snap["weather_label"], snap["regime"],
            )
        except Exception as exc:
            logger.error("  ✗ %s  FAILED: %s", symbol, exc)
            failures.append(symbol)

    await db.commit()

    elapsed_ms = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
    summary = {
        "symbols_attempted":  len(target_symbols),
        "symbols_succeeded":  len(results),
        "symbols_failed":     len(failures),
        "failed_symbols":     failures,
        "elapsed_ms":         round(elapsed_ms, 1),
        "macro_score_shared": round(macro_score, 1),
    }
    logger.info("GAS precompute batch complete: %s", summary)
    return summary


async def get_snapshot_cached(symbol: str, db: AsyncSession) -> Optional[dict]:
    symbol    = symbol.upper()
    cache_key = f"gas:snapshot:{symbol}"

    cache = get_cache()
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Cache HIT for gas:snapshot:%s", symbol)
            return {**cached, "source": "cache"}

    snap = await get_latest(db, symbol)
    if snap:
        snap_dict = snap.to_dict()
        if cache:
            await cache.set(cache_key, snap_dict, ttl=_CACHE_TTL_S)
        logger.debug("DB snapshot HIT for %s (age: %s)", symbol, snap.computed_at)
        return {**snap_dict, "source": "db_snapshot"}

    logger.info("No snapshot found for %s — running live compute (cold start)", symbol)
    try:
        snap_dict = await compute_gas_for_symbol(symbol, db)
        await db.commit()
        return snap_dict
    except Exception as exc:
        logger.error("Live compute failed for %s: %s", symbol, exc)
        return None
