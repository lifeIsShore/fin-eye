from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
from app.services.reddit_service import RedditService

router = APIRouter()


@router.get(
    "/{symbol}/timeseries",
    response_model=SentimentTimeseriesResponse,
)
async def get_news_sentiment_timeseries(
    symbol: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Return 30-day news sentiment timeseries and current 1d/7d/30d averages
    for the requested symbol, along with a list of recent articles.
    """
    symbol = symbol.upper()
    service = SentimentService(db=db)

    # Refresh underlying data on-demand for MVP
    await service.refresh_symbol_sentiment(symbol=symbol, days_back=30)

    aggregates = service.get_aggregated_sentiment(symbol=symbol, days=30)
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
    articles_stmt = (
        db.query(NewsArticle)
        .filter(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc())
        .limit(150)
    )
    article_rows = articles_stmt.all()
    articles = [
        NewsData(
            symbol=row.symbol,
            title=row.title,
            source=row.source,
            published_at=row.published_at,
            sentiment_score=row.sentiment_score,
        )
        for row in article_rows
    ]

    if not series and not articles:
        raise HTTPException(
            status_code=404,
            detail=f"No news sentiment data available for symbol {symbol}",
        )

    return SentimentTimeseriesResponse(
        symbol=symbol,
        series=series,
        sentiment_1d=window_avgs.get("1d"),
        sentiment_7d=window_avgs.get("7d"),
        sentiment_30d=window_avgs.get("30d"),
        articles=articles,
    )


@router.get(
    "/{symbol}/sources",
    response_model=SentimentSourceBreakdownResponse,
)
async def get_news_sentiment_sources(
    symbol: str,
    days: int = 30,
    db: Session = Depends(get_db),
) -> Any:
    """
    Return per-source positive/negative/neutral article counts over the last
    `days` days for the requested symbol.
    """
    symbol = symbol.upper()
    service = SentimentService(db=db)

    # Ensure we have reasonably fresh news data
    await service.refresh_symbol_sentiment(symbol=symbol, days_back=days)

    breakdown_map = service.get_source_breakdown(symbol=symbol, days=days)
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
    Get recent retail sentiment from Reddit for a specific ticker.
    Returns aggregated stats and top bullish/bearish comments.
    """
    ticker = ticker.upper()
    try:
        reddit_service = RedditService()
        summary, top_bullish, top_bearish = reddit_service.get_sentiment_summary(ticker)
        
        return SentimentResponse(
            ticker=ticker,
            summary=summary,
            top_bullish=top_bullish,
            top_bearish=top_bearish
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
