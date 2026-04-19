"""
app/api/v1/endpoints/compliance.py — Sprint 55
Compliance audit log export and summary for B2B tenant admins and platform admins.

Endpoints:
  GET /api/v1/admin/compliance/export   – paginated JSON or CSV stream
  GET /api/v1/admin/compliance/summary  – aggregate stats
"""
import csv
import io
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.database import AsyncSessionLocal
from app.models.compliance_audit_log import ComplianceAuditLog
from app.models.tenant import Tenant
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

MAX_EXPORT_DAYS = 90


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin_or_tenant_owner(current_user: User, tenant: Optional[Tenant] = None) -> None:
    """Raises 403 unless user is platform admin, or tenant owner/admin."""
    if current_user.is_admin:
        return
    if tenant and str(tenant.owner_user_id) == str(current_user.id):
        return
    raise HTTPException(status_code=403, detail="Not authorised.")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComplianceLogEntry(BaseModel):
    id: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    action: str
    resource: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime


class ComplianceSummary(BaseModel):
    total_calls: int
    unique_users: int
    unique_tenants: int
    from_date: Optional[str]
    to_date: Optional[str]
    calls_by_action: dict[str, int]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="Export compliance audit log (JSON or CSV)",
    response_model=None,
)
async def export_compliance_log(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant UUID"),
    from_date: Optional[str] = Query(None, description="ISO date e.g. 2026-01-01"),
    to_date:   Optional[str] = Query(None, description="ISO date e.g. 2026-04-01"),
    format:    str           = Query("json", description="json | csv"),
    limit:     int           = Query(200, le=1000, description="Max rows (JSON only)"),
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        # Resolve tenant for ownership check
        tenant: Optional[Tenant] = None
        if tenant_id:
            res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = res.scalar_one_or_none()
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found.")

        _require_admin_or_tenant_owner(current_user, tenant)

        # Build query
        q = select(ComplianceAuditLog).order_by(ComplianceAuditLog.timestamp.desc())

        if tenant_id:
            q = q.where(ComplianceAuditLog.tenant_id == tenant_id)

        if from_date:
            try:
                dt_from = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
                q = q.where(ComplianceAuditLog.timestamp >= dt_from)
            except ValueError:
                raise HTTPException(400, "Invalid from_date format. Use ISO 8601 e.g. 2026-01-01")

        if to_date:
            try:
                dt_to = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
                q = q.where(ComplianceAuditLog.timestamp <= dt_to)
            except ValueError:
                raise HTTPException(400, "Invalid to_date format. Use ISO 8601 e.g. 2026-04-01")

        if format == "csv":
            # Stream full result set (no limit for CSV)
            result = await session.execute(q)
            rows = result.scalars().all()

            def _csv_generator():
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["id", "tenant_id", "user_id", "action", "resource", "ip_address", "timestamp"])
                for row in rows:
                    writer.writerow([
                        str(row.id),
                        str(row.tenant_id) if row.tenant_id else "",
                        str(row.user_id) if row.user_id else "",
                        row.action,
                        row.resource or "",
                        row.ip_address or "",
                        row.timestamp.isoformat() if row.timestamp else "",
                    ])
                yield buf.getvalue()

            filename = f"compliance_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            return StreamingResponse(
                _csv_generator(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        # JSON response
        q = q.limit(limit)
        result = await session.execute(q)
        rows = result.scalars().all()

    return [
        ComplianceLogEntry(
            id=str(r.id),
            tenant_id=str(r.tenant_id) if r.tenant_id else None,
            user_id=str(r.user_id) if r.user_id else None,
            action=r.action,
            resource=r.resource,
            ip_address=r.ip_address,
            timestamp=r.timestamp,
        )
        for r in rows
    ]


@router.get(
    "/summary",
    response_model=ComplianceSummary,
    summary="Aggregate compliance stats for a tenant or platform-wide",
)
async def get_compliance_summary(
    tenant_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        tenant: Optional[Tenant] = None
        if tenant_id:
            res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = res.scalar_one_or_none()
            if not tenant:
                raise HTTPException(404, "Tenant not found.")

        _require_admin_or_tenant_owner(current_user, tenant)

        q_base = select(ComplianceAuditLog)
        if tenant_id:
            q_base = q_base.where(ComplianceAuditLog.tenant_id == tenant_id)
        if from_date:
            try:
                q_base = q_base.where(
                    ComplianceAuditLog.timestamp >= datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
                )
            except ValueError:
                raise HTTPException(400, "Invalid from_date")
        if to_date:
            try:
                q_base = q_base.where(
                    ComplianceAuditLog.timestamp <= datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
                )
            except ValueError:
                raise HTTPException(400, "Invalid to_date")

        result = await session.execute(q_base)
        rows = result.scalars().all()

    calls_by_action: dict[str, int] = {}
    unique_users: set = set()
    unique_tenants: set = set()

    for r in rows:
        calls_by_action[r.action] = calls_by_action.get(r.action, 0) + 1
        if r.user_id:
            unique_users.add(str(r.user_id))
        if r.tenant_id:
            unique_tenants.add(str(r.tenant_id))

    return ComplianceSummary(
        total_calls=len(rows),
        unique_users=len(unique_users),
        unique_tenants=len(unique_tenants),
        from_date=from_date,
        to_date=to_date,
        calls_by_action=calls_by_action,
    )
