"""
tests/api/test_alerts_api.py
API-level tests for CORE-NOTIF-01 alert endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.models.alert import Alert
from app.schemas.alert_models import AlertCreate
from datetime import datetime


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_alert(id=1, symbol="AAPL", alert_type="price_above", threshold=200.0,
                is_active=True, triggered_at=None, triggered_value=None):
    a = Alert()
    a.id = id
    a.symbol = symbol
    a.alert_type = alert_type
    a.threshold = threshold
    a.delivery_channel = "in_app"
    a.is_active = is_active
    a.triggered_at = triggered_at
    a.triggered_value = triggered_value
    a.created_at = datetime(2026, 3, 5, 12, 0, 0)
    return a


# ── Create ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, monkeypatch):
    alert = _make_alert()
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.create_alert",
        AsyncMock(return_value=alert),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.post("/api/v1/alerts", json={
        "symbol": "AAPL",
        "alert_type": "price_above",
        "threshold": 200.0,
        "delivery_channel": "in_app",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["alert_type"] == "price_above"
    assert data["threshold"] == 200.0


@pytest.mark.asyncio
async def test_create_alert_invalid_type(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())
    resp = await client.post("/api/v1/alerts", json={
        "symbol": "AAPL",
        "alert_type": "bad_type",
        "threshold": 100.0,
    })
    assert resp.status_code == 422  # Pydantic validation error


# ── List ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient, monkeypatch):
    alerts = [_make_alert(id=1), _make_alert(id=2, symbol="TSLA", alert_type="price_below", threshold=150.0)]
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.list_alerts",
        AsyncMock(return_value=alerts),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["alerts"][0]["symbol"] == "AAPL"
    assert data["alerts"][1]["symbol"] == "TSLA"


# ── Delete ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_alert(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.delete_alert",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.delete("/api/v1/alerts/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_alert(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.delete_alert",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.delete("/api/v1/alerts/999")
    assert resp.status_code == 404


# ── Triggered poll ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_triggered_alerts(client: AsyncClient, monkeypatch):
    fired = _make_alert(
        id=3, symbol="AAPL", alert_type="price_above", threshold=190.0,
        triggered_at=datetime(2026, 3, 5, 13, 0, 0), triggered_value=195.5,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.get_triggered_alerts",
        AsyncMock(return_value=[fired]),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/alerts/triggered")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["symbol"] == "AAPL"
    assert "rose above" in items[0]["message"]
    assert items[0]["triggered_value"] == 195.5


# ── Acknowledge ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ack_alert(client: AsyncClient, monkeypatch):
    dismissed = _make_alert(id=3, is_active=False)
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.acknowledge_alert",
        AsyncMock(return_value=dismissed),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.post("/api/v1/alerts/3/ack")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_ack_nonexistent_alert(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.alerts.acknowledge_alert",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr("app.api.v1.endpoints.alerts.get_current_user", AsyncMock())

    resp = await client.post("/api/v1/alerts/999/ack")
    assert resp.status_code == 404
