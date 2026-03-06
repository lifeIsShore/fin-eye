"""
app/services/onboarding_email_service.py

Orchestrates the 3-email onboarding sequence and the weekly digest job.

Onboarding sequence:
  Step 0 → Step 1 (welcome)    — triggered immediately at signup
  Step 1 → Step 2 (day3 tips)  — triggered by scheduler ~3 days after signup
  Step 2 → Step 3 (day7 power) — triggered by scheduler ~7 days after signup

Weekly digest:
  Triggered by scheduler for all users with digest_opted_in=True.
  Bi-weekly users receive every other run.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_preference import EmailLog, EmailPreference
from app.models.user import User
from app.services.email_service import (
    send_day3_email,
    send_day7_email,
    send_weekly_digest,
    send_welcome_email,
)

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_pref(db: AsyncSession, user: User) -> EmailPreference:
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = EmailPreference(user_id=user.id)
        db.add(pref)
        await db.flush()
    return pref


async def _already_sent(db: AsyncSession, user_id, email_type: str) -> bool:
    """Return True if this email_type was already successfully sent to this user."""
    result = await db.execute(
        select(EmailLog).where(
            EmailLog.user_id == user_id,
            EmailLog.email_type == email_type,
            EmailLog.success.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def _log_send(db: AsyncSession, user_id, email_type: str, *, success: bool) -> None:
    """Upsert an EmailLog entry. Duplicate sends are silently ignored."""
    # If already logged (unique constraint), don't re-insert
    exists = await db.execute(
        select(EmailLog).where(
            EmailLog.user_id == user_id,
            EmailLog.email_type == email_type,
        )
    )
    if exists.scalar_one_or_none() is None:
        log = EmailLog(user_id=user_id, email_type=email_type, success=success)
        db.add(log)


# ─── Onboarding sequence ──────────────────────────────────────────────────────

async def trigger_onboarding_welcome(db: AsyncSession, user: User) -> None:
    """
    Called at signup. Sends the welcome email and advances step to 1.
    Idempotent — safe to call twice (deduplication via EmailLog).
    """
    pref = await _get_or_create_pref(db, user)

    if await _already_sent(db, user.id, "onboarding_1"):
        logger.debug("Onboarding email 1 already sent to user_id=%s — skipping", user.id)
        return

    success = await send_welcome_email(
        user.email,
        user.name,
        unsubscribe_token=pref.unsubscribe_token,
    )
    await _log_send(db, user.id, "onboarding_1", success=success)
    if success:
        pref.onboarding_step = 1
        logger.info("Onboarding step 1 sent to user_id=%s", user.id)


async def run_onboarding_day3_batch(db: AsyncSession) -> int:
    """
    Scheduler job: send Day-3 email to all users where:
      - onboarding_step == 1 (welcome sent, day3 not yet sent)
      - marketing_opted_in is True
      - account created >= 3 days ago
    Returns count of emails sent.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)

    # Join EmailPreference with User to filter by created_at
    from app.models.user import User as UserModel  # noqa: PLC0415

    result = await db.execute(
        select(EmailPreference, UserModel)
        .join(UserModel, EmailPreference.user_id == UserModel.id)
        .where(
            EmailPreference.onboarding_step == 1,
            EmailPreference.marketing_opted_in.is_(True),
            UserModel.created_at <= cutoff,
        )
    )
    rows = result.all()
    sent = 0

    for pref, user in rows:
        if await _already_sent(db, user.id, "onboarding_2"):
            continue
        success = await send_day3_email(
            user.email, user.name, unsubscribe_token=pref.unsubscribe_token
        )
        await _log_send(db, user.id, "onboarding_2", success=success)
        if success:
            pref.onboarding_step = 2
            sent += 1

    if rows:
        await db.commit()

    logger.info("Onboarding day-3 batch: %d/%d sent", sent, len(rows))
    return sent


