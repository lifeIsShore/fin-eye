"""
tests/api/test_montecarlo_api.py
Sprint 57 — Monte Carlo simulation API tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


# ── /asset endpoint ───────────────────────────────────────────────────────────

ASSET_PAYLOAD = {
    "symbol": "AAPL",
    "starting_value": 10000.0,
    "mu": 0.10,
    "sigma": 0.18,
    "years": 1.0,
    "paths": 100,
    "steps_per_year": 252,
    "model_type": "GBM",
}

MOCK_ASSET_RESULT = {
    "symbol": "AAPL",
    "paths": 100,
    "years": 1.0,
    "percentiles": {"p5": 8500.0, "p25": 9200.0, "p50": 10100.0, "p75": 11000.0, "p95": 13000.0},
    "cvar_95": 8200.0,
    "prob_profit": 0.62,
    "final_values": [10100.0] * 100,
}

MOCK_PORTFOLIO_RESULT = {
    "paths": 100,
    "years": 1.0,
    "percentiles": {"p5": 8000.0, "p25": 9000.0, "p50": 10000.0, "p75": 11000.0, "p95": 12500.0},
    "cvar_95": 7800.0,
    "prob_profit": 0.60,
    "success_rate": None,
    "final_values": [10000.0] * 100,
}


@pytest.mark.asyncio
async def test_asset_mc_returns_result(client: AsyncClient):
    with patch(
        "app.api.v1.endpoints.montecarlo.run_asset_simulation",
        return_value=MagicMock(**MOCK_ASSET_RESULT),
    ):
        response = await client.post("/api/v1/montecarlo/asset", json=ASSET_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "percentiles" in data
    assert "cvar_95" in data


@pytest.mark.asyncio
async def test_asset_mc_rejects_too_many_paths(client: AsyncClient):
    payload = {**ASSET_PAYLOAD, "paths": 99999}
    response = await client.post("/api/v1/montecarlo/asset", json=payload)
    assert response.status_code == 400
    assert "50000" in response.json()["detail"]


@pytest.mark.asyncio
async def test_asset_mc_rejects_too_many_steps(client: AsyncClient):
    payload = {**ASSET_PAYLOAD, "years": 20.0, "steps_per_year": 252}
    response = await client.post("/api/v1/montecarlo/asset", json=payload)
    assert response.status_code == 400
    assert "3650" in response.json()["detail"]


# ── /portfolio endpoint ───────────────────────────────────────────────────────

PORTFOLIO_PAYLOAD = {
    "assets": [
        {"symbol": "AAPL", "weight": 0.6, "mu": 0.10, "sigma": 0.18},
        {"symbol": "TLT",  "weight": 0.4, "mu": 0.04, "sigma": 0.08},
    ],
    "starting_value": 10000.0,
    "years": 1.0,
    "paths": 100,
    "steps_per_year": 12,
}


@pytest.mark.asyncio
async def test_portfolio_mc_returns_result(client: AsyncClient):
    with patch(
        "app.api.v1.endpoints.montecarlo.run_portfolio_simulation",
        return_value=MagicMock(**MOCK_PORTFOLIO_RESULT),
    ):
        response = await client.post("/api/v1/montecarlo/portfolio", json=PORTFOLIO_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "percentiles" in data
    assert "prob_profit" in data


@pytest.mark.asyncio
async def test_portfolio_mc_rejects_too_many_assets(client: AsyncClient):
    assets = [
        {"symbol": f"SYM{i}", "weight": 1 / 51, "mu": 0.08, "sigma": 0.15}
        for i in range(51)
    ]
    payload = {**PORTFOLIO_PAYLOAD, "assets": assets}
    response = await client.post("/api/v1/montecarlo/portfolio", json=payload)
    assert response.status_code == 400
    assert "50" in response.json()["detail"]


# ── /vol-estimate endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vol_estimate_insufficient_data(client: AsyncClient):
    """Returns 404 when fewer than 30 OHLCV rows exist for the symbol."""
    response = await client.get("/api/v1/montecarlo/vol-estimate?symbol=FAKEXYZ")
    assert response.status_code == 404
    assert "Insufficient" in response.json()["detail"]


@pytest.mark.asyncio
async def test_vol_estimate_returns_metrics(client: AsyncClient, test_db):
    """With enough OHLCV rows, returns sigma/mu/data_days."""
    from datetime import date, timedelta as td
    from app.models.market import OHLCVDaily

    base_price = 150.0
    for i in range(60):
        test_db.add(OHLCVDaily(
            symbol="TESTV",
            trade_date=date(2024, 1, 1) + td(days=i),
            open=base_price,
            high=base_price * 1.01,
            low=base_price * 0.99,
            close=base_price + i * 0.10,
            adj_close=base_price + i * 0.10,
            volume=1_000_000,
        ))
    await test_db.commit()

    response = await client.get("/api/v1/montecarlo/vol-estimate?symbol=TESTV&days=60")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TESTV"
    assert "annualized_vol_pct" in data
    assert "annualized_return_pct" in data
    assert data["data_days"] == 60


@pytest.mark.asyncio
async def test_vol_estimate_symbol_uppercased(client: AsyncClient):
    """Lowercase symbol should be normalised — still returns 404 for unknown, not 500."""
    response = await client.get("/api/v1/montecarlo/vol-estimate?symbol=aapl")
    # Either 404 (no data) or 200 — must not be 500
    assert response.status_code in (200, 404)
