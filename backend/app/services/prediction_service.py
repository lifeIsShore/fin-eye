"""
app/services/prediction_service.py

ML Prediction Database — Sprint 2, todos-v5 Phase 5.

Three responsibilities:
  1. store_prediction()         — called from technical_service on every inference
  2. resolve_pending_outcomes() — hourly cron: fills in actual price + correctness
  3. get_prediction_stats()     — per-symbol live accuracy stats for the frontend
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, Integer, case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_prediction import MLPrediction

logger = logging.getLogger(__name__)

# ── Horizon delta helpers ─────────────────────────────────────────────────────

_PERIOD_DURATION: dict[str, timedelta] = {
    "1h":  timedelta(hours=1),
    "4h":  timedelta(hours=4),
    "1d":  timedelta(days=1),
    "1wk": timedelta(weeks=1),
    "1mo": timedelta(days=30),
}


def _horizon_ends(timeframe: str, horizon_periods: int, from_dt: datetime) -> datetime:
    delta = _PERIOD_DURATION.get(timeframe, timedelta(days=1))
    return from_dt + (delta * horizon_periods)


# ── 1. Store prediction ───────────────────────────────────────────────────────

async def store_prediction(
    db: AsyncSession,
    *,
    symbol:              str,
    timeframe:           str,
    model_name:          str,
    predicted_direction: int,
    confidence:          float,
    horizon_periods:     int,
    price_at_prediction: float,
    expected_return:     Optional[float]      = None,
    mlflow_run_id:       Optional[str]        = None,
    feature_snapshot:    Optional[dict]       = None,
    macro_score:         Optional[float]      = None,
    vix:                 Optional[float]      = None,
    market_regime:       Optional[str]        = None,
) -> Optional[MLPrediction]:
    """
    Store one prediction row. Idempotent via ON CONFLICT DO NOTHING on
    (symbol, timeframe, prediction_date). Returns None if duplicate skipped.
    """
    now             = datetime.now(timezone.utc)
    prediction_date = now.date()
    horizon_end     = _horizon_ends(timeframe, horizon_periods, now)

    row = {
        "symbol":               symbol.upper(),
        "timeframe":            timeframe,
        "model_name":           model_name,
        "mlflow_run_id":        mlflow_run_id,
        "predicted_at":         now,
        "prediction_date":      prediction_date,
        "predicted_direction":  predicted_direction,
        "confidence":           round(confidence, 4),
        "expected_return":      round(expected_return, 6) if expected_return is not None else None,
        "horizon_periods":      horizon_periods,
        "horizon_ends_at":      horizon_end,
        "price_at_prediction":  round(price_at_prediction, 4),
        "feature_snapshot":     feature_snapshot,
        "macro_score_at_prediction":   macro_score,
        "vix_at_prediction":           vix,
        "market_regime_at_prediction": market_regime,
    }

    try:
        stmt = (
            pg_insert(MLPrediction)
            .values(**row)
            .on_conflict_do_nothing(constraint="uq_ml_prediction_symbol_tf_date")
            .returning(MLPrediction.id)
        )
        result = await db.execute(stmt)
        await db.flush()

        inserted_id = result.scalar_one_or_none()
        if inserted_id is None:
            logger.debug(
                "Prediction deduped for %s/%s on %s (already stored today)",
                symbol, timeframe, prediction_date,
            )
            return None

        logger.debug(
            "Stored prediction %d: %s/%s → %s (conf=%.1f%%, horizon→%s)",
            inserted_id, symbol, timeframe,
            "UP" if predicted_direction == 1 else "DOWN",
            confidence * 100, horizon_end.strftime("%Y-%m-%d %H:%M"),
        )
        return await db.get(MLPrediction, inserted_id)

    except Exception as exc:
        logger.warning("Failed to store prediction for %s/%s: %s", symbol, timeframe, exc)
        return None


# ── 2. Outcome resolver ───────────────────────────────────────────────────────

async def resolve_pending_outcomes(
    db: AsyncSession,
    *,
    batch_size: int = 200,
) -> dict:
    """
    Find all predictions where horizon_ends_at <= now and outcome not yet resolved.
    Fetch current price for each symbol and fill in actual outcome.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(MLPrediction)
        .where(
            and_(
                MLPrediction.horizon_ends_at <= now,
                MLPrediction.outcome_resolved_at.is_(None),
            )
        )
        .order_by(MLPrediction.horizon_ends_at.asc())
        .limit(batch_size)
    )
    pending = result.scalars().all()

    if not pending:
        return {"resolved": 0, "failed": 0, "skipped": 0}

    symbols_needed = list({p.symbol for p in pending})
    prices: dict[str, Optional[float]] = {}

    for sym in symbols_needed:
        try:
            price = await _fetch_price_async(sym)
            prices[sym] = price
        except Exception as exc:
            logger.warning("Price fetch failed for %s during outcome resolution: %s", sym, exc)
            prices[sym] = None

    resolved = failed = skipped = 0

    for pred in pending:
        price_now = prices.get(pred.symbol)
        if price_now is None:
            skipped += 1
            continue

        try:
            actual_return = (price_now / pred.price_at_prediction) - 1
            actual_dir    = 1 if actual_return > 0 else 0

            pred.price_at_outcome    = round(price_now, 4)
            pred.actual_return       = round(actual_return, 6)
            pred.actual_direction    = actual_dir
            pred.was_correct         = (actual_dir == pred.predicted_direction)
            pred.outcome_resolved_at = now

            resolved += 1
        except Exception as exc:
            logger.warning("Failed to resolve outcome for prediction %d: %s", pred.id, exc)
            failed += 1

    if resolved > 0:
        await db.flush()
        logger.info(
            "Outcome resolution: %d resolved, %d failed, %d skipped",
            resolved, failed, skipped,
        )

    return {"resolved": resolved, "failed": failed, "skipped": skipped}


