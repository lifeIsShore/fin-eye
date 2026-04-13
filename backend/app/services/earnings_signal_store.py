"""
app/services/earnings_signal_store.py
─────────────────────────────────────────────────────────────────────────────
Computes earnings-derived ML features and stores them in the `external_signals`
table so the ML pipeline can consume them as features.

Three signals per symbol, stored daily:

  source="earnings_calendar"

  1. earnings_days_until_norm
     Normalised proximity to next earnings (0.0 = >60 days away or no data,
     1.0 = earnings today). Formula: max(0, 1 - days_until / 60).
     Hypothesis: stocks exhibit abnormal vol in the ~30 days before earnings.

  2. earnings_surprise_score_norm
     EPS surprise score (0–100) divided by 100 → 0.0–1.0.
     Captures the company's historical beat/miss pattern.
     >0.6 = systematic beater, <0.4 = systematic misser.

  3. earnings_beat_streak_norm
     Consecutive beat streak (0–8 capped) divided by 8 → 0.0–1.0.
     Long streaks predict continued beats (analyst sandbagging effect).

These three features add earnings intelligence to every ML model training run
without requiring any DB join at inference time — they are pre-joined into
the price DataFrame via inject_external_features().

Scheduler: runs daily at 07:00 UTC (after macro refresh at 08:00 is fine too
— yfinance is independent).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute_and_store_earnings_signals(
    db: AsyncSession,
    symbols: list[str],
) -> dict:
    """
    Fetch earnings data for each symbol via earnings_service and store
    three normalised ML features in the external_signals table.

    Returns: { "ok": [...], "failed": [...] }
    """
    from app.models.external_signal import ExternalSignal   # noqa: PLC0415
    from app.services.earnings_service import analyse_earnings  # noqa: PLC0415
    import asyncio  # noqa: PLC0415

    ok, failed = [], []
    ts = datetime.now(timezone.utc)
    loop = asyncio.get_event_loop()

    for symbol in symbols:
        try:
            # analyse_earnings is sync + cached (6h TTL) — run in executor
            analysis = await loop.run_in_executor(None, analyse_earnings, symbol.upper())

            # ── Feature 1: days_until_norm ────────────────────────────────────
            days_until = analysis.upcoming.days_until if analysis.upcoming else None
            if days_until is not None and days_until >= 0:
                # 1.0 = today, 0.0 = 60+ days away (or no upcoming)
                days_norm = max(0.0, round(1.0 - days_until / 60.0, 4))
            else:
                days_norm = 0.0

            # ── Feature 2: surprise_score_norm ───────────────────────────────
            surprise_norm = round(analysis.surprise_score.score / 100.0, 4)

            # ── Feature 3: beat_streak_norm ───────────────────────────────────
            streak = min(analysis.surprise_score.consecutive_beats, 8)
            streak_norm = round(streak / 8.0, 4)

            sym = symbol.upper()
            for signal_name, value in [
                ("earnings_days_until_norm",    days_norm),
                ("earnings_surprise_score_norm", surprise_norm),
                ("earnings_beat_streak_norm",   streak_norm),
            ]:
                db.add(ExternalSignal(
                    source="earnings_calendar",
                    symbol=sym,
                    signal_name=signal_name,
                    value=value,
                    raw_json={
                        "days_until":      days_until,
                        "surprise_score":  analysis.surprise_score.score,
                        "surprise_label":  analysis.surprise_score.label,
                        "consecutive_beats": analysis.surprise_score.consecutive_beats,
                    },
                    fetched_at=ts,
                ))

            ok.append(symbol)
            logger.info(
                "Earnings signals %s: days_norm=%.3f surprise_norm=%.3f streak_norm=%.3f",
                sym, days_norm, surprise_norm, streak_norm,
            )

        except Exception as exc:
            logger.warning("Earnings signal failed for %s: %s", symbol, exc)
            failed.append(symbol)

    await db.commit()
    logger.info("Earnings signals done: ok=%d failed=%d", len(ok), len(failed))
    return {"ok": ok, "failed": failed}
