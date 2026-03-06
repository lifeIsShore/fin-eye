"""
app/api/v1/endpoints/email.py

Email preference management and unsubscribe endpoints.

Routes:
  GET  /email/preferences          — get current user's email prefs
  PATCH /email/preferences         — update marketing/digest opt-in
  POST /email/unsubscribe          — one-click unsubscribe via token (no auth required)
  GET  /email/unsubscribe          — same, for GET-based unsubscribe links
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.email_preference import EmailPreference
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Email Preferences"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class EmailPreferenceResponse(BaseModel):
    marketing_opted_in: bool
    digest_opted_in: bool
    digest_frequency: str
    onboarding_step: int

    model_config = {"from_attributes": True}


class EmailPreferenceUpdate(BaseModel):
    marketing_opted_in: Optional[bool] = None
    digest_opted_in: Optional[bool] = None
    digest_frequency: Optional[str] = None  # "weekly" | "biweekly"


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_pref(db: AsyncSession, user: User) -> EmailPreference:
    """Fetch or lazily create the EmailPreference row for a user."""
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = EmailPreference(user_id=user.id)
        db.add(pref)
        await db.flush()
    return pref


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=EmailPreferenceResponse)
async def get_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EmailPreference:
    pref = await _get_or_create_pref(db, current_user)
    await db.commit()
    return pref


@router.patch("/preferences", response_model=EmailPreferenceResponse)
async def update_preferences(
    body: EmailPreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EmailPreference:
    pref = await _get_or_create_pref(db, current_user)

    if body.marketing_opted_in is not None:
        pref.marketing_opted_in = body.marketing_opted_in

    if body.digest_opted_in is not None:
        pref.digest_opted_in = body.digest_opted_in

    if body.digest_frequency is not None:
        if body.digest_frequency not in ("weekly", "biweekly"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="digest_frequency must be 'weekly' or 'biweekly'.",
            )
        pref.digest_frequency = body.digest_frequency

    await db.commit()
    await db.refresh(pref)
    return pref


@router.get("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_get(
    token: str = Query(..., description="Unsubscribe token from email link"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET-based unsubscribe — used when users click an email link."""
    return await _do_unsubscribe(token, db)


@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_post(
    token: str = Query(..., description="Unsubscribe token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """POST-based unsubscribe — used from the frontend unsubscribe page."""
    return await _do_unsubscribe(token, db)


async def _do_unsubscribe(token: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.unsubscribe_token == token)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired unsubscribe token.",
        )
    pref.marketing_opted_in = False
    pref.digest_opted_in = False
    await db.commit()
    logger.info("User unsubscribed via token (user_id=%s)", pref.user_id)
    return {"status": "unsubscribed", "message": "You have been unsubscribed from all marketing emails."}
