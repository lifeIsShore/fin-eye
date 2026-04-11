"""add churn tracking and last_login to users

Revision ID: s44_001_churn_tracking
Revises: 5e66ab23ac8b
Create Date: 2026-04-11

Adds:
  - users.last_login          (DateTime, nullable) — stamped on every successful login
  - users.weekly_digest       (Boolean, default False) — Sprint 33 weekly digest opt-in
  - users.churn_email_sent_at (DateTime, nullable) — Sprint 44 cooldown tracker
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s44_001_churn_tracking"
down_revision: Union[str, None] = "5e66ab23ac8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("weekly_digest", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("churn_email_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "churn_email_sent_at")
    op.drop_column("users", "weekly_digest")
    op.drop_column("users", "last_login")
