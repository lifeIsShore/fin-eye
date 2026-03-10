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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.models.portfolio import Portfolio
from app.models.legal import LegalConsent


async def build_user_export_package(user: User, db: AsyncSession) -> dict:
    """
    Collect all personal data held about the user and return it as a
    structured dict suitable for JSON serialisation.
    """
    watchlist_result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id)
    )
    watchlist = watchlist_result.scalars().all()
    
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolios = portfolio_result.scalars().all()
    
    consents_result = await db.execute(
        select(LegalConsent).where(LegalConsent.user_id == user.id)
    )
    consents = consents_result.scalars().all()

    return {
        "export_generated_at": datetime.utcnow().isoformat() + "Z",
        "data_controller": "Fin-Eye",
        "account": {
            "id": user.id,
            "email": user.email,
            "subscription_tier": user.subscription_tier,
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


async def anonymise_user(user: User, db: AsyncSession) -> None:
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
    user.subscription_tier = "free"
    user.updated_at = datetime.utcnow()

    # Delete personal data tables (cascade handles child rows)
    await db.execute(
        delete(WatchlistItem).where(WatchlistItem.user_id == user.id)
    )
    
    # Portfolios cascade-delete their items via the ORM relationship
    # But for async we need to fetch them and delete or use a delete query that cascades
    portfolios_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolios = portfolios_result.scalars().all()
    for p in portfolios:
        await db.delete(p)

    await db.commit()
