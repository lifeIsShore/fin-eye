"""
app/services/macro_orchestrator.py
Orchestrates all FRED + VIX fetches and persists results.
Extended for P2-MACRO-ADV-01.

BUG FIX: VIX fetch now uses the correct OHLCVFetcher from market_data (which
has fetch_vix as a @staticmethod). The ohlcv_fetcher.OHLCVFetcher is a
different class for DB persistence — it does not have fetch_vix.

BUG FIX: nonfarm_payrolls raw level is now converted to MoM delta
(nonfarm_payrolls_mom) before upsert, since macro_scoring.py expects the
month-over-month change in thousands, not the raw level.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.macro import upsert_macro_data_async
from app.services.macro_data import MacroFetcher
# FIX: import from market_data (has fetch_vix) NOT ohlcv_fetcher (does not)
from app.services.market_data import OHLCVFetcher
from app.schemas.data_models import MacroData

logger = logging.getLogger(__name__)


def _compute_nfp_mom(records: list[MacroData]) -> list[MacroData]:
    """
    Convert raw NFP level records (nonfarm_payrolls) into MoM delta records
    (nonfarm_payrolls_mom) which is what macro_scoring.py expects.

    MoM = current_value - previous_month_value (in thousands of jobs).
    The first record has no prior month, so it is dropped.
    """
    if len(records) < 2:
        return []

    records_sorted = sorted(records, key=lambda r: r.date)
    mom_records = []
    for i in range(1, len(records_sorted)):
        curr = records_sorted[i]
        prev = records_sorted[i - 1]
        mom_value = round(curr.value - prev.value, 1)
        mom_records.append(MacroData(
            indicator_name="nonfarm_payrolls_mom",
            value=mom_value,
            date=curr.date,
        ))

    return mom_records


async def refresh_all_macro_indicators(db: AsyncSession) -> None:
    """
    Fetch every macro series and upsert into macro_indicators.
    Called by the scheduler and the manual POST /macro/refresh endpoint.
    """
    logger.info("Starting full macro data refresh")
    fetcher = MacroFetcher()

    fetch_jobs = {
        "fed_funds_rate":        fetcher.fetch_fed_funds_rate,
        "unemployment_rate":     fetcher.fetch_unemployment_rate,
        "yield_spread_10y_2y":   fetcher.fetch_yield_spread,
        "cpi_yoy":               fetcher.fetch_cpi_yoy,
        "treasury_2y":           fetcher.fetch_dgs2,
        "treasury_5y":           fetcher.fetch_dgs5,
        "treasury_10y":          fetcher.fetch_dgs10,
        "treasury_30y":          fetcher.fetch_dgs30,
        "recession_indicator":   fetcher.fetch_recession_indicator,
        "nonfarm_payrolls":      fetcher.fetch_nonfarm_payrolls,
        "industrial_production": fetcher.fetch_industrial_production,
    }

    for name, fetch_fn in fetch_jobs.items():
        try:
            records = await fetch_fn()
            if not records:
                continue

            # BUG FIX: NFP raw level must be converted to MoM delta before storing.
            # macro_scoring.py reads "nonfarm_payrolls_mom", not "nonfarm_payrolls".
            if name == "nonfarm_payrolls":
                mom_records = _compute_nfp_mom(records)
                if mom_records:
                    inserted = await upsert_macro_data_async(db, mom_records)
                    logger.info(
                        "  %-30s  fetched=%d  mom_records=%d  inserted=%d",
                        "nonfarm_payrolls_mom", len(records), len(mom_records), inserted,
                    )
                else:
                    logger.warning("  nonfarm_payrolls: not enough data for MoM computation")
                continue

            inserted = await upsert_macro_data_async(db, records)
            logger.info("  %-30s  fetched=%d  inserted=%d", name, len(records), inserted)

        except Exception as exc:
            logger.error("  FAILED %-28s: %s", name, exc)

    # BUG FIX: fetch_vix lives on market_data.OHLCVFetcher (correct import above).
    # ohlcv_fetcher.OHLCVFetcher is the DB-persistence class and has no fetch_vix.
    try:
        vix_records = OHLCVFetcher.fetch_vix()
        if vix_records:
            inserted = await upsert_macro_data_async(db, vix_records)
            logger.info("  %-30s  fetched=%d  inserted=%d", "vix", len(vix_records), inserted)
    except Exception as exc:
        logger.error("  FAILED vix: %s", exc)

    await db.commit()
    logger.info("Macro data refresh complete")
