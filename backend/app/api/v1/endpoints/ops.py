"""
app/api/v1/endpoints/ops.py

Admin-only observability endpoints (CORE-OPS-01).

GET  /api/v1/ops/metrics          — full metrics snapshot
GET  /api/v1/ops/pipeline-status  — latest run per pipeline job
GET  /api/v1/ops/jobs             — APScheduler job schedule
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.services.metrics import get_metrics
from app.services.auth import require_admin

router = APIRouter()


@router.get("/metrics", dependencies=[Depends(require_admin)])
def get_full_metrics() -> Dict[str, Any]:
    """
    Full observability snapshot:
      - API latency (P50/P95/P99) per route
      - Error rates (4xx/5xx) per route
      - Pipeline job last-run outcomes and success rates
      - Model inference timing summary
    """
    return get_metrics().snapshot()


@router.get("/pipeline-status", dependencies=[Depends(require_admin)])
def get_pipeline_status() -> List[Dict[str, Any]]:
    """Latest run summary for each scheduled pipeline job."""
    return get_metrics().get_pipeline_status()


@router.get("/jobs", dependencies=[Depends(require_admin)])
def get_job_schedule() -> List[Dict[str, Any]]:
    """
    List all registered APScheduler jobs with their next fire time.
    Useful for confirming schedules without reading the source code.
    """
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
