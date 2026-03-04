import pytest
from datetime import datetime, timezone
from app.services.reddit_service import RedditService

def test_reddit_service_mock_data():
    service = RedditService()
    
    # We force the client_id to be "mock_id" to test the mock data retrieval
    if service.reddit:
        service.reddit.config.client_id = "mock_id"
        
    summary, top_bullish, top_bearish = service.get_sentiment_summary("AAPL")
    
    # We know the mock data has 3 items: 1 pos, 1 neg, 1 neu
    assert summary.total_mentions == 3
    assert summary.percent_positive == pytest.approx(33.33, 0.1)
    assert summary.percent_negative == pytest.approx(33.33, 0.1)
    assert summary.percent_neutral == pytest.approx(33.33, 0.1)
    
    # Check top bullish contains 1 item (the positive one)
    assert len(top_bullish) == 1
    assert top_bullish[0].sentiment_label == "Positive"
    assert top_bullish[0].upvotes == 150
    
    # Check top bearish contains 1 item (the negative one)
    assert len(top_bearish) == 1
    assert top_bearish[0].sentiment_label == "Negative"
    assert top_bearish[0].upvotes == 25

def test_sentiment_analyzer():
    service = RedditService()
    
    score, label = service._analyze_sentiment("This is the best stock ever! Huge gains coming.")
    assert label == "Positive"
    assert score > 0.05
    
    score, label = service._analyze_sentiment("Terrible earnings report. Sell everything.")
    assert label == "Negative"
    assert score < -0.05
    
    score, label = service._analyze_sentiment("The stock is trading sideways today.")
    assert label == "Neutral"
    assert -0.05 <= score <= 0.05
