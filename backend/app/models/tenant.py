"""
app/models/tenant.py — Sprint 45
B2B white-label tenant model. Each advisor / firm gets a subdomain-scoped
tenant with their own branding and custom GAS weights.
"""
import uuid
from sqlalchemy import Boolean, Column, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.db.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug         = Column(String(64), unique=True, nullable=False, index=True)  # subdomain key
    name         = Column(String(128), nullable=False)
    logo_url     = Column(String(512), nullable=True)
    accent_colour = Column(String(7), nullable=True)   # hex e.g. "#0ea5e9"

    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Custom GAS component weights — must sum to 1.0 (enforced at API layer)
    weight_technical = Column(Float, nullable=False, default=0.40)
    weight_macro     = Column(Float, nullable=False, default=0.30)
    weight_sentiment = Column(Float, nullable=False, default=0.30)

    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
