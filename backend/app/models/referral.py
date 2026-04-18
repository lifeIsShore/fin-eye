"""
app/models/referral.py
Sprint 50 — Referral Program

ReferralEvent tracks when a user signs up or upgrades via a referral link.
Each referred_id is unique (one referral record per referred user).
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base


class ReferralEvent(Base):
    __tablename__ = "referral_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    referrer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one record per referred user
    )

    # 'signup' — referred user registered  |  'upgrade' — referred user went Pro
    event = Column(String(20), nullable=False)

    credited_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
