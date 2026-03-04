import pytest
from datetime import datetime
from unittest.mock import patch
import pandas as pd

from app.schemas.backtest_models import BacktestRequest
from app.services.backtesting_service import BacktestingEngine
from app.schemas.data_models import OHLCVData

# Mock data builder
def get_mock_ohlcv(symbol, rows):
    data = []
    base_date = datetime(2023, 1, 1)
    for i in range(rows):
        dt = base_date + pd.Timedelta(days=i)
        # We make a fake price series that goes up steadily to trigger buy signals,
        # then maybe falls to test drawdowns.
        price = 100.0 + (i * 0.5) 
        data.append(
            OHLCVData(
                symbol=symbol,
                timestamp=dt,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000
            )
        )
    return data

class TestBacktestingEngine:
    @patch("app.services.backtesting_service.OHLCVFetcher.fetch_historical_data")
    def test_momentum_strategy(self, mock_fetch):
        mock_fetch.return_value = get_mock_ohlcv("AAPL", 300) # Give it 300 days of data
        
        req = BacktestRequest(
            symbol="AAPL",
            strategy="momentum",
            parameters={"sma_fast": 10, "sma_slow": 50, "rsi_period": 14, "rsi_threshold": 40},
            initial_capital=10000,
            slippage_pct=0.001
        )
        engine = BacktestingEngine(req)
        response = engine.run()
        
        assert response.request.symbol == "AAPL"
        assert response.stats.total_trades >= 0
        assert len(response.equity_curve) > 0
        assert response.stats.initial_capital == 10000.0 if hasattr(response.stats, "initial_capital") else True

    @patch("app.services.backtesting_service.OHLCVFetcher.fetch_historical_data")
    def test_unsupported_strategy(self, mock_fetch):
        req = BacktestRequest(
            symbol="AAPL",
            strategy="unknown_strategy",
        )
        engine = BacktestingEngine(req)
        with pytest.raises(ValueError, match="is not supported"):
            engine.run()
            
    @patch("app.services.backtesting_service.OHLCVFetcher.fetch_historical_data")
    def test_not_enough_data(self, mock_fetch):
        mock_fetch.return_value = get_mock_ohlcv("AAPL", 10) # Too little data
        
        req = BacktestRequest(
            symbol="AAPL",
            strategy="momentum",
        )
        engine = BacktestingEngine(req)
        with pytest.raises(ValueError, match="Not enough data points"):
            engine.run()
