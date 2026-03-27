"""
alembic/versions/v4_003_trial_pause.py
=======================================
Sprint 38 — add trial_ends_at and paused_until to users table.

Upgrade:  alembic upgrade head
Downgrade: alembic downgrade -1
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "v4_003_trial_pause"
down_revision = ("v4_002_news_extend", "6fe5eb0b421c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "paused_until")
    op.drop_column("users", "trial_ends_at")
