"""add external_signals table

Revision ID: s40_001_external_signals
Revises: 5e66ab23ac8b
Create Date: 2026-03-30

Sprint 40 — External data signals (CNN/Crypto Fear&Greed, Google Trends,
Reddit mentions, Wikipedia pageviews).
"""
from alembic import op
import sqlalchemy as sa

revision = "s40_001_external_signals"
down_revision = "5e66ab23ac8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_signals",
        sa.Column("id",          sa.BigInteger(),                   nullable=False, autoincrement=True),
        sa.Column("source",      sa.String(30),                     nullable=False),
        sa.Column("symbol",      sa.String(20),                     nullable=True),
        sa.Column("signal_name", sa.String(50),                     nullable=False),
        sa.Column("value",       sa.Float(),                        nullable=False),
        sa.Column("raw_json",    sa.JSON(),                         nullable=True),
        sa.Column("fetched_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now(),                     nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ext_sig_source",          "external_signals", ["source"])
    op.create_index("idx_ext_sig_symbol",          "external_signals", ["symbol"])
    op.create_index("idx_ext_sig_signal_name",     "external_signals", ["signal_name"])
    op.create_index("idx_ext_sig_symbol_name_time","external_signals",
                    ["symbol", "signal_name", "fetched_at"])
    op.create_index("idx_ext_sig_source_time",     "external_signals",
                    ["source",  "fetched_at"])


def downgrade() -> None:
    op.drop_index("idx_ext_sig_source_time",      table_name="external_signals")
    op.drop_index("idx_ext_sig_symbol_name_time", table_name="external_signals")
    op.drop_index("idx_ext_sig_signal_name",      table_name="external_signals")
    op.drop_index("idx_ext_sig_symbol",           table_name="external_signals")
    op.drop_index("idx_ext_sig_source",           table_name="external_signals")
    op.drop_table("external_signals")
