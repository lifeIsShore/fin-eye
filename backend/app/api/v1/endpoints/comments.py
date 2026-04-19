"""
app/api/v1/endpoints/comments.py
Sprint 52 — Per-ticker discussion threads

Endpoints:
  GET    /api/v1/comments/{symbol}              — paginated comments list
  POST   /api/v1/comments/{symbol}              — post a comment
  DELETE /api/v1/comments/{comment_id}          — soft-delete (author or admin)
  POST   /api/v1/comments/{comment_id}/react    — toggle up/down reaction
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_optional_user
from app.db.database import get_db
from app.models.ticker_comment import TickerComment, TickerCommentReaction
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/comments", tags=["Comments"])
limiter = Limiter(key_func=get_remote_address)

BANNED_WORDS: set[str] = {"spam", "scam", "pump", "dump"}  # extend via env/config


# ── Schemas ───────────────────────────────────────────────────────────────────

class CommentOut(BaseModel):
    id: uuid.UUID
    symbol: str
    username: str
    body: str
    created_at: datetime
    upvotes: int
    downvotes: int
    user_reaction: str | None  # "up" | "down" | None

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    comments: list[CommentOut]
    has_more: bool


class PostCommentBody(BaseModel):
    body: str

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        v = v.strip()
        if not (10 <= len(v) <= 500):
            raise ValueError("Comment must be 10–500 characters")
        low = v.lower()
        for word in BANNED_WORDS:
            if word in low:
                raise ValueError("Comment contains prohibited content")
        return v


class ReactBody(BaseModel):
    reaction: Literal["up", "down"]


def _anonymise(username: str | None) -> str:
    if not username:
        return "anon***"
    return username[:3] + "***"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _comment_counts(
    db: AsyncSession, comment_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int]]:
    """Returns {comment_id: (upvotes, downvotes)}."""
    if not comment_ids:
        return {}
    rows = await db.execute(
        select(
            TickerCommentReaction.comment_id,
            TickerCommentReaction.reaction,
            func.count().label("cnt"),
        )
        .where(TickerCommentReaction.comment_id.in_(comment_ids))
        .group_by(TickerCommentReaction.comment_id, TickerCommentReaction.reaction)
    )
    result: dict[uuid.UUID, tuple[int, int]] = {}
    for cid, reaction, cnt in rows:
        up, dn = result.get(cid, (0, 0))
        if reaction == "up":
            result[cid] = (up + cnt, dn)
        else:
            result[cid] = (up, dn + cnt)
    return result


async def _user_reactions(
    db: AsyncSession, user_id: uuid.UUID, comment_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not comment_ids:
        return {}
    rows = await db.execute(
        select(TickerCommentReaction.comment_id, TickerCommentReaction.reaction)
        .where(
            TickerCommentReaction.user_id == user_id,
            TickerCommentReaction.comment_id.in_(comment_ids),
        )
    )
    return {cid: r for cid, r in rows}


# ── GET /comments/{symbol} ────────────────────────────────────────────────────

@router.get("/{symbol}", response_model=CommentListResponse)
async def list_comments(
    symbol: str,
    limit: int = Query(20, ge=1, le=50),
    before_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> Any:
    sym = symbol.upper()
    q = (
        select(TickerComment)
        .where(TickerComment.symbol == sym, TickerComment.is_deleted.is_(False))
        .order_by(TickerComment.created_at.desc())
        .limit(limit + 1)
    )
    if before_id:
        # cursor pagination: find created_at of before_id, then filter
        cursor_row = await db.get(TickerComment, before_id)
        if cursor_row:
            q = q.where(TickerComment.created_at < cursor_row.created_at)

    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    rows = list(rows[:limit])

    ids = [c.id for c in rows]
    counts = await _comment_counts(db, ids)
    user_reacts: dict[uuid.UUID, str] = {}
    if current_user:
        user_reacts = await _user_reactions(db, current_user.id, ids)

    # Fetch usernames
    user_ids = [c.user_id for c in rows if c.user_id]
    usernames: dict[uuid.UUID, str] = {}
    if user_ids:
        urows = await db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        usernames = {uid: name for uid, name in urows}

    out = []
    for c in rows:
        up, dn = counts.get(c.id, (0, 0))
        out.append(CommentOut(
            id=c.id,
            symbol=c.symbol,
            username=_anonymise(usernames.get(c.user_id)),
            body=c.body,
            created_at=c.created_at,
            upvotes=up,
            downvotes=dn,
            user_reaction=user_reacts.get(c.id),
        ))

    return CommentListResponse(comments=out, has_more=has_more)


# ── POST /comments/{symbol} ───────────────────────────────────────────────────

@router.post("/{symbol}", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def post_comment(
    symbol: str,
    body: PostCommentBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # Rate limit: max 10 comments per user per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    count_result = await db.execute(
        select(func.count()).where(
            TickerComment.user_id == current_user.id,
            TickerComment.created_at >= one_hour_ago,
        )
    )
    if (count_result.scalar() or 0) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit: max 10 comments per hour")

    comment = TickerComment(
        user_id=current_user.id,
        symbol=symbol.upper(),
        body=body.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentOut(
        id=comment.id,
        symbol=comment.symbol,
        username=_anonymise(current_user.username),
        body=comment.body,
        created_at=comment.created_at,
        upvotes=0,
        downvotes=0,
        user_reaction=None,
    )


# ── DELETE /comments/{comment_id} ────────────────────────────────────────────

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    comment = await db.get(TickerComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    is_admin = getattr(current_user, "is_admin", False)
    if comment.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorised")

    comment.is_deleted = True
    comment.body = "[deleted]"
    await db.commit()


# ── POST /comments/{comment_id}/react ────────────────────────────────────────

@router.post("/{comment_id}/react", response_model=dict)
async def react_to_comment(
    comment_id: uuid.UUID,
    body: ReactBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    comment = await db.get(TickerComment, comment_id)
    if not comment or comment.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")

    existing = await db.get(TickerCommentReaction, (comment_id, current_user.id))
    if existing:
        if existing.reaction == body.reaction:
            # Toggle off
            await db.delete(existing)
        else:
            existing.reaction = body.reaction
    else:
        db.add(TickerCommentReaction(
            comment_id=comment_id,
            user_id=current_user.id,
            reaction=body.reaction,
        ))
    await db.commit()

    counts = await _comment_counts(db, [comment_id])
    up, dn = counts.get(comment_id, (0, 0))
    return {"upvotes": up, "downvotes": dn}
