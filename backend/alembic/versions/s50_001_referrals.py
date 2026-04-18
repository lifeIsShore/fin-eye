"""add_referral_system

Sprint 50 — Referral Program
- referral_code, referred_by, referral_credits_months columns on users
- referral_events table

Revision ID: s50_001
Revises: s49_001
Create Date: 2026-04-18
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = "s50_001"
down_revision = "06d9d06f1ef3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users table additions ───────────────────────────────────────────────
    op.add_column("users", sa.Column(
        "referral_code",
        sa.String(length=12),
        nullable=True,
    ))
    op.create_unique_constraint("uq_users_referral_code", "users", ["referral_code"])

    op.add_column("users", sa.Column(
        "referred_by",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))

    op.add_column("users", sa.Column(
        "referral_credits_months",
        sa.Integer(),
        nullable=False,
        server_default="0",
    ))

    # ── referral_events table ───────────────────────────────────────────────
    op.create_table(
        "referral_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "referrer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "referred_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event",
            sa.String(length=20),
            nullable=False,
            comment="'signup' or 'upgrade'",
        ),
        sa.Column("credited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("referred_id", name="uq_referral_events_referred_id"),
    )
    op.create_index("idx_referral_events_referrer", "referral_events", ["referrer_id"])


def downgrade() -> None:
    op.drop_index("idx_referral_events_referrer", table_name="referral_events")
    op.drop_table("referral_events")
    op.drop_constraint("uq_users_referral_code", "users", type_="unique")
    op.drop_column("users", "referral_credits_months")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "referral_code")
