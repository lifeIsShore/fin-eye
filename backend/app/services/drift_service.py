"""
app/services/drift_service.py

Sprint 6 — todos-v5 Phase 5.5

Model drift detection and alert management.
"""

from __future__ import annotations

import logging
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_prediction import MLPrediction
from app.models.model_drift_alert import ModelDriftAlert, DRIFT_THRESHOLD_PP

logger = logging.getLogger(__name__)

_REPEAT_ALERT_COOLDOWN_DAYS = 3
_CRITICAL_THRESHOLD_PP      = 20.0
_MIN_PREDICTIONS            = 20


async def detect_and_record_drift(
    db: AsyncSession,
    *,
    registry_file: Optional[str] = None,
    auto_retrain: bool = False,
) -> dict:
    """
    Main drift detection job. Called hourly after resolve_pending_outcomes().
    """
    if registry_file is None:
        from app.services.ml_pipeline import REGISTRY_FILE  # noqa: PLC0415
        registry_file = REGISTRY_FILE

    val_accuracies = _load_val_accuracies(registry_file)
    cutoff_30d     = datetime.now(timezone.utc) - timedelta(days=30)

    # Use case() with SQLAlchemy 2.x syntax (no func.cast needed)
    rows = await db.execute(
        select(
            MLPrediction.symbol,
            MLPrediction.timeframe,
            func.count().label("n"),
            func.sum(
                case((MLPrediction.was_correct == True, 1), else_=0)  # noqa: E712
            ).label("correct"),
        )
        .where(
            MLPrediction.outcome_resolved_at.isnot(None),
            MLPrediction.predicted_at >= cutoff_30d,
        )
        .group_by(MLPrediction.symbol, MLPrediction.timeframe)
        .having(func.count() >= _MIN_PREDICTIONS)
    )

    checked = alerts_created = auto_retrains = drifted = 0

    for row in rows:
        checked += 1
        sym, tf, n, correct = row.symbol, row.timeframe, int(row.n), int(row.correct or 0)
        live_acc_pct = (correct / n) * 100.0
        val_acc_pct  = val_accuracies.get((sym, tf))

        if val_acc_pct is None:
            logger.debug("No validation accuracy found for %s/%s in registry", sym, tf)
            continue

        delta_pp = val_acc_pct - live_acc_pct

        if delta_pp <= DRIFT_THRESHOLD_PP:
            continue

        drifted += 1
        severity = "critical" if delta_pp >= _CRITICAL_THRESHOLD_PP else "warning"

        recent_alert = await db.execute(
            select(ModelDriftAlert)
            .where(
                ModelDriftAlert.symbol    == sym,
                ModelDriftAlert.timeframe == tf,
                ModelDriftAlert.detected_at >= datetime.now(timezone.utc) - timedelta(days=_REPEAT_ALERT_COOLDOWN_DAYS),
            )
            .limit(1)
        )
        if recent_alert.scalar_one_or_none():
            logger.debug("Drift alert cooldown active for %s/%s — skipping", sym, tf)
            continue

        alert = ModelDriftAlert(
            symbol              = sym,
            timeframe           = tf,
            val_accuracy_pct    = round(val_acc_pct, 2),
            live_accuracy_pct   = round(live_acc_pct, 2),
            delta_pp            = round(delta_pp, 2),
            n_live_predictions  = n,
            severity            = severity,
            auto_retrain        = auto_retrain,
        )
        db.add(alert)
        alerts_created += 1

        logger.warning(
            "DRIFT DETECTED %s/%s: val=%.1f%% live=%.1f%% delta=%.1fpp severity=%s",
            sym, tf, val_acc_pct, live_acc_pct, delta_pp, severity,
        )

        if auto_retrain:
            auto_retrains += 1
            try:
                await _trigger_retrain_async(sym, tf)
            except Exception as exc:
                logger.warning("Auto-retrain trigger failed for %s/%s: %s", sym, tf, exc)

    if alerts_created:
        await db.flush()

    return {
        "checked":        checked,
        "drifted":        drifted,
        "alerts_created": alerts_created,
        "auto_retrains":  auto_retrains,
    }


def _load_val_accuracies(registry_file: str) -> dict[tuple[str, str], float]:
    if not os.path.exists(registry_file):
        return {}

    latest: dict[tuple[str, str], dict] = {}
    try:
        with open(registry_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (rec.get("symbol", "").upper(), rec.get("timeframe", ""))
                existing = latest.get(key)
                if existing is None or rec.get("trained_at", "") > existing.get("trained_at", ""):
                    latest[key] = rec
    except OSError:
        return {}

    result: dict[tuple[str, str], float] = {}
    for key, rec in latest.items():
        model_name = rec.get("model_name", "")
        metrics    = rec.get("metrics", {})
        acc        = metrics.get(model_name, {}).get("accuracy")
        if acc is not None:
            result[key] = round(float(acc) * 100, 2)

    return result


async def _trigger_retrain_async(symbol: str, timeframe: str) -> None:
    import asyncio  # noqa: PLC0415
    from app.services.market_data import OHLCVFetcher  # noqa: PLC0415
    from app.services.ml_pipeline import run_training_pipeline  # noqa: PLC0415
    import pandas as pd  # noqa: PLC0415

    def _sync_retrain():
        period  = "730d" if timeframe == "1h" else "5y"
        records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=timeframe)
        if len(records) < 200:
            logger.warning("Auto-retrain: not enough data for %s/%s (%d rows)", symbol, timeframe, len(records))
            return
        df = pd.DataFrame([
            {"date": r.timestamp, "open": r.open, "high": r.high,
             "low": r.low, "close": r.close, "volume": r.volume}
            for r in records
        ]).set_index("date").sort_index()
        run_training_pipeline(symbol, timeframe, df)
        logger.info("Auto-retrain complete for drifted model %s/%s", symbol, timeframe)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_retrain)


async def get_drift_report(db: AsyncSession, *, unacked_only: bool = False) -> list[dict]:
    q = select(ModelDriftAlert).order_by(ModelDriftAlert.detected_at.desc())
    if unacked_only:
        q = q.where(ModelDriftAlert.acknowledged == False)  # noqa: E712
    rows = await db.execute(q.limit(200))
    alerts = rows.scalars().all()
    return [
        {
            "id":                 a.id,
            "symbol":             a.symbol,
            "timeframe":          a.timeframe,
            "val_accuracy_pct":   a.val_accuracy_pct,
            "live_accuracy_pct":  a.live_accuracy_pct,
            "delta_pp":           a.delta_pp,
            "n_live_predictions": a.n_live_predictions,
            "severity":           a.severity,
            "auto_retrain":       a.auto_retrain,
            "retrained_at":       a.retrained_at.isoformat() if a.retrained_at else None,
            "acknowledged":       a.acknowledged,
            "detected_at":        a.detected_at.isoformat(),
            "resolved_at":        a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in alerts
    ]


async def acknowledge_drift_alert(db: AsyncSession, alert_id: int) -> bool:
    row = await db.get(ModelDriftAlert, alert_id)
    if not row:
        return False
    row.acknowledged = True
    row.ack_at       = datetime.now(timezone.utc)
    await db.flush()
    return True
