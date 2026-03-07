"""
app/api/v1/endpoints/insiders.py
───────────────────────────────────────────────────────────────────────────────
EXP-INSID-01 — Insider Trading Intelligence endpoints

Routes:
  GET /insiders/{symbol}           — full analysis (all recent transactions + score)
  GET /insiders/{symbol}/summary   — headline card (sentiment score + buy/sell counts)
  GET /insiders/{symbol}/recent    — latest N transactions (default 20)

All routes:
  - No auth required
  - CPU-bound httpx fetching offloaded to thread pool
  - 1-hour in-process cache inside insider_service
  - SEC User-Agent header is set in insider_service ("Fin-Eye/1.0 contact@fin-eye.com")
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.services.insider_service import (
    InsiderAnalysis,
    InsiderSentiment,
    InsiderTransaction,
    analyse_insiders,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response Schemas ────────────────────────────────────────────────────────

class InsiderSentimentDto(BaseModel):
    score: float
    label: str
    buy_transactions: int
    sell_transactions: int
    buy_shares: float
    sell_shares: float
    buy_value: Optional[float]
    sell_value: Optional[float]
    net_shares: float
    net_value: Optional[float]
    lookback_days: int


class InsiderTransactionDto(BaseModel):
    filing_date: str
    transaction_date: str
    insider_name: str
    insider_title: str
    transaction_type: str
    transaction_type_label: str
    shares: float
    price_per_share: Optional[float]
    total_value: Optional[float]
    shares_after: Optional[float]
    ownership_type: str
    is_buy: bool
    is_sell: bool
    accession_number: str


class InsiderAnalysisDto(BaseModel):
    symbol: str
    company_name: str
    cik: str
    sentiment: InsiderSentimentDto
    transactions: List[InsiderTransactionDto]
    total_filings_found: int
    disclaimer: str


class InsiderSummaryDto(BaseModel):
    symbol: str
    company_name: str
    sentiment_score: float
    sentiment_label: str
    buy_transactions: int
    sell_transactions: int
    net_shares: float
    net_value: Optional[float]
    lookback_days: int
    disclaimer: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _sentiment_to_dto(s: InsiderSentiment) -> InsiderSentimentDto:
    return InsiderSentimentDto(
        score=s.score,
        label=s.label,
        buy_transactions=s.buy_transactions,
        sell_transactions=s.sell_transactions,
        buy_shares=s.buy_shares,
        sell_shares=s.sell_shares,
        buy_value=s.buy_value,
        sell_value=s.sell_value,
        net_shares=s.net_shares,
        net_value=s.net_value,
        lookback_days=s.lookback_days,
    )


def _txn_to_dto(t: InsiderTransaction) -> InsiderTransactionDto:
    from app.services.insider_service import _is_buy, _is_sell
    return InsiderTransactionDto(
        filing_date=t.filing_date,
        transaction_date=t.transaction_date,
        insider_name=t.insider_name,
        insider_title=t.insider_title,
        transaction_type=t.transaction_type,
        transaction_type_label=t.transaction_type_label,
        shares=t.shares,
        price_per_share=t.price_per_share,
        total_value=t.total_value,
        shares_after=t.shares_after,
        ownership_type=t.ownership_type,
        is_buy=_is_buy(t.transaction_type),
        is_sell=_is_sell(t.transaction_type),
        accession_number=t.accession_number,
    )


def _analysis_to_dto(a: InsiderAnalysis) -> InsiderAnalysisDto:
    return InsiderAnalysisDto(
        symbol=a.symbol,
        company_name=a.company_name,
        cik=a.cik,
        sentiment=_sentiment_to_dto(a.sentiment),
        transactions=[_txn_to_dto(t) for t in a.transactions],
        total_filings_found=a.total_filings_found,
        disclaimer=a.disclaimer,
    )


async def _fetch(symbol: str) -> InsiderAnalysis:
    """Run synchronous insider analysis in the thread pool."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, analyse_insiders, symbol.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Insider analysis failed for %s: %s", symbol, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Insider data temporarily unavailable for {symbol}: {exc}",
        ) from exc


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}",
    response_model=InsiderAnalysisDto,
    summary="Full insider activity analysis — sentiment score + transaction history",
)
async def get_insider_analysis(symbol: str) -> InsiderAnalysisDto:
    """
    Returns full insider trading analysis for a US-listed symbol including:

    - **Insider Sentiment Score** (0–100): derived from the buy/sell balance
      of open-market transactions in the past 180 days, weighted by dollar value.
    - **Transaction history**: up to 50 most recent Form 4 transactions (purchases,
      sales, awards, option exercises) with insider name, title, shares, and price.
    - **Buy/sell summary**: aggregate shares and dollar value bought vs sold.

    Data is sourced from SEC EDGAR Form 4 filings. Form 4 must be filed within
    2 business days of a transaction. Results are cached for 1 hour.

    Only US-exchange-listed securities with SEC filings are supported.
    """
    analysis = await _fetch(symbol)
    return _analysis_to_dto(analysis)


@router.get(
    "/{symbol}/summary",
    response_model=InsiderSummaryDto,
    summary="Lightweight insider sentiment card for dashboard integration",
)
async def get_insider_summary(symbol: str) -> InsiderSummaryDto:
    """
    Returns just the headline insider sentiment signal — ideal for embedding
    in the main dashboard without loading the full transaction list.
    """
    analysis = await _fetch(symbol)
    return InsiderSummaryDto(
        symbol=analysis.symbol,
        company_name=analysis.company_name,
        sentiment_score=analysis.sentiment.score,
        sentiment_label=analysis.sentiment.label,
        buy_transactions=analysis.sentiment.buy_transactions,
        sell_transactions=analysis.sentiment.sell_transactions,
        net_shares=analysis.sentiment.net_shares,
        net_value=analysis.sentiment.net_value,
        lookback_days=analysis.sentiment.lookback_days,
        disclaimer=analysis.disclaimer,
    )


@router.get(
    "/{symbol}/recent",
    response_model=List[InsiderTransactionDto],
    summary="Most recent insider transactions (default 20, max 50)",
)
async def get_recent_transactions(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=50, description="Number of transactions to return"),
) -> List[InsiderTransactionDto]:
    """
    Returns the N most recent Form 4 transactions for the symbol,
    sorted newest first. Useful for building a compact activity feed.
    """
    analysis = await _fetch(symbol)
    return [_txn_to_dto(t) for t in analysis.transactions[:limit]]
