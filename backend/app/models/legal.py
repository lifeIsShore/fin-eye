"""app/models/legal.py"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base

# Bump this string any time the ToS or Privacy Policy materially changes.
CURRENT_LEGAL_VERSION = "1.0.0"


class LegalConsent(Base):
    __tablename__ = "legal_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doc_version = Column(String(20), nullable=False, default=CURRENT_LEGAL_VERSION)
    accepted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "doc_version", name="uq_consent_user_version"),
    )

    owner = relationship("User", back_populates="legal_consents")
