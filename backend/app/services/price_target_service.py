"""
app/services/price_target_service.py

Sprint 5 — todos-v5 Phase 6.2 + 7.1

Probabilistic price target computation and Kelly Criterion position sizing.

Design principles:
  - ATR-based targets are ALWAYS computable (just need price + recent OHLCV)
  - Expected return is model-driven: Sharpe-weighted avg of per-timeframe confidence
  - Kelly sizing uses live accuracy from prediction DB when available,
    falls back to validation accuracy when not enough live data exists
  - All outputs are probabilistic estimates with explicit confidence bands
  - Nothing here is investment advice — framing enforced at display layer

Data flow:
  GET /api/v1/technical/{symbol}/price-targets
    → fetch_live_indicators(symbol)      # price + ATR from latest daily bars
    → load_signal_context(symbol)        # expected return from model signals
    → compute_price_targets(...)         # upside / expected / stop
    → compute_kelly(...)                 # position sizing suggestion
    → return PriceTargetResponse
"""

from __future__ import annotations

import logging
from typing import Optional

from app.services.market_data import OHLCVFetcher

logger = logging.getLogger(__name__)


# ── ATR + price fetcher ───────────────────────────────────────────────────────

def fetch_live_indicators_sync(symbol: str) -> dict:
    """
    Fetch the last 30 daily bars and compute:
      - current_price   (latest close)
      - atr_14          (14-period ATR in price units)
      - atr_pct         (ATR as % of price)
      - high_52w        (52-week high)
      - low_52w         (52-week low)

    Runs synchronously — call via run_in_executor from async endpoints.
    Returns empty dict on failure (caller must handle gracefully).
    """
    try:
        # 252 trading days ≈ 1 year for 52-week high/low
        records = OHLCVFetcher.fetch_historical_data(symbol, period="1y", interval="1d")
        if not records or len(records) < 15:
            logger.warning("Not enough daily bars for %s (%d)", symbol, len(records))
            return {}

        closes = [r.close for r in records]
        highs  = [r.high  for r in records]
        lows   = [r.low   for r in records]

        current_price = float(closes[-1])

        # True Range series
        tr_values = []
        for i in range(1, len(records)):
            hl  = highs[i]  - lows[i]
            hpc = abs(highs[i]  - closes[i - 1])
            lpc = abs(lows[i]   - closes[i - 1])
            tr_values.append(max(hl, hpc, lpc))

        # ATR-14 (simple rolling average over last 14 TR values)
        atr_14 = sum(tr_values[-14:]) / 14 if len(tr_values) >= 14 else sum(tr_values) / max(len(tr_values), 1)

        return {
            "current_price": round(current_price, 4),
            "atr_14":        round(atr_14, 4),
            "atr_pct":       round(atr_14 / current_price, 6) if current_price > 0 else 0.0,
            "high_52w":      round(max(highs), 4),
            "low_52w":       round(min(lows), 4),
            "pct_from_52w_high": round((current_price / max(highs) - 1) * 100, 2),
            "pct_from_52w_low":  round((current_price / min(lows)  - 1) * 100, 2),
            "bars_available": len(records),
        }
    except Exception as exc:
        logger.error("fetch_live_indicators_sync failed for %s: %s", symbol, exc)
        return {}


# ── Price target computation ──────────────────────────────────────────────────

def compute_price_targets(
    current_price:   float,
    atr_14:          float,
    expected_return: float,   # signed decimal, e.g. +0.018 = +1.8%
    confidence:      float,   # 0.5–1.0 from model
    horizon_label:   str = "~3 days",
) -> dict:
    """
    Probabilistic price targets based on ATR and model-expected return.

    Three levels:
      upside   = expected_price + 1 ATR   (optimistic — ~1σ above expected)
      expected = current × (1 + expected_return)   (base case from model)
      stop     = current − 1 ATR          (conservative stop, 1 ATR below current)

    All are probabilistic — not guarantees. ATR represents one standard deviation
    of typical daily price movement, so upside/stop are ≈ 1σ confidence intervals.
    """
    if current_price <= 0:
        return {}

    expected_price = current_price * (1 + expected_return)
    upside_target  = expected_price + atr_14
    stop_loss      = current_price - atr_14

    # Conservative stop slightly tighter (0.75 ATR) for lower-confidence signals
    if confidence < 0.60:
        stop_loss = current_price - (atr_14 * 0.75)

    return {
        "upside":   {
            "price":      round(upside_target, 2),
            "pct_change": round((upside_target  - current_price) / current_price * 100, 2),
            "basis":      "expected price + 1 ATR",
        },
        "expected": {
            "price":      round(expected_price, 2),
            "pct_change": round(expected_return * 100, 2),
            "basis":      f"model expected return over {horizon_label}",
        },
        "stop": {
            "price":      round(max(stop_loss, 0.01), 2),
            "pct_change": round((max(stop_loss, 0.01) - current_price) / current_price * 100, 2),
            "basis":      "current price − 1 ATR" if confidence >= 0.60 else "current − 0.75 ATR (tighter for lower confidence)",
        },
        "risk_reward_ratio": round(
            abs(upside_target - current_price) / max(abs(current_price - stop_loss), 0.01),
            2,
        ),
        "horizon_label": horizon_label,
        "atr_used":      round(atr_14, 2),
        "confidence":    round(confidence, 4),
        "note": "Probabilistic estimate. ATR represents typical daily price movement (≈1σ). Not a guarantee.",
    }


# ── Kelly Criterion ───────────────────────────────────────────────────────────

