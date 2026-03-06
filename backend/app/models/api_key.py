"""
app/models/api_key.py

P3-API-01 — Public API key model.

Each API key:
  - Belongs to a user
  - Has a hashed secret (never stored in plaintext after creation)
  - Has a prefix for identification (first 8 chars of the raw key, shown in UI)
  - Has a rate limit (requests per minute)
  - Has a scope set (e.g. ["gas", "macro", "sentiment", "risk", "backtest"])
  - Tracks usage stats (total calls, last used)
  - Can be revoked (is_active=False)
"""
from __future__ import annotations

import secrets
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Display
    name = Column(String(128), nullable=False)           # user-chosen label
    key_prefix = Column(String(12), nullable=False)      # first 8 chars, shown in UI
    hashed_key = Column(String(256), nullable=False, unique=True, index=True)

    # Scopes — comma-separated, e.g. "gas,macro,sentiment"
    scopes = Column(String(256), nullable=False, default="gas,macro,sentiment")

    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=False, default=30)

    # Usage tracking
    total_calls = Column(BigInteger, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # State
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # None = never expires

    # Audit
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(Text, nullable=True)


class ApiKeyUsageLog(Base):
    """
    Per-call usage log for the public API.
    Kept for 90 days then pruned by a scheduler job.
    """
    __tablename__ = "api_key_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request metadata
    endpoint = Column(String(256), nullable=False)
    method = Column(String(8), nullable=False, default="GET")
    status_code = Column(Integer, nullable=True)
    response_ms = Column(Integer, nullable=True)  # latency in ms

    called_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
