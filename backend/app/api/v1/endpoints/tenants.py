"""
app/api/v1/endpoints/tenants.py — Sprint 45
B2B advisor tenant registration and custom GAS weight management.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from typing import Any, Optional
import uuid

from app.db.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=128)
    logo_url: Optional[str] = None
    accent_colour: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class GasWeightsUpdate(BaseModel):
    weight_technical: float = Field(..., ge=0.0, le=1.0)
    weight_macro:     float = Field(..., ge=0.0, le=1.0)
    weight_sentiment: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "GasWeightsUpdate":
        total = round(self.weight_technical + self.weight_macro + self.weight_sentiment, 6)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0 (got {total:.4f})")
        return self


class TenantResponse(BaseModel):
    id: str
    slug: str
    name: str
    logo_url: Optional[str]
    accent_colour: Optional[str]
    weight_technical: float
    weight_macro: float
    weight_sentiment: float
    is_active: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TenantResponse, summary="Register a new advisor tenant")
async def register_tenant(
    payload: TenantCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Tenant).where(Tenant.slug == payload.slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Slug '{payload.slug}' already taken.")

        tenant = Tenant(
            id=uuid.uuid4(),
            slug=payload.slug,
            name=payload.name,
            logo_url=payload.logo_url,
            accent_colour=payload.accent_colour,
            owner_user_id=current_user.id,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    return TenantResponse(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        logo_url=tenant.logo_url, accent_colour=tenant.accent_colour,
        weight_technical=tenant.weight_technical, weight_macro=tenant.weight_macro,
        weight_sentiment=tenant.weight_sentiment, is_active=tenant.is_active,
    )


@router.patch("/{slug}/gas-weights", response_model=TenantResponse, summary="Update custom GAS weights")
async def update_gas_weights(
    slug: str,
    payload: GasWeightsUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        if str(tenant.owner_user_id) != str(current_user.id) and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorised.")

        tenant.weight_technical = payload.weight_technical
        tenant.weight_macro     = payload.weight_macro
        tenant.weight_sentiment = payload.weight_sentiment
        await session.commit()
        await session.refresh(tenant)

    return TenantResponse(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        logo_url=tenant.logo_url, accent_colour=tenant.accent_colour,
        weight_technical=tenant.weight_technical, weight_macro=tenant.weight_macro,
        weight_sentiment=tenant.weight_sentiment, is_active=tenant.is_active,
    )


@router.get("/{slug}", response_model=TenantResponse, summary="Get tenant details")
async def get_tenant(slug: str) -> Any:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True))  # noqa: E712
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")

    return TenantResponse(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        logo_url=tenant.logo_url, accent_colour=tenant.accent_colour,
        weight_technical=tenant.weight_technical, weight_macro=tenant.weight_macro,
        weight_sentiment=tenant.weight_sentiment, is_active=tenant.is_active,
    )
