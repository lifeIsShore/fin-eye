"""Sprint 52 — ORM models for weekly_polls and poll_votes."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class WeeklyPoll(Base):
    __tablename__ = "weekly_polls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, default="SPY")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    opens_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    votes: Mapped[list[PollVote]] = relationship("PollVote", back_populates="poll",
                                                  cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("week_number", "year", "symbol", name="uq_poll_week_symbol"),
    )


class PollVote(Base):
    __tablename__ = "poll_votes"

    poll_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                ForeignKey("weekly_polls.id", ondelete="CASCADE"),
                                                primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                ForeignKey("users.id", ondelete="CASCADE"),
                                                primary_key=True)
    vote: Mapped[str] = mapped_column(String(10), nullable=False)  # bullish|bearish|neutral
    voted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False,
                                                default=datetime.utcnow)

    poll: Mapped[WeeklyPoll] = relationship("WeeklyPoll", back_populates="votes")
