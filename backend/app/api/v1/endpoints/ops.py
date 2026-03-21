"""
app/api/v1/endpoints/ops.py

Admin-only observability endpoints (CORE-OPS-01).

GET  /api/v1/ops/metrics          — full metrics snapshot
GET  /api/v1/ops/pipeline-status  — latest run per pipeline job
GET  /api/v1/ops/jobs             — APScheduler job schedule
GET  /api/v1/ops/health           — composite health check (DB + Redis + pipelines)
GET  /api/v1/ops/alerts           — threshold-breach alerts
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.services.metrics import get_metrics
from app.api.v1.deps import require_admin

router = APIRouter()

# ─── Thresholds (tune as needed) ────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "api_error_rate_pct":   10.0,   # alert if any route error rate > 10%
    "api_p95_latency_ms":  2000.0,  # alert if any route P95 > 2 s
    "pipeline_success_rate_pct": 80.0,  # alert if any job success rate < 80%
    "inference_p95_ms":    5000.0,  # alert if inference P95 > 5 s
}


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/metrics", dependencies=[Depends(require_admin)])
def get_full_metrics() -> Dict[str, Any]:
    """Full observability snapshot: API latency, error rates, pipelines, inference."""
    return get_metrics().snapshot()


@router.get("/pipeline-status", dependencies=[Depends(require_admin)])
def get_pipeline_status() -> List[Dict[str, Any]]:
    """Latest run summary for each scheduled pipeline job."""
    return get_metrics().get_pipeline_status()


@router.get("/jobs", dependencies=[Depends(require_admin)])
def get_job_schedule() -> List[Dict[str, Any]]:
    """List all APScheduler jobs with their next fire time."""
    try:
        from app.services.scheduler import scheduler  # noqa: PLC0415
        jobs = []
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_at": next_run.isoformat() if next_run else None,
            })
        return jobs
    except Exception as exc:
        return [{"error": str(exc)}]


@router.get("/health", dependencies=[Depends(require_admin)])
async def get_health_summary() -> Dict[str, Any]:
    """
    Composite health check:
      - Database connectivity
      - Redis connectivity
      - Pipeline job health (last run success + staleness)
    """
    from app.db.database import test_db_connection   # noqa: PLC0415
    from app.db.redis_client import redis_client      # noqa: PLC0415

    db_ok = await test_db_connection()

    redis_ok = False
    try:
        redis_ok = await redis_client.ping()
    except Exception:
        pass

    # Pipeline staleness check: flag any job not run in >25h
    pipelines = get_metrics().get_pipeline_status()
    pipeline_issues: List[str] = []
    now = datetime.now(timezone.utc)
    stale_threshold = timedelta(hours=25)
    for p in pipelines:
        if not p["last_success"]:
            pipeline_issues.append(f"{p['job_id']} last run FAILED")
        if p["last_run_at"]:
            try:
                last_dt = datetime.fromisoformat(p["last_run_at"].replace("Z", "+00:00"))
                if now - last_dt > stale_threshold:
                    pipeline_issues.append(f"{p['job_id']} stale ({p['last_run_at']})")
            except Exception:
                pass

    overall = "ok" if db_ok and redis_ok and not pipeline_issues else "degraded"

    return {
        "status": overall,
        "checked_at": now.isoformat(),
        "components": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
            "pipelines": "ok" if not pipeline_issues else "degraded",
        },
        "pipeline_issues": pipeline_issues,
    }


@router.get("/backup-status", dependencies=[Depends(require_admin)])
def get_backup_status() -> Dict[str, Any]:
    """
    Latest backup job run from the metrics store.
    Also lists local backup files if BACKUP_DIR is accessible.
    """
    import os
    from pathlib import Path

    pipeline_rows = get_metrics().get_pipeline_status()
    backup_row = next((r for r in pipeline_rows if r["job_id"] == "backup_db"), None)

    backup_dir = Path(os.getenv("BACKUP_DIR", "backups")).resolve()
    local_files: list[Dict[str, Any]] = []
    if backup_dir.exists():
        dumps = sorted(backup_dir.glob("fin_eye_*.dump"), reverse=True)
        for f in dumps[:10]:   # last 10 only
            local_files.append({
                "filename": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "modified_at": datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })

    return {
        "last_run": backup_row,
        "backup_dir": str(backup_dir),
        "local_files_count": len(list(backup_dir.glob("fin_eye_*.dump"))) if backup_dir.exists() else 0,
        "recent_files": local_files,
    }


@router.post("/backup-now", dependencies=[Depends(require_admin)])
async def trigger_backup_now() -> Dict[str, Any]:
    """
    Manually trigger an immediate DB backup (runs in background task).
    Returns immediately — check /backup-status for result.
    """
    import asyncio  # noqa: PLC0415
    from app.services.scheduler import job_backup_db  # noqa: PLC0415

    asyncio.create_task(job_backup_db())
    return {"status": "started", "message": "Backup triggered. Check /backup-status for result."}


@router.get("/alerts", dependencies=[Depends(require_admin)])
def get_threshold_alerts() -> Dict[str, Any]:
    """
    Evaluate current metrics against configured thresholds.
    Returns a list of active breaches — empty list means all clear.
    """
    snap = get_metrics().snapshot()
    breaches: List[Dict[str, Any]] = []

    # API route checks
    for route in snap["api"]["routes"]:
        if route["error_rate_pct"] > ALERT_THRESHOLDS["api_error_rate_pct"]:
            breaches.append({
                "type": "api_error_rate",
                "severity": "warning",
                "message": (
                    f"{route['route']} error rate {route['error_rate_pct']}% "
                    f"exceeds threshold {ALERT_THRESHOLDS['api_error_rate_pct']}%"
                ),
                "value": route["error_rate_pct"],
                "threshold": ALERT_THRESHOLDS["api_error_rate_pct"],
            })
        p95 = route["latency_ms"].get("p95")
        if p95 and p95 > ALERT_THRESHOLDS["api_p95_latency_ms"]:
            breaches.append({
                "type": "api_latency",
                "severity": "warning",
                "message": (
                    f"{route['route']} P95 latency {p95}ms "
                    f"exceeds threshold {ALERT_THRESHOLDS['api_p95_latency_ms']}ms"
                ),
                "value": p95,
                "threshold": ALERT_THRESHOLDS["api_p95_latency_ms"],
            })

    # Pipeline checks
    for pipeline in snap["pipelines"]:
        if pipeline["success_rate_pct"] < ALERT_THRESHOLDS["pipeline_success_rate_pct"]:
            breaches.append({
                "type": "pipeline_failures",
                "severity": "error",
                "message": (
                    f"{pipeline['job_id']} success rate {pipeline['success_rate_pct']}% "
                    f"below threshold {ALERT_THRESHOLDS['pipeline_success_rate_pct']}%"
                ),
                "value": pipeline["success_rate_pct"],
                "threshold": ALERT_THRESHOLDS["pipeline_success_rate_pct"],
            })

    # Inference checks
    inf = snap["inference"]
    if inf.get("p95_ms") and inf["p95_ms"] > ALERT_THRESHOLDS["inference_p95_ms"]:
        breaches.append({
            "type": "inference_latency",
            "severity": "warning",
            "message": (
                f"Inference P95 {inf['p95_ms']}ms "
                f"exceeds threshold {ALERT_THRESHOLDS['inference_p95_ms']}ms"
            ),
            "value": inf["p95_ms"],
            "threshold": ALERT_THRESHOLDS["inference_p95_ms"],
        })

    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "all_clear": len(breaches) == 0,
        "breach_count": len(breaches),
        "thresholds": ALERT_THRESHOLDS,
        "breaches": breaches,
    }
