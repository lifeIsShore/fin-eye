"""
app/api/v1/endpoints/admin_ml.py

Sprint 6 — todos-v5 Phase 5.5 admin endpoints.

Drift report + acknowledge + admin drift summary.
Requires admin user (is_admin=True).

Routes:
  GET  /api/v1/admin/ml/drift-report              — all drift alerts
  GET  /api/v1/admin/ml/drift-report?unacked_only=true  — unacknowledged only
  POST /api/v1/admin/ml/drift-report/{id}/ack     — acknowledge an alert
  GET  /api/v1/admin/ml/optuna-params/{symbol}/{timeframe}/{model} — tuned params
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List

from app.db.database import get_db
from app.api.v1.deps import require_admin

router = APIRouter()


@router.get("/drift-report", dependencies=[Depends(require_admin)])
async def get_drift_report(
    unacked_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all model drift alerts, newest first.
    Pass ?unacked_only=true to filter to unacknowledged alerts.
    """
    from app.services.drift_service import get_drift_report  # noqa: PLC0415
    return await get_drift_report(db, unacked_only=unacked_only)


@router.post("/drift-report/{alert_id}/ack", dependencies=[Depends(require_admin)])
async def acknowledge_drift_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Acknowledge a drift alert (marks it as reviewed)."""
    from app.services.drift_service import acknowledge_drift_alert  # noqa: PLC0415
    ok = await acknowledge_drift_alert(db, alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Drift alert {alert_id} not found")
    await db.commit()
    return {"acknowledged": True, "alert_id": alert_id}


@router.get("/drift-summary", dependencies=[Depends(require_admin)])
async def get_drift_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Quick summary: how many alerts exist, how many are critical/unacked."""
    from app.services.drift_service import get_drift_report  # noqa: PLC0415
    alerts = await get_drift_report(db, unacked_only=False)
    total      = len(alerts)
    unacked    = sum(1 for a in alerts if not a["acknowledged"])
    critical   = sum(1 for a in alerts if a["severity"] == "critical" and not a["acknowledged"])
    return {
        "total_alerts":    total,
        "unacked_alerts":  unacked,
        "critical_alerts": critical,
        "all_clear":       unacked == 0,
    }


@router.get("/optuna-params/{symbol}/{timeframe}/{model}")
async def get_optuna_params(symbol: str, timeframe: str, model: str) -> Dict[str, Any]:
    """
    Returns the best Optuna-tuned hyperparameters for a symbol/timeframe/model,
    if a tuning run has completed. Returns 404 if not yet tuned.
    """
    from app.services.optuna_tuner import load_best_params  # noqa: PLC0415
    params = load_best_params(symbol.upper(), timeframe, model.lower())
    if params is None:
        raise HTTPException(
            status_code=404,
            detail=f"No tuned params found for {symbol}/{timeframe}/{model}. "
                   "Run the overnight tuning job (ENABLE_HYPERTUNING=True) first."
        )
    return {"symbol": symbol.upper(), "timeframe": timeframe, "model": model, "best_params": params}
