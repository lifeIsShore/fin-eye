"""
app/services/metrics.py

In-process metrics store for Fin-Eye observability (CORE-OPS-01).

Design: single-process, in-memory. No external dependency (Prometheus/StatsD optional
future upgrade). All writes use threading.Lock for safety with FastAPI's thread pool.

Tracks:
  - API request counts and latency per route (P50, P95, P99)
  - API error rates per route (4xx, 5xx)
  - Pipeline job outcomes (success/failure/duration) per job_id
  - Model inference times per symbol+timeframe

Exposed via GET /api/v1/ops/metrics (admin-only).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class LatencySample:
    ts: float       # unix timestamp
    duration_ms: float


@dataclass
class RouteStats:
    route: str
    total_requests: int = 0
    error_4xx: int = 0
    error_5xx: int = 0
    # Rolling window: last 500 samples
    _samples: Deque[LatencySample] = field(default_factory=lambda: deque(maxlen=500))

    def record(self, duration_ms: float, status_code: int) -> None:
        self.total_requests += 1
        self._samples.append(LatencySample(ts=time.time(), duration_ms=duration_ms))
        if 400 <= status_code < 500:
            self.error_4xx += 1
        elif status_code >= 500:
            self.error_5xx += 1

    def percentiles(self) -> Dict[str, Optional[float]]:
        if not self._samples:
            return {"p50": None, "p95": None, "p99": None, "avg": None}
        vals = sorted(s.duration_ms for s in self._samples)
        n = len(vals)
        def pct(p: float) -> float:
            idx = min(int(p / 100 * n), n - 1)
            return round(vals[idx], 2)
        return {
            "p50": pct(50),
            "p95": pct(95),
            "p99": pct(99),
            "avg": round(sum(vals) / n, 2),
        }

    def error_rate_pct(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round((self.error_4xx + self.error_5xx) / self.total_requests * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        p = self.percentiles()
        return {
            "route": self.route,
            "total_requests": self.total_requests,
            "error_4xx": self.error_4xx,
            "error_5xx": self.error_5xx,
            "error_rate_pct": self.error_rate_pct(),
            "latency_ms": p,
        }


@dataclass
class PipelineRun:
    job_id: str
    started_at: str          # ISO-8601
    finished_at: Optional[str]
    duration_ms: Optional[float]
    success: bool
    detail: str              # e.g. "Fetched 12 symbols" or error message


@dataclass
class InferenceRecord:
    symbol: str
    timeframe: str
    duration_ms: float
    ts: float = field(default_factory=time.time)


# ─── Singleton store ─────────────────────────────────────────────────────────

class MetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._routes: Dict[str, RouteStats] = {}
        # Per job: keep last 50 runs
        self._pipeline_runs: Dict[str, Deque[PipelineRun]] = defaultdict(
            lambda: deque(maxlen=50)
        )
        # Last 200 inference samples
        self._inference: Deque[InferenceRecord] = deque(maxlen=200)
        self._started_at = datetime.now(timezone.utc).isoformat()

    # ── API metrics ──────────────────────────────────────────────────────────

    def record_request(self, route: str, duration_ms: float, status_code: int) -> None:
        with self._lock:
            if route not in self._routes:
                self._routes[route] = RouteStats(route=route)
            self._routes[route].record(duration_ms, status_code)

    # ── Pipeline metrics ─────────────────────────────────────────────────────

    def record_pipeline_run(
        self,
        job_id: str,
        started_at: str,
        finished_at: str,
        duration_ms: float,
        success: bool,
        detail: str = "",
    ) -> None:
        run = PipelineRun(
            job_id=job_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 1),
            success=success,
            detail=detail,
        )
        with self._lock:
            self._pipeline_runs[job_id].append(run)

    def get_pipeline_status(self) -> List[Dict[str, Any]]:
        """Return the latest run for each job_id."""
        with self._lock:
            results = []
            for job_id, runs in self._pipeline_runs.items():
                if runs:
                    last = runs[-1]
                    total = len(runs)
                    successes = sum(1 for r in runs if r.success)
                    results.append({
                        "job_id": job_id,
                        "last_run_at": last.started_at,
                        "last_duration_ms": last.duration_ms,
                        "last_success": last.success,
                        "last_detail": last.detail,
                        "success_rate_pct": round(successes / total * 100, 1),
                        "total_runs_recorded": total,
                    })
            return sorted(results, key=lambda x: x["job_id"])

    # ── Inference metrics ────────────────────────────────────────────────────

    def record_inference(self, symbol: str, timeframe: str, duration_ms: float) -> None:
        with self._lock:
            self._inference.append(
                InferenceRecord(symbol=symbol, timeframe=timeframe, duration_ms=duration_ms)
            )

    def get_inference_stats(self) -> Dict[str, Any]:
        with self._lock:
            if not self._inference:
                return {"count": 0, "avg_ms": None, "p95_ms": None}
            vals = sorted(r.duration_ms for r in self._inference)
            n = len(vals)
            p95_idx = min(int(0.95 * n), n - 1)
            return {
                "count": n,
                "avg_ms": round(sum(vals) / n, 2),
                "p95_ms": round(vals[p95_idx], 2),
            }

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            routes_snapshot = [r.to_dict() for r in self._routes.values()]

        # Sort by total_requests desc
        routes_snapshot.sort(key=lambda r: r["total_requests"], reverse=True)

        return {
            "server_started_at": self._started_at,
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "api": {
                "routes": routes_snapshot,
                "total_routes_tracked": len(routes_snapshot),
            },
            "pipelines": self.get_pipeline_status(),
            "inference": self.get_inference_stats(),
        }


# Module-level singleton
_store = MetricsStore()


def get_metrics() -> MetricsStore:
    return _store
