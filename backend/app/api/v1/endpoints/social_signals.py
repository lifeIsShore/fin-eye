"""
app/api/v1/endpoints/social_signals.py
───────────────────────────────────────────────────────────────────────────────
Sprint 42 — Social Signals combined endpoint

GET /api/v1/sentiment/{symbol}/social

Combines Reddit mentions/sentiment, StockTwits bull/bear ratio,
and insider net sentiment into a single response for the
SocialSignalsPanel frontend component.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Response DTOs ───────────────────────────────────────────────────────────

class RedditSignalDto(BaseModel):
    mentions: int
    sentiment_score: float       # -1..1
    sentiment_label: str         # Positive / Neutral / Negative
    bullish_pct: float
    bearish_pct: float
    subreddits: list[str]

class StockTwitsSignalDto(BaseModel):
    total_messages: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    bullish_pct: float
    bearish_pct: float
    bull_bear_ratio: Optional[float]
    sentiment_label: str         # Very Bullish / Bullish / Neutral / Bearish / Very Bearish

class InsiderSignalDto(BaseModel):
    sentiment_score: float       # 0-100
    sentiment_label: str         # Bullish / Neutral / Bearish
    buy_transactions: int
    sell_transactions: int
    net_shares: float
    lookback_days: int

class SocialSignalsResponse(BaseModel):
    symbol: str
    reddit: Optional[RedditSignalDto]
    stocktwits: Optional[StockTwitsSignalDto]
    insider: Optional[InsiderSignalDto]
    composite_score: float       # 0-100 (50 = neutral)
    composite_label: str         # Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish
    disclaimer: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe_reddit(ticker: str) -> Optional[dict]:
    """Fetch Reddit sentiment (sync) and return raw data or None."""
    try:
        from app.services.reddit_service import RedditService
        svc = RedditService()
        summary, bullish, bearish = svc.get_sentiment_summary(ticker)
        return {
            "mentions": summary.total_mentions,
            "sentiment_score": round(
                (summary.retail_sentiment_score - 50) / 50, 2
            ),  # 0-100 → -1..1
            "sentiment_label": (
                "Positive" if summary.retail_sentiment_score > 60
                else "Negative" if summary.retail_sentiment_score < 40
                else "Neutral"
            ),
            "bullish_pct": summary.percent_positive,
            "bearish_pct": summary.percent_negative,
            "subreddits": ["stocks", "wallstreetbets", "investing", "de", "aktien"],
        }
    except Exception as exc:
        logger.debug("Reddit social signal failed for %s: %s", ticker, exc)
        return None


def _safe_insider(symbol: str) -> Optional[dict]:
    """Fetch insider sentiment (sync) and return summary data or None."""
    try:
        from app.services.insider_service import analyse_insiders
        analysis = analyse_insiders(symbol)
        return {
            "sentiment_score": analysis.sentiment.score,
            "sentiment_label": analysis.sentiment.label,
            "buy_transactions": analysis.sentiment.buy_transactions,
            "sell_transactions": analysis.sentiment.sell_transactions,
            "net_shares": analysis.sentiment.net_shares,
            "lookback_days": analysis.sentiment.lookback_days,
        }
    except Exception as exc:
        logger.debug("Insider social signal failed for %s: %s", symbol, exc)
        return None


async def _safe_stocktwits(ticker: str) -> Optional[dict]:
    """Fetch StockTwits snapshot and return summary data or None."""
    try:
        from app.services.stocktwits_service import StockTwitsService
        svc = StockTwitsService()
        summary, bullish, bearish = await svc.get_sentiment_summary_async(ticker)
        total = summary.total_mentions
        pos = round(summary.percent_positive / 100 * total) if total else 0
        neg = round(summary.percent_negative / 100 * total) if total else 0
        neu = total - pos - neg

        labeled = pos + neg
        bb_ratio = round(pos / neg, 2) if neg > 0 else None

        if labeled == 0:
            label = "Neutral"
        else:
            bp = pos / labeled * 100
            if bp >= 75:
                label = "Very Bullish"
            elif bp >= 60:
                label = "Bullish"
            elif bp >= 40:
                label = "Neutral"
            elif bp >= 25:
                label = "Bearish"
            else:
                label = "Very Bearish"

        return {
            "total_messages": total,
            "bullish_count": pos,
            "bearish_count": neg,
            "neutral_count": neu,
            "bullish_pct": summary.percent_positive,
            "bearish_pct": summary.percent_negative,
            "bull_bear_ratio": bb_ratio,
            "sentiment_label": label,
        }
    except Exception as exc:
        logger.debug("StockTwits social signal failed for %s: %s", ticker, exc)
        return None


def _compute_composite(
    reddit: Optional[dict],
    stocktwits: Optional[dict],
    insider: Optional[dict],
) -> tuple[float, str]:
    """
    Blend all three social signals into one 0-100 composite.
    Weights: StockTwits 40%, Reddit 30%, Insider 30%.
    """
    scores = []
    weights = []

    if stocktwits and stocktwits["total_messages"] > 0:
        labeled = stocktwits["bullish_count"] + stocktwits["bearish_count"]
        if labeled > 0:
            twits_score = (stocktwits["bullish_count"] / labeled) * 100
            scores.append(twits_score)
            weights.append(0.40)

    if reddit and reddit["mentions"] > 0:
        # retail_sentiment_score is already 0-100 via mapping
        reddit_score = (reddit["sentiment_score"] + 1.0) * 50.0
        scores.append(reddit_score)
        weights.append(0.30)

    if insider:
        scores.append(insider["sentiment_score"])
        weights.append(0.30)

    if not scores:
        return 50.0, "Insufficient Data"

    total_w = sum(weights)
    composite = sum(s * w for s, w in zip(scores, weights)) / total_w
    composite = round(max(5.0, min(95.0, composite)), 1)

    if composite >= 72:
        label = "Strong Bullish"
    elif composite >= 58:
        label = "Bullish"
    elif composite >= 42:
        label = "Neutral"
    elif composite >= 28:
        label = "Bearish"
    else:
        label = "Strong Bearish"

    return composite, label


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.get(
    "/{symbol}/social",
    response_model=SocialSignalsResponse,
    summary="Combined social signals — Reddit + StockTwits + Insider sentiment",
)
async def get_social_signals(
    symbol: str,
    response: Response,
) -> SocialSignalsResponse:
    """
    Aggregate social sentiment from three sources:

    - **Reddit**: mentions + VADER sentiment across r/stocks, r/wallstreetbets, etc.
    - **StockTwits**: bullish/bearish message ratio from the last ~30 messages.
    - **Insider**: SEC EDGAR Form 4 buy/sell score over 180 days.

    Returns a composite score (0-100) and per-source breakdowns.
    """
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"

    sym = symbol.upper()
    loop = asyncio.get_running_loop()

    # Fetch all three in parallel
    reddit_task = loop.run_in_executor(None, _safe_reddit, sym)
    insider_task = loop.run_in_executor(None, _safe_insider, sym)
    stocktwits_task = _safe_stocktwits(sym)

    reddit_data, insider_data, stocktwits_data = await asyncio.gather(
        reddit_task, insider_task, stocktwits_task,
        return_exceptions=True,
    )

    # Handle exceptions gracefully
    if isinstance(reddit_data, Exception):
        reddit_data = None
    if isinstance(insider_data, Exception):
        insider_data = None
    if isinstance(stocktwits_data, Exception):
        stocktwits_data = None

    composite_score, composite_label = _compute_composite(
        reddit_data, stocktwits_data, insider_data,
    )

    return SocialSignalsResponse(
        symbol=sym,
        reddit=RedditSignalDto(**reddit_data) if reddit_data else None,
        stocktwits=StockTwitsSignalDto(**stocktwits_data) if stocktwits_data else None,
        insider=InsiderSignalDto(**insider_data) if insider_data else None,
        composite_score=composite_score,
        composite_label=composite_label,
        disclaimer=(
            "Social sentiment data is derived from public sources (Reddit, StockTwits, "
            "SEC EDGAR). Retail sentiment is not predictive and should not be used as "
            "the sole basis for investment decisions."
        ),
    )
