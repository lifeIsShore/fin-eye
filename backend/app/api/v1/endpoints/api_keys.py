"""
app/api/v1/endpoints/api_keys.py

P3-API-01 — API key management for authenticated users.

Routes:
  GET    /api-keys          — list my API keys
  POST   /api-keys          — create a new API key (raw key shown once)
  PATCH  /api-keys/{id}     — update scopes
  DELETE /api-keys/{id}     — revoke key
  GET    /api-keys/{id}/usage — recent usage log
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.api_key import ApiKey, ApiKeyUsageLog
from app.models.user import User
from app.services.api_key_service import (
    ALL_SCOPES,
    create_api_key,
    list_api_keys,
    revoke_api_key,
    update_api_key_scopes,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(default=["gas", "macro", "sentiment"])
    rate_limit_per_minute: int = Field(default=30, ge=1, le=300)
    expires_at: Optional[datetime] = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        invalid = set(v) - ALL_SCOPES
        if invalid:
            raise ValueError(f"Invalid scopes: {invalid}. Valid: {sorted(ALL_SCOPES)}")
        return v


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    rate_limit_per_minute: int
    total_calls: int
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_key(cls, k: ApiKey) -> "ApiKeyResponse":
        return cls(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes.split(","),
            rate_limit_per_minute=k.rate_limit_per_minute,
            total_calls=k.total_calls or 0,
            last_used_at=k.last_used_at,
            is_active=k.is_active,
            created_at=k.created_at,
            expires_at=k.expires_at,
        )


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Includes the raw key — shown exactly once."""
    raw_key: str
    warning: str = (
        "Store this key securely. It will not be shown again. "
        "Anyone with this key can make API calls on your behalf."
    )


class ApiKeyScopesUpdate(BaseModel):
    scopes: list[str]

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        invalid = set(v) - ALL_SCOPES
        if invalid:
            raise ValueError(f"Invalid scopes: {invalid}")
        if not v:
            raise ValueError("At least one scope is required.")
        return v


class UsageLogEntry(BaseModel):
    endpoint: str
    method: str
    status_code: Optional[int]
    response_ms: Optional[int]
    called_at: datetime


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ApiKeyResponse], summary="List my API keys")
async def get_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    keys = await list_api_keys(db, current_user.id)
    return [ApiKeyResponse.from_orm_key(k) for k in keys]


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_key(
    body: ApiKeyCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """
    Creates a new API key. The raw key is returned **once only** — store it immediately.
    Subsequent requests only show the key prefix for identification.
    """
    # Cap at 10 keys per user
    existing = await list_api_keys(db, current_user.id)
    active = [k for k in existing if k.is_active]
    if len(active) >= 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum of 10 active API keys per account.",
        )

    try:
        key_obj, raw_key = await create_api_key(
            db,
            user_id=current_user.id,
            name=body.name,
            scopes=body.scopes,
            rate_limit_per_minute=body.rate_limit_per_minute,
            expires_at=body.expires_at,
        )
        await db.commit()
        await db.refresh(key_obj)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    resp = ApiKeyResponse.from_orm_key(key_obj)
    return ApiKeyCreatedResponse(**resp.model_dump(), raw_key=raw_key)


@router.patch(
    "/{key_id}/scopes",
    response_model=ApiKeyResponse,
    summary="Update scopes on an existing API key",
)
async def patch_scopes(
    key_id: uuid.UUID,
    body: ApiKeyScopesUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    try:
        key_obj = await update_api_key_scopes(db, key_id, current_user.id, body.scopes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if key_obj is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    await db.commit()
    await db.refresh(key_obj)
    return ApiKeyResponse.from_orm_key(key_obj)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke (delete) an API key",
)
async def revoke_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    found = await revoke_api_key(db, key_id, current_user.id)
    if not found:
        raise HTTPException(status_code=404, detail="API key not found.")
    await db.commit()


@router.get(
    "/{key_id}/usage",
    response_model=list[UsageLogEntry],
    summary="Recent usage log for an API key (last 100 calls)",
)
async def get_usage(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[UsageLogEntry]:
    # Verify ownership
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    key_obj = result.scalar_one_or_none()
    if key_obj is None:
        raise HTTPException(status_code=404, detail="API key not found.")

    logs_result = await db.execute(
        select(ApiKeyUsageLog)
        .where(ApiKeyUsageLog.api_key_id == key_id)
        .order_by(ApiKeyUsageLog.called_at.desc())
        .limit(100)
    )
    logs = logs_result.scalars().all()
    return [
        UsageLogEntry(
            endpoint=l.endpoint,
            method=l.method,
            status_code=l.status_code,
            response_ms=l.response_ms,
            called_at=l.called_at,
        )
        for l in logs
    ]
