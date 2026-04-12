"""add tenants, compliance_audit_logs tables

Revision ID: s45_001_tenants
Revises: s44_002_leaderboard
Create Date: 2026-04-12

Sprint 45 B2B foundation:
  - tenants table (slug, branding, custom GAS weights)
  - compliance_audit_logs table (append-only per-call log)
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "s45_001_tenants"
down_revision: Union[str, None] = "s44_002_leaderboard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug",         sa.String(64),  nullable=False, unique=True),
        sa.Column("name",         sa.String(128), nullable=False),
        sa.Column("logo_url",     sa.String(512), nullable=True),
        sa.Column("accent_colour",sa.String(7),   nullable=True),
        sa.Column("owner_user_id",UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("weight_technical", sa.Float,   nullable=False, server_default="0.4"),
        sa.Column("weight_macro",     sa.Float,   nullable=False, server_default="0.3"),
        sa.Column("weight_sentiment", sa.Float,   nullable=False, server_default="0.3"),
        sa.Column("is_active",    sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "compliance_audit_logs",
        sa.Column("id",        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("action",    sa.String(64),  nullable=False),
        sa.Column("resource",  sa.String(256), nullable=True),
        sa.Column("ip_address",sa.String(45),  nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_cal_tenant_id",  "compliance_audit_logs", ["tenant_id"])
    op.create_index("idx_cal_user_id",    "compliance_audit_logs", ["user_id"])
    op.create_index("idx_cal_timestamp",  "compliance_audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("compliance_audit_logs")
    op.drop_table("tenants")
