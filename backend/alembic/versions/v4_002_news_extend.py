"""extend news_articles with url, sentiment_label, finbert_score, fetch metadata

Revision ID: v4_002_news_extend
Revises: v4_001_bulk_tables
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = "v4_002_news_extend"
down_revision = "v4_001_bulk_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns (all nullable so existing rows are unaffected)
    op.add_column("news_articles", sa.Column("url",             sa.Text(),    nullable=True))
    op.add_column("news_articles", sa.Column("sentiment_label", sa.String(10), nullable=True))
    op.add_column("news_articles", sa.Column("finbert_score",   sa.Float(),   nullable=True))
    op.add_column("news_articles", sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("news_articles", sa.Column("fetch_source",    sa.String(20), nullable=True, server_default="finnhub"))

    # Create indexes — wrap each in try/except because an earlier autogenerate
    # or Base.metadata.create_all may have already created them on existing DBs.
    try:
        op.create_index("idx_news_symbol_date", "news_articles", ["symbol", "published_at"])
    except Exception:
        pass  # index already exists — safe to skip

    try:
        op.create_index("idx_news_last_fetched", "news_articles", ["symbol", "last_fetched_at"])
    except Exception:
        pass  # index already exists — safe to skip

    # Unique constraint to prevent duplicate articles — same guard
    try:
        op.create_unique_constraint(
            "uq_news_symbol_title_ts",
            "news_articles",
            ["symbol", "title", "published_at"],
        )
    except Exception:
        pass  # constraint already exists — safe to skip


def downgrade() -> None:
    try:
        op.drop_constraint("uq_news_symbol_title_ts", "news_articles", type_="unique")
    except Exception:
        pass
    try:
        op.drop_index("idx_news_last_fetched", table_name="news_articles")
    except Exception:
        pass
    try:
        op.drop_index("idx_news_symbol_date", table_name="news_articles")
    except Exception:
        pass
    op.drop_column("news_articles", "fetch_source")
    op.drop_column("news_articles", "last_fetched_at")
    op.drop_column("news_articles", "finbert_score")
    op.drop_column("news_articles", "sentiment_label")
    op.drop_column("news_articles", "url")
