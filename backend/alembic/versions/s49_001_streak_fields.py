"""add streak fields to users

Revision ID: s49_001_streak_fields
Revises: s45_001_tenants
Create Date: 2026-04-13

Adds login_streak_days, longest_streak_days, last_streak_date to users table.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "s49_001_streak_fields"
down_revision: Union[str, None] = "s45_001_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("login_streak_days",   sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_streak_date",    sa.Date(),    nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_streak_date")
    op.drop_column("users", "longest_streak_days")
    op.drop_column("users", "login_streak_days")
