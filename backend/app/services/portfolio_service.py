"""
app/services/portfolio_service.py

Fixed: uses async SQLAlchemy (select + await) instead of sync db.query().
"""
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.portfolio import Portfolio
from app.services.technical_service import compute_technical_consensus
from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)
fetcher = OHLCVFetcher()


async def calculate_portfolio_analysis(db: AsyncSession, portfolio_id: int) -> Dict[str, Any]:
    """
    Calculates the 3 core portfolio metrics:
      - Weighted Average GAS (Technical Consensus)
      - Sector Breakdown
      - Diversification Score (0-100 based on inter-asset correlation)
    """
    # ── Load portfolio with items eagerly ────────────────────────────────────
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.items))
        .where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio or not portfolio.items:
        return {
            "weighted_gas": 0,
            "sector_breakdown": {},
            "diversification_score": 0,
            "error": "Portfolio is empty or does not exist.",
        }

    items = portfolio.items

    # Normalise weights so they always sum to 1.0
    total_weight = sum(item.weight for item in items)
    if total_weight == 0:
        return {"error": "Portfolio weights sum to 0."}

    normalized = [
        {"symbol": item.symbol, "weight": item.weight / total_weight}
        for item in items
    ]

    tickers = [n["symbol"] for n in normalized]

    # ── 1. Weighted Average GAS ──────────────────────────────────────────────
    weighted_gas = 0.0
    for item in normalized:
        try:
            consensus = compute_technical_consensus(item["symbol"])
            weighted_gas += consensus["consensus_score"] * item["weight"]
        except Exception as exc:
            logger.warning("GAS skipped for %s: %s", item["symbol"], exc)

    # ── 2. Sector Breakdown ──────────────────────────────────────────────────
    sector_breakdown: Dict[str, float] = {}
    for item in normalized:
        try:
            info = yf.Ticker(item["symbol"]).info
            sector = info.get("sector") or "Unknown"
            sector_breakdown[sector] = sector_breakdown.get(sector, 0.0) + item["weight"] * 100
        except Exception as exc:
            logger.warning("Sector lookup failed for %s: %s", item["symbol"], exc)

    # ── 3. Diversification Score ─────────────────────────────────────────────
    div_score = 0.0
    if len(tickers) > 1:
        try:
            price_data: Dict[str, pd.Series] = {}
            for symbol in tickers:
                try:
                    records = OHLCVFetcher.fetch_historical_data(symbol, period="6mo", interval="1d")
                    if records:
                        closes = pd.Series(
                            {r.timestamp: r.close for r in records},
                            name=symbol,
                        ).sort_index()
                        price_data[symbol] = closes.pct_change()
                except Exception:
                    pass

            if len(price_data) > 1:
                combined = pd.DataFrame(price_data).dropna()
                if not combined.empty:
                    corr = combined.corr()
                    idx = np.triu_indices_from(corr.values, k=1)
                    correlations = corr.values[idx]
                    if len(correlations) > 0:
                        avg_corr = float(np.nanmean(correlations))
                        div_score = ((1 - avg_corr) / 2) * 100
        except Exception as exc:
            logger.warning("Diversification score failed: %s", exc)

    return {
        "weighted_gas": round(weighted_gas, 2),
        "sector_breakdown": {k: round(v, 2) for k, v in sector_breakdown.items()},
        "diversification_score": round(div_score, 2),
    }
