"""
tests/services/test_stocktwits.py
Tests for StockTwitsService — covers happy path, 422 (unknown ticker),
timeout, and the mock fallback.  All HTTP calls are mocked with httpx.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.services.stocktwits_service import StockTwitsService


def _make_response(status_code: int, json_data: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception(f"HTTP {status_code}")
    )
    return resp


_SAMPLE_MESSAGES = {
    "messages": [
        {
            "body": "AAPL to the moon! Loading up.",
            "created_at": "2025-01-01T12:00:00Z",
            "likes": {"total": 20},
            "user": {"username": "bull_trader"},
            "entities": {"sentiment": {"basic": "Bullish"}},
        },
        {
            "body": "I think AAPL is overvalued here.",
            "created_at": "2025-01-01T11:00:00Z",
            "likes": {"total": 5},
            "user": {"username": "bear_watcher"},
            "entities": {"sentiment": {"basic": "Bearish"}},
        },
        {
            "body": "Watching AAPL. No position.",
            "created_at": "2025-01-01T10:00:00Z",
            "likes": {"total": 1},
            "user": {"username": "neutral_watcher"},
            "entities": {"sentiment": None},
        },
    ]
}


@pytest.mark.asyncio
async def test_fetch_messages_happy_path():
    svc = StockTwitsService()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_c = AsyncMock()
        mock_c.__aenter__ = AsyncMock(return_value=mock_c)
        mock_c.__aexit__ = AsyncMock(return_value=False)
        mock_c.get = AsyncMock(return_value=_make_response(200, _SAMPLE_MESSAGES))
        mock_cls.return_value = mock_c
        comments = await svc.fetch_messages("AAPL")

    assert len(comments) == 3
    labels = {c.sentiment_label for c in comments}
    assert "Positive" in labels
    assert "Negative" in labels
    bullish = next(c for c in comments if c.sentiment_label == "Positive")
    assert bullish.upvotes == 20


@pytest.mark.asyncio
async def test_fetch_messages_422_returns_mock():
    svc = StockTwitsService()
    mock_resp = _make_response(422, {})
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_c = AsyncMock()
        mock_c.__aenter__ = AsyncMock(return_value=mock_c)
        mock_c.__aexit__ = AsyncMock(return_value=False)
        mock_c.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_c
        comments = await svc.fetch_messages("XXXXXX")
    assert len(comments) >= 1


@pytest.mark.asyncio
async def test_fetch_messages_timeout_returns_mock():
    import httpx
    svc = StockTwitsService()
    with patch("httpx.AsyncClient") as mock_cls:
        mock_c = AsyncMock()
        mock_c.__aenter__ = AsyncMock(return_value=mock_c)
        mock_c.__aexit__ = AsyncMock(return_value=False)
        mock_c.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_cls.return_value = mock_c
        comments = await svc.fetch_messages("TSLA")
    assert len(comments) >= 1


@pytest.mark.asyncio
async def test_get_sentiment_summary_scoring():
    svc = StockTwitsService()
    now = datetime.now(timezone.utc)
    from app.schemas.sentiment_models import SentimentComment
    with patch.object(svc, "fetch_messages", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [
            SentimentComment(subreddit="@a", timestamp=now, text="bull", sentiment_score=0.7, sentiment_label="Positive", upvotes=10, url=""),
            SentimentComment(subreddit="@b", timestamp=now, text="bull2", sentiment_score=0.7, sentiment_label="Positive", upvotes=5, url=""),
            SentimentComment(subreddit="@c", timestamp=now, text="bear", sentiment_score=-0.7, sentiment_label="Negative", upvotes=2, url=""),
            SentimentComment(subreddit="@d", timestamp=now, text="neutral", sentiment_score=0.0, sentiment_label="Neutral", upvotes=1, url=""),
        ]
        summary, top_bullish, top_bearish = await svc.get_sentiment_summary_async("AAPL")

    assert summary.total_mentions == 4
    assert summary.percent_positive == 50.0
    assert abs(summary.retail_sentiment_score - 66.7) < 0.2
    assert len(top_bullish) == 2
    assert top_bullish[0].upvotes >= top_bullish[-1].upvotes


@pytest.mark.asyncio
async def test_get_sentiment_summary_empty_is_neutral():
    svc = StockTwitsService()
    with patch.object(svc, "fetch_messages", new_callable=AsyncMock, return_value=[]):
        summary, bullish, bearish = await svc.get_sentiment_summary_async("ZZZZ")
    assert summary.retail_sentiment_score == 50.0
    assert summary.total_mentions == 0
    assert bullish == []
    assert bearish == []
