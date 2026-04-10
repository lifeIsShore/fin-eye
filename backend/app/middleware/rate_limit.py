"""
app/middleware/rate_limit.py
BUG-005 FIX: Wire up slowapi rate limiting.

Limits (configurable via .env):
  RATE_LIMIT_ANON      = 30   requests/minute  (anonymous / IP-based)
  RATE_LIMIT_AUTH      = 120  requests/minute  (authenticated users)
  RATE_LIMIT_API_KEY   = 300  requests/minute  (API key holders)

Usage in an endpoint:
    from app.middleware.rate_limit import limiter
    from fastapi import Request

    @router.post("/login")
    @limiter.limit("10/minute")
    async def login(request: Request, ...):
        ...

The default limit (RATE_LIMIT_ANON/minute) is applied globally to all routes
that do NOT have an explicit @limiter.limit() decorator.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()

# Key function: use IP address as the rate-limit key for anonymous requests.
# For authenticated endpoints, override with a custom key_func per-route.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_anon}/minute"],
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a clean 429 JSON response instead of a plain-text slowapi default."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}. Please slow down and try again.",
        },
        headers={"Retry-After": "60"},
    )
