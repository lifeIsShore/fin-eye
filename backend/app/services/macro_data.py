import httpx
from typing import List, Optional
import os
import logging
from datetime import datetime
from app.config import settings
from app.schemas.data_models import MacroData

logger = logging.getLogger(__name__)

class MacroFetcher:
    """Service to fetch macroeconomic data from FRED API."""
    
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.fred_api_key
        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("FRED API key not configured or set to default.")
            
    async def fetch_series(self, series_id: str, indicator_name: str, observation_start: str) -> List[MacroData]:
        """
        Fetch historical macroeconomic data for a given series.
        
        Args:
            series_id (str): FRED Series ID (e.g., 'FEDFUNDS', 'CPIAUCSL')
            indicator_name (str): The name to assign to the indicator in our DB
            observation_start (str): Start date in YYYY-MM-DD format
            
        Returns:
            List[MacroData]: List of validated macro data records
        """
        if not self.api_key or self.api_key == "your_key_here":
            logger.error("Cannot fetch FRED data without a valid API key.")
            return []
            
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": observation_start
        }
        
        logger.info(f"Fetching macro data for {indicator_name} ({series_id})")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
            observations = data.get("observations", [])
            results = []
            
            for obs in observations:
                try:
                    # Some values might be '.' indicating missing data
                    value_str = obs.get("value")
                    if value_str == ".":
                        continue
                        
                    date_obj = datetime.strptime(obs.get("date"), "%Y-%m-%d").date()
                    
                    data_point = MacroData(
                        indicator_name=indicator_name,
                        value=float(value_str),
                        date=date_obj
                    )
                    results.append(data_point)
                except Exception as e:
                    logger.error(f"Error parsing row for {indicator_name}: {e}")
                    continue
                    
            logger.info(f"Successfully fetched {len(results)} records for {indicator_name}")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error fetching data for {indicator_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch data for {indicator_name}: {e}")
            return []
