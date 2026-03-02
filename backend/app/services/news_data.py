import httpx
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import pytz

from app.config import settings
from app.schemas.data_models import NewsData

logger = logging.getLogger(__name__)

class NewsFetcher:
    """Service to fetch recent news using Finnhub API."""
    
    BASE_URL = "https://finnhub.io/api/v1/company-news"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.finnhub_api_key
        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("Finnhub API key not configured or set to default.")
            
    async def fetch_recent_news(self, symbol: str, days_back: int = 7) -> List[NewsData]:
        """
        Fetch news for a symbol over the last N days.
        
        Args:
            symbol (str): Ticker symbol
            days_back (int): Number of days back to look
            
        Returns:
            List[NewsData]: Validated news records
        """
        if not self.api_key or self.api_key == "your_key_here":
            logger.error("Cannot fetch Finnhub data without a valid API key.")
            return []
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Finnhub requires YYYY-MM-DD
        _from = start_date.strftime("%Y-%m-%d")
        _to = end_date.strftime("%Y-%m-%d")
        
        params = {
            "symbol": symbol,
            "from": _from,
            "to": _to,
            "token": self.api_key
        }
        
        logger.info(f"Fetching news for {symbol} from {_from} to {_to}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
            results = []
            # data is a list of news items
            for item in data:
                try:
                    # datetime is Unix timestamp
                    published_at = datetime.fromtimestamp(item.get("datetime"), tz=pytz.UTC)
                    
                    # Sentiment score is not provided directly by Finnhub basic news API,
                    # we would typically calculate it later or use a different endpoint.
                    
                    news_point = NewsData(
                        symbol=symbol,
                        title=item.get("headline", ""),
                        source=item.get("source", ""),
                        published_at=published_at,
                        sentiment_score=None # Placeholder until sentiment analysis is implemented
                    )
                    results.append(news_point)
                except Exception as e:
                    logger.error(f"Error parsing news item for {symbol}: {e}")
                    continue
                    
            logger.info(f"Successfully fetched {len(results)} news records for {symbol}")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error fetching news for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            return []
