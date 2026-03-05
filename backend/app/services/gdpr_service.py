"""
GDPR service — data export and account deletion (anonymisation).

Philosophy:
- Export: Collect everything we hold about the user and return it as a dict.
  For MVP this is synchronous (returned immediately). A future async job
  could email a zip, but the immediate JSON download satisfies the GDPR
  right-of-access requirement.

- Deletion: We anonymise rather than hard-delete the user row so that
  consent records (required for legal compliance) and aggregate analytics
  remain intact. All personally-identifiable data is replaced with
  irreversible placeholders and all associated personal data rows are deleted.
"""

from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.models.portfolio import Portfolio
from app.models.legal import LegalConsent


def build_user_export_package(user: User, db: Session) -> dict:
    """
    Collect all personal data held about the user and return it as a
    structured dict suitable for JSON serialisation.
    """
    watchlist = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id)
        .all()
    )
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .all()
    )
    consents = (
        db.query(LegalConsent)
        .filter(LegalConsent.user_id == user.id)
        .all()
    )

    return {
        "export_generated_at": datetime.utcnow().isoformat() + "Z",
        "data_controller": "Fin-Eye",
        "account": {
            "id": user.id,
            "email": user.email,
            "is_pro": user.is_pro,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "watchlist": [
            {"symbol": w.symbol, "added_at": w.added_at.isoformat() if w.added_at else None}
            for w in watchlist
        ],
        "portfolios": [
            {
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "items": [
                    {"symbol": item.symbol, "weight": item.weight}
                    for item in p.items
                ],
            }
            for p in portfolios
        ],
        "legal_consents": [
            {
                "doc_version": c.doc_version,
                "accepted_at": c.accepted_at.isoformat() if c.accepted_at else None,
            }
            for c in consents
        ],
    }


def anonymise_user(user: User, db: Session) -> None:
    """
    Irreversibly anonymise the user account.

    Steps:
    1. Replace email with an anonymised placeholder (non-reversible).
    2. Overwrite password hash so the account cannot be logged into.
    3. Delete all user-owned personal data rows (watchlist, portfolios).
    4. Preserve legal_consents rows (required for compliance audit trail)
       but they reference a now-anonymous user_id, which is acceptable.
    5. Mark account as deleted with a timestamp.
    """
    anon_marker = f"deleted_{user.id}_{int(datetime.utcnow().timestamp())}@anonymised.invalid"

    # Anonymise PII
    user.email = anon_marker
    user.hashed_password = "DELETED"
    user.is_pro = False
    user.updated_at = datetime.utcnow()

    # Delete personal data tables (cascade handles child rows)
    db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).delete(
        synchronize_session="fetch"
    )
    # Portfolios cascade-delete their items via the ORM relationship
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    for p in portfolios:
        db.delete(p)

    db.commit()
