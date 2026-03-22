"""
app/api/v1/endpoints/symbols.py

Symbol search endpoint (todos-v3.md POLISH-02 / UX-PERF).

GET /api/v1/symbols/search?q=AAPL&limit=8
  — Searches Finnhub symbol database for matching tickers.
  — Falls back to a curated static list when Finnhub key is not set.
  — Results are annotated with whether the symbol has a trained ML model.
  — Used by GlobalTickerSearch autocomplete dropdown.

Response shape:
  [
    { "symbol": "AAPL", "description": "Apple Inc", "type": "Common Stock",
      "exchange": "NASDAQ", "trained": true },
    ...
  ]
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Static fallback list (shown when Finnhub key is absent) ───────────────────
# Top 60 most-traded symbols across US equities, ETFs, and crypto
_STATIC_SYMBOLS: list[dict] = [
    # Mega-cap equities
    {"symbol": "AAPL",  "description": "Apple Inc",                  "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "MSFT",  "description": "Microsoft Corp",             "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "description": "Alphabet Inc Class A",       "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "AMZN",  "description": "Amazon.com Inc",             "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "NVDA",  "description": "NVIDIA Corp",                "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "META",  "description": "Meta Platforms Inc",         "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "TSLA",  "description": "Tesla Inc",                  "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "BRK.B", "description": "Berkshire Hathaway Class B", "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "AVGO",  "description": "Broadcom Inc",               "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "JPM",   "description": "JPMorgan Chase & Co",        "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "V",     "description": "Visa Inc",                   "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "UNH",   "description": "UnitedHealth Group Inc",     "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "XOM",   "description": "Exxon Mobil Corp",           "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "MA",    "description": "Mastercard Inc",             "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "LLY",   "description": "Eli Lilly and Co",           "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "JNJ",   "description": "Johnson & Johnson",          "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "NFLX",  "description": "Netflix Inc",                "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "AMD",   "description": "Advanced Micro Devices Inc", "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "INTC",  "description": "Intel Corp",                 "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "CRM",   "description": "Salesforce Inc",             "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "PYPL",  "description": "PayPal Holdings Inc",        "type": "Common Stock", "exchange": "NASDAQ"},
    {"symbol": "PLTR",  "description": "Palantir Technologies Inc",  "type": "Common Stock", "exchange": "NYSE"},
    {"symbol": "COIN",  "description": "Coinbase Global Inc",        "type": "Common Stock", "exchange": "NASDAQ"},
    # Broad market ETFs
    {"symbol": "SPY",   "description": "SPDR S&P 500 ETF Trust",     "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "QQQ",   "description": "Invesco QQQ Trust Series 1", "type": "ETF", "exchange": "NASDAQ"},
    {"symbol": "IWM",   "description": "iShares Russell 2000 ETF",   "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "VOO",   "description": "Vanguard S&P 500 ETF",       "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "VTI",   "description": "Vanguard Total Stock Market ETF", "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "DIA",   "description": "SPDR Dow Jones Industrial Average ETF", "type": "ETF", "exchange": "NYSE ARCA"},
    # Sector ETFs
    {"symbol": "XLK",   "description": "Technology Select Sector SPDR Fund", "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "XLF",   "description": "Financial Select Sector SPDR Fund",  "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "XLE",   "description": "Energy Select Sector SPDR Fund",     "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "XLV",   "description": "Health Care Select Sector SPDR Fund","type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "XLI",   "description": "Industrial Select Sector SPDR Fund", "type": "ETF", "exchange": "NYSE ARCA"},
    # Fixed income & macro
    {"symbol": "TLT",   "description": "iShares 20+ Year Treasury Bond ETF", "type": "ETF", "exchange": "NASDAQ"},
    {"symbol": "GLD",   "description": "SPDR Gold Shares",                   "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "SLV",   "description": "iShares Silver Trust",               "type": "ETF", "exchange": "NYSE ARCA"},
    {"symbol": "USO",   "description": "United States Oil Fund LP",          "type": "ETF", "exchange": "NYSE ARCA"},
    # Crypto
    {"symbol": "BTC-USD",  "description": "Bitcoin USD",   "type": "Crypto", "exchange": "CCC"},
    {"symbol": "ETH-USD",  "description": "Ethereum USD",  "type": "Crypto", "exchange": "CCC"},
    {"symbol": "SOL-USD",  "description": "Solana USD",    "type": "Crypto", "exchange": "CCC"},
    {"symbol": "BNB-USD",  "description": "Binance Coin USD", "type": "Crypto", "exchange": "CCC"},
]


def _static_search(query: str, limit: int) -> list[dict]:
    """Filter _STATIC_SYMBOLS by query prefix/substring."""
    q = query.upper().strip()
    if not q:
        return _STATIC_SYMBOLS[:limit]
    # Symbol prefix match first, then description substring
    prefix = [s for s in _STATIC_SYMBOLS if s["symbol"].startswith(q)]
    desc   = [s for s in _STATIC_SYMBOLS if q in s["description"].upper() and s not in prefix]
    return (prefix + desc)[:limit]


def _get_trained_set() -> set[str]:
    """Read trained symbols from the JSONL model registry."""
    import json, os  # noqa: PLC0415
    try:
        from app.services.ml_pipeline import REGISTRY_FILE  # noqa: PLC0415
        if not os.path.exists(REGISTRY_FILE):
            return set()
        trained: set[str] = set()
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    sym = rec.get("symbol", "").upper()
                    if sym:
                        trained.add(sym)
                except Exception:
                    continue
        return trained
    except Exception:
        return set()


@router.get("/search", summary="Search tickers by symbol or company name")
async def search_symbols(
    q:     str = Query(default="", max_length=20, description="Query string — symbol prefix or company name"),
    limit: int = Query(default=8, ge=1, le=20),
) -> List[Dict[str, Any]]:
    """
    Returns matching ticker symbols with company name, type, and exchange.
    Annotates each result with `trained: bool` based on the local model registry.

    Priority order: symbol prefix matches before description substring matches.
    Trained symbols are surfaced first within each group.

    Live Finnhub search is used when FINNHUB_API_KEY is set; otherwise falls back
    to a curated static list of ~60 top symbols.
    """
    settings = get_settings()
    query    = q.strip().upper()

    # ── Try Finnhub live search ───────────────────────────────────────────────
    results: list[dict] = []

    if settings.has_finnhub and query:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    "https://finnhub.io/api/v1/search",
                    params={"q": query, "token": settings.finnhub_api_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in (data.get("result") or []):
                        # Filter to US-listed equities and ETFs — exclude OTC pink sheets
                        sym  = (item.get("symbol") or "").upper()
                        desc = item.get("description") or ""
                        typ  = item.get("type") or ""
                        exch = item.get("displaySymbol") or sym
                        if not sym or len(sym) > 10:
                            continue
                        results.append({
                            "symbol":      sym,
                            "description": desc,
                            "type":        typ,
                            "exchange":    exch,
                        })
                        if len(results) >= limit * 2:  # fetch extra, trim after sorting
                            break
        except Exception as exc:
            logger.debug("Finnhub search failed, falling back to static: %s", exc)

    # ── Static fallback ───────────────────────────────────────────────────────
    if not results:
        results = _static_search(query, limit * 2)

    # ── Annotate with trained status + sort trained first ─────────────────────
    trained_set = _get_trained_set()
    annotated = [
        {**r, "trained": r["symbol"] in trained_set}
        for r in results
    ]
    # trained symbols surface first, then alphabetical within each group
    annotated.sort(key=lambda x: (0 if x["trained"] else 1, x["symbol"]))

    return annotated[:limit]
