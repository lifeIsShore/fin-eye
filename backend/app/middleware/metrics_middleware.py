"""
app/middleware/metrics_middleware.py

Starlette middleware that records per-route API latency and error counts
into the MetricsStore singleton after every request.

Route normalisation: path parameters are collapsed so
  GET /api/v1/technical/AAPL/latest  →  /api/v1/technical/{symbol}/latest
This prevents high-cardinality explosion in the metrics store.

Registration in main.py:
    from app.middleware.metrics_middleware import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)
"""

from __future__ import annotations

import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics import get_metrics

# ─── Path normalisation rules ─────────────────────────────────────────────────
# Order matters — more specific patterns first.
_NORMALISE_RULES: list[tuple[re.Pattern, str]] = [
    # Symbol segments:  AAPL, SPY, BTC-USD → {symbol}
    (re.compile(r"/[A-Z]{1,10}(-[A-Z]{2,5})?(?=/|$)"), "/{symbol}"),
    # Integer IDs
    (re.compile(r"/\d+(?=/|$)"), "/{id}"),
    # Slugs: all-lowercase-with-dashes
    (re.compile(r"/[a-z][a-z0-9-]{3,}(?=/|$)"), "/{slug}"),
]


def _normalise(path: str) -> str:
    for pattern, replacement in _NORMALISE_RULES:
        path = pattern.sub(replacement, path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Only instrument /api/ routes to avoid noise from static assets
        path = request.url.path
        if path.startswith("/api/"):
            route = f"{request.method} {_normalise(path)}"
            get_metrics().record_request(route, duration_ms, response.status_code)

        return response