async def _fetch_price_async(symbol: str) -> Optional[float]:
    import asyncio
    loop = asyncio.get_running_loop()

    def _sync_fetch() -> Optional[float]:
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist   = ticker.history(period="2d", interval="1d", auto_adjust=True)
            if hist.empty:
                return None
            return float(hist["Close"].iloc[-1])
        except Exception:
            return None

    return await loop.run_in_executor(None, _sync_fetch)


# ── 3. Live accuracy stats ────────────────────────────────────────────────────

async def get_prediction_stats(
    db: AsyncSession,
    symbol: str,
    *,
    min_resolved: int = 10,
) -> dict:
    """
    Compute live accuracy statistics for a symbol across all timeframes.
    """
    sym = symbol.upper()

    # ── Per-timeframe aggregate ───────────────────────────────────────────────
    # Use case() with new SQLAlchemy 2.x syntax: case(condition, value)
    correct_expr = func.sum(
        case((MLPrediction.was_correct == True, 1), else_=0)  # noqa: E712
    )
    avg_ret_correct_expr = func.avg(
        case((MLPrediction.was_correct == True, MLPrediction.actual_return), else_=None)  # noqa: E712
    )
    avg_ret_wrong_expr = func.avg(
        case((MLPrediction.was_correct == False, MLPrediction.actual_return), else_=None)  # noqa: E712
    )

    tf_rows = await db.execute(
        select(
            MLPrediction.timeframe,
            func.count().label("total"),
            correct_expr.label("correct"),
            avg_ret_correct_expr.label("avg_ret_correct"),
            avg_ret_wrong_expr.label("avg_ret_wrong"),
        )
        .where(
            MLPrediction.symbol == sym,
            MLPrediction.outcome_resolved_at.isnot(None),
        )
        .group_by(MLPrediction.timeframe)
    )
    tf_stats: dict[str, dict] = {}
    for row in tf_rows:
        total   = int(row.total)
        correct = int(row.correct or 0)
        acc     = round(correct / total, 4) if total >= min_resolved else None
        tf_stats[row.timeframe] = {
            "total_resolved":      total,
            "correct":             correct,
            "live_accuracy":       acc,
            "avg_return_correct":  round(float(row.avg_ret_correct), 6) if row.avg_ret_correct else None,
            "avg_return_wrong":    round(float(row.avg_ret_wrong), 6)   if row.avg_ret_wrong   else None,
        }

    # ── Recent 30-day accuracy ────────────────────────────────────────────────
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    recent_rows = await db.execute(
        select(
            MLPrediction.timeframe,
            func.count().label("total"),
            func.sum(
                case((MLPrediction.was_correct == True, 1), else_=0)  # noqa: E712
            ).label("correct"),
        )
        .where(
            MLPrediction.symbol == sym,
            MLPrediction.outcome_resolved_at.isnot(None),
            MLPrediction.predicted_at >= cutoff_30d,
        )
        .group_by(MLPrediction.timeframe)
    )
    for row in recent_rows:
        tf = row.timeframe
        if tf not in tf_stats:
            continue
        total   = int(row.total)
        correct = int(row.correct or 0)
        tf_stats[tf]["recent_30d_accuracy"] = (
            round(correct / total, 4) if total >= min_resolved else None
        )
        overall = tf_stats[tf].get("live_accuracy")
        recent  = tf_stats[tf].get("recent_30d_accuracy")
        if overall and recent:
            diff = recent - overall
            tf_stats[tf]["trend"] = "improving" if diff > 0.02 else "degrading" if diff < -0.02 else "stable"
        else:
            tf_stats[tf]["trend"] = None

    # ── Regime-conditional accuracy ───────────────────────────────────────────
    regime_rows = await db.execute(
        select(
            MLPrediction.timeframe,
            MLPrediction.market_regime_at_prediction,
            func.count().label("n"),
            func.sum(
                case((MLPrediction.was_correct == True, 1), else_=0)  # noqa: E712
            ).label("correct"),
        )
        .where(
            MLPrediction.symbol == sym,
            MLPrediction.outcome_resolved_at.isnot(None),
            MLPrediction.market_regime_at_prediction.isnot(None),
        )
        .group_by(MLPrediction.timeframe, MLPrediction.market_regime_at_prediction)
    )
    for row in regime_rows:
        tf = row.timeframe
        if tf not in tf_stats:
            continue
        by_regime = tf_stats[tf].setdefault("by_regime", {})
        n       = int(row.n)
        correct = int(row.correct or 0)
        if row.market_regime_at_prediction:
            by_regime[row.market_regime_at_prediction] = {
                "accuracy": round(correct / n, 4) if n >= 5 else None,
                "n":        n,
            }

    # ── Best performing timeframe ─────────────────────────────────────────────
    best_tf = None
    best_acc = -1.0
    for tf, stats in tf_stats.items():
        acc = stats.get("live_accuracy")
        if acc is not None and acc > best_acc:
            best_acc = acc
            best_tf  = tf

    # ── Overall model health ──────────────────────────────────────────────────
    total_all  = sum(s["total_resolved"] for s in tf_stats.values())
    has_enough = any(s.get("live_accuracy") is not None for s in tf_stats.values())
    model_health = "insufficient_data" if not has_enough else (
        "good"     if best_acc >= 0.55 else
        "marginal" if best_acc >= 0.50 else
        "poor"
    )

    return {
        "symbol":                    sym,
        "available":                 bool(tf_stats),
        "total_resolved_all_tfs":    total_all,
        "timeframes":                tf_stats,
        "best_performing_timeframe": best_tf,
        "model_health":              model_health,
    }
