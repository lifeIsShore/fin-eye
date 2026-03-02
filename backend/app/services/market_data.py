import yfinance as yf
import pandas as pd
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.schemas.data_models import OHLCVData, MacroData

logger = logging.getLogger(__name__)

class OHLCVFetcher:
    """Service to fetch historical OHLCV data from Yahoo Finance."""
    
    @staticmethod
    def fetch_historical_data(symbol: str, period: str = "1y", interval: str = "1d") -> List[OHLCVData]:
        """
        Fetch historical data for a given symbol.
        
        Args:
            symbol (str): Ticker symbol (e.g., 'AAPL', 'MSFT')
            period (str): Data period to download (e.g., '1mo', '1y', '5y')
            interval (str): Data interval (e.g., '1d', '1wk', '1mo')
            
        Returns:
            List[OHLCVData]: List of validated OHLCV records
        """
        logger.info(f"Fetching {period} of {interval} data for {symbol}")
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"No data found for {symbol}")
                return []
                
            results = []
            for index, row in hist.iterrows():
                try:
                    # Yahoo Finance usually returns naive datetime or timezone-aware depending on format
                    # Ensure timestamp can be parsed by Pydantic
                    timestamp = index.to_pydatetime() if isinstance(index, pd.Timestamp) else index
                    
                    data_point = OHLCVData(
                        symbol=symbol,
                        timestamp=timestamp, # type: ignore
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=float(row['Volume'])
                    )
                    results.append(data_point)
                except Exception as e:
                    logger.error(f"Error parsing row for {symbol} at {index}: {e}")
                    continue
                    
            logger.info(f"Successfully fetched {len(results)} records for {symbol}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return []

    @staticmethod
    def fetch_vix(period: str = "1mo") -> List[MacroData]:
        """
        Fetch VIX data and return it as MacroData.
        """
        logger.info(f"Fetching {period} of VIX data")
        try:
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period=period, interval="1d")
            
            if hist.empty:
                logger.warning("No data found for ^VIX")
                return []
                
            results = []
            for index, row in hist.iterrows():
                try:
                    date_obj = index.date() if hasattr(index, 'date') else index
                    
                    data_point = MacroData(
                        indicator_name="vix",
                        value=float(row['Close']),
                        date=date_obj
                    )
                    results.append(data_point)
                except Exception as e:
                    logger.error(f"Error parsing row for ^VIX at {index}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(results)} records for VIX")
            return results
        except Exception as e:
            logger.error(f"Failed to fetch VIX data: {e}")
            return []

