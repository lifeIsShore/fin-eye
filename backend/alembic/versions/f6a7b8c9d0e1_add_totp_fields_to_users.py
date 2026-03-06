"""
f6a7b8c9d0e1_add_totp_fields_to_users

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-06

Adds TOTP-based 2FA fields to the users table (CORE-SEC-01).

Design notes:
  - totp_secret is encrypted-at-rest using Fernet symmetric encryption in the
    service layer. The DB stores only the ciphertext; the encryption key is
    in settings.totp_encryption_key.
  - totp_enabled defaults to False. It is set to True only after the user
    successfully verifies their first code via POST /auth/2fa/enable.
  - No new table is needed — 2FA state lives entirely on the user row.
"""

from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'totp_secret',
        sa.String(256),
        nullable=True,
        comment='Fernet-encrypted TOTP secret; null until 2FA setup begins',
    ))
    op.add_column('users', sa.Column(
        'totp_enabled',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='True once user has verified their first TOTP code',
    ))


def downgrade() -> None:
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
