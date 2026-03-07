"""
app/services/options_service.py
─────────────────────────────────────────────────────────────────────────────
EXP-OPT-01 — Options Fear & Greed Signal

Computes three interrelated options-market signals from yfinance data:

  1. Put/Call Ratio (PCR)
     total open interest in puts / total open interest in calls.
     Elevated PCR → hedging/fear; depressed PCR → complacency/greed.

  2. IV Skew
     25-delta put IV minus 25-delta call IV (approximated as the
     implied volatility of the nearest OTM put vs nearest OTM call at
     roughly 10% away from spot).
     Positive skew → market paying more for downside protection (bearish lean).
     Negative skew → market pricing in upside surprise (bullish lean).

  3. Max Pain
     The strike price at which the total value of all options contracts
     is minimised — i.e. where option sellers face the smallest loss.
     Many traders watch whether spot converges toward max pain near expiry.

  4. Options Fear & Greed Score (0–100)
     Composite score derived from PCR and IV skew, normalised to 0–100:
       0 = Extreme Fear (PCR >> 1, high negative skew for puts)
     100 = Extreme Greed (PCR << 0.5, high negative skew for calls)

Data source: yfinance options chain (already installed — no new API key needed).

Limitations (clearly surfaced to users):
  - yfinance options data is 15-min delayed; near-expiry data may be sparse.
  - PCR uses aggregate open interest across ALL available expiries, not just
    the near-term contract, so it should be read as a broad sentiment proxy
    rather than a precise short-term signal.
  - Max pain is a theoretical construct with mixed empirical support; present
    educational context clearly.

Design:
  - All computation is synchronous CPU-bound work.
  - Callers should use run_in_executor when calling from async contexts.
  - Results are cached in-process for 15 minutes to avoid hammering yfinance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# ── In-process cache ──────────────────────────────────────────────────────────
_CACHE: dict[str, tuple[float, "OptionsAnalysis"]] = {}
_CACHE_TTL_S = 900  # 15 minutes — matches scheduler cadence


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass
class OptionChainSummary:
    expiry: str
    calls_oi: int
    puts_oi: int
    pcr: float                     # puts_oi / calls_oi for this expiry
    total_call_volume: int
    total_put_volume: int
    max_pain_strike: Optional[float]


@dataclass
class OptionsAnalysis:
    symbol: str
    spot_price: float

    # Aggregate across all expiries
    total_calls_oi: int
    total_puts_oi: int
    aggregate_pcr: float           # 0–∞;  >1 = more puts open; <1 = more calls

    # PCR signal classification
    pcr_label: str                 # "Extreme Fear" | "Fear" | "Neutral" | "Greed" | "Extreme Greed"
    pcr_interpretation: str        # plain-English explanation

    # IV skew (nearest expiry)
    iv_skew: Optional[float]       # put IV - call IV (%); positive = put-skewed (bearish)
    iv_skew_label: str
    near_put_iv: Optional[float]
    near_call_iv: Optional[float]

    # Max pain (nearest expiry with sufficient OI)
    max_pain_strike: Optional[float]
    max_pain_distance_pct: Optional[float]  # (max_pain - spot) / spot * 100

    # Composite score
    fear_greed_score: float        # 0–100;  0 = extreme fear, 100 = extreme greed
    fear_greed_label: str

    # Per-expiry breakdown (up to 5 nearest)
    expiry_breakdown: list[OptionChainSummary] = field(default_factory=list)

    computed_at: float = field(default_factory=time.time)

    # Educational disclaimer
    disclaimer: str = (
        "Options data is 15-min delayed and uses aggregate open interest across "
        "all expiries. Put/Call Ratio and IV Skew are sentiment proxies — they "
        "indicate positioning, not guaranteed future direction. Max Pain is a "
        "theoretical construct with mixed empirical support. This is educational "
        "analysis only, not investment advice."
    )


# ── PCR classification ─────────────────────────────────────────────────────────

def _classify_pcr(pcr: float) -> tuple[str, str]:
    """Return (label, interpretation) for a given aggregate PCR."""
    if pcr > 1.5:
        return (
            "Extreme Fear",
            f"PCR of {pcr:.2f} is very elevated — significantly more put open interest "
            "than calls. This indicates heavy hedging or directional bearish bets. "
            "Contrarian traders sometimes read extreme PCR as a potential bottom signal.",
        )
    if pcr > 1.0:
        return (
            "Fear",
            f"PCR of {pcr:.2f} is above 1 — more put OI than call OI. "
            "The market is leaning bearish in its options positioning.",
        )
    if pcr > 0.7:
        return (
            "Neutral",
            f"PCR of {pcr:.2f} is within a neutral range. "
            "Puts and calls are roughly balanced — no strong directional signal.",
        )
    if pcr > 0.5:
        return (
            "Greed",
            f"PCR of {pcr:.2f} is below 0.7 — more call OI than puts. "
            "The market is leaning bullish in its options positioning.",
        )
    return (
        "Extreme Greed",
        f"PCR of {pcr:.2f} is very low — call OI substantially outweighs puts. "
        "This level of call positioning can indicate complacency or speculative froth. "
        "Contrarian traders sometimes read extreme low PCR as a caution signal.",
    )


# ── IV skew classification ─────────────────────────────────────────────────────

def _classify_skew(skew: Optional[float]) -> str:
    if skew is None:
        return "Unavailable"
    if skew > 10:
        return "Steep Put Skew — strong downside hedging demand"
    if skew > 4:
        return "Moderate Put Skew — mild hedging preference"
    if skew > -4:
        return "Flat — balanced IV between puts and calls"
    if skew > -10:
        return "Moderate Call Skew — slight upside speculation"
    return "Steep Call Skew — elevated demand for upside calls"


# ── Fear & Greed composite ─────────────────────────────────────────────────────

def _compute_fg_score(pcr: float, iv_skew: Optional[float]) -> tuple[float, str]:
    """
    Combine PCR and IV skew into a 0–100 score.
    PCR carries 70% weight; IV skew carries 30%.

    PCR contribution:
      PCR ≥ 2.0  → 0 (extreme fear)
      PCR ≤ 0.3  → 100 (extreme greed)
      Linear interpolation between those endpoints.

    Skew contribution:
      skew ≥ +20% → 0 (extreme fear)
      skew ≤ −20% → 100 (extreme greed)
      Linear interpolation.
    """
    # PCR component (0–100)
    pcr_norm = max(0.0, min(1.0, (2.0 - pcr) / 1.7))
    pcr_score = pcr_norm * 100

    # Skew component (0–100) — only if available
    if iv_skew is not None:
        skew_norm = max(0.0, min(1.0, (-iv_skew + 20) / 40))
        skew_score = skew_norm * 100
        composite = pcr_score * 0.70 + skew_score * 0.30
    else:
        composite = pcr_score

    composite = round(max(0.0, min(100.0, composite)), 1)

    if composite >= 75:
        label = "Greed"
    elif composite >= 60:
        label = "Mild Greed"
    elif composite >= 40:
        label = "Neutral"
    elif composite >= 25:
        label = "Mild Fear"
    else:
        label = "Fear"

    return composite, label


# ── Max pain computation ───────────────────────────────────────────────────────

def _compute_max_pain(chain: pd.DataFrame) -> Optional[float]:
    """
    Compute the max pain strike from a combined calls+puts DataFrame.

    For each candidate strike, sum the intrinsic value that would be owed to
    ALL option holders if spot expired at that strike. The strike that minimises
    this total liability to option sellers is max pain.

    chain must have columns: strike, call_oi, put_oi.
    """
    if chain.empty:
        return None

    strikes = sorted(chain["strike"].unique())
    if len(strikes) < 3:
        return None

    min_pain = float("inf")
    max_pain_strike = strikes[0]

    for s in strikes:
        # Intrinsic value owed to call holders if spot = s
        call_pain = float(
            chain.apply(
                lambda row: max(0.0, s - row["strike"]) * row.get("call_oi", 0),
                axis=1,
            ).sum()
        )
        # Intrinsic value owed to put holders if spot = s
        put_pain = float(
            chain.apply(
                lambda row: max(0.0, row["strike"] - s) * row.get("put_oi", 0),
                axis=1,
            ).sum()
        )
        total_pain = call_pain + put_pain
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = s

    return float(max_pain_strike)


# ── IV skew computation ────────────────────────────────────────────────────────

def _compute_iv_skew(
    spot: float,
    calls: pd.DataFrame,
    puts: pd.DataFrame,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Approximate IV skew as:
      put_iv (10% OTM) minus call_iv (10% OTM)

    Both expressed as percentages (e.g. 25.0 = 25% annualised IV).

    Returns (skew, near_put_iv, near_call_iv).
    """
    target_put_strike  = spot * 0.90   # 10% OTM put
    target_call_strike = spot * 1.10   # 10% OTM call

    def nearest_iv(df: pd.DataFrame, target: float) -> Optional[float]:
        if df.empty or "impliedVolatility" not in df.columns:
            return None
        df = df.copy()
        df["dist"] = (df["strike"] - target).abs()
        row = df.loc[df["dist"].idxmin()]
        iv = row.get("impliedVolatility")
        if iv is None or pd.isna(iv) or float(iv) == 0:
            return None
        return round(float(iv) * 100, 2)  # convert to %

    near_put_iv  = nearest_iv(puts,  target_put_strike)
    near_call_iv = nearest_iv(calls, target_call_strike)

    if near_put_iv is not None and near_call_iv is not None:
        return round(near_put_iv - near_call_iv, 2), near_put_iv, near_call_iv

    return None, near_put_iv, near_call_iv


