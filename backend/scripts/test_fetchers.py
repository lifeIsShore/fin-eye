import asyncio
import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.market_data import OHLCVFetcher
from app.services.macro_data import MacroFetcher
from app.services.news_data import NewsFetcher
from app.config import settings

async def main():
    print("--- Testing OHLCV Fetcher ---")
    ohlcv_data = OHLCVFetcher.fetch_historical_data("AAPL", period="5d", interval="1d")
    for data in ohlcv_data:
        print(f"AAPL: {data.timestamp.date()} - Close: {data.close:.2f}")

    print("\n--- Testing Macro Fetcher ---")
    if settings.fred_api_key and settings.fred_api_key != "your_key_here":
        macro_fetcher = MacroFetcher()
        macro_data = await macro_fetcher.fetch_series(
            series_id="FEDFUNDS", 
            indicator_name="Fed Funds Rate", 
            observation_start="2023-01-01"
        )
        # Print first 3 and last 3
        if macro_data:
            print(f"Found {len(macro_data)} FEDFUNDS records.")
            for data in macro_data[:3]:
                print(f"{data.date}: {data.value}%")
            if len(macro_data) > 3:
                print("...")
                for data in macro_data[-3:]:
                    print(f"{data.date}: {data.value}%")
    else:
        print("Skipping FRED test: API key not configured")

    print("\n--- Testing News Fetcher ---")
    if settings.finnhub_api_key and settings.finnhub_api_key != "your_key_here":
        news_fetcher = NewsFetcher()
        news_data = await news_fetcher.fetch_recent_news("AAPL", days_back=3)
        if news_data:
            print(f"Found {len(news_data)} news articles for AAPL.")
            for data in news_data[:3]:
                print(f"[{data.published_at.strftime('%Y-%m-%d %H:%M')}] {data.title[:50]}...")
    else:
        print("Skipping Finnhub test: API key not configured")

if __name__ == "__main__":
    asyncio.run(main())
