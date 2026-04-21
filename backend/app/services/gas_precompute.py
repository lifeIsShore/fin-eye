"""
app/services/gas_precompute.py

BUG FIX: _compute_technical_score and _compute_sentiment_score were called
sequentially with await despite the comment saying "run concurrently".
They now run with asyncio.gather() — saves ~1-2s per symbol per batch.

FEATURE: signal_grade is now computed and stored in every GAS snapshot.
The grade combines GAS score, model quality (technical Sharpe), macro stress,
and sentiment conviction into a single letter grade A+ → F.
This grade is the primary filter for portfolio construction, AI allocation,
and eventually the autonomous trading bot.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud.gas_snapshot import get_latest, upsert_snapshot
from app.services.cache import get_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_W_TECHNICAL = 0.40
_W_SENTIMENT = 0.30
_W_MACRO     = 0.30

_CACHE_TTL_S = 900

# ── GAS score thresholds (single source of truth) ─────────────────────────────
GAS_THRESHOLD_STRONG = 75   # A-grade strong tailwind
GAS_THRESHOLD_MILD   = 60   # B-grade mild support
GAS_THRESHOLD_MIXED  = 45   # C-grade mixed signals
GAS_THRESHOLD_WEAK   = 30   # F-grade disqualifier

DEFAULT_SYMBOLS: list[str] = settings.ohlcv_symbols_default  # type: ignore[attr-defined]


# ── Signal Grade ───────────────────────────────────────────────────────────────

def compute_signal_grade(
    gas_score: float,
    technical_score: float,
    sentiment_score: float,
    macro_score: float,
    technical_signals: list,
) -> dict:
    """
    Compute a letter grade (A+ → F) that summarises the investment decision
    quality for this symbol at this moment.

    The grade is the PRIMARY filter for:
      - Portfolio construction (only include A/B grade signals)
      - AI allocation decisions (weight by grade)
      - Autonomous trading bot (only execute on A+ / A signals)
      - UI filtering (let users filter watchlist by grade)

    Grade scale:
      A+  Exceptional alignment — all signals agree strongly
      A   Strong alignment — reliable signal
      B   Good signal — minor disagreements
      C   Moderate signal — mixed, use with caution
      D   Weak signal — significant disagreements or low confidence
      F   Do not use — conflicting signals, model quality issues, or GAS < 30

    Scoring methodology:
      - GAS score (0-40 points):     the primary composite signal
      - Component alignment (0-30):  do technical/sentiment/macro agree?
      - Technical confidence (0-20): best timeframe Sharpe from signals
      - Signal conviction (0-10):    how far from neutral (50)?

    Total 0-100 → letter grade.
    """

    score = 0.0
    reasons = []
    disqualified = False

    # ── Hard disqualifiers → F ─────────────────────────────────────────────
    if gas_score < GAS_THRESHOLD_WEAK:
        disqualified = True
        reasons.append(f"GAS {gas_score:.0f} < {GAS_THRESHOLD_WEAK} — high instability zone")

    # All components at default 50 = no real data computed
    if technical_score == 50.0 and sentiment_score == 50.0 and macro_score == 50.0:
        disqualified = True
        reasons.append("All components at default 50 — no real data computed")

    if disqualified:
        return {
            "grade":       "F",
            "grade_score": 0,
            "description": "Do not use — signal disqualified",
            "reasons":     reasons,
            "tradeable":   False,
        }

    # ── 1. GAS score contribution (0–40 pts) ──────────────────────────────
    # Map GAS 30-100 → 0-40 pts
    gas_pts = max(0.0, (gas_score - 30) / 70 * 40)
    score  += gas_pts
    if gas_score >= 75:
        reasons.append(f"GAS {gas_score:.0f} — strong tailwind")
    elif gas_score >= 60:
        reasons.append(f"GAS {gas_score:.0f} — mild support")
    elif gas_score >= 45:
        reasons.append(f"GAS {gas_score:.0f} — mixed signals")
    else:
        reasons.append(f"GAS {gas_score:.0f} — weak environment")

    # ── 2. Component alignment (0–30 pts) ─────────────────────────────────
    # All three components above 55 = fully aligned bullish
    # All three below 45 = fully aligned bearish (still a valid signal)
    # Mixed = penalised
    above_neutral = sum(1 for s in [technical_score, sentiment_score, macro_score] if s > 55)
    below_neutral = sum(1 for s in [technical_score, sentiment_score, macro_score] if s < 45)
    neutral_count = 3 - above_neutral - below_neutral

    if above_neutral == 3:
        align_pts = 30
        reasons.append("All 3 components bullish — full alignment")
    elif above_neutral == 2 and neutral_count == 1:
        align_pts = 22
        reasons.append("2/3 components bullish, 1 neutral")
    elif above_neutral == 2 and below_neutral == 1:
        align_pts = 12
        reasons.append("2/3 bullish but 1 bearish — mixed")
    elif below_neutral == 3:
        align_pts = 28   # fully bearish = also valid signal (penalise less)
        reasons.append("All 3 components bearish — full alignment (bearish)")
    elif below_neutral == 2 and neutral_count == 1:
        align_pts = 20
        reasons.append("2/3 components bearish, 1 neutral")
    elif neutral_count == 3:
        align_pts = 5
        reasons.append("All 3 components neutral — no clear signal")
    else:
        align_pts = 8
        reasons.append("Components mixed — low conviction")

    score += align_pts

    # ── 3. Technical model confidence (0–20 pts) ───────────────────────────
    # Best timeframe Sharpe from the signals list
    if technical_signals:
        sharpes = [
            s.get("validation_sharpe", 0)
            for s in technical_signals
            if isinstance(s, dict)
        ]
        best_sharpe = max(sharpes) if sharpes else 0.0

        if best_sharpe >= 2.0:
            tech_pts = 20
            reasons.append(f"Best model Sharpe {best_sharpe:.2f} — strong ML confidence")
        elif best_sharpe >= 1.0:
            tech_pts = 15
            reasons.append(f"Best model Sharpe {best_sharpe:.2f} — good ML confidence")
        elif best_sharpe >= 0.5:
            tech_pts = 10
            reasons.append(f"Best model Sharpe {best_sharpe:.2f} — acceptable ML signal")
        elif best_sharpe >= 0.3:
            tech_pts = 5
            reasons.append(f"Best model Sharpe {best_sharpe:.2f} — weak ML signal")
        else:
            tech_pts = 0
            reasons.append(f"Best model Sharpe {best_sharpe:.2f} — ML signal not trusted")
    else:
        tech_pts = 0
        reasons.append("No technical signals available — ML models not trained")

    score += tech_pts

    # ── 4. Signal conviction (0–10 pts) ────────────────────────────────────
    # How far is GAS from neutral (50)? Strong conviction in either direction.
    conviction = abs(gas_score - 50)
    conv_pts   = min(10.0, conviction / 50 * 10)
    score     += conv_pts
    if conviction >= 20:
        reasons.append(f"High conviction (GAS {conviction:.0f}pts from neutral)")
    elif conviction >= 10:
        reasons.append(f"Moderate conviction")
    else:
        reasons.append(f"Low conviction — GAS near neutral")

    # ── Map 0–100 score to letter grade ────────────────────────────────────
    grade_score = round(score)

    if   grade_score >= 88: grade, tradeable = "A+", True
    elif grade_score >= 78: grade, tradeable = "A",  True
    elif grade_score >= 65: grade, tradeable = "B",  True
    elif grade_score >= 50: grade, tradeable = "C",  False   # monitor, don't trade
    elif grade_score >= 35: grade, tradeable = "D",  False
    else:                   grade, tradeable = "F",  False

    descriptions = {
        "A+": "Exceptional signal — all factors strongly aligned",
        "A":  "Strong signal — reliable for trade decisions",
        "B":  "Good signal — minor disagreements, use with normal risk sizing",
        "C":  "Moderate signal — mixed factors, monitor closely",
        "D":  "Weak signal — significant disagreements, avoid new positions",
        "F":  "Do not use — conflicting signals or model quality issues",
    }

    return {
        "grade":       grade,
        "grade_score": grade_score,
        "description": descriptions[grade],
        "reasons":     reasons,
        "tradeable":   tradeable,
    }


# ── Weather and regime helpers ─────────────────────────────────────────────────

def _gas_to_weather(score: float) -> str:
    if score >= 80: return "Strong Tailwind"
    if score >= 60: return "Mild Support"
    if score >= 40: return "Mixed Signals"
    if score >= 20: return "Headwind"
    return "High Instability"


def _technical_to_regime(technical_score: float) -> str:
    if technical_score >= 60: return "Risk-On"
    if technical_score <= 40: return "Risk-Off"
    return "Transitional"


# ── Score computation helpers ─────────────────────────────────────────────────

async def _compute_technical_score(symbol: str) -> tuple[float, Optional[list]]:
    try:
        from app.services.technical_service import compute_technical_consensus  # noqa: PLC0415
        loop   = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, compute_technical_consensus, symbol)
        score   = float(result.get("consensus_score", 50.0))
        signals = result.get("signals", [])
        logger.debug("Technical score for %s: %.1f", symbol, score)
        return score, signals
    except Exception as exc:
        logger.warning("Technical inference failed for %s: %s — using 50.0", symbol, exc)
        return 50.0, []


async def _compute_sentiment_score(symbol: str, db: AsyncSession) -> float:
    # BUG-BE-09: For crypto symbols, use Crypto Fear & Greed index from
    # external_signals table instead of always returning neutral 50.0.
    sym_upper = symbol.upper()
    if sym_upper.endswith("-USD"):
        try:
            from sqlalchemy import select as _select, desc as _desc  # noqa: PLC0415
            from app.models.external_signal import ExternalSignal  # noqa: PLC0415
            row = await db.execute(
                _select(ExternalSignal.value)
                .where(ExternalSignal.signal_name == "crypto_fear_greed_norm")
                .order_by(_desc(ExternalSignal.fetched_at))
                .limit(1)
            )
            val: Optional[float] = row.scalar_one_or_none()
            if val is not None:
                # norm is 0-1; map to 0-100
                score = round(max(0.0, min(100.0, float(val) * 100.0)), 1)
                logger.debug("Crypto Fear & Greed sentiment for %s: %.1f", sym_upper, score)
                return score
        except Exception as exc:
            logger.warning("Crypto Fear & Greed lookup failed for %s: %s — using 50.0", sym_upper, exc)
        return 50.0

    try:
        from sqlalchemy import select, func  # noqa: PLC0415
        from app.models.sentiment import SentimentAggregate  # noqa: PLC0415
        from datetime import timedelta  # noqa: PLC0415

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(func.avg(SentimentAggregate.sentiment_score))
            .where(
                SentimentAggregate.symbol == sym_upper,
                SentimentAggregate.date >= cutoff.date(),
            )
        )
        avg_raw: Optional[float] = result.scalar_one_or_none()
        if avg_raw is None:
            logger.debug("No sentiment data for %s — using 50.0", sym_upper)
            return 50.0
        score = ((float(avg_raw) + 1.0) / 2.0) * 100.0
        score = max(0.0, min(100.0, score))
        logger.debug("Sentiment score for %s: %.1f (raw=%.3f)", sym_upper, score, avg_raw)
        return round(score, 1)
    except Exception as exc:
        logger.warning("Sentiment score failed for %s: %s — using 50.0", sym_upper, exc)
        return 50.0


async def _compute_macro_score(db: AsyncSession) -> float:
    try:
        from app.crud.macro import get_latest_batch_async  # noqa: PLC0415
        from app.services.macro_scoring import compute_macro_score  # noqa: PLC0415

        indicator_names = [
            "fed_funds_rate", "unemployment_rate", "yield_spread_10y_2y",
            "cpi_yoy", "vix", "nonfarm_payrolls_mom", "industrial_production_yoy",
        ]
        rows       = await get_latest_batch_async(db, indicator_names)
        indicators = {name: row.value if row else None for name, row in rows.items()}
        result     = compute_macro_score(indicators)
        logger.debug("Macro score: %.1f (%s)", result.score, result.label)
        return float(result.score)
    except Exception as exc:
        logger.warning("Macro score computation failed: %s — using 50.0", exc)
        return 50.0


# ── Main per-symbol computation ───────────────────────────────────────────────

async def compute_gas_for_symbol(
    symbol: str,
    db: AsyncSession,
    macro_score: Optional[float] = None,
) -> dict:
    symbol = symbol.upper()

    # Run technical inference and sentiment concurrently
    (technical_score, technical_signals), sentiment_score = await asyncio.gather(
        _compute_technical_score(symbol),
        _compute_sentiment_score(symbol, db),
    )

    if macro_score is None:
        macro_score = await _compute_macro_score(db)

    gas_score = (
        technical_score * _W_TECHNICAL
        + sentiment_score * _W_SENTIMENT
        + macro_score    * _W_MACRO
    )
    gas_score = round(max(0.0, min(100.0, gas_score)), 2)

    weather_label = _gas_to_weather(gas_score)
    regime        = _technical_to_regime(technical_score)

    component_scores = {
        "technical": round(technical_score, 1),
        "sentiment": round(sentiment_score, 1),
        "macro":     round(macro_score, 1),
    }

    # ── Compute signal grade ───────────────────────────────────────────────
    grade_result = compute_signal_grade(
        gas_score        = gas_score,
        technical_score  = technical_score,
        sentiment_score  = sentiment_score,
        macro_score      = macro_score,
        technical_signals = technical_signals or [],
    )

    logger.info(
        "Grade for %s: %s (%d/100) — tradeable=%s",
        symbol,
        grade_result["grade"],
        grade_result["grade_score"],
        grade_result["tradeable"],
    )

    # BUG-BE-14: capture previous grade BEFORE the upsert overwrites it
    try:
        from app.crud.gas_snapshot import get_latest as _get_latest  # noqa: PLC0415
        _prev_snap_before = await _get_latest(db, symbol)
        _prev_grade_before: Optional[str] = _prev_snap_before.signal_grade if _prev_snap_before else None
    except Exception:
        _prev_grade_before = None

    snap = await upsert_snapshot(
        db,
        symbol           = symbol,
        gas_score        = gas_score,
        weather_label    = weather_label,
        regime           = regime,
        component_scores = component_scores,
        technical_signals = technical_signals or [],
        source           = "live",
        # Pass grade fields (Phase 2D updates)
        signal_grade         = grade_result["grade"],
        signal_grade_score   = grade_result["grade_score"],
        signal_tradeable     = grade_result["tradeable"],
        signal_grade_desc    = grade_result["description"],
        signal_grade_reasons = grade_result["reasons"],
    )

    snap_dict = snap.to_dict()

    # Merge grade into the snapshot dict (available immediately even before DB migration)
    snap_dict["signal_grade"]         = grade_result["grade"]
    snap_dict["signal_grade_score"]   = grade_result["grade_score"]
    snap_dict["signal_tradeable"]     = grade_result["tradeable"]
    snap_dict["signal_grade_desc"]    = grade_result["description"]
    snap_dict["signal_grade_reasons"] = grade_result["reasons"]

    # ── Sprint 27: record grade change in history table ──────────────────────
    # BUG-BE-14 FIX: read previous grade BEFORE upsert (was reading after, always equal).
    # prev_grade was captured above before the upsert_snapshot call.
    try:
        from app.models.signal_grade_history import SignalGradeHistory  # noqa: PLC0415

        prev_grade = _prev_grade_before  # captured before upsert — BUG-BE-14
        new_grade  = grade_result["grade"]

        # Always write the first record; thereafter only write on grade change
        if prev_grade != new_grade:
            history_row = SignalGradeHistory(
                symbol          = symbol,
                grade           = new_grade,
                prev_grade      = prev_grade,
                grade_score     = grade_result["grade_score"],
                gas_score       = gas_score,
                component_scores = component_scores,
                tradeable       = str(grade_result["tradeable"]),
                recorded_at     = datetime.now(timezone.utc),
            )
            db.add(history_row)
            logger.info(
                "Grade history: %s %s → %s (GAS=%.1f)",
                symbol, prev_grade or "(new)", new_grade, gas_score,
            )
    except Exception as _hist_exc:
        # Never let grade history writes break the main precompute path
        logger.warning("Grade history write failed for %s: %s", symbol, _hist_exc)

    cache = get_cache()
    if cache:
        cache_key = f"gas:snapshot:{symbol}"
        await cache.set(cache_key, snap_dict, ttl=_CACHE_TTL_S)
        logger.debug("Cached gas:snapshot:%s (TTL=%ds)", symbol, _CACHE_TTL_S)

    return snap_dict


# ── Batch job ─────────────────────────────────────────────────────────────────

async def run_gas_precompute_batch(
    db: AsyncSession,
    symbols: Optional[list[str]] = None,
) -> dict:
    target_symbols = [s.upper() for s in (symbols or DEFAULT_SYMBOLS)]
    started_at     = datetime.now(timezone.utc)

    logger.info("GAS precompute batch started — %d symbols: %s", len(target_symbols), target_symbols)

    macro_score = await _compute_macro_score(db)
    logger.info("Shared macro score for this batch: %.1f", macro_score)

    results:  dict[str, dict] = {}
    failures: list[str]       = []

    # PERF: run symbols concurrently (max 4 at a time to avoid overwhelming DB)
    _sem = asyncio.Semaphore(4)

    async def _compute_one(symbol: str) -> None:
        async with _sem:
            try:
                snap = await compute_gas_for_symbol(symbol, db, macro_score=macro_score)
                results[symbol] = snap
                logger.info(
                    "  ✓ %s  GAS=%.1f  grade=%s  weather=%s  regime=%s  tradeable=%s",
                    symbol,
                    snap["gas_score"],
                    snap.get("signal_grade", "?"),
                    snap["weather_label"],
                    snap["regime"],
                    snap.get("signal_tradeable", "?"),
                )
            except Exception as exc:
                logger.error("  ✗ %s  FAILED: %s", symbol, exc)
                failures.append(symbol)

    await asyncio.gather(*[_compute_one(s) for s in target_symbols])

    await db.commit()

    elapsed_ms = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000

    # Grade summary for logging
    grade_summary = {}
    for snap in results.values():
        g = snap.get("signal_grade", "?")
        grade_summary[g] = grade_summary.get(g, 0) + 1

    summary = {
        "symbols_attempted":  len(target_symbols),
        "symbols_succeeded":  len(results),
        "symbols_failed":     len(failures),
        "failed_symbols":     failures,
        "elapsed_ms":         round(elapsed_ms, 1),
        "macro_score_shared": round(macro_score, 1),
        "grade_summary":      grade_summary,
    }
    logger.info("GAS precompute batch complete: %s", summary)
    return summary


# ── Cache-first read ──────────────────────────────────────────────────────────

async def get_snapshot_cached(symbol: str, db: AsyncSession) -> Optional[dict]:
    symbol    = symbol.upper()
    cache_key = f"gas:snapshot:{symbol}"

    cache = get_cache()
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Cache HIT for gas:snapshot:%s", symbol)
            return {**cached, "source": "cache"}

    snap = await get_latest(db, symbol)
    if snap:
        snap_dict = snap.to_dict()
        if cache:
            await cache.set(cache_key, snap_dict, ttl=_CACHE_TTL_S)
        logger.debug("DB snapshot HIT for %s (age: %s)", symbol, snap.computed_at)
        return {**snap_dict, "source": "db_snapshot"}

    logger.info("No snapshot found for %s — running live compute (cold start)", symbol)
    try:
        snap_dict = await compute_gas_for_symbol(symbol, db)
        await db.commit()
        return snap_dict
    except Exception as exc:
        logger.error("Live compute failed for %s: %s", symbol, exc)
        return None
