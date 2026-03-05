"""
app/models/analytics.py

AnalyticsEvent — persisted product analytics events (CORE-ANALYTICS-01).

Design principles:
  - No PII stored in properties. User identified only by UUID FK (nullable for anon).
  - Event names are free-form strings validated at the service layer against the
    canonical taxonomy in app/schemas/analytics_models.py.
  - Properties are stored as JSON for flexibility without requiring schema migrations
    for new event properties.
  - session_id is a client-generated UUID allowing session-level aggregation without
    server-side session state.
  - anon_id is a SHA-256(IP+UA) hash for pre-login funnel tracking; cleared once the
    user authenticates (user_id takes over).

Indexes:
  - (event_name, created_at) — funnel queries filter by event name + date range.
  - (user_id, event_name)    — per-user feature adoption queries.
  - created_at               — time-series aggregation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.db.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    # Who triggered the event (nullable for anonymous / pre-login events)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Pre-login anonymous tracking (SHA-256 hash of IP+UA — no raw PII)
    anon_id = Column(String(64), nullable=True)

    # Client session identifier (UUID generated on page load, persisted in memory)
    session_id = Column(UUID(as_uuid=True), nullable=True)

    # Canonical event name — validated against EventName enum in the service layer
    event_name = Column(String(128), nullable=False, index=True)

    # Freeform JSON properties — must not contain PII (enforced at service layer)
    properties = Column(JSON, nullable=True, default=dict)

    # Convenience denormed fields for fast dashboard queries (no JSON extraction needed)
    page = Column(String(255), nullable=True)   # e.g. "/dashboard", "/backtesting"
    feature = Column(String(128), nullable=True)  # e.g. "hedging_simulator", "macro_advanced"

    # Server timestamp — always UTC, never client-supplied
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Funnel queries: event_name + time window
        Index("ix_analytics_event_name_created", "event_name", "created_at"),
        # Per-user adoption: who used what feature
        Index("ix_analytics_user_event", "user_id", "event_name"),
        # Daily active users (DAU) style aggregations
        Index("ix_analytics_created_user", "created_at", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalyticsEvent id={self.id} event={self.event_name} "
            f"user={self.user_id} at={self.created_at}>"
        )
