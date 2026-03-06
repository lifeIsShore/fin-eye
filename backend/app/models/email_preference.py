"""
app/models/email_preference.py

EmailPreference — stores per-user email opt-in/out state and unsubscribe token.
EmailLog — records every sent email for deduplication (prevents double-sending).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class EmailPreference(Base):
    __tablename__ = "email_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK to users — cascade delete so anonymised users are cleaned up
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one row per user
        index=True,
    )

    # Onboarding sequence (CORE-EMAIL-01)
    # Tracks which step (0=not started, 1=welcome sent, 2=day3 sent, 3=day7 sent)
    onboarding_step = Column(Integer, default=0, nullable=False)

    # Marketing / non-transactional opt-out
    # False = opted out; True = opted in (default for new signups)
    marketing_opted_in = Column(Boolean, default=True, nullable=False)

    # Weekly digest (CORE-EMAIL-02) — explicit toggle, separate from marketing
    digest_opted_in = Column(Boolean, default=False, nullable=False)
    # "weekly" or "biweekly"
    digest_frequency = Column(String(16), default="weekly", nullable=False)

    # Unsubscribe token — used in one-click unsubscribe links (GDPR)
    # 32-byte URL-safe random string
    unsubscribe_token = Column(
        String(64),
        default=lambda: secrets.token_urlsafe(32),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationship back to User (optional, for convenience)
    # user = relationship("User", back_populates="email_preference")


class EmailLog(Base):
    """
    Lightweight deduplication log.
    Before sending an onboarding email we check this table — prevents
    double-sending if the scheduler fires twice within the same window.
    """
    __tablename__ = "email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g. "onboarding_1", "onboarding_2", "onboarding_3", "weekly_digest"
    email_type = Column(String(64), nullable=False)

    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    success = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        # Ensures we never send the same email type to the same user twice
        UniqueConstraint("user_id", "email_type", name="uq_email_log_user_type"),
    )
