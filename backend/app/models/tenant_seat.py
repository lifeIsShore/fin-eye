"""
app/models/tenant_seat.py — Sprint 55
One row per invited/accepted seat within a B2B advisor tenant.
"""
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base


class TenantSeat(Base):
    __tablename__ = "tenant_seats"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id",   ondelete="CASCADE"), nullable=True,  index=True)
    invited_email = Column(String(255), nullable=False)
    role          = Column(String(20),  nullable=False, default="member")   # owner | admin | member
    invite_token  = Column(String(64),  nullable=True, unique=True)
    invited_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at   = Column(DateTime(timezone=True), nullable=True)
