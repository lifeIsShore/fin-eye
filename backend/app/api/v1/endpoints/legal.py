from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.models.legal import LegalConsent, CURRENT_LEGAL_VERSION
from app.models.user import User
from app.api.v1.deps import get_current_user

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class ConsentStatusResponse(BaseModel):
    has_accepted: bool
    current_version: str
    accepted_version: str | None
    accepted_at: str | None


class ConsentRecordResponse(BaseModel):
    id: int
    doc_version: str
    accepted_at: str


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/consent/status", response_model=ConsentStatusResponse)
async def get_consent_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentStatusResponse:
    """
    Return whether the current user has accepted the current legal version.
    Frontend uses this on every app load to decide whether to show the ConsentGate.
    """
    result = await db.execute(
        select(LegalConsent).where(
            LegalConsent.user_id == current_user.id,
            LegalConsent.doc_version == CURRENT_LEGAL_VERSION,
        )
    )
    consent = result.scalar_one_or_none()

    if consent:
        return ConsentStatusResponse(
            has_accepted=True,
            current_version=CURRENT_LEGAL_VERSION,
            accepted_version=consent.doc_version,
            accepted_at=consent.accepted_at.isoformat(),
        )

    return ConsentStatusResponse(
        has_accepted=False,
        current_version=CURRENT_LEGAL_VERSION,
        accepted_version=None,
        accepted_at=None,
    )


@router.post(
    "/consent",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_consent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentRecordResponse:
    """
    Record that the current user has accepted the current legal version.
    Idempotent — if already accepted, returns the existing record.
    """
    # Return existing record if user already accepted this version
    result = await db.execute(
        select(LegalConsent).where(
            LegalConsent.user_id == current_user.id,
            LegalConsent.doc_version == CURRENT_LEGAL_VERSION,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return ConsentRecordResponse(
            id=existing.id,
            doc_version=existing.doc_version,
            accepted_at=existing.accepted_at.isoformat(),
        )

    consent = LegalConsent(
        user_id=current_user.id,
        doc_version=CURRENT_LEGAL_VERSION,
        accepted_at=datetime.utcnow(),
    )
    db.add(consent)
    try:
        await db.commit()
        await db.refresh(consent)
    except IntegrityError:
        await db.rollback()
        # Race condition — fetch and return existing
        result = await db.execute(
            select(LegalConsent).where(
                LegalConsent.user_id == current_user.id,
                LegalConsent.doc_version == CURRENT_LEGAL_VERSION,
            )
        )
        consent = result.scalar_one_or_none()

    return ConsentRecordResponse(
        id=consent.id,
        doc_version=consent.doc_version,
        accepted_at=consent.accepted_at.isoformat(),
    )
