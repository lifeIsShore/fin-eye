"""add tickers_universe and bulk_job_runs tables

Revision ID: v4_001_bulk_tables
Revises: 1cd7803cd96a
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = "v4_001_bulk_tables"
down_revision = "1cd7803cd96a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tickers_universe ─────────────────────────────────────────────────────
    op.create_table(
        "tickers_universe",
        sa.Column("id",          sa.Integer(),     nullable=False),
        sa.Column("symbol",      sa.String(20),    nullable=False),
        sa.Column("name",        sa.String(200),   nullable=True),
        sa.Column("asset_class", sa.String(20),    nullable=True),
        sa.Column("tr_rank",     sa.Integer(),     nullable=True),
        sa.Column("exchange",    sa.String(20),    nullable=True),
        sa.Column("is_active",   sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("yf_valid",    sa.Boolean(),     nullable=True),
        sa.Column("added_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_ticker_universe_symbol"),
    )
    op.create_index("ix_tickers_universe_symbol", "tickers_universe", ["symbol"])

    # ── bulk_job_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "bulk_job_runs",
        sa.Column("id",           sa.Integer(),  nullable=False),
        sa.Column("job_type",     sa.String(20), nullable=False),
        sa.Column("scope",        sa.String(20), nullable=False),
        sa.Column("symbol",       sa.String(20), nullable=True),
        sa.Column("status",       sa.String(20), nullable=False),
        sa.Column("reason",       sa.Text(),     nullable=True),
        sa.Column("rows_added",   sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("started_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_bulk_job_symbol",  "bulk_job_runs", ["symbol"])
    op.create_index("idx_bulk_job_status",  "bulk_job_runs", ["status"])
    op.create_index("idx_bulk_job_type_ts", "bulk_job_runs", ["job_type", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_bulk_job_type_ts", table_name="bulk_job_runs")
    op.drop_index("idx_bulk_job_status",  table_name="bulk_job_runs")
    op.drop_index("idx_bulk_job_symbol",  table_name="bulk_job_runs")
    op.drop_table("bulk_job_runs")

    op.drop_index("ix_tickers_universe_symbol", table_name="tickers_universe")
    op.drop_table("tickers_universe")
