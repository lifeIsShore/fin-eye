import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from httpx import AsyncClient

from app.models.sentiment import SentimentAggregate, NewsArticle


@pytest.mark.asyncio
@patch("app.services.sentiment_service.FinBERTSentimentAnalyzer.score_text")
async def test_get_news_sentiment_timeseries_success(
    mock_score_text,
    client: AsyncClient,
    test_app,
    test_db,
):
    # FinBERT always returns 0.5 (positive) in this test
    mock_score_text.return_value = 0.5

    # Seed some existing aggregates to avoid relying entirely on Finnhub
    today = date.today()
    agg = SentimentAggregate(
        symbol="AAPL",
        date=today,
        mentions=2,
        sentiment_score=0.5,
        source_type="news",
    )
    test_db.add(agg)

    # Seed a recent article
    article = NewsArticle(
        symbol="AAPL",
        title="Apple launches new product",
        source="TestSource",
        published_at=datetime.now() - timedelta(hours=1),
        sentiment_score=0.5,
    )
    test_db.add(article)
    test_db.commit()

    # Mock Finnhub HTTP call so we do not hit the network
    with patch("app.services.news_data.httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = await client.get("/api/v1/sentiment/AAPL/timeseries")

    assert response.status_code == 200
    payload = response.json()

    assert payload["symbol"] == "AAPL"
    assert isinstance(payload["series"], list)
    assert len(payload["series"]) >= 1

    # Check window averages are present (may be None if no data in window)
    assert "sentiment_1d" in payload
    assert "sentiment_7d" in payload
    assert "sentiment_30d" in payload

    # Articles list should include our seeded article
    assert len(payload["articles"]) >= 1
    titles = [a["title"] for a in payload["articles"]]
    assert "Apple launches new product" in titles

