"""
e5f6a7b8c9d0_add_experiments_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-06

Adds experiments and experiment_assignments tables for CORE-EXPERIMENT-01.

Design notes:
  - experiments.key has a unique index — used as the public API identifier.
  - experiment_assignments has TWO unique constraints:
      (experiment_id, user_id)  — for authenticated users
      (experiment_id, anon_id)  — for anonymous visitors
    These enforce idempotency at the DB level; the service layer checks first
    but the constraint is the authoritative guard.
  - experiment_assignments.user_id FK uses ON DELETE SET NULL for GDPR parity.
  - experiment_assignments.experiment_id FK uses ON DELETE CASCADE — deleting
    an experiment removes all its assignment records automatically.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── experiments ────────────────────────────────────────────────────────
    op.create_table(
        'experiments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(128), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=True),
        sa.Column('variants', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('traffic_pct', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(32), nullable=False, server_default='draft'),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_experiments_key', 'experiments', ['key'], unique=True)
    op.create_index('ix_experiments_status', 'experiments', ['status'])

    # ── experiment_assignments ─────────────────────────────────────────────
    op.create_table(
        'experiment_assignments',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            'experiment_id',
            sa.Integer(),
            sa.ForeignKey('experiments.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('anon_id', sa.String(64), nullable=True),
        sa.Column('variant_key', sa.String(128), nullable=False),
        sa.Column(
            'assigned_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('in_traffic', sa.Boolean(), nullable=False, server_default='true'),
        # Idempotency constraints
        sa.UniqueConstraint(
            'experiment_id', 'user_id',
            name='uq_experiment_assignment_user',
        ),
        sa.UniqueConstraint(
            'experiment_id', 'anon_id',
            name='uq_experiment_assignment_anon',
        ),
    )
    op.create_index(
        'ix_exp_assign_exp_user',
        'experiment_assignments',
        ['experiment_id', 'user_id'],
    )
    op.create_index(
        'ix_exp_assign_user_id',
        'experiment_assignments',
        ['user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_exp_assign_user_id', table_name='experiment_assignments')
    op.drop_index('ix_exp_assign_exp_user', table_name='experiment_assignments')
    op.drop_table('experiment_assignments')

    op.drop_index('ix_experiments_status', table_name='experiments')
    op.drop_index('ix_experiments_key', table_name='experiments')
    op.drop_table('experiments')
