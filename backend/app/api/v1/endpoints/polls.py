"""
app/api/v1/endpoints/polls.py
Sprint 52 — Weekly Bull vs Bear Poll

Endpoints:
  GET  /api/v1/polls/current          — current week's poll + counts + user vote
  POST /api/v1/polls/{poll_id}/vote   — cast or change vote
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_optional_user
from app.db.database import get_db
from app.models.weekly_poll import PollVote, WeeklyPoll
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/polls", tags=["Polls"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PollResults(BaseModel):
    bullish: int
    bearish: int
    neutral: int
    total: int


class PollResponse(BaseModel):
    poll_id: uuid.UUID
    question: str
    opens_at: datetime
    closes_at: datetime
    results: PollResults
    user_vote: str | None  # "bullish" | "bearish" | "neutral" | None


class VoteBody(BaseModel):
    vote: Literal["bullish", "bearish", "neutral"]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_results(db: AsyncSession, poll_id: uuid.UUID) -> PollResults:
    rows = await db.execute(
        select(PollVote.vote, func.count().label("cnt"))
        .where(PollVote.poll_id == poll_id)
        .group_by(PollVote.vote)
    )
    counts = {vote: cnt for vote, cnt in rows}
    b = counts.get("bullish", 0)
    be = counts.get("bearish", 0)
    n = counts.get("neutral", 0)
    return PollResults(bullish=b, bearish=be, neutral=n, total=b + be + n)


async def _current_poll(db: AsyncSession) -> WeeklyPoll | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(WeeklyPoll)
        .where(WeeklyPoll.opens_at <= now, WeeklyPoll.closes_at >= now)
        .order_by(WeeklyPoll.opens_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── GET /polls/current ────────────────────────────────────────────────────────

@router.get("/current", response_model=PollResponse)
async def get_current_poll(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> Any:
    poll = await _current_poll(db)
    if not poll:
        raise HTTPException(status_code=404, detail="No active poll this week")

    results = await _get_results(db, poll.id)

    user_vote: str | None = None
    if current_user:
        row = await db.get(PollVote, (poll.id, current_user.id))
        if row:
            user_vote = row.vote

    return PollResponse(
        poll_id=poll.id,
        question=poll.question,
        opens_at=poll.opens_at,
        closes_at=poll.closes_at,
        results=results,
        user_vote=user_vote,
    )


# ── POST /polls/{poll_id}/vote ────────────────────────────────────────────────

@router.post("/{poll_id}/vote", response_model=PollResponse)
async def cast_vote(
    poll_id: uuid.UUID,
    body: VoteBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    poll = await db.get(WeeklyPoll, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    now = datetime.now(timezone.utc)
    if now > poll.closes_at:
        raise HTTPException(status_code=400, detail="Poll has closed")

    existing = await db.get(PollVote, (poll_id, current_user.id))
    if existing:
        existing.vote = body.vote
        existing.voted_at = now
    else:
        db.add(PollVote(poll_id=poll_id, user_id=current_user.id, vote=body.vote))
    await db.commit()

    results = await _get_results(db, poll_id)
    return PollResponse(
        poll_id=poll.id,
        question=poll.question,
        opens_at=poll.opens_at,
        closes_at=poll.closes_at,
        results=results,
        user_vote=body.vote,
    )
