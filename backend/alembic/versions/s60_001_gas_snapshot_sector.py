"""s60_001_gas_snapshot_sector — add sector column to gas_snapshots"""
from alembic import op
import sqlalchemy as sa

revision = "s60_001_gas_snapshot_sector"
down_revision = "s59_001_bot_verbose_logging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gas_snapshots",
        sa.Column("sector", sa.String(60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gas_snapshots", "sector")
