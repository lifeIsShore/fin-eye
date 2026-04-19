"""
app/api/v1/endpoints/tenants.py — Sprint 45 (seat management: Sprint 55)
B2B advisor tenant registration, custom GAS weight management, and per-seat management.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.tenant import Tenant, TIER_SEAT_LIMITS
from app.models.tenant_seat import TenantSeat
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
    tier: str
    seat_count: int
    billing_cycle_end: Optional[str]
    is_active: bool


class SeatInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern=r"^(admin|member)$")


class SeatResponse(BaseModel):
    id: str
    tenant_id: str
    invited_email: str
    role: str
    accepted: bool
    invited_at: str
    accepted_at: Optional[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tenant_response(tenant: Tenant) -> TenantResponse:
    return TenantResponse(
        id=str(tenant.id),
        slug=tenant.slug,
        name=tenant.name,
        logo_url=tenant.logo_url,
        accent_colour=tenant.accent_colour,
        weight_technical=tenant.weight_technical,
        weight_macro=tenant.weight_macro,
        weight_sentiment=tenant.weight_sentiment,
        tier=tenant.tier,
        seat_count=tenant.seat_count,
        billing_cycle_end=tenant.billing_cycle_end.isoformat() if tenant.billing_cycle_end else None,
        is_active=tenant.is_active,
    )


def _seat_response(seat: TenantSeat) -> SeatResponse:
    return SeatResponse(
        id=str(seat.id),
        tenant_id=str(seat.tenant_id),
        invited_email=seat.invited_email,
        role=seat.role,
        accepted=seat.accepted_at is not None,
        invited_at=seat.invited_at.isoformat(),
        accepted_at=seat.accepted_at.isoformat() if seat.accepted_at else None,
    )


async def _get_tenant_or_404(session, slug: str) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return tenant


def _require_owner_or_admin(tenant: Tenant, current_user: User) -> None:
    if current_user.is_admin:
        return
    if str(tenant.owner_user_id) == str(current_user.id):
        return
    raise HTTPException(status_code=403, detail="Not authorised.")


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

    return _tenant_response(tenant)


@router.patch("/{slug}/gas-weights", response_model=TenantResponse, summary="Update custom GAS weights")
async def update_gas_weights(
    slug: str,
    payload: GasWeightsUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        tenant = await _get_tenant_or_404(session, slug)
        _require_owner_or_admin(tenant, current_user)

        tenant.weight_technical = payload.weight_technical
        tenant.weight_macro     = payload.weight_macro
        tenant.weight_sentiment = payload.weight_sentiment
        await session.commit()
        await session.refresh(tenant)

    return _tenant_response(tenant)


@router.get("/{slug}", response_model=TenantResponse, summary="Get tenant details")
async def get_tenant(slug: str) -> Any:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)  # noqa: E712
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")

    return _tenant_response(tenant)


# ── Sprint 55: Seat Management ─────────────────────────────────────────────────

@router.post(
    "/{slug}/seats/invite",
    response_model=SeatResponse,
    summary="Invite a user to this tenant by email",
)
async def invite_seat(
    slug: str,
    payload: SeatInviteRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Creates a seat invitation. Returns the seat with an invite_token.
    In production, wire this token into an email via Resend:
      https://fin-eye.app/accept-invite?token={invite_token}
    """
    async with AsyncSessionLocal() as session:
        tenant = await _get_tenant_or_404(session, slug)
        _require_owner_or_admin(tenant, current_user)

        # Enforce seat limit
        seat_limit = TIER_SEAT_LIMITS.get(tenant.tier, 10)
        count_res = await session.execute(
            select(TenantSeat).where(TenantSeat.tenant_id == tenant.id)
        )
        current_seat_count = len(count_res.scalars().all())
        if current_seat_count >= seat_limit:
            raise HTTPException(
                status_code=402,
                detail=f"Seat limit reached for '{tenant.tier}' tier ({seat_limit} seats). Upgrade to add more.",
            )

        # Check for duplicate invite
        dupe = await session.execute(
            select(TenantSeat).where(
                TenantSeat.tenant_id == tenant.id,
                TenantSeat.invited_email == payload.email,
            )
        )
        if dupe.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="This email has already been invited.")

        token = secrets.token_urlsafe(32)
        seat = TenantSeat(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            invited_email=payload.email,
            role=payload.role,
            invite_token=token,
        )
        session.add(seat)
        await session.commit()
        await session.refresh(seat)

    return _seat_response(seat)


@router.get(
    "/{slug}/seats",
    response_model=list[SeatResponse],
    summary="List all seats (pending and accepted) for a tenant",
)
async def list_seats(
    slug: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        tenant = await _get_tenant_or_404(session, slug)
        _require_owner_or_admin(tenant, current_user)

        result = await session.execute(
            select(TenantSeat)
            .where(TenantSeat.tenant_id == tenant.id)
            .order_by(TenantSeat.invited_at.desc())
        )
        seats = result.scalars().all()

    return [_seat_response(s) for s in seats]


@router.delete(
    "/{slug}/seats/{seat_id}",
    status_code=204,
    summary="Remove a seat from a tenant",
)
async def remove_seat(
    slug: str,
    seat_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    async with AsyncSessionLocal() as session:
        tenant = await _get_tenant_or_404(session, slug)
        _require_owner_or_admin(tenant, current_user)

        result = await session.execute(
            select(TenantSeat).where(
                TenantSeat.id == seat_id,
                TenantSeat.tenant_id == tenant.id,
            )
        )
        seat = result.scalar_one_or_none()
        if not seat:
            raise HTTPException(404, "Seat not found.")

        await session.delete(seat)
        await session.commit()


@router.post(
    "/accept-invite",
    response_model=SeatResponse,
    summary="Accept a seat invitation via token",
)
async def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TenantSeat).where(TenantSeat.invite_token == token)
        )
        seat = result.scalar_one_or_none()
        if not seat:
            raise HTTPException(404, "Invalid or expired invite token.")
        if seat.accepted_at:
            raise HTTPException(409, "Invite already accepted.")

        seat.user_id = current_user.id
        seat.accepted_at = datetime.now(timezone.utc)
        seat.invite_token = None  # consume token
        await session.commit()
        await session.refresh(seat)

    return _seat_response(seat)


@router.get(
    "/{slug}/billing",
    summary="Get billing info for a tenant",
)
async def get_billing_info(
    slug: str,
    current_user: User = Depends(get_current_user),
) -> Any:
    async with AsyncSessionLocal() as session:
        tenant = await _get_tenant_or_404(session, slug)
        _require_owner_or_admin(tenant, current_user)

        seat_limit = TIER_SEAT_LIMITS.get(tenant.tier, 10)
        count_res = await session.execute(
            select(TenantSeat).where(TenantSeat.tenant_id == tenant.id)
        )
        seats_used = len(count_res.scalars().all())

    return {
        "tier": tenant.tier,
        "seat_limit": seat_limit,
        "seats_used": seats_used,
        "seats_available": max(0, seat_limit - seats_used),
        "stripe_customer_id": tenant.stripe_customer_id,
        "stripe_subscription_id": tenant.stripe_subscription_id,
        "billing_cycle_end": tenant.billing_cycle_end.isoformat() if tenant.billing_cycle_end else None,
        # Stripe billing portal URL (only available after Stripe customer is created)
        "stripe_portal_url": (
            f"https://billing.stripe.com/p/login/{tenant.stripe_customer_id}"
            if tenant.stripe_customer_id else None
        ),
    }
