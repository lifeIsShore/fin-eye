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
