from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.api.v1.deps import get_current_user
from app.services.gdpr_service import build_user_export_package, anonymise_user

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class DeleteAccountRequest(BaseModel):
    confirmation: str  # Must equal "DELETE MY ACCOUNT" to prevent accidents


class DeleteAccountResponse(BaseModel):
    message: str
    anonymised_at: str


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/export")
def request_data_export(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    GDPR Article 20 — Right to data portability.

    Returns a structured JSON document containing all personal data held
    about the current user. The response carries a Content-Disposition
    header so browsers trigger a file download automatically.
    """
    package = build_user_export_package(current_user, db)

    return JSONResponse(
        content=package,
        headers={
            "Content-Disposition": (
                f'attachment; filename="fin-eye-data-export-{current_user.id}.json"'
            )
        },
    )


@router.post("/delete", response_model=DeleteAccountResponse)
def delete_account(
    body: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteAccountResponse:
    """
    GDPR Article 17 — Right to erasure ("right to be forgotten").

    Requires the client to send { "confirmation": "DELETE MY ACCOUNT" }
    as an explicit, hard-to-accidental-trigger safety gate.

    The account is anonymised (not hard-deleted) so that:
    - Legal consent audit records are preserved.
    - Auto-increment IDs in related tables remain consistent.
    - The email slot is freed for re-registration.
    """
    if body.confirmation != "DELETE MY ACCOUNT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                'Confirmation phrase must be exactly "DELETE MY ACCOUNT". '
                "This prevents accidental deletions."
            ),
        )

    # Fetch a fresh DB-bound instance (current_user may be a detached mock in tests)
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    from datetime import datetime
    anonymised_at = datetime.utcnow().isoformat() + "Z"

    anonymise_user(db_user, db)

    return DeleteAccountResponse(
        message=(
            "Your account has been anonymised and all personal data deleted. "
            "Legal consent records are retained as required by law. "
            "You have been logged out."
        ),
        anonymised_at=anonymised_at,
    )
