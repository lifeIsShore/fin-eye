import pytest
from datetime import datetime, timedelta

from httpx import AsyncClient

from app.models.sentiment import NewsArticle


@pytest.mark.asyncio
async def test_get_news_sentiment_sources_success(
    client: AsyncClient,
    test_app,
    test_db,
):
    # Seed a couple of articles for two sources with different sentiment
    now = datetime.utcnow()
    articles = [
        NewsArticle(
            symbol="AAPL",
            title="Positive story 1",
            source="Reuters",
            published_at=now - timedelta(days=1),
            sentiment_score=0.6,
        ),
        NewsArticle(
            symbol="AAPL",
            title="Negative story 1",
            source="Reuters",
            published_at=now - timedelta(days=1),
            sentiment_score=-0.7,
        ),
        NewsArticle(
            symbol="AAPL",
            title="Neutral story",
            source="Bloomberg",
            published_at=now - timedelta(days=2),
            sentiment_score=0.0,
        ),
    ]
    test_db.add_all(articles)
    test_db.commit()

    response = await client.get("/api/v1/sentiment/AAPL/sources?days=30")

    assert response.status_code == 200
    payload = response.json()

    assert payload["symbol"] == "AAPL"
    assert payload["days"] == 30
    assert isinstance(payload["breakdown"], list)
    assert len(payload["breakdown"]) >= 2

    by_source = {row["source"]: row for row in payload["breakdown"]}
    assert by_source["Reuters"]["positive"] >= 1
    assert by_source["Reuters"]["negative"] >= 1
    assert by_source["Bloomberg"]["neutral"] >= 1

