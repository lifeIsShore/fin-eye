"""
app/services/sector_service.py
─────────────────────────────────────────────────────────────────────────────
EXP-SECT-01 — Sector Rotation Heatmap

Fetches weekly/monthly/quarterly price performance for the 11 SPDR Sector ETFs
and SPY via yfinance, then computes:

  1. Absolute return for 1W / 1M / 3M periods
  2. Relative Strength vs SPY  (sector_return / spy_return, normalised to 0–100)
  3. Momentum score            (rate of change of 4-week rolling return)
  4. RRG quadrant              (Leading / Weakening / Lagging / Improving)
  5. Economic cycle phase      (Early / Mid / Late / Recession)
  6. Dominant cycle phase      (which phase is currently "in favour")

All computation is CPU-bound (pandas / yfinance). Callers must use
run_in_executor() from async contexts.

15-minute in-process cache. No new API key needed.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ── Sector universe ────────────────────────────────────────────────────────────

SECTORS: list[dict] = [
    {"ticker": "XLK",  "name": "Technology",            "cycle": "Mid Cycle"},
    {"ticker": "XLV",  "name": "Health Care",           "cycle": "Recession"},
    {"ticker": "XLF",  "name": "Financials",            "cycle": "Early Cycle"},
    {"ticker": "XLE",  "name": "Energy",                "cycle": "Late Cycle"},
    {"ticker": "XLI",  "name": "Industrials",           "cycle": "Mid Cycle"},
    {"ticker": "XLB",  "name": "Materials",             "cycle": "Late Cycle"},
    {"ticker": "XLRE", "name": "Real Estate",           "cycle": "Early Cycle"},
    {"ticker": "XLY",  "name": "Consumer Discretionary","cycle": "Early Cycle"},
    {"ticker": "XLP",  "name": "Consumer Staples",      "cycle": "Recession"},
    {"ticker": "XLU",  "name": "Utilities",             "cycle": "Recession"},
    {"ticker": "XLC",  "name": "Communication Svcs",    "cycle": "Mid Cycle"},
]

CYCLE_PHASES = ["Early Cycle", "Mid Cycle", "Late Cycle", "Recession"]

BENCHMARK = "SPY"

# ── Cache ──────────────────────────────────────────────────────────────────────

_CACHE: dict[str, tuple[float, "SectorRotationData"]] = {}
_CACHE_TTL_S = 900  # 15 minutes


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass
class SectorData:
    ticker: str
    name: str
    cycle_phase: str

    # Absolute returns (%)
    return_1w: Optional[float]
    return_1m: Optional[float]
    return_3m: Optional[float]

    # Relative strength vs SPY (ratio, SPY = 1.0)
    rs_1w: Optional[float]
    rs_1m: Optional[float]
    rs_3m: Optional[float]

    # RS normalised 0–100 (for colour scale; 50 = same as SPY)
    rs_score: float  # based on 1M RS

    # Momentum: rate-of-change of RS over the last 4 weeks (positive = accelerating)
    momentum: Optional[float]

    # RRG quadrant derived from RS and Momentum
    # Leading: RS > 1 and momentum > 0
    # Weakening: RS > 1 and momentum < 0
    # Lagging: RS < 1 and momentum < 0
    # Improving: RS < 1 and momentum > 0
    rrg_quadrant: str  # "Leading" | "Weakening" | "Lagging" | "Improving"

    # Latest close price
    last_price: Optional[float]


@dataclass
class SectorRotationData:
    sectors: list[SectorData]
    spy_return_1w: Optional[float]
    spy_return_1m: Optional[float]
    spy_return_3m: Optional[float]

    # Which economic cycle phase is currently most "in favour"
    dominant_cycle_phase: str
    dominant_cycle_description: str

    # Cycle phase summary: average RS score per phase
    cycle_phase_scores: dict[str, float]

    computed_at: float = field(default_factory=time.time)

    disclaimer: str = (
        "Sector data is sourced from yfinance (15-min delayed). Performance is based "
        "on SPDR Sector ETF price returns. Relative Rotation Graph (RRG) quadrants are "
        "educational approximations — not professional investment signals. Past sector "
        "leadership does not guarantee future performance."
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pct_return(series: pd.Series, lookback: int) -> Optional[float]:
    """
    Compute percentage return over `lookback` trading days.
    Returns None if not enough data.
    """
    if len(series) < lookback + 1:
        return None
    end   = float(series.iloc[-1])
    start = float(series.iloc[-lookback - 1])
    if start == 0:
        return None
    return round((end - start) / start * 100, 3)


def _relative_strength(sector_ret: Optional[float], spy_ret: Optional[float]) -> Optional[float]:
    """
    Ratio of sector return to SPY return.
    Values > 1.0 = sector outperforming, < 1.0 = underperforming.
    Both inputs are % returns (not raw; we convert to decimal factors).
    """
    if sector_ret is None or spy_ret is None:
        return None
    s_factor   = 1 + sector_ret / 100
    spy_factor = 1 + spy_ret   / 100
    if spy_factor == 0:
        return None
    return round(s_factor / spy_factor, 4)


def _rs_to_score(rs: Optional[float], all_rs: list[Optional[float]]) -> float:
    """
    Normalise RS to 0–100 scale where 50 = SPY parity.
    Uses the min/max of all sectors in the universe.
    """
    if rs is None:
        return 50.0
    valid = [x for x in all_rs if x is not None]
    if not valid:
        return 50.0
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return 50.0
    return round(50.0 + (rs - 1.0) / max(abs(hi - 1.0), abs(lo - 1.0), 0.001) * 50.0, 1)


def _rrg_quadrant(rs_1m: Optional[float], momentum: Optional[float]) -> str:
    rs  = rs_1m  if rs_1m  is not None else 1.0
    mom = momentum if momentum is not None else 0.0
    if rs >= 1.0 and mom >= 0:
        return "Leading"
    if rs >= 1.0 and mom < 0:
        return "Weakening"
    if rs < 1.0 and mom < 0:
        return "Lagging"
    return "Improving"


def _momentum(closes: pd.Series, short_window: int = 4, long_window: int = 8) -> Optional[float]:
    """
    Rate of change of relative strength proxy: difference between
    short-term and long-term average weekly RS.
    Positive = RS is accelerating (improving momentum).
    """
    weeks_needed = long_window + 1
    if len(closes) < weeks_needed * 5:
        return None
    # Resample to weekly
    weekly = closes.resample("W").last().dropna()
    if len(weekly) < long_window + 1:
        return None
    short_avg = float(weekly.iloc[-short_window:].pct_change().mean())
    long_avg  = float(weekly.iloc[-long_window:].pct_change().mean())
    if pd.isna(short_avg) or pd.isna(long_avg):
        return None
    return round((short_avg - long_avg) * 100, 3)


# ── Main entry point ───────────────────────────────────────────────────────────

def fetch_sector_rotation() -> SectorRotationData:
    """
    Download ~6 months of daily closes for all sector ETFs + SPY,
    compute all metrics, and return structured SectorRotationData.

    Synchronous — wrap with run_in_executor() from async callers.
    Results are cached for 15 minutes.
    """
    cache_key = "sector_rotation"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_S:
        logger.debug("Sector rotation cache HIT")
        return cached[1]

    logger.info("Fetching sector rotation data from yfinance")

    tickers = [s["ticker"] for s in SECTORS] + [BENCHMARK]

    # Download ~6 months of daily closes (need 65 trading days for 3M return)
    raw = yf.download(
        tickers,
        period="6mo",
        interval="1d",
        auto_adjust=True,
        actions=False,
        progress=False,
    )

    # Normalise DataFrame structure
    # yfinance v0.2+ returns MultiIndex with (Price, Ticker) ordering
    if isinstance(raw.columns, pd.MultiIndex):
        # Try both level orderings for compatibility
        try:
            closes = raw.xs("Close", axis=1, level=0)
        except KeyError:
            closes = raw.xs("Close", axis=1, level=1)
    else:
        closes = raw[["Close"]]
        closes.columns = [tickers[0]]

    closes = closes.dropna(how="all").sort_index()

    # SPY data
    spy_closes = closes.get(BENCHMARK)
    spy_1w = _pct_return(spy_closes, 5)   if spy_closes is not None else None
    spy_1m = _pct_return(spy_closes, 21)  if spy_closes is not None else None
    spy_3m = _pct_return(spy_closes, 63)  if spy_closes is not None else None

    # Per-sector computation
    rs_1m_list: list[Optional[float]] = []
    raw_sectors: list[dict] = []

    for s in SECTORS:
        ticker = s["ticker"]
        col = closes.get(ticker)

        if col is None or col.dropna().empty:
            rs_1m_list.append(None)
            raw_sectors.append({**s, "closes": None, "ret_1w": None, "ret_1m": None,
                                 "ret_3m": None, "rs_1w": None, "rs_1m": None,
                                 "rs_3m": None, "momentum": None, "last_price": None})
            continue

        col = col.dropna()
        ret_1w = _pct_return(col, 5)
        ret_1m = _pct_return(col, 21)
        ret_3m = _pct_return(col, 63)
        rs_1w  = _relative_strength(ret_1w, spy_1w)
        rs_1m  = _relative_strength(ret_1m, spy_1m)
        rs_3m  = _relative_strength(ret_3m, spy_3m)
        mom    = _momentum(col)
        last_price = float(col.iloc[-1]) if not col.empty else None

        rs_1m_list.append(rs_1m)
        raw_sectors.append({
            **s, "closes": col,
            "ret_1w": ret_1w, "ret_1m": ret_1m, "ret_3m": ret_3m,
            "rs_1w": rs_1w, "rs_1m": rs_1m, "rs_3m": rs_3m,
            "momentum": mom, "last_price": last_price,
        })

    # Normalise RS scores after we have the full universe
    sector_list: list[SectorData] = []
    for s in raw_sectors:
        rs_score = _rs_to_score(s["rs_1m"], rs_1m_list)
        rrg      = _rrg_quadrant(s["rs_1m"], s["momentum"])
        sector_list.append(SectorData(
            ticker=s["ticker"],
            name=s["name"],
            cycle_phase=s["cycle"],
            return_1w=s["ret_1w"],
            return_1m=s["ret_1m"],
            return_3m=s["ret_3m"],
            rs_1w=s["rs_1w"],
            rs_1m=s["rs_1m"],
            rs_3m=s["rs_3m"],
            rs_score=rs_score,
            momentum=s["momentum"],
            rrg_quadrant=rrg,
            last_price=s["last_price"],
        ))

    # Cycle phase scores: average RS score of sectors in each phase
    phase_scores: dict[str, list[float]] = {p: [] for p in CYCLE_PHASES}
    for s in sector_list:
        if s.return_1m is not None:
            phase_scores[s.cycle_phase].append(s.rs_score)

    cycle_phase_scores = {
        phase: round(sum(vals) / len(vals), 1) if vals else 50.0
        for phase, vals in phase_scores.items()
    }

    dominant_phase = max(cycle_phase_scores, key=lambda p: cycle_phase_scores[p])
    dominant_description = _cycle_description(dominant_phase)

    result = SectorRotationData(
        sectors=sector_list,
        spy_return_1w=spy_1w,
        spy_return_1m=spy_1m,
        spy_return_3m=spy_3m,
        dominant_cycle_phase=dominant_phase,
        dominant_cycle_description=dominant_description,
        cycle_phase_scores=cycle_phase_scores,
    )

    _CACHE[cache_key] = (time.time(), result)
    logger.info(
        "Sector rotation computed — dominant cycle: %s (score %.1f)",
        dominant_phase, cycle_phase_scores[dominant_phase],
    )
    return result


def _cycle_description(phase: str) -> str:
    descriptions = {
        "Early Cycle": (
            "Early-cycle sectors (Financials, Consumer Discretionary, Real Estate) "
            "are leading. This typically occurs as the economy recovers from a downturn "
            "— credit expands, consumer spending rebounds, and rate-sensitive sectors benefit."
        ),
        "Mid Cycle": (
            "Mid-cycle sectors (Technology, Industrials, Communication Services) "
            "are in favour. This is characteristic of a maturing expansion — corporate "
            "investment rises, tech capex grows, and broad growth remains solid."
        ),
        "Late Cycle": (
            "Late-cycle sectors (Energy, Materials) are outperforming. "
            "This often signals an overheating economy where commodities are in demand, "
            "inflation is present, and the expansion may be nearing its peak."
        ),
        "Recession": (
            "Defensive/recession sectors (Utilities, Health Care, Consumer Staples) "
            "are leading. Investors are rotating into defensive havens, suggesting "
            "risk-off sentiment or expectations of an economic slowdown."
        ),
    }
    return descriptions.get(phase, "")
