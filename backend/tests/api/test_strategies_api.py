"""
tests/api/test_strategies_api.py
API-level tests for P2-STRAT-01 Strategy Library.
"""
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from datetime import datetime

from app.models.strategy import SavedStrategy


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_strategy(
    id=1,
    name="My Momentum",
    symbol="AAPL",
    is_public=False,
    sharpe=0.95,
    user_id="00000000-0000-0000-0000-000000000001",
):
    s = SavedStrategy()
    s.id = id
    s.user_id = user_id
    s.name = name
    s.description = "Test strategy"
    s.request_snapshot = {
        "symbol": symbol,
        "strategy": "momentum",
        "parameters": {"sma_fast": 10, "sma_slow": 50},
        "initial_capital": 10000.0,
        "slippage_pct": 0.001,
        "start_date": None,
        "end_date": None,
    }
    s.total_return_pct = 32.5
    s.annualized_return_pct = 9.1
    s.sharpe_ratio = sharpe
    s.max_drawdown_pct = -14.2
    s.win_rate_pct = 57.3
    s.total_trades = 38
    s.is_public = is_public
    s.created_at = datetime(2026, 3, 5, 10, 0, 0)
    s.updated_at = None
    return s


# ── Save ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_strategy(client: AsyncClient, monkeypatch):
    strat = _make_strategy()
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.save_strategy",
        AsyncMock(return_value=strat),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.post("/api/v1/strategies", json={
        "name": "My Momentum",
        "symbol": "AAPL",
        "strategy": "momentum",
        "parameters": {"sma_fast": 10, "sma_slow": 50},
        "initial_capital": 10000,
        "sharpe_ratio": 0.95,
        "total_return_pct": 32.5,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Momentum"
    assert data["symbol"] == "AAPL"
    assert data["sharpe_ratio"] == 0.95


# ── List mine ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_my_strategies(client: AsyncClient, monkeypatch):
    strats = [_make_strategy(id=1), _make_strategy(id=2, name="RSI Swing", symbol="TSLA")]
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.list_my_strategies",
        AsyncMock(return_value=strats),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/strategies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["strategies"][1]["symbol"] == "TSLA"


# ── Public leaderboard ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_public_strategies(client: AsyncClient, monkeypatch):
    pub = [_make_strategy(id=3, is_public=True, sharpe=1.1)]
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.list_public_strategies",
        AsyncMock(return_value=pub),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/strategies/public")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["strategies"][0]["is_public"] is True


# ── Get one ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_strategy(client: AsyncClient, monkeypatch):
    strat = _make_strategy(id=1)
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.get_strategy",
        AsyncMock(return_value=strat),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/strategies/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


@pytest.mark.asyncio
async def test_get_strategy_not_found(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.get_strategy",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.get("/api/v1/strategies/999")
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_strategy(client: AsyncClient, monkeypatch):
    updated = _make_strategy(id=1, name="Renamed", is_public=True)
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.update_strategy",
        AsyncMock(return_value=updated),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.patch("/api/v1/strategies/1", json={"name": "Renamed", "is_public": True})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["is_public"] is True


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_strategy(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.delete_strategy",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.delete("/api/v1/strategies/1")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_strategy_not_found(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.strategies.delete_strategy",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr("app.api.v1.endpoints.strategies.get_current_user", AsyncMock())

    resp = await client.delete("/api/v1/strategies/999")
    assert resp.status_code == 404
