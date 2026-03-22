from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.schemas.data_models import (
    SentimentTimeseriesResponse,
    SentimentAggregateData,
    NewsData,
    SentimentSourceBreakdownResponse,
    SentimentSourceBreakdownEntry,
)
from app.models.sentiment import NewsArticle
from app.services.sentiment_service import SentimentService
from app.schemas.sentiment_models import SentimentResponse
from app.services.stocktwits_service import StockTwitsService

router = APIRouter()


@router.get(
    "/{symbol}/timeseries",
    response_model=SentimentTimeseriesResponse,
)
async def get_news_sentiment_timeseries(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return 30-day news sentiment timeseries and current 1d/7d/30d averages
    for the requested symbol, along with a list of recent articles.
    """
    symbol = symbol.upper()
    service = SentimentService(db=db)

    # Refresh underlying data on-demand for MVP
    await service.refresh_symbol_sentiment(symbol=symbol, days_back=30)

    aggregates = await service.get_aggregated_sentiment(symbol=symbol, days=30)
    window_avgs = service.compute_window_averages(aggregates)

    # Map aggregates to response DTO
    series = [
        SentimentAggregateData(
            date=agg.date,
            sentiment_score=agg.sentiment_score or 0.0,
            mentions=agg.mentions,
        )
        for agg in aggregates
    ]

    # Fetch recent articles (last 30 days) for context
    result = await db.execute(
        select(NewsArticle)
        .where(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc())
        .limit(150)
    )
    article_rows = result.scalars().all()
    articles = [
        NewsData(
            symbol=row.symbol,
            title=row.title,
            source=row.source,
            published_at=row.published_at,
            sentiment_score=row.sentiment_score,
            sentiment_label=getattr(row, "sentiment_label", None),  # Phase 5.1 FinBERT label
            finbert_score=getattr(row, "finbert_score", None),       # Phase 5.1 FinBERT confidence
            url=getattr(row, "url", None),                           # Phase 5.1 URL click-through
        )
        for row in article_rows
    ]

    if not series and not articles:
        raise HTTPException(
            status_code=404,
            detail=f"No news sentiment data available for symbol {symbol}",
        )

    # Sprint 11 (UX-TRUST-01) — derive fetched_at from most-recent article timestamp
    fetched_at: Optional[str] = None
    if article_rows:
        most_recent = max(article_rows, key=lambda r: r.published_at)
        fetched_at = most_recent.published_at.isoformat() + "Z"

    return SentimentTimeseriesResponse(
        symbol=symbol,
        series=series,
        sentiment_1d=window_avgs.get("1d"),
        sentiment_7d=window_avgs.get("7d"),
        sentiment_30d=window_avgs.get("30d"),
        articles=articles,
        fetched_at=fetched_at,
    )


@router.get(
    "/{symbol}/sources",
    response_model=SentimentSourceBreakdownResponse,
)
async def get_news_sentiment_sources(
    symbol: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return per-source positive/negative/neutral article counts over the last
    `days` days for the requested symbol.
    """
    symbol = symbol.upper()
    service = SentimentService(db=db)

    # Ensure we have reasonably fresh news data
    await service.refresh_symbol_sentiment(symbol=symbol, days_back=days)

    breakdown_map = await service.get_source_breakdown(symbol=symbol, days=days)
    if not breakdown_map:
        raise HTTPException(
            status_code=404,
            detail=f"No news sentiment source data available for symbol {symbol}",
        )

    breakdown_entries = [
        SentimentSourceBreakdownEntry(
            source=source,
            positive=counts["positive"],
            negative=counts["negative"],
            neutral=counts["neutral"],
        )
        for source, counts in sorted(
            breakdown_map.items(),
            key=lambda item: item[1]["positive"] + item[1]["negative"] + item[1]["neutral"],
            reverse=True,
        )
    ]

    return SentimentSourceBreakdownResponse(
        symbol=symbol,
        days=days,
        breakdown=breakdown_entries,
    )


@router.get(
    "/retail/{ticker}",
    response_model=SentimentResponse,
)
async def get_retail_sentiment(
    ticker: str
) -> Any:
    """
    Get recent retail sentiment from StockTwits for a specific ticker.
    """
    ticker = ticker.upper()
    try:
        svc = StockTwitsService()
        summary, top_bullish, top_bearish = await svc.get_sentiment_summary_async(ticker)
        return SentimentResponse(
            ticker=ticker,
            summary=summary,
            top_bullish=top_bullish,
            top_bearish=top_bearish,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
