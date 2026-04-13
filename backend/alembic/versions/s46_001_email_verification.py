"""s46_001_email_verification.py
Sprint 46 — SEC-07: Email verification fields on users table.

Adds:
  - verification_token VARCHAR(128) NULLABLE
  - verification_token_expires_at TIMESTAMPTZ NULLABLE
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "s46_001_email_verification"
down_revision = "s45_001_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("verification_token", sa.String(128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "verification_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_verification_token",
        "users",
        ["verification_token"],
        unique=True,
        postgresql_where=sa.text("verification_token IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_verification_token", table_name="users")
    op.drop_column("users", "verification_token_expires_at")
    op.drop_column("users", "verification_token")
