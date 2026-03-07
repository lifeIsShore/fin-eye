"""add gas_snapshots table

EXP-PERF-01 — GAS pre-computation job

Revision ID: i9c0d1e2f3a4
Revises: h8b9c0d1e2f3
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = "i9c0d1e2f3a4"
down_revision = "h8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gas_snapshots",
        sa.Column("id",               sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("symbol",           sa.String(20),    nullable=False),
        sa.Column("gas_score",        sa.Float(),       nullable=False),
        sa.Column("weather_label",    sa.String(40),    nullable=False),
        sa.Column("regime",           sa.String(30),    nullable=False),
        sa.Column("component_scores", sa.JSON(),        nullable=False, server_default="{}"),
        sa.Column("technical_signals",sa.JSON(),        nullable=True),
        sa.Column("computed_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("source",           sa.String(10),    nullable=False, server_default="live"),
    )
    op.create_index(
        "ix_gas_snapshots_symbol",
        "gas_snapshots",
        ["symbol"],
    )
    op.create_index(
        "ix_gas_snapshots_symbol_computed",
        "gas_snapshots",
        ["symbol", "computed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_gas_snapshots_symbol_computed", table_name="gas_snapshots")
    op.drop_index("ix_gas_snapshots_symbol",           table_name="gas_snapshots")
    op.drop_table("gas_snapshots")
