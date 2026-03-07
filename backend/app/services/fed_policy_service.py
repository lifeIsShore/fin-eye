"""
app/services/fed_policy_service.py
───────────────────────────────────────────────────────────────────────────────
EXP-MACRO-ADV-02 — Fed Policy Visualiser

Data source: FRED (Federal Reserve Economic Data) via fredapi.
API key required (already in settings.fred_api_key).

FRED series used:
  FEDTARMD   — Fed Funds Rate Target Midpoint (daily, from 2008)
  DFEDTARL   — Fed Funds Rate Target Lower Bound (daily)
  DFEDTARU   — Fed Funds Rate Target Upper Bound (daily)
  FEDFUNDS   — Effective Fed Funds Rate (monthly)
  DFF        — Effective Federal Funds Rate (daily, 1954-present)
  SOFR       — Secured Overnight Financing Rate (daily, 2018-present)
  DPCREDIT   — Discount Window Primary Credit Rate (daily)
  WALCL      — Fed Balance Sheet: Total Assets (weekly, billions)
  RRPONTSYD  — Overnight Reverse Repo Facility (daily, USD billions)
  WRESBAL    — Reserve Balances with Fed (weekly, billions)

Forward rate expectations (market-implied):
  FF*1  — 30-Day Federal Funds Futures not available free via FRED.
  Instead we use the FRED forward rate series:
    THREEFF*  style is not reliable; we approximate using:
    - Current target rate
    - Dot plot median projections scraped from SEP (not available via FRED directly)
    
  For dot plot: FRED publishes SEP dot plot data via:
    FEDTARMD projections in the FRED API aren't always available.
    We use the 1-year and 2-year Treasury yields as forward rate proxies
    and the Fed's own FOMC projection series where available.

Simplified approach (no paid data):
  - Historical: DFEDTARL, DFEDTARU, DFF (last 3 years)
  - Current target range from DFEDTARL + DFEDTARU (latest)
  - Market expectations approximated from:
      THREEFF — 3-month Treasury Bill as floor proxy
      DGS1    — 1-year Treasury as 12-month expectation
      DGS2    — 2-year Treasury as 24-month expectation
  - Fed balance sheet trend: WALCL
  - Reverse repo: RRPONTSYD
  - Dot plot: hand-encoded from most recent publicly available SEP,
    updated each FOMC meeting (stored as a static dict here, updated manually
    each quarter — this is how most finance apps handle it since FRED
    doesn't publish machine-readable dot plot data)

Cache TTL: 3 hours (FRED data doesn't change intraday for most series)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_TTL = 10_800   # 3 hours
_CACHE: Dict[str, tuple] = {}

# ─── Dot plot (SEP median projections) ───────────────────────────────────────
# Source: Federal Reserve Summary of Economic Projections (SEP)
# Last updated: December 2024 FOMC meeting
# Format: {year: median_rate_pct, "longer_run": rate}
# These are the FOMC participants' median projections for year-end Fed funds rate.
DOT_PLOT_SEP: Dict[str, float] = {
    "2025": 3.875,   # Median of Dec 2024 dots: 3.75-4.00 range
    "2026": 3.375,
    "2027": 3.125,
    "longer_run": 3.00,
    "as_of": 2024.12,   # FOMC meeting date encoded as year.month
}

# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class RatePoint:
    date: str           # ISO date
    value: float        # rate in %


@dataclass
class RateRange:
    date: str
    lower: float
    upper: float
    midpoint: float


@dataclass
class DotPlotProjection:
    year: str           # "2025", "2026", "2027", "longer_run"
    median_rate: float
    as_of_label: str    # e.g. "Dec 2024 SEP"


@dataclass
class ForwardExpectation:
    label: str          # "12-month", "24-month"
    implied_rate: float
    source: str         # "1Y Treasury yield (proxy)"


@dataclass
class FedPolicySnapshot:
    # Current target
    current_target_lower: float
    current_target_upper: float
    current_midpoint: float
    current_effective_rate: Optional[float]

    # Historical path (daily, 3 years)
    target_range_history: List[RateRange]       # lower/upper/mid
    effective_rate_history: List[RatePoint]     # DFF daily

    # Balance sheet
    balance_sheet_history: List[RatePoint]      # WALCL weekly, billions
    current_balance_sheet_b: Optional[float]    # latest balance sheet, billions

    # Reverse repo
    reverse_repo_history: List[RatePoint]       # RRPONTSYD daily, billions
    current_reverse_repo_b: Optional[float]

    # SOFR vs EFFR spread
    sofr_history: List[RatePoint]               # SOFR daily

    # Market expectations (proxy)
    forward_expectations: List[ForwardExpectation]

    # SEP dot plot
    dot_plot: List[DotPlotProjection]

    # Context
    hike_or_cut_trend: str      # "Hiking" / "Cutting" / "Holding" / "Unknown"
    total_moves_ytd: int        # net hikes - cuts this calendar year in bps
    disclaimer: str = (
        "Rate data sourced from FRED (Federal Reserve Economic Data). "
        "Forward rate expectations are approximated using Treasury yields as proxies — "
        "they do not represent actual Fed funds futures pricing. "
        "Dot plot projections are from the most recent FOMC Summary of Economic Projections (SEP) "
        "and are updated quarterly. Not investment advice."
    )


# ─── FRED fetch helpers ───────────────────────────────────────────────────────

def _get_fred():
    """Lazy-load fredapi Fred instance."""
    from fredapi import Fred
    from app.config import settings
    return Fred(api_key=settings.fred_api_key)


def _fetch_series(series_id: str, start_date: str, end_date: Optional[str] = None) -> List[RatePoint]:
    """Fetch a FRED series and return as List[RatePoint]. Returns [] on failure."""
    try:
        fred = _get_fred()
        data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        if data is None or data.empty:
            return []
        points = []
        for dt, val in data.items():
            try:
                import math
                if val is None or (hasattr(val, '__float__') and math.isnan(float(val))):
                    continue
                iso = dt.date().isoformat() if hasattr(dt, 'date') else str(dt)[:10]
                points.append(RatePoint(date=iso, value=round(float(val), 4)))
            except Exception:
                continue
        return points
    except Exception as exc:
        logger.warning("FRED fetch failed for %s: %s", series_id, exc)
        return []


def _latest_value(points: List[RatePoint]) -> Optional[float]:
    return points[-1].value if points else None


def _start(years: int = 3) -> str:
    return (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")


# ─── Main analysis ────────────────────────────────────────────────────────────

def analyse_fed_policy() -> FedPolicySnapshot:
    """
    Fetch and assemble the full Fed policy picture.
    Cached for 3 hours (no key rotation needed — FRED is read-only).
    """
    cache_key = "fed_policy"
    now = time.time()
    if cache_key in _CACHE:
        ts, cached = _CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached

    start3y = _start(3)
    start1y = _start(1)

    # ── Target range history ─────────────────────────────────────────────────
    lower_pts = _fetch_series("DFEDTARL", start3y)
    upper_pts = _fetch_series("DFEDTARU", start3y)

    # Build aligned RateRange list
    lower_map = {p.date: p.value for p in lower_pts}
    upper_map = {p.date: p.value for p in upper_pts}
    all_dates = sorted(set(lower_map) | set(upper_map))
    range_history: List[RateRange] = []
    last_lower, last_upper = 0.0, 0.0
    for d in all_dates:
        l = lower_map.get(d, last_lower)
        u = upper_map.get(d, last_upper)
        last_lower, last_upper = l, u
        range_history.append(RateRange(date=d, lower=l, upper=u, midpoint=round((l + u) / 2, 4)))

    current_lower = last_lower
    current_upper = last_upper
    current_mid   = round((current_lower + current_upper) / 2, 4)

    # ── Effective rate (DFF, daily) ──────────────────────────────────────────
    dff_pts = _fetch_series("DFF", start3y)
    current_eff = _latest_value(dff_pts)

    # ── Balance sheet (WALCL, weekly, billions) ──────────────────────────────
    walcl_pts = _fetch_series("WALCL", start3y)
    # WALCL is in millions — convert to billions
    walcl_b = [RatePoint(date=p.date, value=round(p.value / 1000, 2)) for p in walcl_pts]
    current_bs = _latest_value(walcl_b)

    # ── Reverse repo (RRPONTSYD, daily, billions) ────────────────────────────
    rrp_pts = _fetch_series("RRPONTSYD", start1y)
    # RRPONTSYD is in billions already
    current_rrp = _latest_value(rrp_pts)

    # ── SOFR (daily) ─────────────────────────────────────────────────────────
    sofr_pts = _fetch_series("SOFR", start3y)

    # ── Market forward expectations (Treasury yield proxies) ────────────────
    t3m_pts = _fetch_series("DTB3",  start1y[-10:])   # 3-month T-Bill
    t1y_pts = _fetch_series("DGS1",  start1y[-10:])   # 1-year Treasury
    t2y_pts = _fetch_series("DGS2",  start1y[-10:])   # 2-year Treasury

    # Use latest values
    t3m = _latest_value(_fetch_series("DTB3", (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")))
    t1y = _latest_value(_fetch_series("DGS1", (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")))
    t2y = _latest_value(_fetch_series("DGS2", (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")))

    forward_expectations: List[ForwardExpectation] = []
    if t3m is not None:
        forward_expectations.append(ForwardExpectation(
            label="3-month (near-term)",
            implied_rate=t3m,
            source="3M T-Bill yield (proxy)",
        ))
    if t1y is not None:
        forward_expectations.append(ForwardExpectation(
            label="12-month",
            implied_rate=t1y,
            source="1Y Treasury yield (proxy)",
        ))
    if t2y is not None:
        forward_expectations.append(ForwardExpectation(
            label="24-month",
            implied_rate=t2y,
            source="2Y Treasury yield (proxy)",
        ))

    # ── Dot plot projections ─────────────────────────────────────────────────
    as_of_raw = DOT_PLOT_SEP.get("as_of", 0)
    yr  = int(as_of_raw)
    mo  = int(round((as_of_raw - yr) * 100))
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    as_of_label = f"{month_names.get(mo, '?')} {yr} SEP"

    dot_plot = [
        DotPlotProjection(year=yr_str, median_rate=rate, as_of_label=as_of_label)
        for yr_str, rate in DOT_PLOT_SEP.items()
        if yr_str != "as_of"
    ]

    # ── Hike/cut trend ───────────────────────────────────────────────────────
    hike_or_cut = "Unknown"
    total_moves_ytd = 0
    if len(range_history) >= 2:
        # Compare last 365 days of rate changes
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        recent_ranges = [r for r in range_history if r.date >= one_year_ago]
        if len(recent_ranges) >= 2:
            delta_bps = round((recent_ranges[-1].midpoint - recent_ranges[0].midpoint) * 100)
            total_moves_ytd = delta_bps
            if delta_bps > 25:
                hike_or_cut = "Hiking"
            elif delta_bps < -25:
                hike_or_cut = "Cutting"
            else:
                hike_or_cut = "Holding"

    result = FedPolicySnapshot(
        current_target_lower=current_lower,
        current_target_upper=current_upper,
        current_midpoint=current_mid,
        current_effective_rate=current_eff,
        target_range_history=range_history,
        effective_rate_history=dff_pts,
        balance_sheet_history=walcl_b,
        current_balance_sheet_b=current_bs,
        reverse_repo_history=rrp_pts,
        current_reverse_repo_b=current_rrp,
        sofr_history=sofr_pts,
        forward_expectations=forward_expectations,
        dot_plot=dot_plot,
        hike_or_cut_trend=hike_or_cut,
        total_moves_ytd=total_moves_ytd,
    )

    _CACHE[cache_key] = (now, result)
    return result
