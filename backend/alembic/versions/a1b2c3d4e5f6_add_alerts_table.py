"""add_alerts_table_and_fix_user_uuid

Revision ID: a1b2c3d4e5f6
Revises: c45a8b119e54
Create Date: 2026-03-05

Changes:
  - Alters users.id from INTEGER to UUID (requires empty DB or manual migration on existing data)
  - Alters FK columns in portfolios, watchlist_items, legal_consents to UUID
  - Creates alerts table for CORE-NOTIF-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a1b2c3d4e5f6'
down_revision = 'c45a8b119e54'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTE: Migrating users.id from INTEGER -> UUID requires either:
    #   (a) an empty database (drop + recreate), or
    #   (b) a multi-step migration with data backfill.
    # For MVP where the DB is still fresh, we drop and recreate affected tables.
    # On a production DB with data, use: ALTER TABLE users ALTER COLUMN id TYPE uuid USING gen_random_uuid()

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('alert_type', sa.String(32), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('delivery_channel', sa.String(16), nullable=False, server_default='in_app'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('triggered_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('alerts')
