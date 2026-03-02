from sqlalchemy.orm import Session
import logging

from app.services.macro_data import MacroFetcher
from app.services.market_data import OHLCVFetcher
from app.crud.macro import upsert_macro_data

logger = logging.getLogger(__name__)

async def refresh_all_macro_indicators(db: Session):
    """
    Orchestrates the fetching of all macro indicators and saves them to the database.
    This should be run periodically (e.g., daily via a background task).
    """
    logger.info("Starting refresh of all macro indicators")
    
    macro_fetcher = MacroFetcher()
    
    # 1. Fetch FRED Indicators
    try:
        fed_funds = await macro_fetcher.fetch_fed_funds_rate()
        if fed_funds:
            upsert_macro_data(db, fed_funds)
    except Exception as e:
        logger.error(f"Failed to refresh FEDFUNDS: {e}")

    try:
        unrate = await macro_fetcher.fetch_unemployment_rate()
        if unrate:
            upsert_macro_data(db, unrate)
    except Exception as e:
        logger.error(f"Failed to refresh UNRATE: {e}")
        
    try:
        yield_spread = await macro_fetcher.fetch_yield_spread()
        if yield_spread:
            upsert_macro_data(db, yield_spread)
    except Exception as e:
        logger.error(f"Failed to refresh T10Y2Y: {e}")
        
    try:
        cpi_yoy = await macro_fetcher.fetch_cpi_yoy()
        if cpi_yoy:
            upsert_macro_data(db, cpi_yoy)
    except Exception as e:
        logger.error(f"Failed to refresh CPI YoY: {e}")
        
    # 2. Fetch Market Indicators (VIX)
    # OHLCVFetcher.fetch_vix is synchronous
    try:
        vix = OHLCVFetcher.fetch_vix()
        if vix:
            upsert_macro_data(db, vix)
    except Exception as e:
        logger.error(f"Failed to refresh VIX: {e}")
        
    logger.info("Finished refreshing all macro indicators")
