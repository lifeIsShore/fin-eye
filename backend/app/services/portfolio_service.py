"""
app/services/portfolio_service.py

Fixed: uses async SQLAlchemy (select + await) instead of sync db.query().
Sprint 13: symbol_gas_breakdown added — per-symbol GAS scores for the
           portfolio detail page banner widget.
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
    Also returns symbol_gas_breakdown for the per-symbol GAS bar chart.
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
            "symbol_gas_breakdown": [],
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

    # ── 1. Weighted Average GAS + per-symbol breakdown ────────────────────────
    # Prefer GAS snapshots (fast, pre-computed); fall back to live technical consensus
    from app.services.gas_precompute import get_snapshot_cached  # noqa: PLC0415

    weighted_gas = 0.0
    symbol_gas_breakdown = []
    for item in normalized:
        sym = item["symbol"]
        gas_score: float = 50.0  # neutral default
        try:
            snap = await get_snapshot_cached(sym, db)
            if snap is not None:
                raw = snap.get("gas_score") if isinstance(snap, dict) else getattr(snap, "gas_score", None)
                if raw is not None:
                    gas_score = float(raw)
                else:
                    raise ValueError("no score in snapshot")
            else:
                raise ValueError("no snapshot found")
        except Exception:
            # Fallback: live technical consensus (slower but always works)
            try:
                consensus = compute_technical_consensus(sym)
                gas_score = float(consensus.get("consensus_score", 50.0))
            except Exception as exc2:
                logger.warning("GAS skipped for %s: %s", sym, exc2)

        weighted_gas += gas_score * item["weight"]
        symbol_gas_breakdown.append({
            "symbol":    sym,
            "gas_score": round(gas_score, 1),
            "weight_pct": round(item["weight"] * 100, 1),
        })

    # Sort breakdown by weight descending so the biggest positions show first
    symbol_gas_breakdown.sort(key=lambda r: r["weight_pct"], reverse=True)

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
        "weighted_gas":        round(weighted_gas, 2),
        "symbol_gas_breakdown": symbol_gas_breakdown,
        "sector_breakdown":    {k: round(v, 2) for k, v in sector_breakdown.items()},
        "diversification_score": round(div_score, 2),
    }
