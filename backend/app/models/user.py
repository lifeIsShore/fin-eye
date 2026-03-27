"""
app/models/user.py
User model — UUID primary key, fields aligned with auth_service and UserResponse schema.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String(128), nullable=True)

    # Account state
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Subscription tier: "free" | "pro" | "institutional"
    subscription_tier = Column(String(32), default="free", nullable=False)

    # User preferences — Sprint 23
    default_symbol = Column(String(20), nullable=True)   # e.g. "AAPL" — loads on dashboard open

    # Risk profile — Sprint 24
    risk_profile = Column(String(32), nullable=True)     # Conservative | Moderate | Aggressive | Income

    # Two-factor authentication (TOTP) — CORE-SEC-01
    totp_secret  = Column(String(256), nullable=True)   # Fernet-encrypted; null until setup
    totp_enabled = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Monetisation (Sprint 38)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)   # null = never trialed
    paused_until  = Column(DateTime(timezone=True), nullable=True)   # null = not paused

    # Relationships
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="owner", cascade="all, delete-orphan")
    legal_consents = relationship("LegalConsent", back_populates="owner", cascade="all, delete-orphan")
