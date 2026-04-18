"""
app/services/auth_service.py
Business logic for user registration and authentication.
"""
import logging
import secrets
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.referral import ReferralEvent

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: Optional[str] = None,
    ref_code: Optional[str] = None,
) -> User:
    """
    Create a new user. Raises ValueError if email already registered.
    Sets a verification token (24h TTL) — caller should send the verification email.
    Generates a unique referral code. If ref_code is provided and valid, links the referrer.
    """
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415

    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("Email already registered.")

    token = secrets.token_urlsafe(64)
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    # Generate a unique referral code for this new user
    referral_code: Optional[str] = None
    for _ in range(5):  # retry loop to avoid collisions
        candidate = secrets.token_urlsafe(6)[:8]  # 8 URL-safe chars
        result = await db.execute(select(User).where(User.referral_code == candidate))
        if result.scalar_one_or_none() is None:
            referral_code = candidate
            break

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        name=name,
        verification_token=token,
        verification_token_expires_at=expiry,
        referral_code=referral_code,
        # is_verified stays False — user must click email link
    )
    db.add(user)
    await db.flush()   # get the id without committing
    await db.refresh(user)

    # Link referrer if a valid ref_code was provided
    if ref_code:
        referrer_result = await db.execute(
            select(User).where(User.referral_code == ref_code)
        )
        referrer = referrer_result.scalar_one_or_none()
        if referrer and referrer.id != user.id:
            user.referred_by = referrer.id
            db.add(ReferralEvent(
                referrer_id=referrer.id,
                referred_id=user.id,
                event="signup",
            ))
            await db.flush()

    logger.info("Created user id=%s email=%s referral_code=%s", user.id, user.email, user.referral_code)
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """
    Return the User if credentials are valid, else None.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def update_user_name(
    db: AsyncSession,
    user: User,
    name: Optional[str],
    default_symbol: Optional[str] = None,
    risk_profile: Optional[str] = None,
) -> User:
    """
    Update the user's display name, default_symbol, and risk_profile. Persist the change.
    """
    if name is not None:
        user.name = name
    if default_symbol is not None:
        user.default_symbol = default_symbol.strip().upper() if default_symbol.strip() else None
    if risk_profile is not None:
        user.risk_profile = risk_profile or None
    await db.commit()
    await db.refresh(user)
    logger.info("Updated profile for user id=%s", user.id)
    return user


async def change_user_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    """
    Verify current_password then replace it with new_password.
    Returns True on success, False if current_password is wrong.
    """
    if not verify_password(current_password, user.hashed_password):
        return False
    user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    logger.info("Password changed for user id=%s", user.id)
    return True


def update_streak(user: User) -> None:
    """
    Sprint 49 — Update login streak in-place (no DB commit here; caller commits).
    Rules:
      - same calendar day: no change (already counted today)
      - consecutive day: increment streak
      - gap > 1 day: reset streak to 1
    """
    from datetime import date as _date, timezone, datetime  # noqa: PLC0415

    today = datetime.now(timezone.utc).date()
    last  = user.last_streak_date

    if last is None or (today - last).days > 1:
        user.login_streak_days = 1                          # first login or streak broken
    elif (today - last).days == 1:
        user.login_streak_days += 1                         # consecutive day
    # else: last == today, already counted — no change

    user.longest_streak_days = max(user.longest_streak_days or 0, user.login_streak_days)
    user.last_streak_date    = today
    user.last_login          = datetime.now(timezone.utc)