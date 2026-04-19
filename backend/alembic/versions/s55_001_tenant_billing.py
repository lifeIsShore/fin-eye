"""Sprint 55 — tenant billing tiers + tenant_seats

Revision ID: s55_001_tenant_billing
Revises: s52_002_polls
Create Date: 2026-04-19

Adds:
  - tenants.tier, seat_count, stripe_customer_id, stripe_subscription_id, billing_cycle_end
  - tenant_seats table (per-seat membership with role + invite lifecycle)
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "s55_001_tenant_billing"
down_revision: Union[str, None] = "s52_002_polls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extend tenants table ───────────────────────────────────────────────────
    op.add_column("tenants", sa.Column("tier", sa.String(20), nullable=False, server_default="starter"))
    op.add_column("tenants", sa.Column("seat_count", sa.Integer, nullable=False, server_default="1"))
    op.add_column("tenants", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("stripe_subscription_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("billing_cycle_end", sa.DateTime(timezone=True), nullable=True))

    # ── tenant_seats ───────────────────────────────────────────────────────────
    op.create_table(
        "tenant_seats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),  # null until accepted
        sa.Column("invited_email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),  # owner | admin | member
        sa.Column("invite_token", sa.String(64), nullable=True, unique=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "invited_email", name="uq_tenant_seat_email"),
    )
    op.create_index("idx_tenant_seats_tenant", "tenant_seats", ["tenant_id"])
    op.create_index("idx_tenant_seats_user",   "tenant_seats", ["user_id"])
    op.create_index("idx_tenant_seats_token",  "tenant_seats", ["invite_token"])


def downgrade() -> None:
    op.drop_table("tenant_seats")
    op.drop_column("tenants", "billing_cycle_end")
    op.drop_column("tenants", "stripe_subscription_id")
    op.drop_column("tenants", "stripe_customer_id")
    op.drop_column("tenants", "seat_count")
    op.drop_column("tenants", "tier")
