"""
add_advanced_macro_indicator_names

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-05

NO schema changes — macro_indicators already stores (indicator_name, value, date)
with a unique constraint on (indicator_name, date).  The new indicators introduced
by P2-MACRO-ADV-01 are purely data-level additions:

  treasury_2y            DGS2  — 2-Year CMT yield
  treasury_5y            DGS5  — 5-Year CMT yield
  treasury_10y           DGS10 — 10-Year CMT yield
  treasury_30y           DGS30 — 30-Year CMT yield
  recession_indicator    USREC — NBER recession dummy (0/1)
  nonfarm_payrolls       PAYEMS — thousands of persons
  industrial_production  INDPRO — index level

Action: Run POST /api/v1/macro/refresh (or the APScheduler job) to
populate these new indicator names.  No SQL migration required.
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No DDL changes required — the macro_indicators table already has the
    # correct schema.  New indicator_name values are populated by the refresh job.
    pass


def downgrade() -> None:
    # Optionally remove the new indicator rows if rolling back:
    op.execute(
        sa.text("""
            DELETE FROM macro_indicators
            WHERE indicator_name IN (
                'treasury_2y', 'treasury_5y', 'treasury_10y', 'treasury_30y',
                'recession_indicator', 'nonfarm_payrolls', 'industrial_production'
            )
        """)
    )
