import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_run_backtest_endpoint(client: AsyncClient, monkeypatch):
    # Mock the engine since we just want to test the API layer
    from app.schemas.backtest_models import BacktestResponse, BacktestStats, BacktestRequest, EquityPoint
    
    req = BacktestRequest(symbol="TSLA", strategy="momentum")
    mock_response = BacktestResponse(
        request=req,
        stats=BacktestStats(
            total_return_pct=15.0,
            annualized_return_pct=10.0,
            max_drawdown_pct=-5.0,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            win_rate_pct=55.0,
            profit_factor=1.8,
            total_trades=10
        ),
        equity_curve=[EquityPoint(date="2023-01-01", equity=10000.0)]
    )
    
    def mock_run(self):
        return mock_response
        
    monkeypatch.setattr("app.api.v1.endpoints.backtesting.BacktestingEngine.run", mock_run)
    
    response = await client.post(
        "/api/v1/backtest",
        json={"symbol": "TSLA", "strategy": "momentum"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["request"]["symbol"] == "TSLA"
    assert data["stats"]["total_return_pct"] == 15.0

@pytest.mark.asyncio
async def test_run_backtest_invalid_strategy(client: AsyncClient, monkeypatch):
    # Let the real engine raise a ValueError for validation
    response = await client.post(
        "/api/v1/backtest",
        json={"symbol": "TSLA", "strategy": "fake_strat"}
    )
    
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]
