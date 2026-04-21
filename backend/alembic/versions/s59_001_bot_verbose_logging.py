"""s59_001_bot_verbose_logging — add verbose_logging to bot_configs"""
from alembic import op
import sqlalchemy as sa

revision = "s59_001_bot_verbose_logging"
down_revision = "s55_001_tenant_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bot_configs",
        sa.Column("verbose_logging", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("bot_configs", "verbose_logging")
