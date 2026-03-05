import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.legal import CURRENT_LEGAL_VERSION
from app.services.auth import get_password_hash


def make_user(db: Session, email: str = "legal_test@example.com") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        is_pro=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def patch_auth(monkeypatch, user: User) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.legal.get_current_user",
        lambda **_: user,
    )


@pytest.mark.asyncio
async def test_consent_status_not_yet_accepted(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Status returns has_accepted=False before the user records consent."""
    user = make_user(test_db)
    patch_auth(monkeypatch, user)

    res = await client.get("/api/v1/legal/consent/status")
    assert res.status_code == 200
    body = res.json()
    assert body["has_accepted"] is False
    assert body["current_version"] == CURRENT_LEGAL_VERSION
    assert body["accepted_version"] is None
    assert body["accepted_at"] is None


@pytest.mark.asyncio
async def test_record_consent_creates_record(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """POST /consent creates a record and returns it."""
    user = make_user(test_db, "legal2@example.com")
    patch_auth(monkeypatch, user)

    res = await client.post("/api/v1/legal/consent")
    assert res.status_code == 201
    body = res.json()
    assert body["doc_version"] == CURRENT_LEGAL_VERSION
    assert "accepted_at" in body
    assert "id" in body


@pytest.mark.asyncio
async def test_consent_status_accepted_after_record(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Status flips to has_accepted=True after POST /consent."""
    user = make_user(test_db, "legal3@example.com")
    patch_auth(monkeypatch, user)

    await client.post("/api/v1/legal/consent")

    res = await client.get("/api/v1/legal/consent/status")
    assert res.status_code == 200
    body = res.json()
    assert body["has_accepted"] is True
    assert body["accepted_version"] == CURRENT_LEGAL_VERSION
    assert body["accepted_at"] is not None


@pytest.mark.asyncio
async def test_record_consent_is_idempotent(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Calling POST /consent twice returns the same record, not an error."""
    user = make_user(test_db, "legal4@example.com")
    patch_auth(monkeypatch, user)

    r1 = await client.post("/api/v1/legal/consent")
    r2 = await client.post("/api/v1/legal/consent")

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["accepted_at"] == r2.json()["accepted_at"]
