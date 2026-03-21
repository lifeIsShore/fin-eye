"""add ml_predictions table

Revision ID: v5_001_ml_predictions
Revises: v4_002_news_extend
Create Date: 2026-03-21

Sprint 2 — todos-v5 Phase 5.1
Creates the ml_predictions table that stores every model signal plus its
resolved outcome, enabling live accuracy tracking and regime analysis.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "v5_001_ml_predictions"
down_revision = "v4_002_news_extend"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_predictions",
        # ── Primary key ───────────────────────────────────────────────────────
        sa.Column("id", sa.BigInteger(), nullable=False),

        # ── What was predicted ────────────────────────────────────────────────
        sa.Column("symbol",            sa.String(20),  nullable=False),
        sa.Column("timeframe",         sa.String(10),  nullable=False),
        sa.Column("model_name",        sa.String(30),  nullable=False),
        sa.Column("mlflow_run_id",     sa.String(100), nullable=True),
        sa.Column("predicted_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("prediction_date",   sa.Date(),      nullable=False),
        sa.Column("predicted_direction", sa.Integer(), nullable=False),
        sa.Column("confidence",        sa.Float(),     nullable=False),
        sa.Column("expected_return",   sa.Float(),     nullable=True),
        sa.Column("horizon_periods",   sa.Integer(),   nullable=False),
        sa.Column("horizon_ends_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_at_prediction", sa.Float(),   nullable=False),

        # ── Outcome (filled in by cron after horizon passes) ──────────────────
        sa.Column("price_at_outcome",    sa.Float(),    nullable=True),
        sa.Column("actual_direction",    sa.Integer(),  nullable=True),
        sa.Column("actual_return",       sa.Float(),    nullable=True),
        sa.Column("was_correct",         sa.Boolean(),  nullable=True),
        sa.Column("outcome_resolved_at", sa.DateTime(timezone=True), nullable=True),

        # ── Context snapshot ──────────────────────────────────────────────────
        sa.Column("feature_snapshot",            JSONB,         nullable=True),
        sa.Column("macro_score_at_prediction",   sa.Float(),    nullable=True),
        sa.Column("vix_at_prediction",           sa.Float(),    nullable=True),
        sa.Column("market_regime_at_prediction", sa.String(30), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        # ── Constraints ───────────────────────────────────────────────────────
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol", "timeframe", "prediction_date",
            name="uq_ml_prediction_symbol_tf_date",
        ),
    )

    # Indexes
    op.create_index("idx_mlpred_symbol_tf",    "ml_predictions", ["symbol", "timeframe"])
    op.create_index("idx_mlpred_correct",      "ml_predictions", ["was_correct", "symbol"])
    op.create_index("idx_mlpred_regime",       "ml_predictions", ["market_regime_at_prediction"])
    op.create_index("idx_mlpred_predicted_at", "ml_predictions", ["predicted_at"])

    # Partial index: only unresolved rows — keeps the resolver query fast
    op.create_index(
        "idx_mlpred_pending",
        "ml_predictions",
        ["horizon_ends_at"],
        postgresql_where="outcome_resolved_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index("idx_mlpred_pending",       table_name="ml_predictions")
    op.drop_index("idx_mlpred_predicted_at",  table_name="ml_predictions")
    op.drop_index("idx_mlpred_regime",        table_name="ml_predictions")
    op.drop_index("idx_mlpred_correct",       table_name="ml_predictions")
    op.drop_index("idx_mlpred_symbol_tf",     table_name="ml_predictions")
    op.drop_table("ml_predictions")
