import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth import get_password_hash


async def create_test_user(db: AsyncSession) -> User:
    """Create and persist a real user for watchlist FK constraints."""
    user = User(
        email="watchlist_test@example.com",
        hashed_password=get_password_hash("testpass"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_watchlist_add_and_list(client: AsyncClient, test_db: Session, monkeypatch):
    """Can add a ticker and then see it in the list."""
    test_user = await create_test_user(test_db)

    # Override get_current_user to return our real seeded user
    monkeypatch.setattr(
        "app.api.v1.endpoints.watchlist.get_current_user",
        lambda **kwargs: test_user,
    )

    add_res = await client.post("/api/v1/watchlist/", json={"symbol": "AAPL"})
    assert add_res.status_code == 201
    data = add_res.json()
    assert data["symbol"] == "AAPL"
    assert "id" in data
    assert "added_at" in data

    list_res = await client.get("/api/v1/watchlist/")
    assert list_res.status_code == 200
    symbols = [i["symbol"] for i in list_res.json()]
    assert "AAPL" in symbols


@pytest.mark.asyncio
async def test_watchlist_add_duplicate_is_idempotent(client: AsyncClient, test_db: Session, monkeypatch):
    """Adding the same symbol twice returns the existing row, not an error."""
    test_user = await create_test_user(test_db)
    monkeypatch.setattr(
        "app.api.v1.endpoints.watchlist.get_current_user",
        lambda **kwargs: test_user,
    )

    await client.post("/api/v1/watchlist/", json={"symbol": "TSLA"})
    res = await client.post("/api/v1/watchlist/", json={"symbol": "TSLA"})
    assert res.status_code == 201
    assert res.json()["symbol"] == "TSLA"

    list_res = await client.get("/api/v1/watchlist/")
    symbols = [i["symbol"] for i in list_res.json()]
    assert symbols.count("TSLA") == 1


@pytest.mark.asyncio
async def test_watchlist_remove(client: AsyncClient, test_db: Session, monkeypatch):
    """Can remove a ticker from the watchlist."""
    test_user = await create_test_user(test_db)
    monkeypatch.setattr(
        "app.api.v1.endpoints.watchlist.get_current_user",
        lambda **kwargs: test_user,
    )

    await client.post("/api/v1/watchlist/", json={"symbol": "NVDA"})
    del_res = await client.delete("/api/v1/watchlist/NVDA")
    assert del_res.status_code == 204

    list_res = await client.get("/api/v1/watchlist/")
    symbols = [i["symbol"] for i in list_res.json()]
    assert "NVDA" not in symbols


@pytest.mark.asyncio
async def test_watchlist_remove_nonexistent(client: AsyncClient, test_db: Session, monkeypatch):
    """Removing a symbol not in the watchlist returns 404."""
    test_user = await create_test_user(test_db)
    monkeypatch.setattr(
        "app.api.v1.endpoints.watchlist.get_current_user",
        lambda **kwargs: test_user,
    )

    res = await client.delete("/api/v1/watchlist/FAKESYMBOL")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_symbol_normalised_to_uppercase(client: AsyncClient, test_db: Session, monkeypatch):
    """Symbols are stored and returned in uppercase regardless of input case."""
    test_user = await create_test_user(test_db)
    monkeypatch.setattr(
        "app.api.v1.endpoints.watchlist.get_current_user",
        lambda **kwargs: test_user,
    )

    res = await client.post("/api/v1/watchlist/", json={"symbol": "msft"})
    assert res.status_code == 201
    assert res.json()["symbol"] == "MSFT"
