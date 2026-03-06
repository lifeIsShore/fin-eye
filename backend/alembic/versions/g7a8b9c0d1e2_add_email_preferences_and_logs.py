"""add email preferences and email log tables

CORE-EMAIL-01 / CORE-EMAIL-02

Revision ID: g7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "g7a8b9c0d1e2"
down_revision = "d86515b1d6ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── email_preferences ───────────────────────────────────────────────────
    op.create_table(
        "email_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("onboarding_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("marketing_opted_in", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("digest_opted_in", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("digest_frequency", sa.String(16), nullable=False, server_default="weekly"),
        sa.Column("unsubscribe_token", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_email_preferences_user_id", "email_preferences", ["user_id"])
    op.create_index(
        "ix_email_preferences_unsubscribe_token",
        "email_preferences",
        ["unsubscribe_token"],
    )

    # ── email_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "email_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_type", sa.String(64), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("user_id", "email_type", name="uq_email_log_user_type"),
    )
    op.create_index("ix_email_logs_user_id", "email_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("email_logs")
    op.drop_table("email_preferences")
