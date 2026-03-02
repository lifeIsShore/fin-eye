import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, date
import pandas as pd

from app.services.market_data import OHLCVFetcher
from app.services.macro_data import MacroFetcher
from app.services.news_data import NewsFetcher

# OHLCVFetcher Tests
@patch('app.services.market_data.yf.Ticker')
def test_ohlcv_fetcher_success(mock_ticker):
    # Mocking dataframe returned by history()
    mock_df = pd.DataFrame({
        'Open': [150.0],
        'High': [155.0],
        'Low': [149.0],
        'Close': [154.0],
        'Volume': [1000000.0]
    }, index=[pd.Timestamp('2023-10-01')])
    
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_instance
    
    results = OHLCVFetcher.fetch_historical_data("AAPL", period="1d", interval="1d")
    
    assert len(results) == 1
    assert results[0].symbol == "AAPL"
    assert results[0].open == 150.0
    assert results[0].close == 154.0

@patch('app.services.market_data.yf.Ticker')
def test_ohlcv_fetcher_empty(mock_ticker):
    mock_df = pd.DataFrame()
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_instance
    
    results = OHLCVFetcher.fetch_historical_data("INVALID", period="1d")
    assert len(results) == 0


# MacroFetcher Tests
@pytest.mark.asyncio
@patch('app.services.macro_data.httpx.AsyncClient.get')
async def test_macro_fetcher_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "observations": [
            {"date": "2023-10-01", "value": "5.25"},
            {"date": "2023-10-02", "value": "."} # Missing data point
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    fetcher = MacroFetcher(api_key="test_key")
    results = await fetcher.fetch_series("FEDFUNDS", "fed_funds_rate", "2023-10-01")
    
    assert len(results) == 1
    assert results[0].indicator_name == "fed_funds_rate"
    assert results[0].value == 5.25
    assert results[0].date == date(2023, 10, 1)

@pytest.mark.asyncio
async def test_macro_fetcher_no_key():
    fetcher = MacroFetcher(api_key="your_key_here")
    results = await fetcher.fetch_series("FEDFUNDS", "fed_funds_rate", "2023-10-01")
    assert len(results) == 0


# NewsFetcher Tests
@pytest.mark.asyncio
@patch('app.services.news_data.httpx.AsyncClient.get')
async def test_news_fetcher_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "datetime": 1696118400, # 2023-10-01
            "headline": "Apple announces new product",
            "source": "Reuters"
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    fetcher = NewsFetcher(api_key="test_key")
    results = await fetcher.fetch_recent_news("AAPL", days_back=1)
    
    assert len(results) == 1
    assert results[0].symbol == "AAPL"
    assert results[0].title == "Apple announces new product"
    assert results[0].source == "Reuters"

@pytest.mark.asyncio
async def test_news_fetcher_no_key():
    fetcher = NewsFetcher(api_key="your_key_here")
    results = await fetcher.fetch_recent_news("AAPL", days_back=1)
    assert len(results) == 0
