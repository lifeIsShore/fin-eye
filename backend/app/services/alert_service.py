"""
app/services/alert_service.py
Business logic for creating, listing, evaluating, and acknowledging alerts.

Evaluation is called by the APScheduler job (scheduler.py) every 5 minutes.
For each active alert it fetches the latest price or GAS score and compares
against the user-defined threshold.  On breach the alert is marked triggered
and (later) dispatched via email when CORE-EMAIL-01 is wired.
"""
import logging
from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert_models import AlertCreate

logger = logging.getLogger(__name__)


# ── CRUD ───────────────────────────────────────────────────────────────────────

async def create_alert(db: AsyncSession, user: User, payload: AlertCreate) -> Alert:
    alert = Alert(
        user_id=user.id,
        symbol=payload.symbol,
        alert_type=payload.alert_type,
        threshold=payload.threshold,
        delivery_channel=payload.delivery_channel,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    logger.info("Alert %d created for user %s — %s %s @ %.4f",
                alert.id, user.id, alert.symbol, alert.alert_type, alert.threshold)
    return alert


async def list_alerts(
    db: AsyncSession,
    user: User,
    active_only: bool = False,
) -> List[Alert]:
    stmt = select(Alert).where(Alert.user_id == user.id)
    if active_only:
        stmt = stmt.where(Alert.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Alert.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_alert(db: AsyncSession, alert_id: int, user: User) -> Optional[Alert]:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def delete_alert(db: AsyncSession, alert_id: int, user: User) -> bool:
    alert = await get_alert(db, alert_id, user)
    if not alert:
        return False
    await db.delete(alert)
    await db.flush()
    return True


async def acknowledge_alert(db: AsyncSession, alert_id: int, user: User) -> Optional[Alert]:
    """Mark a triggered alert as inactive (dismiss it from the UI)."""
    alert = await get_alert(db, alert_id, user)
    if not alert:
        return None
    alert.is_active = False
    await db.flush()
    return alert


# ── Sprint 30: default alert seeding on watchlist add ────────────────────────────────

_DEFAULT_GAS_ABOVE = 65.0  # "GAS just turned bullish"
_DEFAULT_GAS_BELOW = 35.0  # "GAS entered danger zone"


# ── Sprint 31: grade-drop rebalancing trigger ──────────────────────────────────────────

_GRADE_ORDER = ["A+", "A", "B", "C", "D", "F"]
_REBALANCE_STEP_THRESHOLD = 2   # grade must drop ≥2 steps
_REBALANCE_ALERT_COOLDOWN_HOURS = 24  # don’t fire the same alert twice per day


def _grade_rank(grade: str) -> int:
    """Lower rank = better grade. F = 5."""
    try:
        return _GRADE_ORDER.index(grade)
    except ValueError:
        return len(_GRADE_ORDER)


async def check_and_fire_rebalancing_alerts(db: AsyncSession) -> dict:
    """
    Sprint 31 (Phase 2B): Scan signal_grade_history for symbols where the most
    recent grade change was a drop of ≥2 steps.  For every user who has that
    symbol on their watchlist, fire an in-app alert with type="rebalance_suggested".

    Design:
      • Runs once per GAS precompute cycle (every 15 min on market days).
      • Reads the two most-recent grade rows per symbol from signal_grade_history.
      • Fires only when current < prev AND rank difference ≥ threshold.
      • Cool-down: skips if a rebalance alert for that user+symbol was already
        fired within _REBALANCE_ALERT_COOLDOWN_HOURS (avoids alert spam).
      • Never blocks the calling job — all exceptions are caught and logged.

    Returns a summary dict for logging.
    """
    from sqlalchemy import select as _sel, func as _func  # noqa: PLC0415
    from datetime import timedelta  # noqa: PLC0415
    from app.models.signal_grade_history import SignalGradeHistory  # noqa: PLC0415
    from app.models.watchlist import WatchlistItem  # noqa: PLC0415

    started = datetime.utcnow()
    fired = 0
    skipped = 0
    errors: list[str] = []

    try:
        # 1. Find all symbols that have at least 2 grade history rows
        sym_result = await db.execute(
            _sel(SignalGradeHistory.symbol, _func.count(SignalGradeHistory.id).label("cnt"))
            .group_by(SignalGradeHistory.symbol)
            .having(_func.count(SignalGradeHistory.id) >= 2)
        )
        symbols = [row.symbol for row in sym_result.all()]

        for sym in symbols:
            try:
                # 2. Get the two most-recent grade events for this symbol
                hist_result = await db.execute(
                    _sel(SignalGradeHistory)
                    .where(SignalGradeHistory.symbol == sym)
                    .order_by(SignalGradeHistory.recorded_at.desc())
                    .limit(2)
                )
                rows = hist_result.scalars().all()
                if len(rows) < 2:
                    continue

                current_grade = rows[0].grade
                prev_grade    = rows[1].grade
                current_rank  = _grade_rank(current_grade)
                prev_rank     = _grade_rank(prev_grade)
                drop          = current_rank - prev_rank

                if drop < _REBALANCE_STEP_THRESHOLD:
                    skipped += 1
                    continue

                # 3. Find all watchlist users that hold this symbol
                wl_result = await db.execute(
                    _sel(WatchlistItem).where(WatchlistItem.symbol == sym)
                )
                watchlist_rows = wl_result.scalars().all()

                cooldown_cutoff = datetime.utcnow() - timedelta(hours=_REBALANCE_ALERT_COOLDOWN_HOURS)

                for wl in watchlist_rows:
                    try:
                        # 4. Cool-down check — skip if we already fired recently
                        recent = await db.execute(
                            _sel(Alert).where(
                                Alert.user_id == wl.user_id,
                                Alert.symbol  == sym,
                                Alert.alert_type == "rebalance_suggested",
                                Alert.created_at >= cooldown_cutoff,
                            )
                        )
                        if recent.scalar_one_or_none():
                            skipped += 1
                            continue

                        # 5. Fire the in-app rebalancing alert
                        # threshold stores the grade drop size as a float for sorting/display
                        alert = Alert(
                            user_id         = wl.user_id,
                            symbol          = sym,
                            alert_type      = "rebalance_suggested",
                            threshold       = float(drop),
                            delivery_channel = "in_app",
                            is_active       = True,
                            triggered_at    = datetime.utcnow(),
                            triggered_value = float(drop),
                        )
                        db.add(alert)
                        fired += 1
                        logger.info(
                            "Rebalancing alert fired: user=%s sym=%s %s→%s (drop %d steps)",
                            wl.user_id, sym, prev_grade, current_grade, drop,
                        )
                    except Exception as inner_exc:
                        errors.append(f"user={wl.user_id} sym={sym}: {inner_exc}")

            except Exception as outer_exc:
                errors.append(f"sym={sym}: {outer_exc}")

        await db.commit()

    except Exception as top_exc:
        errors.append(f"top-level: {top_exc}")
        logger.error("check_and_fire_rebalancing_alerts failed: %s", top_exc)

    elapsed_ms = round((datetime.utcnow() - started).total_seconds() * 1000, 1)
    summary = {"fired": fired, "skipped": skipped, "errors": len(errors), "elapsed_ms": elapsed_ms}
    logger.info("Rebalancing alert check: %s", summary)
    return summary


async def seed_watchlist_alerts(db: AsyncSession, user: User, symbol: str) -> list[Alert]:
    """
    Sprint 30 (POLISH-03): When a symbol is first added to the watchlist,
    automatically create two GAS threshold alerts:
      • gas_above 65  — “Bullish environment opening up”
      • gas_below 35  — “Instability zone — review exposure”

    Idempotent: skips any alert type/threshold combo that already exists
    for this user + symbol so re-adding doesn’t double up.
    """
    sym = symbol.upper()
    created: list[Alert] = []

    # Fetch existing active alerts for this symbol to avoid duplicates
    existing = await db.execute(
        select(Alert).where(
            Alert.user_id == user.id,
            Alert.symbol == sym,
            Alert.is_active == True,  # noqa: E712
        )
    )
    existing_set = {
        (a.alert_type, a.threshold)
        for a in existing.scalars().all()
    }

    for alert_type, threshold in [
        ("gas_above", _DEFAULT_GAS_ABOVE),
        ("gas_below", _DEFAULT_GAS_BELOW),
    ]:
        if (alert_type, threshold) in existing_set:
            logger.debug("Skipping duplicate alert %s %s @ %.0f", sym, alert_type, threshold)
            continue

        alert = Alert(
            user_id=user.id,
            symbol=sym,
            alert_type=alert_type,
            threshold=threshold,
            delivery_channel="in_app",
        )
        db.add(alert)
        created.append(alert)
        logger.info(
            "Auto-created alert for %s %s (%s @ %.0f)",
            user.id, sym, alert_type, threshold,
        )

    if created:
        await db.flush()  # caller commits

    return created


# ── Evaluation engine ──────────────────────────────────────────────────────────

async def get_triggered_alerts(db: AsyncSession, user: User) -> List[Alert]:
    """Return alerts that have fired but not yet been dismissed."""
    result = await db.execute(
        select(Alert).where(
            Alert.user_id == user.id,
            Alert.triggered_at != None,  # noqa: E711
            Alert.is_active == True,     # noqa: E712
        ).order_by(Alert.triggered_at.desc())
    )
    return list(result.scalars().all())


async def get_alert_history(
    db: AsyncSession,
    user: User,
    limit: int = 50,
) -> List[Alert]:
    """Return last `limit` alerts that have ever been triggered (fired + dismissed)."""
    result = await db.execute(
        select(Alert).where(
            Alert.user_id == user.id,
            Alert.triggered_at != None,  # noqa: E711
        ).order_by(Alert.triggered_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def evaluate_alerts_for_symbol(
    db: AsyncSession,
    symbol: str,
    current_price: float,
    current_gas: Optional[float] = None,
) -> List[Alert]:
    """
    Called by the scheduler or inline after a price refresh.
    Returns a list of alerts that just fired.
    """
    # Load all active, un-triggered alerts for this symbol
    result = await db.execute(
        select(Alert).where(
            Alert.symbol == symbol,
            Alert.is_active == True,       # noqa: E712
            Alert.triggered_at == None,    # noqa: E711
        )
    )
    alerts: List[Alert] = list(result.scalars().all())
    fired: List[Alert] = []

    for alert in alerts:
        triggered_value: Optional[float] = None

        if alert.alert_type == "price_above" and current_price > alert.threshold:
            triggered_value = current_price
        elif alert.alert_type == "price_below" and current_price < alert.threshold:
            triggered_value = current_price
        elif alert.alert_type == "gas_above" and current_gas is not None and current_gas > alert.threshold:
            triggered_value = current_gas
        elif alert.alert_type == "gas_below" and current_gas is not None and current_gas < alert.threshold:
            triggered_value = current_gas

        if triggered_value is not None:
            alert.triggered_at = datetime.utcnow()
            alert.triggered_value = triggered_value
            fired.append(alert)
            logger.info(
                "Alert %d FIRED — %s %s threshold=%.4f actual=%.4f",
                alert.id, symbol, alert.alert_type, alert.threshold, triggered_value,
            )

    if fired:
        await db.flush()

    return fired


def build_trigger_message(alert: Alert) -> str:
    """Human-readable message for a triggered alert."""
    verb = "rose above" if "above" in alert.alert_type else "fell below"
    metric = "price" if alert.alert_type.startswith("price") else "GAS score"
    return (
        f"{alert.symbol} {metric} {verb} your threshold of {alert.threshold:.2f} "
        f"(current: {alert.triggered_value:.2f})"
    )


# ── Email alert batch evaluation (CORE-NOTIF-ADV-01) ─────────────────────────

async def evaluate_all_email_alerts(db: AsyncSession) -> dict:
    """
    Called by the APScheduler job every 5 minutes during market hours.

    Strategy:
      1. Load all active, un-triggered alerts with delivery_channel='email'.
      2. Deduplicate symbols — fetch GAS snapshot once per unique symbol.
      3. For each alert, check the threshold against live GAS or cached price.
      4. On breach: mark triggered in DB, send email via alert_email_service.

    Price data for price_above/price_below alerts:
      We use the GAS snapshot's last known price from yfinance ticker.info
      (fast_info.last_price). If unavailable we fall back to yfinance directly.
      This avoids a separate price API — the GAS pre-compute job already
      fetches yfinance data every 15 minutes.

    Returns a summary dict suitable for scheduler metrics logging.
    """
    from sqlalchemy import select as _select  # local import to avoid circular
    import time

    started = time.perf_counter()
    total_checked = 0
    total_fired   = 0
    total_emailed = 0
    errors: list[str] = []

    # ── 1. Load all active email alerts ───────────────────────────────────
    result = await db.execute(
        _select(Alert).where(
            Alert.is_active == True,        # noqa: E712
            Alert.triggered_at == None,     # noqa: E711
            Alert.delivery_channel == "email",
        )
    )
    email_alerts: list[Alert] = list(result.scalars().all())
    total_checked = len(email_alerts)

    if not total_checked:
        logger.info("evaluate_all_email_alerts: no active email alerts — skipping")
        return {"checked": 0, "fired": 0, "emailed": 0, "errors": 0, "elapsed_ms": 0}

    logger.info("evaluate_all_email_alerts: evaluating %d email alerts", total_checked)

    # ── 2. Resolve current values per unique symbol ────────────────────────
    unique_symbols = list({a.symbol for a in email_alerts})
    symbol_gas: dict[str, float | None]   = {}
    symbol_price: dict[str, float | None] = {}

    for symbol in unique_symbols:
        # Try GAS snapshot (Redis → DB)
        try:
            from app.services.gas_precompute import get_snapshot_cached  # noqa: PLC0415
            snap = await get_snapshot_cached(symbol, db)
            symbol_gas[symbol] = snap["gas_score"] if snap else None
        except Exception as exc:
            logger.warning("GAS lookup failed for %s: %s", symbol, exc)
            symbol_gas[symbol] = None

        # Price lookup via yfinance fast_info (already available)
        try:
            import asyncio as _asyncio  # noqa: PLC0415
            import yfinance as _yf       # noqa: PLC0415

            def _get_price(sym: str) -> float | None:
                try:
                    t = _yf.Ticker(sym)
                    p = t.fast_info.get("last_price") or t.fast_info.get("lastPrice")
                    return float(p) if p else None
                except Exception:
                    return None

            loop = _asyncio.get_running_loop()
            price = await loop.run_in_executor(None, _get_price, symbol)
            symbol_price[symbol] = price
        except Exception as exc:
            logger.warning("Price lookup failed for %s: %s", symbol, exc)
            symbol_price[symbol] = None

    # ── 3. Evaluate each alert ─────────────────────────────────────────────
    fired_alerts: list[Alert] = []

    from datetime import datetime as _dt  # noqa: PLC0415
    for alert in email_alerts:
        sym   = alert.symbol
        gas   = symbol_gas.get(sym)
        price = symbol_price.get(sym)

        triggered_value: float | None = None

        if alert.alert_type == "price_above" and price is not None and price > alert.threshold:
            triggered_value = price
        elif alert.alert_type == "price_below" and price is not None and price < alert.threshold:
            triggered_value = price
        elif alert.alert_type == "gas_above" and gas is not None and gas > alert.threshold:
            triggered_value = gas
        elif alert.alert_type == "gas_below" and gas is not None and gas < alert.threshold:
            triggered_value = gas

        if triggered_value is not None:
            alert.triggered_at    = _dt.utcnow()
            alert.triggered_value = triggered_value
            alert.is_active       = False   # deactivate after email alert fires
            fired_alerts.append(alert)
            total_fired += 1
            logger.info(
                "Email alert %d FIRED — %s %s threshold=%.2f actual=%.2f",
                alert.id, sym, alert.alert_type, alert.threshold, triggered_value,
            )

    if fired_alerts:
        await db.flush()   # persist triggered_at + is_active=False before emailing

    # ── 4. Send emails for fired alerts ───────────────────────────────────
    if fired_alerts:
        from app.services.alert_email_service import send_alert_email  # noqa: PLC0415
        from sqlalchemy import select as _sel  # noqa: PLC0415
        from app.models.email_preference import EmailPreference  # noqa: PLC0415

        for alert in fired_alerts:
            try:
                # Load user
                user_result = await db.execute(
                    _select(User).where(User.id == alert.user_id)
                )
                user: User | None = user_result.scalar_one_or_none()
                if not user or not user.is_active:
                    logger.warning("Alert %d: user %s not found or inactive", alert.id, alert.user_id)
                    continue

                # Load unsubscribe token
                pref_result = await db.execute(
                    _select(EmailPreference).where(EmailPreference.user_id == user.id)
                )
                pref: EmailPreference | None = pref_result.scalar_one_or_none()
                unsubscribe_token = pref.unsubscribe_token if pref else "no-token"

                sent = await send_alert_email(db, alert, user, unsubscribe_token)
                if sent:
                    total_emailed += 1

            except Exception as exc:
                err_msg = f"alert_id={alert.id}: {exc}"
                logger.error("Email send failed — %s", err_msg)
                errors.append(err_msg)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    summary = {
        "checked":    total_checked,
        "fired":      total_fired,
        "emailed":    total_emailed,
        "errors":     len(errors),
        "elapsed_ms": elapsed_ms,
    }
    logger.info("evaluate_all_email_alerts complete: %s", summary)
    return summary
