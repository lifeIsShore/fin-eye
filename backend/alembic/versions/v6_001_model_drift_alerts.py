"""add model_drift_alerts table

Revision ID: v6_001_model_drift_alerts
Revises: v5_001_ml_predictions
Create Date: 2026-03-21

Sprint 6 — todos-v5 Phase 5.5
"""
from alembic import op
import sqlalchemy as sa

revision = "v6_001_model_drift_alerts"
down_revision = "v5_001_ml_predictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_drift_alerts",
        sa.Column("id",                  sa.BigInteger(), nullable=False),
        sa.Column("symbol",              sa.String(20),   nullable=False),
        sa.Column("timeframe",           sa.String(10),   nullable=False),
        sa.Column("val_accuracy_pct",    sa.Float(),      nullable=False),
        sa.Column("live_accuracy_pct",   sa.Float(),      nullable=False),
        sa.Column("delta_pp",            sa.Float(),      nullable=False),
        sa.Column("n_live_predictions",  sa.Integer(),    nullable=False),
        sa.Column("severity",            sa.String(10),   nullable=False, server_default="warning"),
        sa.Column("auto_retrain",        sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("retrained_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged",        sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("ack_at",              sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at",         sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at",         sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_drift_symbol_tf",  "model_drift_alerts", ["symbol", "timeframe"])
    op.create_index("idx_drift_unacked",    "model_drift_alerts", ["acknowledged", "detected_at"])
    op.create_index("idx_drift_severity",   "model_drift_alerts", ["severity"])


def downgrade() -> None:
    op.drop_index("idx_drift_severity",  table_name="model_drift_alerts")
    op.drop_index("idx_drift_unacked",   table_name="model_drift_alerts")
    op.drop_index("idx_drift_symbol_tf", table_name="model_drift_alerts")
    op.drop_table("model_drift_alerts")
