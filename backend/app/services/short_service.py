"""
app/services/short_service.py
───────────────────────────────────────────────────────────────────────────────
EXP-SHORT-01 — Short Interest & Squeeze Risk

Data sources:
  1. FINRA short interest API (free, no key required)
     https://cdn.finra.org/equity/regsho/daily/{YYYYMMDD}.txt  — daily settlement files
     https://regsho.finra.org/regsho-Index.html
  2. yfinance ticker.info — short float %, short ratio (days-to-cover), float shares,
     shares outstanding, 52w high/low (for squeeze price distance)

Features:
  - Short interest (shares shorted absolute)
  - Short float % (shares shorted / float shares)
  - Days-to-cover (short ratio = short interest / avg daily volume)
  - Borrow fee rate (fee_rate from yfinance when available)
  - Short squeeze score (0–100): composite of short float, days-to-cover,
    recent price momentum, and distance from 52w high
  - Trend: last 2 FINRA settlement readings compared (rising/falling/flat)

Cache TTL: 4 hours (FINRA data updates bi-monthly; yfinance info updates daily)

No API key required.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL = 14_400   # 4 hours
_CACHE: Dict[str, tuple] = {}

# FINRA REGSHO daily short volume endpoint
# Format: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
FINRA_DAILY_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"
FINRA_INDEX_URL = "https://cdn.finra.org/equity/regsho/daily/"

_FINRA_CACHE: Dict[str, tuple] = {}  # date_str -> (ts, {symbol: ShortVolumeDay})
_FINRA_DATE_LIST: Optional[List[str]] = None
_FINRA_DATE_LIST_TS: float = 0.0


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class ShortVolumeDay:
    date: str           # YYYY-MM-DD
    short_volume: int
    total_volume: int
    short_volume_ratio: float   # short_volume / total_volume


@dataclass
class SqueezeScore:
    score: float        # 0–100
    label: str          # "Extreme Squeeze Risk" / "High" / "Moderate" / "Low" / "Minimal"
    drivers: List[str]  # plain-language factors that pushed score up


@dataclass
class ShortAnalysis:
    symbol: str
    company_name: str

    # Core short metrics
    shares_short: Optional[int]           # absolute shares shorted
    short_float_pct: Optional[float]      # % of float that is shorted
    short_ratio: Optional[float]          # days-to-cover
    float_shares: Optional[int]
    shares_outstanding: Optional[int]

    # Borrow
    borrow_fee_rate: Optional[float]      # annualised % cost to borrow (when available)

    # Price context
    current_price: Optional[float]
    price_52w_high: Optional[float]
    price_52w_low: Optional[float]
    pct_from_52w_high: Optional[float]    # negative = below high
    avg_volume_10d: Optional[int]

    # FINRA daily short volume trend (last 2 available dates)
    short_volume_trend: List[ShortVolumeDay]  # newest first
    trend_direction: str   # "Rising" / "Falling" / "Flat" / "Insufficient data"

    # Composite
    squeeze_score: SqueezeScore

    disclaimer: str = (
        "Short interest data is sourced from FINRA REGSHO daily settlement files and Yahoo Finance. "
        "Short float % and days-to-cover are as-of the last available settlement date. "
        "This is for educational purposes only and does not constitute investment advice. "
        "Short squeeze events are unpredictable and carry significant risk."
    )


# ─── FINRA helpers ────────────────────────────────────────────────────────────

def _fetch_finra_date_list() -> List[str]:
    """Fetch the list of available FINRA REGSHO daily files (date strings YYYYMMDD)."""
    global _FINRA_DATE_LIST, _FINRA_DATE_LIST_TS
    now = time.time()
    if _FINRA_DATE_LIST is not None and (now - _FINRA_DATE_LIST_TS) < 3600:
        return _FINRA_DATE_LIST

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(FINRA_INDEX_URL)
            resp.raise_for_status()
            text = resp.text
            # Parse date strings from filenames like CNMSshvol20250103.txt
            import re
            dates = sorted(set(re.findall(r'CNMSshvol(\d{8})\.txt', text)), reverse=True)
            _FINRA_DATE_LIST = dates[:10]   # keep last 10 trading days
            _FINRA_DATE_LIST_TS = now
            return _FINRA_DATE_LIST
    except Exception as exc:
        logger.warning("FINRA index fetch failed: %s", exc)
        return []


def _fetch_finra_day(date_str: str, symbol: str) -> Optional[ShortVolumeDay]:
    """
    Fetch FINRA REGSHO daily short volume for a specific date and symbol.
    Parses the pipe-delimited text file and extracts the row for `symbol`.
    """
    now = time.time()
    cache_key = f"{date_str}:{symbol}"

    if cache_key in _FINRA_CACHE:
        ts, val = _FINRA_CACHE[cache_key]
        if now - ts < 86400:   # cache individual symbol lookups for 24h
            return val

    url = FINRA_DAILY_URL.format(date=date_str)
    try:
        with httpx.Client(timeout=12) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            # Parse pipe-delimited: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market
            for line in resp.text.splitlines():
                parts = line.strip().split("|")
                if len(parts) < 5:
                    continue
                if parts[1].upper() != symbol.upper():
                    continue
                try:
                    sv = int(parts[2])
                    tv = int(parts[4])
                    ratio = sv / tv if tv > 0 else 0.0
                    raw_date = parts[0]  # YYYYMMDD
                    iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                    result = ShortVolumeDay(
                        date=iso_date,
                        short_volume=sv,
                        total_volume=tv,
                        short_volume_ratio=round(ratio, 4),
                    )
                    _FINRA_CACHE[cache_key] = (now, result)
                    return result
                except (ValueError, IndexError):
                    continue
    except Exception as exc:
        logger.debug("FINRA day fetch failed %s/%s: %s", date_str, symbol, exc)

    _FINRA_CACHE[cache_key] = (now, None)
    return None


def _get_short_volume_trend(symbol: str, n_days: int = 5) -> List[ShortVolumeDay]:
    """Fetch last n_days of FINRA short volume for a symbol."""
    dates = _fetch_finra_date_list()
    results: List[ShortVolumeDay] = []
    for d in dates[:n_days]:
        day = _fetch_finra_day(d, symbol)
        if day:
            results.append(day)
        if len(results) >= n_days:
            break
    return results   # newest first (dates list is sorted newest-first)


def _trend_direction(trend: List[ShortVolumeDay]) -> str:
    if len(trend) < 2:
        return "Insufficient data"
    newest = trend[0].short_volume_ratio
    oldest = trend[-1].short_volume_ratio
    delta = newest - oldest
    if delta > 0.03:
        return "Rising"
    if delta < -0.03:
        return "Falling"
    return "Flat"


# ─── Squeeze score ────────────────────────────────────────────────────────────

def _compute_squeeze_score(
    short_float_pct: Optional[float],
    days_to_cover: Optional[float],
    pct_from_52w_high: Optional[float],
    trend: List[ShortVolumeDay],
    borrow_fee: Optional[float],
) -> SqueezeScore:
    """
    Composite squeeze risk score (0–100).

    Components:
    - Short float %: primary driver. >20% is very high, >30% is extreme.
      Contributes up to 45 pts.
    - Days-to-cover: secondary. >5 = elevated, >10 = high.
      Contributes up to 25 pts.
    - Price vs 52w high: stocks close to highs are harder to squeeze (already squeezed)
      while stocks far below highs have more upside potential in a squeeze.
      Contributes up to 15 pts.
    - Short volume trend: rising short interest adds to risk.
      Contributes up to 10 pts.
    - Borrow fee: high fee = hard to borrow = forced covering pressure.
      Contributes up to 5 pts.
    """
    score = 0.0
    drivers: List[str] = []

    # Component 1: short float % (0–45 pts)
    if short_float_pct is not None:
        if short_float_pct >= 30:
            c1 = 45.0
            drivers.append(f"Extremely high short float ({short_float_pct:.1f}%)")
        elif short_float_pct >= 20:
            c1 = 35.0
            drivers.append(f"Very high short float ({short_float_pct:.1f}%)")
        elif short_float_pct >= 10:
            c1 = 22.0
            drivers.append(f"Elevated short float ({short_float_pct:.1f}%)")
        elif short_float_pct >= 5:
            c1 = 10.0
        else:
            c1 = short_float_pct * 1.5
        score += c1

    # Component 2: days-to-cover (0–25 pts)
    if days_to_cover is not None:
        if days_to_cover >= 10:
            c2 = 25.0
            drivers.append(f"Very high days-to-cover ({days_to_cover:.1f}d)")
        elif days_to_cover >= 5:
            c2 = 15.0
            drivers.append(f"Elevated days-to-cover ({days_to_cover:.1f}d)")
        elif days_to_cover >= 2:
            c2 = 7.0
        else:
            c2 = days_to_cover * 2.0
        score += c2

    # Component 3: distance from 52w high (0–15 pts)
    # pct_from_52w_high is negative when below high (e.g. -0.40 = 40% below high)
    if pct_from_52w_high is not None:
        dist_below = -pct_from_52w_high   # positive = below high
        if dist_below > 0.5:
            c3 = 15.0   # deeply depressed — maximum squeeze potential on recovery
            drivers.append("Stock is deeply below 52w high (high upside in squeeze)")
        elif dist_below > 0.25:
            c3 = 10.0
        elif dist_below > 0.10:
            c3 = 5.0
        else:
            c3 = 0.0   # near high — squeeze already playing out or low risk
        score += c3

    # Component 4: trend (0–10 pts)
    if len(trend) >= 2:
        direction = _trend_direction(trend)
        if direction == "Rising":
            score += 10.0
            drivers.append("Short volume trend is rising")
        elif direction == "Flat":
            score += 3.0

    # Component 5: borrow fee (0–5 pts)
    if borrow_fee is not None and borrow_fee > 1.0:
        if borrow_fee >= 50:
            score += 5.0
            drivers.append(f"Hard-to-borrow (fee: {borrow_fee:.1f}%)")
        elif borrow_fee >= 10:
            score += 3.0
            drivers.append(f"Elevated borrow fee ({borrow_fee:.1f}%)")
        else:
            score += 1.0

    score = round(min(95.0, max(5.0, score)), 1)

    if score >= 75:
        label = "Extreme Squeeze Risk"
    elif score >= 60:
        label = "High Squeeze Risk"
    elif score >= 40:
        label = "Moderate"
    elif score >= 25:
        label = "Low"
    else:
        label = "Minimal"

    return SqueezeScore(score=score, label=label, drivers=drivers)


# ─── Main analysis ────────────────────────────────────────────────────────────

def analyse_short_interest(symbol: str) -> ShortAnalysis:
    """
    Fetch and analyse short interest data for a symbol.
    Combines yfinance fundamentals with FINRA short volume trend.
    Cached for 4 hours.
    """
    sym = symbol.upper()
    now = time.time()

    if sym in _CACHE:
        ts, cached = _CACHE[sym]
        if now - ts < CACHE_TTL:
            return cached

    # ── yfinance info ────────────────────────────────────────────────────────
    ticker = yf.Ticker(sym)
    info: dict = {}
    try:
        info = ticker.info or {}
    except Exception as exc:
        logger.warning("yfinance info failed for %s: %s", sym, exc)

    company_name    = info.get("longName") or info.get("shortName") or sym
    shares_short    = info.get("sharesShort")
    short_float_pct = info.get("shortPercentOfFloat")
    short_ratio     = info.get("shortRatio")          # days-to-cover
    float_shares    = info.get("floatShares")
    shares_out      = info.get("sharesOutstanding")
    current_price   = info.get("currentPrice") or info.get("regularMarketPrice")
    high_52w        = info.get("fiftyTwoWeekHigh")
    low_52w         = info.get("fiftyTwoWeekLow")
    avg_volume      = info.get("averageVolume10days") or info.get("averageDailyVolume10Day")

    # Borrow fee — not always available; yfinance exposes it as borrowCost on some tickers
    borrow_fee = info.get("borrowCost")   # annualised % when present

    # Normalise short float % (yfinance sometimes returns as decimal 0–1)
    if short_float_pct is not None:
        if short_float_pct < 1.0:
            short_float_pct = round(short_float_pct * 100, 2)
        else:
            short_float_pct = round(float(short_float_pct), 2)

    pct_from_high: Optional[float] = None
    if current_price and high_52w and high_52w > 0:
        pct_from_high = round((current_price - high_52w) / high_52w, 4)

    # ── FINRA short volume trend ─────────────────────────────────────────────
    trend = _get_short_volume_trend(sym, n_days=5)
    direction = _trend_direction(trend)

    # ── Squeeze score ────────────────────────────────────────────────────────
    squeeze = _compute_squeeze_score(
        short_float_pct=short_float_pct,
        days_to_cover=float(short_ratio) if short_ratio else None,
        pct_from_52w_high=pct_from_high,
        trend=trend,
        borrow_fee=float(borrow_fee) if borrow_fee else None,
    )

    result = ShortAnalysis(
        symbol=sym,
        company_name=company_name,
        shares_short=int(shares_short) if shares_short else None,
        short_float_pct=short_float_pct,
        short_ratio=round(float(short_ratio), 2) if short_ratio else None,
        float_shares=int(float_shares) if float_shares else None,
        shares_outstanding=int(shares_out) if shares_out else None,
        borrow_fee_rate=round(float(borrow_fee), 2) if borrow_fee else None,
        current_price=round(float(current_price), 2) if current_price else None,
        price_52w_high=round(float(high_52w), 2) if high_52w else None,
        price_52w_low=round(float(low_52w), 2) if low_52w else None,
        pct_from_52w_high=round(pct_from_high * 100, 2) if pct_from_high is not None else None,
        avg_volume_10d=int(avg_volume) if avg_volume else None,
        short_volume_trend=trend,
        trend_direction=direction,
        squeeze_score=squeeze,
    )

    _CACHE[sym] = (now, result)
    return result
