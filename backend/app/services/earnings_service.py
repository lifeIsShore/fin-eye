"""
app/services/earnings_service.py
───────────────────────────────────────────────────────────────────────────────
EXP-EARN-01 — Earnings Calendar & Surprise Tracker

Data source: yfinance (already installed, no new dependency)

Features:
  1. Single-stock earnings history — EPS actual vs estimate, revenue actual vs
     estimate, surprise %, date, period label (Q1/Q2…). Last 8 quarters.
  2. Upcoming earnings date — next earnings date, estimated EPS, days-to-event
     countdown.
  3. Watchlist earnings calendar — upcoming earnings for a list of tickers
     within the next N days.
  4. Surprise score (0–100) — composite of last 4 quarters' EPS beat/miss
     magnitude and consistency.

Cache TTL: 6 hours (earnings dates rarely change intraday; revisions happen
weekly at most).

No API key required — yfinance fetches from Yahoo Finance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL = 21_600   # 6 hours
_CACHE: Dict[str, tuple] = {}   # symbol -> (ts, EarningsAnalysis)
_CALENDAR_CACHE: Dict[str, tuple] = {}  # "calendar:{symbols_hash}:{days}" -> (ts, list)


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class EarningsRecord:
    """One historical earnings quarter."""
    period_label: str          # e.g. "Q3 2024"
    earnings_date: str         # YYYY-MM-DD (report date)
    eps_estimate: Optional[float]
    eps_actual: Optional[float]
    eps_surprise: Optional[float]      # actual - estimate
    eps_surprise_pct: Optional[float]  # (actual - estimate) / |estimate| * 100
    revenue_estimate: Optional[float]  # in USD
    revenue_actual: Optional[float]
    revenue_surprise_pct: Optional[float]
    beat_eps: Optional[bool]           # True/False/None


@dataclass
class UpcomingEarnings:
    """Next scheduled earnings event for a symbol."""
    symbol: str
    company_name: str
    earnings_date: str         # YYYY-MM-DD
    days_until: int
    eps_estimate: Optional[float]
    revenue_estimate: Optional[float]
    time_of_day: str           # "BMO" (before market open) / "AMC" (after market close) / "Unknown"


@dataclass
class SurpriseScore:
    """Composite beat/miss score from recent quarters."""
    score: float               # 0–100
    label: str                 # "Strong Beater" / "Consistent Beater" / "Mixed" / "Miss Tendency" / "Consistent Misser"
    quarters_beat: int
    quarters_missed: int
    quarters_inline: int       # within ±2%
    avg_eps_surprise_pct: Optional[float]
    consecutive_beats: int     # streak of beats going into latest quarter


@dataclass
class EarningsAnalysis:
    symbol: str
    company_name: str
    history: List[EarningsRecord]          # newest first, up to 8 quarters
    upcoming: Optional[UpcomingEarnings]
    surprise_score: SurpriseScore
    disclaimer: str = (
        "Earnings data sourced from Yahoo Finance via yfinance (15-min delayed). "
        "EPS estimates are analyst consensus at time of data fetch and may differ from "
        "values at the actual report date. Not investment advice."
    )


# ─── yfinance helpers ─────────────────────────────────────────────────────────

def _quarter_label(dt: date) -> str:
    """Convert a date to 'Q1 2024' style label."""
    q = (dt.month - 1) // 3 + 1
    return f"Q{q} {dt.year}"


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if pd.isna(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _surprise_pct(actual: Optional[float], estimate: Optional[float]) -> Optional[float]:
    if actual is None or estimate is None:
        return None
    if abs(estimate) < 1e-9:
        return None
    return round((actual - estimate) / abs(estimate) * 100, 2)


# ─── Core fetch ───────────────────────────────────────────────────────────────

def analyse_earnings(symbol: str) -> EarningsAnalysis:
    """
    Fetch and analyse earnings data for a ticker.
    Results cached for 6 hours.
    """
    sym = symbol.upper()
    now = time.time()

    if sym in _CACHE:
        ts, cached = _CACHE[sym]
        if now - ts < CACHE_TTL:
            return cached

    ticker = yf.Ticker(sym)
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        pass

    company_name = info.get("longName") or info.get("shortName") or sym

    # ── Historical earnings ──────────────────────────────────────────────────
    history: List[EarningsRecord] = []

    try:
        # yfinance earnings_history gives EPS actual + estimate per quarter
        earnings_hist = ticker.earnings_history
        if earnings_hist is not None and not earnings_hist.empty:
            # Columns: Earnings Date, EPS Estimate, Reported EPS, Surprise(%)
            for _, row in earnings_hist.iterrows():
                raw_date = row.get("Earnings Date") or row.name
                try:
                    if isinstance(raw_date, str):
                        dt = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                    elif hasattr(raw_date, "date"):
                        dt = raw_date.date()
                    else:
                        dt = date.fromisoformat(str(raw_date)[:10])
                except Exception:
                    continue

                eps_est    = _safe_float(row.get("EPS Estimate"))
                eps_act    = _safe_float(row.get("Reported EPS"))
                surprise   = _safe_float(row.get("Surprise(%)"))

                # Derive from raw if surprise% column missing
                if surprise is None:
                    surprise = _surprise_pct(eps_act, eps_est)

                eps_surp_abs = None
                if eps_act is not None and eps_est is not None:
                    eps_surp_abs = round(eps_act - eps_est, 4)

                beat = None
                if surprise is not None:
                    beat = surprise > 2.0

                history.append(EarningsRecord(
                    period_label=_quarter_label(dt),
                    earnings_date=dt.isoformat(),
                    eps_estimate=eps_est,
                    eps_actual=eps_act,
                    eps_surprise=eps_surp_abs,
                    eps_surprise_pct=surprise,
                    revenue_estimate=None,
                    revenue_actual=None,
                    revenue_surprise_pct=None,
                    beat_eps=beat,
                ))
    except Exception as exc:
        logger.warning("earnings_history failed for %s: %s", sym, exc)

    # Also try income_stmt for revenue actuals (best-effort enrichment)
    try:
        inc = ticker.quarterly_income_stmt
        if inc is not None and not inc.empty and "Total Revenue" in inc.index:
            rev_row = inc.loc["Total Revenue"]
            rev_by_date: Dict[str, float] = {}
            for col in rev_row.index:
                try:
                    dt_str = pd.Timestamp(col).date().isoformat()
                    rev_by_date[dt_str] = float(rev_row[col])
                except Exception:
                    pass
            # Match to history records by approximate quarter
            for rec in history:
                rec_dt = date.fromisoformat(rec.earnings_date)
                # Look within ±45 days
                for rev_dt_str, rev_val in rev_by_date.items():
                    rev_dt = date.fromisoformat(rev_dt_str)
                    if abs((rec_dt - rev_dt).days) <= 45:
                        rec.revenue_actual = round(rev_val, 0)
                        break
    except Exception:
        pass

    # Sort newest-first, cap at 8
    history.sort(key=lambda r: r.earnings_date, reverse=True)
    history = history[:8]

    # ── Upcoming earnings ────────────────────────────────────────────────────
    upcoming: Optional[UpcomingEarnings] = None
    try:
        cal = ticker.calendar
        if cal is not None:
            # calendar is a dict or DataFrame depending on yfinance version
            if isinstance(cal, dict):
                earn_dates = cal.get("Earnings Date", [])
                eps_est_val = cal.get("Earnings Average")
                rev_est_val = cal.get("Revenue Average")
            elif isinstance(cal, pd.DataFrame):
                earn_dates = cal.get("Earnings Date", pd.Series()).tolist() if "Earnings Date" in cal.columns else []
                eps_est_val = cal.get("Earnings Average", pd.Series()).iloc[0] if "Earnings Average" in cal.columns else None
                rev_est_val = cal.get("Revenue Average", pd.Series()).iloc[0] if "Revenue Average" in cal.columns else None
            else:
                earn_dates = []
                eps_est_val = None
                rev_est_val = None

            # Find the soonest future date
            today = date.today()
            future_dates = []
            for d_raw in (earn_dates if isinstance(earn_dates, list) else [earn_dates]):
                try:
                    if isinstance(d_raw, str):
                        d_parsed = datetime.strptime(d_raw[:10], "%Y-%m-%d").date()
                    elif hasattr(d_raw, "date"):
                        d_parsed = d_raw.date()
                    else:
                        d_parsed = date.fromisoformat(str(d_raw)[:10])
                    if d_parsed >= today:
                        future_dates.append(d_parsed)
                except Exception:
                    continue

            if future_dates:
                next_date = min(future_dates)
                days_until = (next_date - today).days

                # Guess time of day from date offset heuristic
                # yfinance sometimes gives two dates (BMO estimate vs AMC estimate)
                time_of_day = "Unknown"
                if len(future_dates) >= 2:
                    time_of_day = "TBD (range given)"

                upcoming = UpcomingEarnings(
                    symbol=sym,
                    company_name=company_name,
                    earnings_date=next_date.isoformat(),
                    days_until=days_until,
                    eps_estimate=_safe_float(eps_est_val),
                    revenue_estimate=_safe_float(rev_est_val),
                    time_of_day=time_of_day,
                )
    except Exception as exc:
        logger.debug("Calendar fetch failed for %s: %s", sym, exc)

    # ── Surprise score ───────────────────────────────────────────────────────
    surprise_score = _compute_surprise_score(history)

    result = EarningsAnalysis(
        symbol=sym,
        company_name=company_name,
        history=history,
        upcoming=upcoming,
        surprise_score=surprise_score,
    )

    _CACHE[sym] = (now, result)
    return result


def _compute_surprise_score(history: List[EarningsRecord]) -> SurpriseScore:
    """
    Compute a 0–100 surprise score from the last 4 quarters.

    Methodology:
    - Weight recent quarters more (4x, 3x, 2x, 1x).
    - Each beat contributes positively (scaled by magnitude), each miss negatively.
    - Score is normalised to 0–100 (50 = neutral / no history).
    - Inline = surprise within ±2%.
    """
    recent = history[:4]  # last 4 quarters

    beats = 0
    misses = 0
    inline = 0
    weighted_sum = 0.0
    weight_total = 0.0
    surprise_pcts = []

    for i, rec in enumerate(recent):
        w = 4 - i  # weight: 4 for most recent, 1 for oldest
        if rec.eps_surprise_pct is None:
            continue
        pct = rec.eps_surprise_pct
        surprise_pcts.append(pct)
        weight_total += w

        if pct > 2.0:
            beats += 1
            weighted_sum += w * min(pct, 30.0)   # cap mega-beats at 30%
        elif pct < -2.0:
            misses += 1
            weighted_sum -= w * min(abs(pct), 30.0)
        else:
            inline += 1
            weighted_sum += w * pct   # small contribution

    if weight_total == 0:
        raw_score = 0.0
    else:
        raw_score = weighted_sum / weight_total   # range roughly -30 to +30

    # Normalise: sigmoid-like mapping to 0–100
    # 0 → 50, +15 → ~85, -15 → ~15
    import math
    score = 50.0 + 50.0 * math.tanh(raw_score / 15.0)
    score = round(max(5.0, min(95.0, score)), 1)

    # Consecutive beat streak
    streak = 0
    for rec in recent:
        if rec.beat_eps:
            streak += 1
        else:
            break

    # Label
    if score >= 75:
        label = "Strong Beater"
    elif score >= 60:
        label = "Consistent Beater"
    elif score >= 40:
        label = "Mixed"
    elif score >= 25:
        label = "Miss Tendency"
    else:
        label = "Consistent Misser"

    avg_surp = round(sum(surprise_pcts) / len(surprise_pcts), 2) if surprise_pcts else None

    return SurpriseScore(
        score=score,
        label=label,
        quarters_beat=beats,
        quarters_missed=misses,
        quarters_inline=inline,
        avg_eps_surprise_pct=avg_surp,
        consecutive_beats=streak,
    )


# ─── Watchlist calendar ───────────────────────────────────────────────────────

def get_upcoming_calendar(symbols: List[str], days_ahead: int = 30) -> List[UpcomingEarnings]:
    """
    Return upcoming earnings events for a list of symbols within `days_ahead` days.
    Results cached independently per symbol (reuses analyse_earnings cache).
    """
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    results: List[UpcomingEarnings] = []

    for sym in symbols:
        try:
            analysis = analyse_earnings(sym.upper())
            if analysis.upcoming and date.fromisoformat(analysis.upcoming.earnings_date) <= cutoff:
                results.append(analysis.upcoming)
        except Exception as exc:
            logger.debug("Calendar skip %s: %s", sym, exc)

    results.sort(key=lambda x: x.earnings_date)
    return results
