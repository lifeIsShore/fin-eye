"""
app/api/v1/endpoints/billing.py
================================
Sprint 38 — Monetisation scaffolding (todos-v3.md §10).

Endpoints are Stripe-ready but do not make live Stripe calls yet.
Replace the stub bodies with real Stripe SDK calls when going live.

Routes (all require authentication):
  POST  /billing/start-trial   — start 7-day free Pro trial
  POST  /billing/pause         — pause subscription for 30 days
  GET   /billing/invoices      — list invoices (stub returns [])
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user   # reuse existing dep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class TrialResponse(BaseModel):
    trial_ends_at: datetime
    message: str


class PauseRequest(BaseModel):
    reason: str | None = None


class PauseResponse(BaseModel):
    paused_until: datetime
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/start-trial",
    response_model=TrialResponse,
    summary="Start 7-day free Pro trial (no card required)",
)
async def start_trial(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Sets trial_ends_at = now + 7 days.
    Idempotent — if trial was already started, returns current end date.
    Does NOT change subscription_tier — the frontend / middleware should
    check trial_ends_at > now to grant Pro access during trial.
    """
    now = datetime.now(timezone.utc)

    if current_user.trial_ends_at is not None:
        # Already trialed — return existing date
        trial_end = current_user.trial_ends_at
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        return TrialResponse(
            trial_ends_at=trial_end,
            message=(
                "Trial already active."
                if trial_end > now
                else "Trial has already expired."
            ),
        )

    trial_end = now + timedelta(days=7)
    current_user.trial_ends_at = trial_end

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to start trial for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start trial.")

    logger.info("Trial started for user %s — ends %s", current_user.id, trial_end.isoformat())
    return TrialResponse(
        trial_ends_at=trial_end,
        message="7-day free trial started! Enjoy full Pro access.",
    )


@router.post(
    "/pause",
    response_model=PauseResponse,
    summary="Pause subscription for 30 days",
)
async def pause_subscription(
    body: PauseRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Sets paused_until = now + 30 days.
    In a live system this would also cancel the Stripe subscription
    and schedule a reactivation webhook.
    """
    now = datetime.now(timezone.utc)
    resume_at = now + timedelta(days=30)
    current_user.paused_until = resume_at

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to pause subscription for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to pause subscription.")

    reason = (body.reason if body else None) or "not specified"
    logger.info("Subscription paused for user %s (reason: %s) — resumes %s", current_user.id, reason, resume_at.isoformat())

    return PauseResponse(
        paused_until=resume_at,
        message=f"Subscription paused for 30 days. It will resume automatically on {resume_at.strftime('%B %d, %Y')}.",
    )


@router.get(
    "/invoices",
    summary="List invoices (Stripe stub — returns [] until payments go live)",
)
async def list_invoices(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Placeholder endpoint — will proxy Stripe invoice list when payments go live.
    Returns empty list so the frontend can render the "no invoices yet" state.
    """
    # TODO: Replace with Stripe invoice fetch:
    # import stripe
    # invoices = stripe.Invoice.list(customer=current_user.stripe_customer_id)
    return []
