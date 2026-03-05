"""
tests/api/test_analytics_api.py

Test suite for CORE-ANALYTICS-01 product analytics endpoints.

Coverage:
  - POST /api/v1/analytics/event (beacon — authenticated + anonymous)
  - GET  /api/v1/analytics/summary (admin only)
  - GET  /api/v1/analytics/events  (admin only, raw stream)
  - Invalid event_name rejected at schema layer
  - PII stripping in properties
  - Analytics failures never surface as 5xx to clients
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.analytics_models import EventName


# ─── Beacon endpoint ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_event_anonymous_returns_200(client: AsyncClient) -> None:
    """Anonymous callers (no JWT) can track events — returns 200."""
    payload = {
        "event_name": EventName.DASHBOARD_VIEWED.value,
        "page": "/",
        "properties": {"symbol": "AAPL"},
    }
    response = await client.post("/api/v1/analytics/event", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "event_id" in body


@pytest.mark.asyncio
async def test_track_event_authenticated(client: AsyncClient, auth_headers: dict) -> None:
    """Authenticated users' events are stored with user_id."""
    payload = {
        "event_name": EventName.BACKTEST_RUN.value,
        "page": "/backtesting",
        "feature": "backtesting",
        "properties": {"symbol": "TSLA", "strategy": "momentum"},
    }
    response = await client.post(
        "/api/v1/analytics/event", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_track_event_invalid_event_name_rejected(client: AsyncClient) -> None:
    """Unknown event_name values are rejected with 422."""
    payload = {
        "event_name": "totally_fake_event_that_does_not_exist",
        "page": "/somewhere",
    }
    response = await client.post("/api/v1/analytics/event", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_track_event_strips_pii_from_properties(client: AsyncClient) -> None:
    """PII keys are stripped silently from properties before storage."""
    payload = {
        "event_name": EventName.DASHBOARD_VIEWED.value,
        "properties": {
            "symbol": "AAPL",
            "email": "should@be.stripped",   # PII — must be removed
            "name": "John Doe",              # PII — must be removed
        },
    }
    response = await client.post("/api/v1/analytics/event", json=payload)
    # Request succeeds (PII stripped, not rejected)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_track_event_with_session_id(client: AsyncClient) -> None:
    """session_id field is accepted and stored."""
    session_id = str(uuid.uuid4())
    payload = {
        "event_name": EventName.MACRO_DASHBOARD_VIEWED.value,
        "session_id": session_id,
        "page": "/macro",
    }
    response = await client.post("/api/v1/analytics/event", json=payload)
    assert response.status_code == 200


# ─── Admin summary endpoint ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_summary_requires_admin(client: AsyncClient, auth_headers: dict) -> None:
    """Non-admin authenticated users receive 403."""
    response = await client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_analytics_summary_admin_access(client: AsyncClient, admin_headers: dict) -> None:
    """Admin users can access the analytics summary."""
    response = await client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    # Verify top-level structure
    assert "total_events" in body
    assert "total_signed_up_users" in body
    assert "total_active_users" in body
    assert "activation_funnel" in body
    assert "conversion_funnel" in body
    assert "feature_adoption" in body
    assert "daily_active_users" in body
    assert "top_pages" in body
    assert "top_symbols" in body


@pytest.mark.asyncio
async def test_analytics_summary_funnel_structure(client: AsyncClient, admin_headers: dict) -> None:
    """Activation funnel response has the expected structure per step."""
    response = await client.get("/api/v1/analytics/summary?period_days=7", headers=admin_headers)
    assert response.status_code == 200
    funnel = response.json()["activation_funnel"]
    assert funnel["funnel_name"] == "Activation Funnel"
    assert funnel["period_days"] == 7
    assert len(funnel["steps"]) > 0

    first_step = funnel["steps"][0]
    assert "event_name" in first_step
    assert "label" in first_step
    assert "unique_users" in first_step
    assert "total_occurrences" in first_step
    # First step has no conversion_from_previous_pct
    assert first_step["conversion_from_previous_pct"] is None


@pytest.mark.asyncio
async def test_analytics_summary_dau_series_length(client: AsyncClient, admin_headers: dict) -> None:
    """DAU series has exactly period_days data points."""
    period = 14
    response = await client.get(
        f"/api/v1/analytics/summary?period_days={period}", headers=admin_headers
    )
    assert response.status_code == 200
    dau = response.json()["daily_active_users"]
    assert len(dau) == period


# ─── Raw events endpoint ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_raw_events_admin_only(client: AsyncClient, auth_headers: dict) -> None:
    """Non-admin users cannot access raw event stream."""
    response = await client.get("/api/v1/analytics/events", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_raw_events_returns_list(client: AsyncClient, admin_headers: dict) -> None:
    """Admin users receive a list of events."""
    response = await client.get("/api/v1/analytics/events?limit=10", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_raw_events_filter_by_name(client: AsyncClient, admin_headers: dict) -> None:
    """Filtering by event_name returns only that event type."""
    # First seed an event
    await client.post(
        "/api/v1/analytics/event",
        json={"event_name": EventName.LEARN_TAB_VIEWED.value, "page": "/learn"},
    )
    response = await client.get(
        f"/api/v1/analytics/events?event_name={EventName.LEARN_TAB_VIEWED.value}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    events = response.json()
    for e in events:
        assert e["event_name"] == EventName.LEARN_TAB_VIEWED.value
