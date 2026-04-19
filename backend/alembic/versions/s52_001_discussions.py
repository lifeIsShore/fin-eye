"""Sprint 52 — ticker_comments + ticker_comment_reactions

Revision ID: s52_001_discussions
Revises: s50_001_referrals
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s52_001_discussions"
down_revision = "s50_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticker_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("length(body) BETWEEN 10 AND 500", name="ck_comment_body_length"),
    )
    op.create_index("idx_tc_symbol_time", "ticker_comments", ["symbol", "created_at"],
                    postgresql_ops={"created_at": "DESC NULLS LAST"})

    op.create_table(
        "ticker_comment_reactions",
        sa.Column("comment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ticker_comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reaction", sa.String(10), nullable=False, server_default="up"),
        sa.PrimaryKeyConstraint("comment_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("ticker_comment_reactions")
    op.drop_index("idx_tc_symbol_time", table_name="ticker_comments")
    op.drop_table("ticker_comments")
