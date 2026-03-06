"""add api_keys, api_key_usage_logs, risk tables

P3-API-01 / P3-RISK-01

Revision ID: h8b9c0d1e2f3
Revises: g7a8b9c0d1e2
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "h8b9c0d1e2f3"
down_revision = "g7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("hashed_key", sa.String(256), nullable=False, unique=True),
        sa.Column("scopes", sa.String(256), nullable=False, server_default="gas,macro,sentiment"),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=False, server_default="30"),
        sa.Column("total_calls", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"], unique=True)

    # ── api_key_usage_logs ────────────────────────────────────────────────────
    op.create_table(
        "api_key_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(256), nullable=False),
        sa.Column("method", sa.String(8), nullable=False, server_default="GET"),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("response_ms", sa.Integer, nullable=True),
        sa.Column(
            "called_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_api_key_usage_logs_api_key_id", "api_key_usage_logs", ["api_key_id"])
    op.create_index("ix_api_key_usage_logs_called_at", "api_key_usage_logs", ["called_at"])


def downgrade() -> None:
    op.drop_table("api_key_usage_logs")
    op.drop_table("api_keys")
