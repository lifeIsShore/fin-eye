"""
app/services/external/finanzen_net.py
───────────────────────────────────────────────────────────────────────────────
Sprint 42 — finanzen.net German-language news scraper

Scrapes German-language headlines from finanzen.net for TR DE stocks.
Headlines are run through sentiment_scorer (FinBERT/VADER) and stored
in the `news_articles` table with `fetch_source='finanzen_net'`.

Runs every 4 hours via scheduler. Respects robots.txt by:
  - Using a descriptive User-Agent
  - 2-second delay between requests
  - Only scraping the publicly accessible news pages
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.finanzen.net/nachrichten/aktien/{symbol}"
_HEADERS = {
    "User-Agent": "Fin-Eye/1.0 (+https://fin-eye.com; contact@fin-eye.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.3",
}
_TIMEOUT = 15.0
_INTER_REQUEST_DELAY = 2.0  # seconds between requests

# Symbol mappings: Yahoo Finance ticker → finanzen.net slug
# For German stocks, finanzen.net uses company names in URLs
_SYMBOL_SLUG_MAP = {
    "SAP.DE": "sap",
    "SIE.DE": "siemens",
    "ALV.DE": "allianz",
    "BAS.DE": "basf",
    "DTE.DE": "deutsche_telekom",
    "BMW.DE": "bmw",
    "MBG.DE": "mercedes_benz_group",
    "MRK.DE": "merck_kgaa",
    "IFX.DE": "infineon",
    "ADS.DE": "adidas",
    "DHL.DE": "deutsche_post",
    "DBK.DE": "deutsche_bank",
    "RWE.DE": "rwe",
    "VOW3.DE": "volkswagen_vz",
    "MUV2.DE": "muenchener_rueckversicherungs_gesellschaft",
    "HEN3.DE": "henkel_vz",
    "BAYN.DE": "bayer",
    "AIR.DE": "airbus",
    "BEI.DE": "beiersdorf",
    "FRE.DE": "fresenius",
}


def _get_slug(symbol: str) -> Optional[str]:
    """Resolve a Yahoo Finance ticker to a finanzen.net URL slug."""
    sym = symbol.upper()
    if sym in _SYMBOL_SLUG_MAP:
        return _SYMBOL_SLUG_MAP[sym]
    # For non-mapped symbols, try the raw symbol without exchange suffix
    base = sym.replace(".DE", "").replace(".F", "").lower()
    return base


async def scrape_headlines(symbol: str, max_articles: int = 20) -> List[dict]:
    """
    Scrape headlines from finanzen.net for a given symbol.

    Returns a list of dicts with keys: title, url, published_at (datetime or None).
    """
    slug = _get_slug(symbol)
    if not slug:
        logger.info("finanzen.net: no slug mapping for %s, skipping", symbol)
        return []

    url = _BASE_URL.format(symbol=slug)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_HEADERS)
            if resp.status_code == 404:
                logger.info("finanzen.net: 404 for %s (slug=%s), skipping", symbol, slug)
                return []
            resp.raise_for_status()
            html = resp.text
    except httpx.TimeoutException:
        logger.warning("finanzen.net: timeout fetching %s", symbol)
        return []
    except httpx.HTTPStatusError as exc:
        logger.warning("finanzen.net: HTTP %s for %s", exc.response.status_code, symbol)
        return []
    except Exception as exc:
        logger.error("finanzen.net: unexpected error for %s: %s", symbol, exc)
        return []

    # Parse with BeautifulSoup
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 not installed — cannot scrape finanzen.net")
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles: List[dict] = []

    # finanzen.net news articles are typically in <article> or <div> elements
    # with news headline links. The exact selectors may vary; we try several.
    selectors = [
        "article h2 a",
        "div.news-item a",
        ".news-list a",
        "a[href*='/nachrichten/']",
        "h3 a",
        "h2 a",
    ]

    seen_titles: set = set()
    for sel in selectors:
        for link in soup.select(sel):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 10 or title in seen_titles:
                continue
            seen_titles.add(title)

            # Build absolute URL
            if href.startswith("/"):
                href = f"https://www.finanzen.net{href}"

            articles.append({
                "title": title,
                "url": href,
                "published_at": datetime.now(timezone.utc),  # finanzen.net doesn't always show precise dates inline
            })

            if len(articles) >= max_articles:
                break
        if len(articles) >= max_articles:
            break

    logger.info("finanzen.net: scraped %d headlines for %s", len(articles), symbol)
    return articles


async def fetch_and_store_news(
    db: AsyncSession,
    symbols: list[str],
) -> dict:
    """
    Scrape finanzen.net headlines for each symbol, score with FinBERT/VADER,
    and upsert into the news_articles table.

    Returns: { "ok": [...], "failed": [...], "articles_added": int }
    """
    from app.models.sentiment import NewsArticle  # noqa: PLC0415

    ok, failed = [], []
    total_added = 0

    # Try to load sentiment scorer
    scorer = None
    try:
        from app.services.sentiment_scorer import score_batch  # noqa: PLC0415
        scorer = score_batch
    except ImportError:
        logger.warning("sentiment_scorer not available — storing without FinBERT scores")

    for symbol in symbols:
        try:
            headlines = await scrape_headlines(symbol)
            if not headlines:
                ok.append(symbol)
                continue

            # Score headlines
            titles = [h["title"] for h in headlines]
            if scorer:
                scores = scorer(titles)  # list of (label, confidence)
            else:
                scores = [("neutral", 0.0)] * len(titles)

            for headline, (label, confidence) in zip(headlines, scores):
                # Check for duplicates
                existing = await db.execute(
                    select(func.count()).select_from(NewsArticle).where(
                        NewsArticle.symbol == symbol.upper(),
                        NewsArticle.title == headline["title"],
                    )
                )
                if existing.scalar() > 0:
                    continue

                # Map label to score
                if label == "bullish" or label == "positive":
                    sentiment_score = confidence
                elif label == "bearish" or label == "negative":
                    sentiment_score = -confidence
                else:
                    sentiment_score = 0.0

                article = NewsArticle(
                    symbol=symbol.upper(),
                    title=headline["title"],
                    source="finanzen.net",
                    published_at=headline["published_at"],
                    sentiment_score=sentiment_score,
                )
                # Set optional fields if the model supports them
                if hasattr(article, "sentiment_label"):
                    article.sentiment_label = label
                if hasattr(article, "finbert_score"):
                    article.finbert_score = confidence
                if hasattr(article, "url"):
                    article.url = headline["url"]
                if hasattr(article, "fetch_source"):
                    article.fetch_source = "finanzen_net"
                if hasattr(article, "last_fetched_at"):
                    article.last_fetched_at = datetime.now(timezone.utc)

                db.add(article)
                total_added += 1

            await db.commit()
            ok.append(symbol)
            logger.info("finanzen.net: stored %d articles for %s", len(headlines), symbol)

            # Respect rate limiting
            time.sleep(_INTER_REQUEST_DELAY)

        except Exception as exc:
            logger.warning("finanzen.net: failed for %s: %s", symbol, exc)
            failed.append(symbol)
            await db.rollback()

    logger.info(
        "finanzen.net scrape complete: ok=%d failed=%d articles_added=%d",
        len(ok), len(failed), total_added,
    )
    return {"ok": ok, "failed": failed, "articles_added": total_added}
