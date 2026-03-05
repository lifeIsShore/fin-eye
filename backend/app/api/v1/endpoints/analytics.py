"""
app/api/v1/endpoints/analytics.py

Analytics API endpoints (CORE-ANALYTICS-01).

Public (auth optional):
  POST /api/v1/analytics/event
    — client-side beacon: records a single analytics event.
      Accepts both authenticated (JWT) and anonymous (anon_id) callers.
      Always returns 200 — analytics must never block the UI.

Admin only:
  GET /api/v1/analytics/summary?period_days=30
    — full analytics summary: funnels, adoption, DAU, top pages/symbols.

  GET /api/v1/analytics/events?event_name=...&limit=...
    — raw event stream for debugging / ad-hoc queries (last N events).
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, bearer_scheme
from app.db.database import get_db
from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.schemas.analytics_models import (
    AnalyticsSummary,
    EventName,
    EventRecordedResponse,
    TrackEventRequest,
)
from app.services.analytics_service import build_analytics_summary, record_event
from app.services.auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Client-side Beacon ──────────────────────────────────────────────────────

@router.post(
    "/event",
    response_model=EventRecordedResponse,
    summary="Track a product analytics event (client beacon)",
    description=(
        "Fire-and-forget analytics beacon. Accepts both authenticated and "
        "anonymous callers. Returns 200 even on internal errors — analytics "
        "must never degrade the user experience."
    ),
)
async def track_event(
    body: TrackEventRequest,
    db: AsyncSession = Depends(get_db),
    # Optional auth — we don't reject unauthenticated requests
    credentials: Annotated[Any, Depends(bearer_scheme)] = None,
) -> EventRecordedResponse:
    """
    Record a client-side analytics event.

    User identification priority:
      1. Valid JWT Bearer token → use authenticated user_id
      2. anon_id in body → use as anonymous identifier
      3. Neither → event is recorded with no user context
    """
    user_id = None

    # Try to resolve user from token without raising (optional auth pattern)
    if credentials is not None:
        try:
            from app.core.security import decode_token  # noqa: PLC0415
            from app.services.auth_service import get_user_by_id  # noqa: PLC0415
            import uuid  # noqa: PLC0415

            payload = decode_token(credentials.credentials)
            if payload and payload.get("type") == "access":
                uid_str = payload.get("sub")
                if uid_str:
                    user = await get_user_by_id(db, uuid.UUID(uid_str))
                    if user and user.is_active:
                        user_id = user.id
        except Exception:
            # Token resolution failure is non-fatal for analytics
            pass

    try:
        event = await record_event(
            db,
            event_name=body.event_name,
            user_id=user_id,
            anon_id=body.anon_id,
            session_id=body.session_id,
            page=body.page,
            feature=body.feature,
            properties=body.properties,
        )
        await db.commit()
        return EventRecordedResponse(event_id=str(event.id))
    except Exception as exc:
        logger.warning("Analytics event recording failed (non-fatal): %s", exc, exc_info=True)
        # Never surface analytics errors to the client
        return EventRecordedResponse(status="degraded", event_id="")


# ─── Admin Analytics Dashboard ───────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Full analytics summary for the admin dashboard",
    dependencies=[Depends(require_admin)],
)
async def get_analytics_summary(
    period_days: int = Query(default=30, ge=1, le=365, description="Lookback window in days"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    """
    Returns aggregated product analytics: activation funnel, feature adoption,
    DAU time-series, top pages, and top searched symbols.
    Admin-only endpoint.
    """
    return await build_analytics_summary(db, period_days=period_days)


@router.get(
    "/events",
    summary="Raw event stream (admin debug)",
    dependencies=[Depends(require_admin)],
)
async def get_recent_events(
    event_name: Optional[str] = Query(None, description="Filter by event name"),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Returns the most recent analytics events, optionally filtered by event_name.
    Useful for debugging instrumentation in development.
    Admin-only endpoint.
    """
    stmt = select(AnalyticsEvent).order_by(desc(AnalyticsEvent.created_at)).limit(limit)
    if event_name:
        stmt = stmt.where(AnalyticsEvent.event_name == event_name)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_name": e.event_name,
            "user_id": str(e.user_id) if e.user_id else None,
            "anon_id": e.anon_id,
            "page": e.page,
            "feature": e.feature,
            "properties": e.properties,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
