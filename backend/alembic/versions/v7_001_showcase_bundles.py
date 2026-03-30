"""add showcase bundle columns

Revision ID: v7_001_showcase_bundles
Revises: v6_001_model_drift_alerts
Create Date: 2026-03-30

Sprint 39 — Showcase Bundles & Preview URLs
"""
from alembic import op
import sqlalchemy as sa

revision = "v7_001_showcase_bundles"
down_revision = "v6_001_model_drift_alerts"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("showcase_products", sa.Column("preview_url", sa.String(500), nullable=True))
    op.add_column("showcase_products", sa.Column("is_bundle", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("showcase_products", sa.Column("bundle_items", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False))

def downgrade() -> None:
    op.drop_column("showcase_products", "bundle_items")
    op.drop_column("showcase_products", "is_bundle")
    op.drop_column("showcase_products", "preview_url")
