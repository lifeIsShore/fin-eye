"""
app/middleware/security_headers.py

Sprint 7 (SEC-06) — SecurityHeadersMiddleware.

Adds the following HTTP response headers on every response:
  X-Content-Type-Options: nosniff
      Prevents MIME-type sniffing — browsers must respect Content-Type.

  X-Frame-Options: DENY
      Prevents this app from being embedded in an <iframe> — blocks clickjacking.

  X-XSS-Protection: 0
      Modern best practice: disable the legacy XSS auditor (causes false positives).
      Rely on CSP instead.

  Referrer-Policy: strict-origin-when-cross-origin
      Sends full URL as Referer only for same-origin requests; for cross-origin
      sends only the origin. Prevents sensitive URL paths from leaking to third parties.

  Permissions-Policy: camera=(), microphone=(), geolocation=()
      Disables browser features the app doesn't use. Defence-in-depth.

  Content-Security-Policy:
      Tightened in production. Dev keeps 'unsafe-inline' for Next.js hot reload.

  Strict-Transport-Security: max-age=31536000; includeSubDomains
      Only set in production (not localhost). Tells browsers to always use HTTPS.

Registered in main.py before all other middleware:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

_settings = get_settings()
_IS_PROD = _settings.environment.lower() in ("production", "prod")

# ── CSP directives ────────────────────────────────────────────────────────────
# In dev: 'unsafe-inline' allowed so Next.js hot-reload works without CSP errors.
# In prod: tightened — no inline scripts, only same-origin + trusted CDNs.

if _IS_PROD:
    _CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "   # Tailwind inlines styles
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
else:
    # Dev: relaxed CSP — allows inline scripts/styles for HMR and eval for source maps
    _CSP = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "   # allow WebSocket for HMR
        "frame-ancestors 'none';"
    )

# ── Static headers applied on every response ─────────────────────────────────
_STATIC_HEADERS: list[tuple[str, str]] = [
    ("X-Content-Type-Options",  "nosniff"),
    ("X-Frame-Options",         "DENY"),
    ("X-XSS-Protection",        "0"),
    ("Referrer-Policy",         "strict-origin-when-cross-origin"),
    ("Permissions-Policy",      "camera=(), microphone=(), geolocation=()"),
    ("Content-Security-Policy", _CSP),
]

# Only add HSTS in production — never on localhost (breaks local HTTP dev)
if _IS_PROD:
    _STATIC_HEADERS.append(
        ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every outbound response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response: Response = await call_next(request)
        for header, value in _STATIC_HEADERS:
            response.headers[header] = value
        return response
