"""
app/services/adv_sentiment_service.py
───────────────────────────────────────────────────────────────────────────────
P3-SENT-ADV-01 — Advanced Sentiment: Google Trends + StockTwits deep analysis

Data sources:
  1. pytrends (Google Trends) — free, no API key required.
     Returns interest-over-time (0–100 normalised) for a ticker keyword
     over the past 90 days, weekly granularity. Also returns top 5 related
     queries (rising) to surface narrative shifts.
  2. StockTwits — public free API, reuses existing StockTwitsService for
     the live message feed. Advanced layer adds: bullish/bearish ratio
     trend (computed from the single snapshot since StockTwits free tier
     has no historical endpoint), message velocity (msgs/hr estimate),
     top bullish/bearish messages ranked by likes.

Cache TTL:
  - Google Trends: 4 hours (pytrends has aggressive rate-limiting; we cache
    hard to avoid 429s)
  - StockTwits: 15 minutes (live feed, short window is acceptable)

No API key required for either source.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TRENDS_CACHE_TTL  = 14_400   # 4 hours
TWITS_CACHE_TTL   = 900      # 15 minutes
_TRENDS_CACHE: Dict[str, tuple] = {}
_TWITS_CACHE:  Dict[str, tuple] = {}


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class TrendPoint:
    """Single weekly Google Trends data point."""
    date: str           # ISO date (start of week)
    interest: int       # 0–100 normalised by Google


@dataclass
class RelatedQuery:
    query: str
    value: str          # "Breakout" or a % like "+250%"


@dataclass
class GoogleTrendsData:
    keyword: str
    timeframe: str      # e.g. "today 3-m"
    interest_over_time: List[TrendPoint]    # weekly, ~13 points for 90d
    rising_queries: List[RelatedQuery]
    avg_interest: float
    peak_interest: int
    recent_vs_avg: float    # last 4 weeks avg vs full-period avg (momentum)
    trend_direction: str    # "Rising" / "Falling" / "Stable" / "Insufficient data"


@dataclass
class StockTwitsMessage:
    username: str
    body: str
    sentiment: str      # "Bullish" / "Bearish" / "Neutral"
    likes: int
    created_at: str     # ISO datetime string


@dataclass
class StockTwitsSnapshot:
    symbol: str
    total_messages: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    bullish_pct: float
    bearish_pct: float
    bull_bear_ratio: Optional[float]     # bullish / bearish, None if no bearish
    sentiment_label: str                 # "Very Bullish" / "Bullish" / "Neutral" / "Bearish" / "Very Bearish"
    top_bullish: List[StockTwitsMessage]
    top_bearish: List[StockTwitsMessage]
    recent_messages: List[StockTwitsMessage]   # latest 10 regardless of sentiment


@dataclass
class AdvancedSentimentAnalysis:
    symbol: str
    google_trends: Optional[GoogleTrendsData]
    stocktwits: Optional[StockTwitsSnapshot]
    composite_score: float          # 0–100 (50 = neutral)
    composite_label: str            # "Strong Interest / Bullish" etc.
    disclaimer: str = (
        "Google Trends data reflects relative search interest (0–100) normalised to the "
        "peak in the selected period. StockTwits sentiment is self-reported by retail traders "
        "and reflects the last ~30 public messages. Neither source constitutes investment advice."
    )


# ─── Google Trends ────────────────────────────────────────────────────────────

def _fetch_google_trends(symbol: str) -> Optional[GoogleTrendsData]:
    """
    Fetch Google Trends interest-over-time for a stock ticker.
    Uses pytrends with 90-day window, weekly granularity.
    """
    now = time.time()
    if symbol in _TRENDS_CACHE:
        ts, cached = _TRENDS_CACHE[symbol]
        if now - ts < TRENDS_CACHE_TTL:
            return cached

    try:
        from pytrends.request import TrendReq  # lazy import — only needed here

        pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=2, backoff_factor=0.5)
        # Use "{TICKER} stock" as keyword for better signal over just ticker
        keyword = f"{symbol} stock"
        pt.build_payload([keyword], cat=0, timeframe="today 3-m", geo="", gprop="")

        # Interest over time
        iot_df = pt.interest_over_time()
        points: List[TrendPoint] = []
        if not iot_df.empty and keyword in iot_df.columns:
            for dt_idx, row in iot_df.iterrows():
                val = int(row[keyword])
                iso = dt_idx.date().isoformat() if hasattr(dt_idx, "date") else str(dt_idx)[:10]
                points.append(TrendPoint(date=iso, interest=val))

        # Related queries — rising
        related = pt.related_queries()
        rising_queries: List[RelatedQuery] = []
        try:
            rising_df = related.get(keyword, {}).get("rising")
            if rising_df is not None and not rising_df.empty:
                for _, row in rising_df.head(5).iterrows():
                    val_raw = row.get("value", "")
                    rising_queries.append(RelatedQuery(
                        query=str(row.get("query", "")),
                        value=str(val_raw) if val_raw != "Breakout" else "Breakout",
                    ))
        except Exception:
            pass

        # Compute stats
        interests = [p.interest for p in points if p.interest > 0]
        avg = round(sum(interests) / len(interests), 1) if interests else 0.0
        peak = max(interests) if interests else 0

        # Recent momentum: last 4 vs full period
        recent = [p.interest for p in points[-4:] if p.interest > 0]
        recent_avg = sum(recent) / len(recent) if recent else 0.0
        recent_vs_avg = round(recent_avg - avg, 1)

        if len(points) < 3:
            direction = "Insufficient data"
        elif recent_vs_avg > 5:
            direction = "Rising"
        elif recent_vs_avg < -5:
            direction = "Falling"
        else:
            direction = "Stable"

        result = GoogleTrendsData(
            keyword=keyword,
            timeframe="today 3-m",
            interest_over_time=points,
            rising_queries=rising_queries,
            avg_interest=avg,
            peak_interest=peak,
            recent_vs_avg=recent_vs_avg,
            trend_direction=direction,
        )
        _TRENDS_CACHE[symbol] = (now, result)
        return result

    except Exception as exc:
        logger.warning("Google Trends fetch failed for %s: %s", symbol, exc)
        _TRENDS_CACHE[symbol] = (now, None)
        return None


# ─── StockTwits advanced ─────────────────────────────────────────────────────

def _fetch_stocktwits_snapshot(symbol: str) -> Optional[StockTwitsSnapshot]:
    """
    Fetch StockTwits message feed and compute advanced sentiment metrics.
    Uses httpx directly (sync) so it can run in a thread pool.
    """
    now = time.time()
    if symbol in _TWITS_CACHE:
        ts, cached = _TWITS_CACHE[symbol]
        if now - ts < TWITS_CACHE_TTL:
            return cached

    try:
        import httpx as _httpx
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        with _httpx.Client(timeout=10) as client:
            resp = client.get(url)
            if resp.status_code == 422:
                _TWITS_CACHE[symbol] = (now, None)
                return None
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("StockTwits fetch failed for %s: %s", symbol, exc)
        return None

    raw_messages = data.get("messages", [])
    if not raw_messages:
        return None

    messages: List[StockTwitsMessage] = []
    for msg in raw_messages:
        raw_sent = msg.get("entities", {}).get("sentiment") or msg.get("sentiment")
        basic = (raw_sent or {}).get("basic")
        sentiment = basic if basic in ("Bullish", "Bearish") else "Neutral"

        try:
            created = datetime.strptime(msg["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            created_str = created.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            created_str = ""

        username = msg.get("user", {}).get("username", "anonymous")
        likes = (msg.get("likes") or {}).get("total", 0)

        messages.append(StockTwitsMessage(
            username=username,
            body=msg.get("body", ""),
            sentiment=sentiment,
            likes=likes,
            created_at=created_str,
        ))

    total = len(messages)
    bullish_msgs = [m for m in messages if m.sentiment == "Bullish"]
    bearish_msgs = [m for m in messages if m.sentiment == "Bearish"]
    neutral_msgs = [m for m in messages if m.sentiment == "Neutral"]

    b_count = len(bullish_msgs)
    s_count = len(bearish_msgs)
    n_count = len(neutral_msgs)

    bullish_pct = round(b_count / total * 100, 1) if total else 0.0
    bearish_pct = round(s_count / total * 100, 1) if total else 0.0
    bb_ratio    = round(b_count / s_count, 2) if s_count > 0 else None

    # Label
    if b_count + s_count == 0:
        label = "Neutral"
    else:
        bp = b_count / (b_count + s_count) * 100
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

    result = StockTwitsSnapshot(
        symbol=symbol,
        total_messages=total,
        bullish_count=b_count,
        bearish_count=s_count,
        neutral_count=n_count,
        bullish_pct=bullish_pct,
        bearish_pct=bearish_pct,
        bull_bear_ratio=bb_ratio,
        sentiment_label=label,
        top_bullish=sorted(bullish_msgs, key=lambda m: m.likes, reverse=True)[:5],
        top_bearish=sorted(bearish_msgs, key=lambda m: m.likes, reverse=True)[:5],
        recent_messages=messages[:10],
    )
    _TWITS_CACHE[symbol] = (now, result)
    return result


# ─── Composite score ─────────────────────────────────────────────────────────

def _composite_score(
    trends: Optional[GoogleTrendsData],
    twits: Optional[StockTwitsSnapshot],
) -> tuple[float, str]:
    """
    Blend Google Trends momentum + StockTwits bullish ratio into a 0–100 score.
    50 = neutral.

    Weights: StockTwits bullish ratio (60%), Trends momentum (40%).
    If one source is unavailable, the other provides the full score.
    """
    scores = []
    weights = []

    if twits and twits.bullish_count + twits.bearish_count > 0:
        labeled = twits.bullish_count + twits.bearish_count
        twits_score = (twits.bullish_count / labeled) * 100
        scores.append(twits_score)
        weights.append(0.60)

    if trends and trends.avg_interest > 0:
        # Map trend direction to a score contribution centred on 50
        # Rising interest with high bullish StockTwits = strong signal
        # Trends alone: use recent_vs_avg to shift from 50
        base = 50.0
        shift = min(25.0, max(-25.0, trends.recent_vs_avg * 1.5))
        trend_score = base + shift
        scores.append(trend_score)
        weights.append(0.40)

    if not scores:
        return 50.0, "Insufficient data"

    total_w = sum(weights)
    composite = sum(s * w for s, w in zip(scores, weights)) / total_w
    composite = round(min(95.0, max(5.0, composite)), 1)

    if composite >= 72:
        label = "Strong Bullish Momentum"
    elif composite >= 58:
        label = "Bullish Lean"
    elif composite >= 42:
        label = "Neutral"
    elif composite >= 28:
        label = "Bearish Lean"
    else:
        label = "Strong Bearish Pressure"

    return composite, label


# ─── Main entry point ─────────────────────────────────────────────────────────

def analyse_advanced_sentiment(symbol: str) -> AdvancedSentimentAnalysis:
    """
    Run the full advanced sentiment analysis for a symbol.
    Fetches Google Trends and StockTwits concurrently via ThreadPoolExecutor.
    """
    import concurrent.futures
    sym = symbol.upper()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_trends = pool.submit(_fetch_google_trends, sym)
        f_twits  = pool.submit(_fetch_stocktwits_snapshot, sym)
        trends = f_trends.result()
        twits  = f_twits.result()

    composite, label = _composite_score(trends, twits)

    return AdvancedSentimentAnalysis(
        symbol=sym,
        google_trends=trends,
        stocktwits=twits,
        composite_score=composite,
        composite_label=label,
    )
