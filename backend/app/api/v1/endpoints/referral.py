"""
app/api/v1/endpoints/referral.py
Sprint 50 — Referral Program

Endpoints:
  GET /api/v1/referral/my-code    — returns user's referral code, link, and stats
  GET /api/v1/referral/leaderboard — top 10 referrers (anonymised)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.referral import ReferralEvent
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/referral", tags=["Referral"])

APP_URL = "https://fin-eye.app"


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReferralStatsResponse(BaseModel):
    code: str
    link: str
    signups: int
    upgrades: int
    credits_earned: int


class LeaderEntry(BaseModel):
    rank: int
    display_name: str
    referrals: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/my-code",
    response_model=ReferralStatsResponse,
    summary="Get current user's referral code, link, and stats",
)
async def my_referral_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not current_user.referral_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral code not found. Please log out and back in to generate one.",
        )

    # Count signups made via this user's referrals
    signup_result = await db.execute(
        select(func.count()).where(
            ReferralEvent.referrer_id == current_user.id,
            ReferralEvent.event == "signup",
        )
    )
    signups = signup_result.scalar_one() or 0

    # Count upgrades credited to this user
    upgrade_result = await db.execute(
        select(func.count()).where(
            ReferralEvent.referrer_id == current_user.id,
            ReferralEvent.event == "upgrade",
        )
    )
    upgrades = upgrade_result.scalar_one() or 0

    return ReferralStatsResponse(
        code=current_user.referral_code,
        link=f"{APP_URL}?ref={current_user.referral_code}",
        signups=signups,
        upgrades=upgrades,
        credits_earned=current_user.referral_credits_months,
    )


@router.get(
    "/leaderboard",
    response_model=list[LeaderEntry],
    summary="Top 10 referrers (anonymised display names)",
)
async def referral_leaderboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Returns top 10 users by number of successful signup referrals.
    Display names are anonymised: first 3 chars + '***'
    """
    result = await db.execute(
        select(
            ReferralEvent.referrer_id,
            func.count(ReferralEvent.id).label("referral_count"),
        )
        .where(ReferralEvent.event == "signup")
        .group_by(ReferralEvent.referrer_id)
        .order_by(func.count(ReferralEvent.id).desc())
        .limit(10)
    )
    rows = result.all()

    entries: list[LeaderEntry] = []
    for rank, (referrer_id, count) in enumerate(rows, start=1):
        # Fetch the referrer's display name (minimal query)
        user_result = await db.execute(
            select(User.name, User.email).where(User.id == referrer_id)
        )
        user_row = user_result.first()
        if user_row:
            display_source = user_row.name or user_row.email or "User"
            # Anonymise: show first 3 chars then ***
            visible = display_source[:3]
            display_name = f"{visible}***"
        else:
            display_name = "***"

        entries.append(LeaderEntry(rank=rank, display_name=display_name, referrals=count))

    return entries
