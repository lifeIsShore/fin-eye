"""Sprint 52 — weekly_polls + poll_votes

Revision ID: s52_002_polls
Revises: s52_001_discussions
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s52_002_polls"
down_revision = "s52_001_discussions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, server_default="SPY"),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("opens_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("closes_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint("week_number", "year", "symbol", name="uq_poll_week_symbol"),
    )

    op.create_table(
        "poll_votes",
        sa.Column("poll_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("weekly_polls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vote", sa.String(10), nullable=False),  # bullish | bearish | neutral
        sa.Column("voted_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("poll_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("poll_votes")
    op.drop_table("weekly_polls")
