"""
app/models/alert.py
Price and GAS alert model for CORE-NOTIF-01.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class Alert(Base):
    """
    User-defined alert that fires when a condition is met.

    alert_type values:
        "price_above"   — fires when close price > threshold
        "price_below"   — fires when close price < threshold
        "gas_above"     — fires when GAS score  > threshold
        "gas_below"     — fires when GAS score  < threshold

    delivery_channel values (MVP):
        "in_app"        — stored as triggered; frontend polls /alerts/triggered
        "email"         — reserved for CORE-EMAIL-01 (not wired yet)
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    alert_type = Column(String(32), nullable=False)   # price_above | price_below | gas_above | gas_below
    threshold = Column(Float, nullable=False)
    delivery_channel = Column(String(16), nullable=False, default="in_app")
    is_active = Column(Boolean, default=True, nullable=False)

    # Trigger tracking
    triggered_at = Column(DateTime, nullable=True)
    triggered_value = Column(Float, nullable=True)  # the actual value that caused the trigger

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User")
