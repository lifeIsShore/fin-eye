"""
app/models/custom_indicator.py
─────────────────────────────────────────────────────────────────────────────
P3-ANALYTICS-01 — Custom Indicator model

Stores a user's named indicator formula (as a JSON expression tree) so it
can be saved, re-loaded, and used in the backtesting engine.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class CustomIndicator(Base):
    __tablename__ = "custom_indicators"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    name        = Column(String(80), nullable=False)
    description = Column(String(255), nullable=True)
    # JSON expression tree — see indicator_service.py for schema
    formula     = Column(JSONB, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User")
