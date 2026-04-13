"""s47_001_bot_tables — Paper Trading Bot: bot_configs, bot_positions, bot_audit_log"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "s47_001_bot_tables"
down_revision = "s46_001_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mode", sa.String(10), nullable=False, server_default="paper"),
        sa.Column("strategy", sa.String(20), nullable=False, server_default="balanced"),
        sa.Column("min_grade", sa.String(3), nullable=False, server_default="B"),
        sa.Column("max_position_pct", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("max_total_pct", sa.Float(), nullable=False, server_default="0.80"),
        sa.Column("max_sector_pct", sa.Float(), nullable=False, server_default="0.40"),
        sa.Column("daily_loss_limit", sa.Float(), nullable=False, server_default="0.03"),
        sa.Column("portfolio_value", sa.Float(), nullable=False, server_default="10000.0"),
        sa.Column("halt_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_bot_configs_user_id", "bot_configs", ["user_id"])

    op.create_table(
        "bot_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("entry_grade", sa.String(3), nullable=False),
        sa.Column("entry_gas", sa.Float(), nullable=False),
        sa.Column("size_units", sa.Float(), nullable=False),
        sa.Column("size_usd", sa.Float(), nullable=False),
        sa.Column("position_pct", sa.Float(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("close_reason", sa.String(50), nullable=True),
        sa.Column("pnl_usd", sa.Float(), nullable=True),
        sa.Column("pnl_pct", sa.Float(), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("idx_bot_pos_user_symbol_open", "bot_positions", ["user_id", "symbol", "is_open"])

    op.create_table(
        "bot_audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("grade", sa.String(3), nullable=True),
        sa.Column("gas_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("size_usd", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("position_id", UUID(as_uuid=True), sa.ForeignKey("bot_positions.id"), nullable=True),
        sa.Column("regime", sa.String(30), nullable=True),
        sa.Column("macro_score", sa.Float(), nullable=True),
    )
    op.create_index("idx_bot_log_user_time", "bot_audit_log", ["user_id", "logged_at"])
    op.create_index("idx_bot_log_symbol", "bot_audit_log", ["symbol", "logged_at"])


def downgrade() -> None:
    op.drop_table("bot_audit_log")
    op.drop_table("bot_positions")
    op.drop_table("bot_configs")
