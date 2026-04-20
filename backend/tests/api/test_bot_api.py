"""
tests/api/test_bot_api.py
Sprint 57 — Paper Trading Bot API tests
"""
import uuid
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


# ── Shared mock user ──────────────────────────────────────────────────────────

class _FakeUser:
    id = uuid.uuid4()
    email = "test@fin-eye.app"
    username = "testuser"
    is_verified = True
    is_admin = False
    subscription_tier = "pro"


FAKE_USER = _FakeUser()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_auth(test_app):
    from app.api.v1.deps import get_current_active_verified_user
    test_app.dependency_overrides[get_current_active_verified_user] = lambda: FAKE_USER
    yield
    test_app.dependency_overrides.pop(get_current_active_verified_user, None)


# ── GET /bot/config ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_config_creates_default(client: AsyncClient):
    """First call creates a default BotConfig row and returns it."""
    response = await client.get("/api/v1/bot/config")
    assert response.status_code == 200
    data = response.json()
    assert data["is_enabled"] is False
    assert data["halt_flag"] is False
    assert data["strategy"] == "balanced"
    assert data["portfolio_value"] == 10000.0


@pytest.mark.asyncio
async def test_get_config_idempotent(client: AsyncClient):
    """Calling GET /config twice returns the same config (no duplicate rows)."""
    r1 = await client.get("/api/v1/bot/config")
    r2 = await client.get("/api/v1/bot/config")
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["strategy"] == r2.json()["strategy"]


# ── PATCH /bot/config ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_config_updates_fields(client: AsyncClient):
    await client.get("/api/v1/bot/config")  # ensure config exists
    response = await client.patch(
        "/api/v1/bot/config",
        json={"strategy": "aggressive", "portfolio_value": 25000.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "aggressive"
    assert data["portfolio_value"] == 25000.0


@pytest.mark.asyncio
async def test_patch_config_rejects_invalid_position_pct(client: AsyncClient):
    """max_position_pct > 0.25 must be rejected with 422."""
    response = await client.patch("/api/v1/bot/config", json={"max_position_pct": 0.99})
    assert response.status_code == 422


# ── POST /bot/enable ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enable_bot_requires_watchlist(client: AsyncClient):
    """Should 422 when the user has no watchlist items."""
    response = await client.post("/api/v1/bot/enable")
    assert response.status_code == 422
    assert "watchlist" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_enable_bot_succeeds_with_watchlist(client: AsyncClient, test_db):
    from app.models.watchlist import WatchlistItem
    test_db.add(WatchlistItem(user_id=FAKE_USER.id, symbol="AAPL"))
    await test_db.commit()

    response = await client.post("/api/v1/bot/enable")
    assert response.status_code == 204

    cfg = await client.get("/api/v1/bot/config")
    assert cfg.json()["is_enabled"] is True
    assert cfg.json()["halt_flag"] is False


# ── POST /bot/disable ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disable_bot(client: AsyncClient, test_db):
    from app.models.watchlist import WatchlistItem
    test_db.add(WatchlistItem(user_id=FAKE_USER.id, symbol="AAPL"))
    await test_db.commit()
    await client.post("/api/v1/bot/enable")

    response = await client.post("/api/v1/bot/disable")
    assert response.status_code == 204

    cfg = await client.get("/api/v1/bot/config")
    assert cfg.json()["is_enabled"] is False


# ── POST /bot/halt + /bot/resume ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_halt_and_resume(client: AsyncClient):
    await client.get("/api/v1/bot/config")  # ensure config exists
    halt_r = await client.post("/api/v1/bot/halt", json={"close_all": False})
    assert halt_r.status_code == 204
    assert (await client.get("/api/v1/bot/config")).json()["halt_flag"] is True

    resume_r = await client.post("/api/v1/bot/resume")
    assert resume_r.status_code == 204
    assert (await client.get("/api/v1/bot/config")).json()["halt_flag"] is False


# ── GET /bot/audit-log ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_populated_after_actions(client: AsyncClient):
    await client.get("/api/v1/bot/config")
    await client.post("/api/v1/bot/halt", json={"close_all": False})
    await client.post("/api/v1/bot/resume")

    response = await client.get("/api/v1/bot/audit-log")
    assert response.status_code == 200
    actions = [e["action"] for e in response.json()]
    assert "HALT" in actions
    assert "RESUME" in actions


@pytest.mark.asyncio
async def test_audit_log_symbol_filter(client: AsyncClient):
    response = await client.get("/api/v1/bot/audit-log?symbol=NVDA")
    assert response.status_code == 200
    # Any returned entries must match the filter symbol (or have null symbol from non-symbol actions)
    for entry in response.json():
        assert entry["symbol"] == "NVDA" or entry["symbol"] is None


# ── GET /bot/positions ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_positions_empty_by_default(client: AsyncClient):
    response = await client.get("/api/v1/bot/positions")
    assert response.status_code == 200
    assert response.json() == []


# ── GET /bot/performance ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_performance_returns_structure(client: AsyncClient):
    with patch(
        "app.api.v1.endpoints.bot.get_bot_performance",
        new_callable=AsyncMock,
        return_value={
            "total_pnl_usd": 0.0, "total_pnl_pct": 0.0, "win_rate_pct": 0.0,
            "total_trades": 0, "open_positions": 0,
            "best_trade_pct": None, "worst_trade_pct": None,
        },
    ):
        response = await client.get("/api/v1/bot/performance")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl_usd" in data
    assert "win_rate_pct" in data
