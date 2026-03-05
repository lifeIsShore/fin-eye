"""
app/services/macro_orchestrator.py
Orchestrates all FRED + VIX fetches and persists results.
Extended for P2-MACRO-ADV-01.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.macro import upsert_macro_data_async
from app.services.macro_data import MacroFetcher
from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)


async def refresh_all_macro_indicators(db: AsyncSession) -> None:
    """
    Fetch every macro series and upsert into macro_indicators.
    Called by the scheduler and the manual POST /macro/refresh endpoint.
    """
    logger.info("Starting full macro data refresh")
    fetcher = MacroFetcher()

    # Ordered dict — name used only for logging; the fetcher sets indicator_name internally
    fetch_jobs = {
        "fed_funds_rate":        fetcher.fetch_fed_funds_rate,
        "unemployment_rate":     fetcher.fetch_unemployment_rate,
        "yield_spread_10y_2y":   fetcher.fetch_yield_spread,
        "cpi_yoy":               fetcher.fetch_cpi_yoy,
        # Advanced yield curve
        "treasury_2y":           fetcher.fetch_dgs2,
        "treasury_5y":           fetcher.fetch_dgs5,
        "treasury_10y":          fetcher.fetch_dgs10,
        "treasury_30y":          fetcher.fetch_dgs30,
        # Recession & depth
        "recession_indicator":   fetcher.fetch_recession_indicator,
        "nonfarm_payrolls":      fetcher.fetch_nonfarm_payrolls,
        "industrial_production": fetcher.fetch_industrial_production,
    }

    for name, fetch_fn in fetch_jobs.items():
        try:
            records = await fetch_fn()
            if records:
                inserted = await upsert_macro_data_async(db, records)
                logger.info("  %-30s  fetched=%d  inserted=%d", name, len(records), inserted)
        except Exception as exc:
            logger.error("  FAILED %-28s: %s", name, exc)

    # VIX from Yahoo Finance (sync, wrapped here)
    try:
        vix_records = OHLCVFetcher.fetch_vix()
        if vix_records:
            inserted = await upsert_macro_data_async(db, vix_records)
            logger.info("  %-30s  fetched=%d  inserted=%d", "vix", len(vix_records), inserted)
    except Exception as exc:
        logger.error("  FAILED vix: %s", exc)

    await db.commit()
    logger.info("Macro data refresh complete")
