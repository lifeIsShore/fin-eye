"""Sprint 27 — add signal_grade_history table

Revision ID: s27_001_signal_grade_history
Revises: v6_001_model_drift_alerts
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa

revision = "s27_001_signal_grade_history"
down_revision = "v6_001_model_drift_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_grade_history",
        sa.Column("id",               sa.Integer(),               primary_key=True, autoincrement=True),
        sa.Column("symbol",           sa.String(20),              nullable=False),
        sa.Column("grade",            sa.String(10),              nullable=False),
        sa.Column("prev_grade",       sa.String(10),              nullable=True),
        sa.Column("grade_score",      sa.Integer(),               nullable=True),
        sa.Column("gas_score",        sa.Float(),                 nullable=False),
        sa.Column("component_scores", sa.JSON(),                  nullable=True),
        sa.Column("tradeable",        sa.String(5),               nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_grade_history_symbol_time",
        "signal_grade_history",
        ["symbol", "recorded_at"],
    )
    op.create_index(
        "ix_signal_grade_history_symbol",
        "signal_grade_history",
        ["symbol"],
    )


def downgrade() -> None:
    op.drop_index("ix_grade_history_symbol_time", table_name="signal_grade_history")
    op.drop_index("ix_signal_grade_history_symbol", table_name="signal_grade_history")
    op.drop_table("signal_grade_history")
