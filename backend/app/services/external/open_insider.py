"""
app/services/external/open_insider.py
───────────────────────────────────────────────────────────────────────────────
Sprint 42 — OpenInsider aggregated insider data scraper

Scrapes https://openinsider.com/screener?s={symbol} daily for insider
cluster-buy scoring. Complement to the SEC EDGAR insider_service.

Computes a `insider_cluster_buy_score` (0-100):
  - 80-100: Strong cluster buying (≥3 insiders buying in 14 days)
  - 60-79:  Moderate buying (2 insiders or 1 large buy)
  - 40-59:  Neutral / mixed
  - 20-39:  Moderate selling pressure
  - 0-19:   Heavy insider selling

Results stored in `external_signals` table.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://openinsider.com/screener?s={symbol}&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr=&feession=&cession=&sid=&pession=&ta=0&ct=0&cnt=100&page=1"
_HEADERS = {
    "User-Agent": "Fin-Eye/1.0 (+https://fin-eye.com; contact@fin-eye.com)",
    "Accept": "text/html,application/xhtml+xml",
}
_TIMEOUT = 15.0
_INTER_REQUEST_DELAY = 3.0  # seconds between requests


async def scrape_insider_data(symbol: str) -> Dict:
    """
    Scrape OpenInsider for recent insider transactions.
    Returns a dict with parsed transaction data and cluster score.
    """
    url = _BASE_URL.format(symbol=symbol.upper())

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_HEADERS)
            if resp.status_code == 404:
                logger.info("OpenInsider: 404 for %s", symbol)
                return {"transactions": [], "cluster_score": 50.0}
            resp.raise_for_status()
            html = resp.text
    except httpx.TimeoutException:
        logger.warning("OpenInsider: timeout for %s", symbol)
        return {"transactions": [], "cluster_score": 50.0}
    except Exception as exc:
        logger.warning("OpenInsider: error for %s: %s", symbol, exc)
        return {"transactions": [], "cluster_score": 50.0}

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 not installed — cannot scrape OpenInsider")
        return {"transactions": [], "cluster_score": 50.0}

    soup = BeautifulSoup(html, "html.parser")

    # Parse the insider transaction table
    transactions: List[Dict] = []
    table = soup.find("table", class_="tinytable")
    if not table:
        # Try alternate selector
        tables = soup.find_all("table")
        for t in tables:
            headers = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            if "insider name" in " ".join(headers) or "trade type" in " ".join(headers):
                table = t
                break

    if table:
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 8:
                continue
            try:
                txn = {
                    "filing_date": cols[1].get_text(strip=True),
                    "trade_date": cols[2].get_text(strip=True),
                    "insider_name": cols[4].get_text(strip=True),
                    "title": cols[5].get_text(strip=True) if len(cols) > 5 else "",
                    "trade_type": cols[6].get_text(strip=True) if len(cols) > 6 else "",
                    "qty": cols[8].get_text(strip=True).replace(",", "").replace("+", "").replace("-", "") if len(cols) > 8 else "0",
                    "price": cols[7].get_text(strip=True).replace("$", "").replace(",", "") if len(cols) > 7 else "0",
                }
                transactions.append(txn)
            except Exception:
                continue

    # Compute cluster buy score
    cluster_score = _compute_cluster_score(transactions)

    logger.info(
        "OpenInsider: %d transactions for %s, cluster_score=%.1f",
        len(transactions), symbol, cluster_score,
    )
    return {
        "transactions": transactions[:20],
        "cluster_score": cluster_score,
        "total_parsed": len(transactions),
    }


def _compute_cluster_score(transactions: List[Dict]) -> float:
    """
    Compute a 0-100 cluster buy score from parsed OpenInsider transactions.

    Methodology:
      - Count distinct buyers vs sellers in the last 30 days
      - Weight purchases more heavily than sales
      - Cluster buying (≥3 unique buyers) → high score
    """
    if not transactions:
        return 50.0

    buyers: set = set()
    sellers: set = set()
    buy_value = 0.0
    sell_value = 0.0

    for txn in transactions:
        trade_type = txn.get("trade_type", "").lower()
        name = txn.get("insider_name", "").strip()
        try:
            qty = abs(float(txn.get("qty", "0") or "0"))
            price = float(txn.get("price", "0") or "0")
        except ValueError:
            qty, price = 0, 0

        value = qty * price

        if "purchase" in trade_type or "buy" in trade_type or trade_type == "p":
            if name:
                buyers.add(name)
            buy_value += value
        elif "sale" in trade_type or "sell" in trade_type or trade_type == "s":
            if name:
                sellers.add(name)
            sell_value += value

    n_buyers = len(buyers)
    n_sellers = len(sellers)

    # Base score from buyer/seller ratio
    total_actors = n_buyers + n_sellers
    if total_actors == 0:
        return 50.0

    buy_ratio = n_buyers / total_actors
    base_score = buy_ratio * 100.0

    # Cluster bonus: ≥3 unique buyers = strong signal
    if n_buyers >= 3:
        base_score = min(100.0, base_score + 15.0)
    elif n_buyers >= 2:
        base_score = min(100.0, base_score + 8.0)

    # Value-weight adjustment
    total_value = buy_value + sell_value
    if total_value > 0:
        value_tilt = (buy_value / total_value - 0.5) * 20.0
        base_score = base_score + value_tilt

    return round(max(0.0, min(100.0, base_score)), 1)


async def fetch_and_store_signals(
    db,  # AsyncSession
    symbols: list[str],
) -> dict:
    """
    Scrape OpenInsider for each symbol and store cluster buy scores
    in the external_signals table.
    """
    from app.models.external_signal import ExternalSignal  # noqa: PLC0415

    ok, failed = [], []
    ts = datetime.now(timezone.utc)

    for symbol in symbols:
        try:
            data = await scrape_insider_data(symbol)
            score = data["cluster_score"]

            db.add(ExternalSignal(
                source="open_insider",
                symbol=symbol.upper(),
                signal_name="insider_cluster_buy_score",
                value=score,
                raw_json={
                    "total_parsed": data.get("total_parsed", 0),
                    "transactions_sample": data["transactions"][:5],
                },
                fetched_at=ts,
            ))

            # Normalised version for ML pipeline
            db.add(ExternalSignal(
                source="open_insider",
                symbol=symbol.upper(),
                signal_name="insider_cluster_buy_norm",
                value=round(score / 100.0, 4),
                raw_json=None,
                fetched_at=ts,
            ))

            ok.append(symbol)

            # Respect rate limiting
            import asyncio
            await asyncio.sleep(_INTER_REQUEST_DELAY)

        except Exception as exc:
            logger.warning("OpenInsider: failed for %s: %s", symbol, exc)
            failed.append(symbol)

    await db.commit()
    logger.info("OpenInsider signals: ok=%d failed=%d", len(ok), len(failed))
    return {"ok": ok, "failed": failed}
