"""add public_backtest_runs leaderboard table

Revision ID: s44_002_leaderboard
Revises: s44_001_churn_tracking
Create Date: 2026-04-11

Creates public_backtest_runs — stores anonymised published backtest results
for the community leaderboard. Resets weekly via a scheduler job.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "s44_002_leaderboard"
down_revision: Union[str, None] = "s44_001_churn_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "public_backtest_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("strategy_name", sa.String(80), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("strategy", sa.String(40), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=True),
        sa.Column("end_date", sa.String(10), nullable=True),
        sa.Column("sharpe_ratio", sa.Float, nullable=False),
        sa.Column("total_return_pct", sa.Float, nullable=False),
        sa.Column("max_drawdown_pct", sa.Float, nullable=False),
        sa.Column("total_trades", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_pbr_sharpe", "public_backtest_runs", ["sharpe_ratio"], postgresql_using="btree")
    op.create_index("idx_pbr_submitted_at", "public_backtest_runs", ["submitted_at"], postgresql_using="btree")


def downgrade() -> None:
    op.drop_table("public_backtest_runs")
