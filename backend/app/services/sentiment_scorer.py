"""
app/services/sentiment_scorer.py
==================================
FinBERT-based sentiment scorer (todos-v4.md Phase 5.2).

Provides a lazy-loaded singleton that scores news headlines using
ProsusAI/finbert. Falls back to VADER if the model isn't available
(no transformers installed, no GPU, etc.).

Usage
-----
    from app.services.sentiment_scorer import get_sentiment_scorer

    scorer = get_sentiment_scorer()
    results = scorer.score_batch(["Apple beats earnings", "Market crash fears"])
    # [{"label": "bullish", "score": 0.94}, {"label": "bearish", "score": 0.87}]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

FINBERT_MODEL = "ProsusAI/finbert"
BATCH_SIZE    = 64


@dataclass
class SentimentResult:
    label: str          # 'bullish', 'bearish', 'neutral'
    score: float        # confidence 0-1
    vader_compound: Optional[float] = None  # VADER fallback, -1 to +1


class FinBERTScorer:
    """
    Singleton wrapper around ProsusAI/finbert.
    Lazy-loads the model on first call — no startup overhead.
    """

    def __init__(self) -> None:
        self._pipeline = None

    def _load(self) -> bool:
        """Load model once. Returns True on success."""
        if self._pipeline is not None:
            return True
        try:
            from transformers import pipeline  # noqa: PLC0415
            self._pipeline = pipeline(
                "text-classification",
                model=FINBERT_MODEL,
                tokenizer=FINBERT_MODEL,
                # Use top_k=None so we get all three class probabilities
                top_k=1,
                truncation=True,
                max_length=512,
            )
            logger.info("FinBERT model loaded: %s", FINBERT_MODEL)
            return True
        except Exception as exc:
            logger.warning(
                "FinBERT unavailable (%s) — falling back to VADER for sentiment scoring. "
                "Install with: pip install transformers torch",
                exc,
            )
            return False

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        """
        Score a batch of texts.  Returns one SentimentResult per text.
        If FinBERT is unavailable, uses VADER compound score remapped to labels.
        """
        if not texts:
            return []

        if self._load():
            return self._finbert_batch(texts)
        return self._vader_batch(texts)

    def score_single(self, text: str) -> SentimentResult:
        return self.score_batch([text])[0]

    # ── private helpers ───────────────────────────────────────────────────────

    def _finbert_batch(self, texts: list[str]) -> list[SentimentResult]:
        results: list[SentimentResult] = []
        for i in range(0, len(texts), BATCH_SIZE):
            chunk = texts[i: i + BATCH_SIZE]
            try:
                preds = self._pipeline(chunk)  # type: ignore[misc]
                for pred in preds:
                    # pipeline returns list of lists when top_k=1
                    p = pred[0] if isinstance(pred, list) else pred
                    raw_label = p["label"].lower()
                    # FinBERT labels: 'positive', 'negative', 'neutral'
                    label = (
                        "bullish" if raw_label == "positive"
                        else "bearish" if raw_label == "negative"
                        else "neutral"
                    )
                    results.append(SentimentResult(label=label, score=round(p["score"], 4)))
            except Exception as exc:
                logger.error("FinBERT batch scoring failed: %s", exc)
                # Fall back to VADER for this chunk
                results.extend(self._vader_batch(chunk))
        return results

    def _vader_batch(self, texts: list[str]) -> list[SentimentResult]:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # noqa: PLC0415
            sia = SentimentIntensityAnalyzer()
            results: list[SentimentResult] = []
            for text in texts:
                compound = sia.polarity_scores(text)["compound"]
                if compound >= 0.05:
                    label = "bullish"
                elif compound <= -0.05:
                    label = "bearish"
                else:
                    label = "neutral"
                results.append(
                    SentimentResult(
                        label=label,
                        score=abs(compound),
                        vader_compound=round(compound, 4),
                    )
                )
            return results
        except Exception as exc:
            logger.error("VADER batch scoring failed: %s", exc)
            # Last resort: return neutral for all
            return [SentimentResult(label="neutral", score=0.0) for _ in texts]


# ── Module-level singleton ────────────────────────────────────────────────────

_scorer: Optional[FinBERTScorer] = None


def get_sentiment_scorer() -> FinBERTScorer:
    global _scorer
    if _scorer is None:
        _scorer = FinBERTScorer()
    return _scorer