async def run_onboarding_day7_batch(db: AsyncSession) -> int:
    """
    Scheduler job: send Day-7 email to all users where:
      - onboarding_step == 2
      - marketing_opted_in is True
      - account created >= 7 days ago
    Returns count of emails sent.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    from app.models.user import User as UserModel  # noqa: PLC0415

    result = await db.execute(
        select(EmailPreference, UserModel)
        .join(UserModel, EmailPreference.user_id == UserModel.id)
        .where(
            EmailPreference.onboarding_step == 2,
            EmailPreference.marketing_opted_in.is_(True),
            UserModel.created_at <= cutoff,
        )
    )
    rows = result.all()
    sent = 0

    for pref, user in rows:
        if await _already_sent(db, user.id, "onboarding_3"):
            continue
        success = await send_day7_email(
            user.email, user.name, unsubscribe_token=pref.unsubscribe_token
        )
        await _log_send(db, user.id, "onboarding_3", success=success)
        if success:
            pref.onboarding_step = 3
            sent += 1

    if rows:
        await db.commit()

    logger.info("Onboarding day-7 batch: %d/%d sent", sent, len(rows))
    return sent


# ─── Weekly Digest (CORE-EMAIL-02) ────────────────────────────────────────────

async def run_weekly_digest_batch(db: AsyncSession, *, is_biweekly_week: bool = False) -> int:
    """
    Scheduler job: send weekly digest to all opted-in users.

    Args:
        is_biweekly_week: Set True on alternate weeks to also send to biweekly users.
                          Weekly users always receive it.
    Returns count of emails sent.
    """
    from app.models.user import User as UserModel  # noqa: PLC0415
    from app.models.blog import BlogPost  # noqa: PLC0415

    # Build frequency filter
    if is_biweekly_week:
        # Both weekly and biweekly
        freq_filter = EmailPreference.digest_opted_in.is_(True)
    else:
        # Weekly only
        from sqlalchemy import and_  # noqa: PLC0415
        freq_filter = and_(
            EmailPreference.digest_opted_in.is_(True),
            EmailPreference.digest_frequency == "weekly",
        )

    result = await db.execute(
        select(EmailPreference, UserModel)
        .join(UserModel, EmailPreference.user_id == UserModel.id)
        .where(freq_filter, UserModel.is_active.is_(True))
    )
    rows = result.all()

    # Fetch recent published posts (last 7 days) for digest content
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    posts_result = await db.execute(
        select(BlogPost)
        .where(BlogPost.status == "published", BlogPost.created_at >= week_ago)
        .order_by(BlogPost.created_at.desc())
        .limit(3)
    )
    recent_posts = [
        {"title": p.title, "slug": p.slug, "excerpt": (p.content or "")[:120] + "…"}
        for p in posts_result.scalars().all()
    ]

    # Build a simple macro summary text
    macro_summary = await _build_macro_summary(db)

    sent = 0
    for pref, user in rows:
        try:
            success = await send_weekly_digest(
                user.email,
                user.name,
                unsubscribe_token=pref.unsubscribe_token,
                macro_summary=macro_summary,
                recent_posts=recent_posts or None,
            )
            if success:
                sent += 1
        except Exception:  # noqa: BLE001
            logger.warning("Weekly digest failed for user_id=%s", user.id, exc_info=True)

    logger.info("Weekly digest batch: %d/%d sent", sent, len(rows))
    return sent


async def _build_macro_summary(db: AsyncSession) -> str | None:
    """
    Build a short plain-text macro summary from the latest macro indicators.
    Returns None if no data is available (digest will omit the macro section).
    """
    try:
        from app.crud.macro import get_latest_async  # noqa: PLC0415

        indicators = {
            name: await get_latest_async(db, name)
            for name in ["vix", "yield_spread_10y_2y", "cpi_yoy", "unemployment_rate"]
        }

        parts = []
        if indicators.get("vix") is not None:
            v = indicators["vix"]
            level = "elevated" if v > 25 else "low"
            parts.append(f"VIX at {v:.1f} ({level} volatility)")

        spread = indicators.get("yield_spread_10y_2y")
        if spread is not None:
            shape = "inverted" if spread < 0 else "normal"
            parts.append(f"yield curve {shape} ({spread:+.2f}%)")

        cpi = indicators.get("cpi_yoy")
        if cpi is not None:
            parts.append(f"CPI YoY {cpi:.1f}%")

        unemp = indicators.get("unemployment_rate")
        if unemp is not None:
            parts.append(f"unemployment {unemp:.1f}%")

        if not parts:
            return None

        return "This week: " + ", ".join(parts) + ". " + \
               "These figures are sourced from FRED and are for educational context only — " \
               "not investment advice."
    except Exception:  # noqa: BLE001
        logger.debug("Could not build macro summary for digest", exc_info=True)
        return None