# ── Main entry point ───────────────────────────────────────────────────────────

def analyse_options(symbol: str) -> OptionsAnalysis:
    """
    Fetch options chain for `symbol` via yfinance and compute all signals.

    This function is synchronous (yfinance is sync). Callers from async
    contexts must wrap with run_in_executor().

    Results are cached for 15 minutes per symbol.
    """
    sym = symbol.upper()

    # ── Cache check ────────────────────────────────────────────────────────
    cached = _CACHE.get(sym)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_S:
        logger.debug("Options cache HIT for %s", sym)
        return cached[1]

    logger.info("Fetching options chain for %s from yfinance", sym)

    ticker = yf.Ticker(sym)

    # ── Spot price ─────────────────────────────────────────────────────────
    try:
        info = ticker.fast_info
        spot = float(getattr(info, "last_price", None) or 0)
        if spot == 0:
            # Fallback: last close from history
            hist = ticker.history(period="2d")
            spot = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
    except Exception as exc:
        logger.warning("Could not fetch spot price for %s: %s", sym, exc)
        spot = 0.0

    # ── Expiries ───────────────────────────────────────────────────────────
    try:
        expiries = ticker.options
    except Exception as exc:
        logger.error("No options data for %s: %s", sym, exc)
        raise ValueError(f"No options data available for {sym}. "
                         "The ticker may not have listed options.") from exc

    if not expiries:
        raise ValueError(f"No options expiries found for {sym}.")

    # Use up to 5 nearest expiries for the breakdown; first expiry for IV skew
    target_expiries = list(expiries[:5])

    all_call_oi = 0
    all_put_oi  = 0
    all_call_vol = 0
    all_put_vol  = 0
    expiry_breakdown: list[OptionChainSummary] = []

    # Combined chain for max pain (first expiry)
    first_chain_calls: pd.DataFrame = pd.DataFrame()
    first_chain_puts:  pd.DataFrame = pd.DataFrame()

    for i, exp in enumerate(target_expiries):
        try:
            chain = ticker.option_chain(exp)
            calls = chain.calls
            puts  = chain.puts

            if calls.empty and puts.empty:
                continue

            c_oi  = int(calls["openInterest"].fillna(0).sum()) if "openInterest" in calls.columns else 0
            p_oi  = int(puts["openInterest"].fillna(0).sum())  if "openInterest" in puts.columns  else 0
            c_vol = int(calls["volume"].fillna(0).sum())       if "volume"       in calls.columns else 0
            p_vol = int(puts["volume"].fillna(0).sum())        if "volume"       in puts.columns  else 0
            pcr   = round(p_oi / c_oi, 4) if c_oi > 0 else 0.0

            # Build merged chain for max pain
            if i == 0 and not calls.empty and not puts.empty:
                first_chain_calls = calls[["strike", "openInterest"]].rename(
                    columns={"openInterest": "call_oi"}
                )
                first_chain_puts = puts[["strike", "openInterest"]].rename(
                    columns={"openInterest": "put_oi"}
                )
                first_chain_calls = calls.copy()
                first_chain_puts  = puts.copy()

            # Max pain for this expiry
            if not calls.empty and not puts.empty:
                merged = pd.merge(
                    calls[["strike", "openInterest"]].rename(columns={"openInterest": "call_oi"}),
                    puts[["strike", "openInterest"]].rename(columns={"openInterest": "put_oi"}),
                    on="strike",
                    how="outer",
                ).fillna(0)
                exp_max_pain = _compute_max_pain(merged)
            else:
                exp_max_pain = None

            all_call_oi  += c_oi
            all_put_oi   += p_oi
            all_call_vol += c_vol
            all_put_vol  += p_vol

            expiry_breakdown.append(
                OptionChainSummary(
                    expiry=exp,
                    calls_oi=c_oi,
                    puts_oi=p_oi,
                    pcr=pcr,
                    total_call_volume=c_vol,
                    total_put_volume=p_vol,
                    max_pain_strike=exp_max_pain,
                )
            )
        except Exception as exc:
            logger.warning("Failed to fetch chain for %s %s: %s", sym, exp, exc)
            continue

    if all_call_oi == 0 and all_put_oi == 0:
        raise ValueError(f"Options data for {sym} returned no open interest. "
                         "The market may be closed or data may be delayed.")

    # ── Aggregate PCR ──────────────────────────────────────────────────────
    agg_pcr = round(all_put_oi / all_call_oi, 4) if all_call_oi > 0 else 0.0
    pcr_label, pcr_interp = _classify_pcr(agg_pcr)

    # ── IV skew (first expiry) ─────────────────────────────────────────────
    iv_skew, near_put_iv, near_call_iv = (None, None, None)
    if not first_chain_calls.empty and not first_chain_puts.empty and spot > 0:
        iv_skew, near_put_iv, near_call_iv = _compute_iv_skew(
            spot, first_chain_calls, first_chain_puts
        )
    iv_skew_label = _classify_skew(iv_skew)

    # ── Max pain (first expiry with sufficient OI) ─────────────────────────
    max_pain_strike: Optional[float] = None
    if expiry_breakdown:
        max_pain_strike = expiry_breakdown[0].max_pain_strike

    max_pain_dist: Optional[float] = None
    if max_pain_strike is not None and spot > 0:
        max_pain_dist = round((max_pain_strike - spot) / spot * 100, 2)

    # ── Composite fear/greed score ─────────────────────────────────────────
    fg_score, fg_label = _compute_fg_score(agg_pcr, iv_skew)

    result = OptionsAnalysis(
        symbol=sym,
        spot_price=round(spot, 2),
        total_calls_oi=all_call_oi,
        total_puts_oi=all_put_oi,
        aggregate_pcr=agg_pcr,
        pcr_label=pcr_label,
        pcr_interpretation=pcr_interp,
        iv_skew=iv_skew,
        iv_skew_label=iv_skew_label,
        near_put_iv=near_put_iv,
        near_call_iv=near_call_iv,
        max_pain_strike=max_pain_strike,
        max_pain_distance_pct=max_pain_dist,
        fear_greed_score=fg_score,
        fear_greed_label=fg_label,
        expiry_breakdown=expiry_breakdown,
    )

    _CACHE[sym] = (time.time(), result)
    logger.info(
        "Options analysis for %s: PCR=%.2f (%s) FG=%.0f (%s) MaxPain=%.2f",
        sym, agg_pcr, pcr_label, fg_score, fg_label,
        max_pain_strike or 0,
    )
    return result
