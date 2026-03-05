import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.models.portfolio import Portfolio
from app.services.auth import get_password_hash


def make_user(db: Session, email: str = "gdpr_test@example.com") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        is_pro=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_personal_data(db: Session, user: User) -> None:
    """Add watchlist + portfolio rows so export has real content."""
    db.add(WatchlistItem(user_id=user.id, symbol="AAPL"))
    db.add(WatchlistItem(user_id=user.id, symbol="TSLA"))
    portfolio = Portfolio(
        user_id=user.id,
        name="My Portfolio",
        description="Test",
    )
    db.add(portfolio)
    db.commit()


def patch_auth(monkeypatch, user: User) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.gdpr.get_current_user",
        lambda **_: user,
    )


# ─── Export tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_data_export_returns_json_package(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """GET /gdpr/export returns a JSON package with account + watchlist data."""
    user = make_user(test_db)
    seed_personal_data(test_db, user)
    patch_auth(monkeypatch, user)

    res = await client.get("/api/v1/gdpr/export")
    assert res.status_code == 200

    body = res.json()
    assert body["account"]["email"] == user.email
    assert body["account"]["id"] == user.id
    assert len(body["watchlist"]) == 2
    symbols = [w["symbol"] for w in body["watchlist"]]
    assert "AAPL" in symbols
    assert "TSLA" in symbols
    assert "export_generated_at" in body
    assert "data_controller" in body


@pytest.mark.asyncio
async def test_data_export_has_portfolio_data(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Export includes portfolio names."""
    user = make_user(test_db, "gdpr_port@example.com")
    seed_personal_data(test_db, user)
    patch_auth(monkeypatch, user)

    res = await client.get("/api/v1/gdpr/export")
    body = res.json()
    assert len(body["portfolios"]) == 1
    assert body["portfolios"][0]["name"] == "My Portfolio"


# ─── Delete tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_account_wrong_confirmation(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """DELETE requires exact confirmation phrase — wrong phrase returns 400."""
    user = make_user(test_db, "gdpr_del_bad@example.com")
    patch_auth(monkeypatch, user)

    res = await client.post(
        "/api/v1/gdpr/delete", json={"confirmation": "yes please"}
    )
    assert res.status_code == 400
    assert "DELETE MY ACCOUNT" in res.json()["detail"]


@pytest.mark.asyncio
async def test_delete_account_anonymises_user(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Correct phrase anonymises the user row and removes personal data."""
    user = make_user(test_db, "gdpr_del_ok@example.com")
    seed_personal_data(test_db, user)
    user_id = user.id
    patch_auth(monkeypatch, user)

    res = await client.post(
        "/api/v1/gdpr/delete", json={"confirmation": "DELETE MY ACCOUNT"}
    )
    assert res.status_code == 200
    body = res.json()
    assert "anonymised" in body["message"].lower()
    assert "anonymised_at" in body

    # Verify DB state
    db_user = test_db.query(User).filter(User.id == user_id).first()
    assert db_user is not None  # Row preserved (not hard-deleted)
    assert "@anonymised.invalid" in db_user.email
    assert db_user.hashed_password == "DELETED"

    # Personal data removed
    watchlist_count = (
        test_db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).count()
    )
    assert watchlist_count == 0

    portfolio_count = (
        test_db.query(Portfolio).filter(Portfolio.user_id == user_id).count()
    )
    assert portfolio_count == 0


@pytest.mark.asyncio
async def test_delete_account_preserves_consent_records(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Consent records are retained after anonymisation (legal audit requirement)."""
    from app.models.legal import LegalConsent, CURRENT_LEGAL_VERSION
    from datetime import datetime

    user = make_user(test_db, "gdpr_consent_keep@example.com")
    consent = LegalConsent(
        user_id=user.id,
        doc_version=CURRENT_LEGAL_VERSION,
        accepted_at=datetime.utcnow(),
    )
    test_db.add(consent)
    test_db.commit()

    patch_auth(monkeypatch, user)

    await client.post(
        "/api/v1/gdpr/delete", json={"confirmation": "DELETE MY ACCOUNT"}
    )

    from app.models.legal import LegalConsent as LC
    consent_count = (
        test_db.query(LC).filter(LC.user_id == user.id).count()
    )
    assert consent_count == 1  # Consent row must survive