def compute_kelly(
    win_rate:       float,          # fraction of correct predictions (0–1)
    avg_win_pct:    float,          # average return when correct (decimal)
    avg_loss_pct:   float,          # average return when wrong (decimal, negative)
    n_resolved:     int   = 0,      # how many outcomes resolved (for confidence)
    source:         str   = "validation",  # "live" | "validation"
) -> dict:
    """
    Half-Kelly Criterion position sizing suggestion.

    Full Kelly:  f = (win_rate / |avg_loss|) - ((1 - win_rate) / avg_win)
    Half Kelly:  f / 2  (standard practice — reduces variance, avoids ruin)
    Cap:         25% of portfolio (hard limit, regardless of Kelly output)

    When live data is sparse (< 30 resolved predictions), blend live + validation
    accuracy to avoid overconfidence on small samples.

    Returns a dict with the suggested fraction and full formula transparency.
    """
    if win_rate <= 0 or avg_win_pct <= 0 or avg_loss_pct >= 0:
        return {
            "suggested_pct": 0.0,
            "full_kelly":    0.0,
            "half_kelly":    0.0,
            "source":        source,
            "n_resolved":    n_resolved,
            "insufficient_data": True,
            "note": "Cannot compute Kelly — need positive win rate, positive avg_win, and negative avg_loss.",
        }

    avg_loss_abs = abs(avg_loss_pct)

    # Full Kelly formula
    full_kelly = (win_rate / avg_loss_abs) - ((1 - win_rate) / avg_win_pct)
    half_kelly = full_kelly / 2.0

    # Cap at 25% — Kelly can suggest absurd fractions with high win rates
    capped = max(0.0, min(half_kelly, 0.25))

    # Confidence penalty for small live samples
    confidence_penalty = 1.0
    if source == "live" and n_resolved < 30:
        confidence_penalty = n_resolved / 30.0  # linear scale: 0 at 0 predictions, 1.0 at 30
        capped *= confidence_penalty

    suggested_pct = round(capped * 100, 1)  # as a percentage

    return {
        "suggested_pct":      suggested_pct,         # e.g. 8.4 = "8.4% of portfolio"
        "full_kelly":         round(full_kelly, 4),
        "half_kelly":         round(half_kelly, 4),
        "capped_at_25pct":    half_kelly > 0.25,
        "confidence_penalty": round(confidence_penalty, 3) if source == "live" else 1.0,
        "inputs": {
            "win_rate":    round(win_rate, 4),
            "avg_win_pct": round(avg_win_pct * 100, 2),
            "avg_loss_pct": round(avg_loss_pct * 100, 2),
        },
        "source":        source,
        "n_resolved":    n_resolved,
        "insufficient_data": False,
        "formula": "Half-Kelly = ((win_rate / |avg_loss|) - ((1-win_rate) / avg_win)) / 2",
        "note": (
            "Half-Kelly Criterion — a mathematical position sizing suggestion. "
            "Adjust for your own risk tolerance, portfolio size, and conviction. "
            "This is NOT investment advice."
        ),
    }


# ── Expected return from model signals ───────────────────────────────────────

def expected_return_from_signals(signals: list[dict]) -> tuple[float, float, str]:
    """
    Derive expected return and confidence from a list of trained ML signals.

    Each signal has:
      - direction:         "Bullish" | "Bearish"
      - confidence:        0–100 (model probability %)
      - validation_sharpe: float
      - horizon_periods:   int
      - timeframe:         str

    Returns (expected_return, confidence_fraction, horizon_label).

    Method:
      - Sharpe-weighted average of per-timeframe expected returns
      - Per-timeframe expected return = (confidence/100 - 0.5) * 0.06
        (maps 50% conf → 0% return, 100% conf → +3% return)
      - Bearish signals flip the sign
    """
    if not signals:
        return 0.0, 0.5, "~3 days"

    # Prefer daily timeframe for the horizon label
    tf_priority = ["1d", "4h", "1wk", "1h", "1mo"]
    anchor_tf   = next((s for p in tf_priority for s in signals if s.get("timeframe") == p), signals[0])
    horizon_periods = anchor_tf.get("horizon_periods", 3)
    tf = anchor_tf.get("timeframe", "1d")
    horizon_label_map = {
        "1h": f"~{horizon_periods * 1}h",
        "4h": f"~{horizon_periods * 4}h",
        "1d": f"~{horizon_periods} days",
        "1wk": f"~{horizon_periods} weeks",
        "1mo": f"~{horizon_periods} months",
    }
    horizon_label = horizon_label_map.get(tf, f"~{horizon_periods} periods")

    total_weight    = 0.0
    weighted_return = 0.0
    weighted_conf   = 0.0

    for sig in signals:
        sharpe = max(sig.get("validation_sharpe", 0.0) or 0.0, 0.1)
        conf   = sig.get("confidence", 50.0) / 100.0      # 0.5–1.0
        # Expected return magnitude: scales from 0% at 50% conf to 3% at 100% conf
        ret_magnitude = (conf - 0.5) * 0.06
        # Sign from direction
        direction = sig.get("direction", "Neutral")
        signed_ret = ret_magnitude if direction == "Bullish" else (
                    -ret_magnitude if direction == "Bearish" else 0.0
        )
        weighted_return += signed_ret * sharpe
        weighted_conf   += conf       * sharpe
        total_weight    += sharpe

    if total_weight > 0:
        avg_return = weighted_return / total_weight
        avg_conf   = weighted_conf   / total_weight
    else:
        avg_return = 0.0
        avg_conf   = 0.5

    return round(avg_return, 6), round(avg_conf, 4), horizon_label
