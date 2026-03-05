from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

# Bump this string any time the ToS or Privacy Policy materially changes.
# Users who accepted an older version will be prompted to re-accept.
CURRENT_LEGAL_VERSION = "1.0.0"


class LegalConsent(Base):
    __tablename__ = "legal_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Which version of the legal docs was accepted
    doc_version = Column(String(20), nullable=False, default=CURRENT_LEGAL_VERSION)
    accepted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # One record per user per version — if we re-ask, a new row is inserted
    __table_args__ = (
        UniqueConstraint("user_id", "doc_version", name="uq_consent_user_version"),
    )

    owner = relationship("User", back_populates="legal_consents")
