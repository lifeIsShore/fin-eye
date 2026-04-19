"""Sprint 52 — ORM models for ticker_comments and ticker_comment_reactions."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class TickerComment(Base):
    __tablename__ = "ticker_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True),
                                                       ForeignKey("users.id", ondelete="SET NULL"),
                                                       nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False,
                                                  default=datetime.utcnow)

    reactions: Mapped[list[TickerCommentReaction]] = relationship(
        "TickerCommentReaction", back_populates="comment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(body) BETWEEN 10 AND 500", name="ck_comment_body_length"),
    )


class TickerCommentReaction(Base):
    __tablename__ = "ticker_comment_reactions"

    comment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                    ForeignKey("ticker_comments.id",
                                                               ondelete="CASCADE"),
                                                    primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                ForeignKey("users.id", ondelete="CASCADE"),
                                                primary_key=True)
    reaction: Mapped[str] = mapped_column(String(10), nullable=False, default="up")

    comment: Mapped[TickerComment] = relationship("TickerComment", back_populates="reactions")
