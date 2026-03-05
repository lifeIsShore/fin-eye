"""
d4e5f6a7b8c9_add_analytics_events_table

Revision ID: d4e5f6a7b8c9
Revises: c45a8b119e54
Create Date: 2026-03-06

Adds the analytics_events table for CORE-ANALYTICS-01 product analytics.

Design notes:
  - user_id FK uses ON DELETE SET NULL so that anonymised/deleted users do
    not cascade-delete their analytics history (valuable for long-term trend data).
  - properties column is JSONB (not JSON) for efficient key-based querying on
    PostgreSQL. Falls back gracefully to JSON on SQLite in tests.
  - Three composite indexes optimise the three primary query patterns:
      1. Funnel queries (event_name + created_at)
      2. Per-user adoption (user_id + event_name)
      3. DAU aggregation (created_at + user_id)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c45a8b119e54'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'analytics_events',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('anon_id', sa.String(length=64), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_name', sa.String(length=128), nullable=False),
        sa.Column('properties', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('page', sa.String(length=255), nullable=True),
        sa.Column('feature', sa.String(length=128), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    # Single-column indexes
    op.create_index('ix_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('ix_analytics_events_event_name', 'analytics_events', ['event_name'])
    op.create_index('ix_analytics_events_created_at', 'analytics_events', ['created_at'])

    # Composite indexes for dashboard query patterns
    op.create_index(
        'ix_analytics_event_name_created',
        'analytics_events',
        ['event_name', 'created_at'],
    )
    op.create_index(
        'ix_analytics_user_event',
        'analytics_events',
        ['user_id', 'event_name'],
    )
    op.create_index(
        'ix_analytics_created_user',
        'analytics_events',
        ['created_at', 'user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_analytics_created_user', table_name='analytics_events')
    op.drop_index('ix_analytics_user_event', table_name='analytics_events')
    op.drop_index('ix_analytics_event_name_created', table_name='analytics_events')
    op.drop_index('ix_analytics_events_created_at', table_name='analytics_events')
    op.drop_index('ix_analytics_events_event_name', table_name='analytics_events')
    op.drop_index('ix_analytics_events_user_id', table_name='analytics_events')
    op.drop_table('analytics_events')
