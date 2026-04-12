"""
app/models/compliance_audit_log.py — Sprint 45
Append-only compliance audit log for B2B tenant API calls.
"""
import uuid
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base


class ComplianceAuditLog(Base):
    __tablename__ = "compliance_audit_logs"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id   = Column(UUID(as_uuid=True), nullable=True, index=True)
    action    = Column(String(64),  nullable=False)   # e.g. "GET_GAS_SNAPSHOT"
    resource  = Column(String(256), nullable=True)    # e.g. "/api/v1/admin/gas/snapshots/AAPL"
    ip_address = Column(String(45), nullable=True)    # IPv4 or IPv6
    timestamp  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
