"""
app/services/analytics_service.py

Service layer for CORE-ANALYTICS-01 product analytics.

Responsibilities:
  - Record an analytics event (async, fire-and-forget safe)
  - Query the activation funnel
  - Query feature adoption rates
  - Compute DAU time-series
  - Build the full AnalyticsSummary for the admin dashboard

All queries are async and use SQLAlchemy 2.0 style.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.schemas.analytics_models import (
    ACTIVATION_FUNNEL,
    CONVERSION_FUNNEL,
    EVENT_LABELS,
    FEATURE_ADOPTION_EVENTS,
    AnalyticsSummary,
    DailyActiveUsersPoint,
    EventName,
    FeatureAdoptionRow,
    FunnelReport,
    FunnelStep,
)

logger = logging.getLogger(__name__)


# ─── Event Recording ─────────────────────────────────────────────────────────

async def record_event(
    db: AsyncSession,
    event_name: EventName | str,
    *,
    user_id: Optional[uuid.UUID] = None,
    anon_id: Optional[str] = None,
    session_id: Optional[uuid.UUID] = None,
    page: Optional[str] = None,
    feature: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
) -> AnalyticsEvent:
    """
    Persist a single analytics event. This is intentionally not transactional with
    the caller's business logic — analytics failures must never break product flows.

    Callers should wrap this in a try/except if calling from business-critical code:

        try:
            await record_event(db, EventName.USER_SIGNED_UP, user_id=user.id)
        except Exception:
            logger.warning("Analytics event failed — non-fatal", exc_info=True)
    """
    name = event_name.value if isinstance(event_name, EventName) else event_name

    event = AnalyticsEvent(
        user_id=user_id,
        anon_id=anon_id,
        session_id=session_id,
        event_name=name,
        properties=properties or {},
        page=page,
        feature=feature,
    )
    db.add(event)
    await db.flush()  # get the id; caller commits
    await db.refresh(event)
    logger.debug("Analytics event recorded: %s user=%s", name, user_id)
    return event


# ─── Funnel Queries ───────────────────────────────────────────────────────────

async def _count_unique_users_for_event(
    db: AsyncSession,
    event_name: str,
    since: datetime,
) -> int:
    """Count distinct user_ids for a given event in the time window."""
    result = await db.execute(
        select(func.count(distinct(AnalyticsEvent.user_id))).where(
            AnalyticsEvent.event_name == event_name,
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.user_id.is_not(None),
        )
    )
    return result.scalar_one() or 0


async def _count_total_occurrences(
    db: AsyncSession,
    event_name: str,
    since: datetime,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            AnalyticsEvent.event_name == event_name,
            AnalyticsEvent.created_at >= since,
        )
    )
    return result.scalar_one() or 0


async def build_funnel_report(
    db: AsyncSession,
    funnel_events: list[EventName],
    funnel_name: str,
    period_days: int,
) -> FunnelReport:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    steps: list[FunnelStep] = []
    prev_users: Optional[int] = None

    for event in funnel_events:
        unique = await _count_unique_users_for_event(db, event.value, since)
        total = await _count_total_occurrences(db, event.value, since)

        if prev_users is not None and prev_users > 0:
            conversion = round(unique / prev_users * 100, 1)
        elif prev_users == 0:
            conversion = 0.0
        else:
            conversion = None

        steps.append(FunnelStep(
            event_name=event.value,
            label=EVENT_LABELS.get(event.value, event.value),
            unique_users=unique,
            total_occurrences=total,
            conversion_from_previous_pct=conversion,
        ))
        prev_users = unique

    return FunnelReport(
        funnel_name=funnel_name,
        period_days=period_days,
        steps=steps,
    )


# ─── Feature Adoption ─────────────────────────────────────────────────────────

async def build_feature_adoption(
    db: AsyncSession,
    period_days: int,
    total_users: int,
) -> list[FeatureAdoptionRow]:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    rows: list[FeatureAdoptionRow] = []

    for event in FEATURE_ADOPTION_EVENTS:
        unique = await _count_unique_users_for_event(db, event.value, since)
        total = await _count_total_occurrences(db, event.value, since)
        adoption_pct = round(unique / total_users * 100, 1) if total_users > 0 else 0.0
        rows.append(FeatureAdoptionRow(
            event_name=event.value,
            label=EVENT_LABELS.get(event.value, event.value),
            unique_users=unique,
            total_occurrences=total,
            adoption_pct=adoption_pct,
        ))

    rows.sort(key=lambda r: r.unique_users, reverse=True)
    return rows


# ─── Daily Active Users ───────────────────────────────────────────────────────

async def build_dau_series(
    db: AsyncSession,
    period_days: int,
) -> list[DailyActiveUsersPoint]:
    """
    Return daily unique users and new signups for the last `period_days` days.
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    # DAU: distinct users per day
    dau_result = await db.execute(
        select(
            func.date(AnalyticsEvent.created_at).label("day"),
            func.count(distinct(AnalyticsEvent.user_id)).label("dau"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.user_id.is_not(None),
        )
        .group_by(func.date(AnalyticsEvent.created_at))
        .order_by(func.date(AnalyticsEvent.created_at))
    )
    dau_by_day: dict[str, int] = {str(row.day): row.dau for row in dau_result}

    # New signups per day
    signup_result = await db.execute(
        select(
            func.date(AnalyticsEvent.created_at).label("day"),
            func.count().label("cnt"),
        )
        .where(
            AnalyticsEvent.event_name == EventName.USER_SIGNED_UP.value,
            AnalyticsEvent.created_at >= since,
        )
        .group_by(func.date(AnalyticsEvent.created_at))
    )
    signups_by_day: dict[str, int] = {str(row.day): row.cnt for row in signup_result}

    # Merge into a continuous series, filling gaps with 0
    series: list[DailyActiveUsersPoint] = []
    for i in range(period_days):
        day = (datetime.now(timezone.utc) - timedelta(days=period_days - 1 - i)).date()
        day_str = str(day)
        series.append(DailyActiveUsersPoint(
            date=day_str,
            dau=dau_by_day.get(day_str, 0),
            new_users=signups_by_day.get(day_str, 0),
        ))

    return series


# ─── Top Pages / Symbols ─────────────────────────────────────────────────────

async def build_top_pages(
    db: AsyncSession,
    period_days: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    result = await db.execute(
        select(
            AnalyticsEvent.page,
            func.count().label("views"),
            func.count(distinct(AnalyticsEvent.user_id)).label("unique_users"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.page.is_not(None),
        )
        .group_by(AnalyticsEvent.page)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {"page": row.page, "views": row.views, "unique_users": row.unique_users}
        for row in result
    ]


async def build_top_symbols(
    db: AsyncSession,
    period_days: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Extract 'symbol' from properties JSON for symbol_searched / symbol_changed events."""
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    result = await db.execute(
        select(
            AnalyticsEvent.properties["symbol"].astext.label("symbol"),
            func.count().label("searches"),
        )
        .where(
            AnalyticsEvent.event_name.in_([
                EventName.SYMBOL_SEARCHED.value,
                EventName.SYMBOL_CHANGED.value,
            ]),
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.properties["symbol"].astext.is_not(None),
        )
        .group_by(AnalyticsEvent.properties["symbol"].astext)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [{"symbol": row.symbol, "searches": row.searches} for row in result]


# ─── Full Summary ─────────────────────────────────────────────────────────────

async def build_analytics_summary(
    db: AsyncSession,
    period_days: int = 30,
) -> AnalyticsSummary:
    """
    Assemble the complete analytics summary for the admin dashboard.
    All sub-queries use the same period window for consistency.
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Total events in period
    total_events_result = await db.execute(
        select(func.count()).where(AnalyticsEvent.created_at >= since)
    )
    total_events = total_events_result.scalar_one() or 0

    # Total signed-up users (all time — denominator for adoption rates)
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one() or 0

    # Active users in period (at least 1 event)
    active_result = await db.execute(
        select(func.count(distinct(AnalyticsEvent.user_id))).where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.user_id.is_not(None),
        )
    )
    active_users = active_result.scalar_one() or 0

    activation_funnel = await build_funnel_report(
        db, ACTIVATION_FUNNEL, "Activation Funnel", period_days
    )
    conversion_funnel = await build_funnel_report(
        db, CONVERSION_FUNNEL, "Conversion Funnel", period_days
    )
    feature_adoption = await build_feature_adoption(db, period_days, total_users)
    dau_series = await build_dau_series(db, period_days)
    top_pages = await build_top_pages(db, period_days)
    top_symbols = await build_top_symbols(db, period_days)

    return AnalyticsSummary(
        period_days=period_days,
        total_events=total_events,
        total_signed_up_users=total_users,
        total_active_users=active_users,
        activation_funnel=activation_funnel,
        conversion_funnel=conversion_funnel,
        feature_adoption=feature_adoption,
        daily_active_users=dau_series,
        top_pages=top_pages,
        top_symbols=top_symbols,
    )
