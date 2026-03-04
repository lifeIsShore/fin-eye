import praw
import os
from typing import List, Tuple
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.schemas.sentiment_models import SentimentComment, SentimentSummary

class RedditService:
    def __init__(self):
        # We need reddit API credentials. For MVP testing, if not present, we can mock it
        # or require them in .env
        client_id = os.getenv("REDDIT_CLIENT_ID", "mock_id")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", "mock_secret")
        user_agent = os.getenv("REDDIT_USER_AGENT", "FinEye:v1.0 (by u/mockuser)")
        
        self.analyzer = SentimentIntensityAnalyzer()
        self.subreddits = ["stocks", "wallstreetbets", "investing"]
        
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            # Check if read_only works (it might fail if credentials are invalid)
            _ = self.reddit.read_only
        except Exception:
            self.reddit = None
            
    def _analyze_sentiment(self, text: str) -> Tuple[float, str]:
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        # Determine label based on typical vader threshold
        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"
            
        return compound, label
            
    def fetch_recent_mentions(self, ticker: str, limit: int = 50) -> List[SentimentComment]:
        """
        Fetches recent posts/comments mentioning the ticker across target subreddits.
        For simplicity, this example searches the subreddits for the ticker.
        """
        comments = []
        if not self.reddit or self.reddit.config.client_id == "mock_id":
            # Return mock data if no real reddit API configured
            return self._get_mock_data(ticker)
            
        query = f"${ticker} OR {ticker}"
        
        for sub_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                # Search submissions
                for submission in subreddit.search(query, sort='new', time_filter='month', limit=limit//len(self.subreddits)):
                    score, label = self._analyze_sentiment(submission.title + " " + submission.selftext)
                    created_dt = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    
                    comments.append(SentimentComment(
                        subreddit=sub_name,
                        timestamp=created_dt,
                        text=submission.title, # Keeping title for brevity
                        sentiment_score=score,
                        sentiment_label=label,
                        upvotes=submission.score,
                        url=f"https://reddit.com{submission.permalink}"
                    ))
            except Exception as e:
                print(f"Error fetching from r/{sub_name}: {e}")
                
        # Sort by most recent
        comments.sort(key=lambda x: x.timestamp, reverse=True)
        return comments
        
    def _get_mock_data(self, ticker: str) -> List[SentimentComment]:
        """Provide some mock data for UI testing if Reddit API isn't set up yet."""
        now = datetime.now(timezone.utc)
        return [
            SentimentComment(
                subreddit="wallstreetbets",
                timestamp=now,
                text=f"{ticker} to the moooooon!! Calls are printing.",
                sentiment_score=0.8,
                sentiment_label="Positive",
                upvotes=150,
                url="https://reddit.com/r/mock"
            ),
            SentimentComment(
                subreddit="stocks",
                timestamp=now,
                text=f"Is {ticker} overvalued right now? P/E seems high.",
                sentiment_score=-0.2,
                sentiment_label="Negative",
                upvotes=25,
                url="https://reddit.com/r/mock"
            ),
            SentimentComment(
                subreddit="investing",
                timestamp=now,
                text=f"{ticker} earnings call was somewhat neutral.",
                sentiment_score=0.0,
                sentiment_label="Neutral",
                upvotes=10,
                url="https://reddit.com/r/mock"
            )
        ]
        
    def get_sentiment_summary(self, ticker: str) -> Tuple[SentimentSummary, List[SentimentComment], List[SentimentComment]]:
        mentions = self.fetch_recent_mentions(ticker)
        
        if not mentions:
            return SentimentSummary(
                total_mentions=0,
                percent_positive=0,
                percent_neutral=0,
                percent_negative=0,
                retail_sentiment_score=50.0 # Neutral default
            ), [], []
            
        total = len(mentions)
        pos = sum(1 for m in mentions if m.sentiment_label == "Positive")
        neg = sum(1 for m in mentions if m.sentiment_label == "Negative")
        neu = total - pos - neg
        
        # Score 0-100: 50 is neutral. 
        # Average compound score ranges from -1 to 1. 
        # Map (-1, 1) to (0, 100)
        avg_compound = sum(m.sentiment_score for m in mentions) / total
        retail_score = (avg_compound + 1.0) * 50.0
        
        summary = SentimentSummary(
            total_mentions=total,
            percent_positive=(pos / total) * 100,
            percent_neutral=(neu / total) * 100,
            percent_negative=(neg / total) * 100,
            retail_sentiment_score=round(retail_score, 1)
        )
        
        # Top 5 by upvotes, separated
        bullish = [m for m in mentions if m.sentiment_label == "Positive"]
        bearish = [m for m in mentions if m.sentiment_label == "Negative"]
        
        bullish.sort(key=lambda x: x.upvotes, reverse=True)
        bearish.sort(key=lambda x: x.upvotes, reverse=True)
        
        return summary, bullish[:5], bearish[:5]
