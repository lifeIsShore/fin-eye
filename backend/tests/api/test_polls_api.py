"""
tests/api/test_polls_api.py
Sprint 57 — Weekly Bull vs Bear Poll API tests
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


# ── Shared mock user ──────────────────────────────────────────────────────────

class _FakeUser:
    id = uuid.uuid4()
    email = "voter@fin-eye.app"
    username = "voter"
    is_verified = True
    is_admin = False


FAKE_USER = _FakeUser()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_auth(test_app):
    from app.api.v1.deps import get_current_user, get_optional_user
    test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    test_app.dependency_overrides[get_optional_user] = lambda: FAKE_USER
    yield
    test_app.dependency_overrides.pop(get_current_user, None)
    test_app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
async def active_poll(test_db):
    """Insert a currently-active SPY poll into the test DB."""
    from app.models.weekly_poll import WeeklyPoll
    now = datetime.now(timezone.utc)
    poll = WeeklyPoll(
        week_number=now.isocalendar().week,
        year=now.isocalendar().year,
        symbol="SPY",
        question="Are you Bullish, Bearish, or Neutral on SPY this week?",
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(days=6),
    )
    test_db.add(poll)
    await test_db.commit()
    await test_db.refresh(poll)
    return poll


# ── GET /polls/current ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_poll_no_poll(client: AsyncClient):
    """Returns 404 when no active poll exists."""
    response = await client.get("/api/v1/polls/current")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_current_poll_returns_structure(client: AsyncClient, active_poll):
    response = await client.get("/api/v1/polls/current")
    assert response.status_code == 200
    data = response.json()
    assert data["poll_id"] == str(active_poll.id)
    assert "question" in data
    assert data["results"]["total"] == 0
    assert data["user_vote"] is None


# ── POST /polls/{poll_id}/vote ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cast_vote_bullish(client: AsyncClient, active_poll):
    response = await client.post(
        f"/api/v1/polls/{active_poll.id}/vote",
        json={"vote": "bullish"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"]["bullish"] == 1
    assert data["results"]["total"] == 1
    assert data["user_vote"] == "bullish"


@pytest.mark.asyncio
async def test_cast_vote_changes_existing(client: AsyncClient, active_poll):
    """Voting twice should update the existing vote, not add a duplicate."""
    await client.post(f"/api/v1/polls/{active_poll.id}/vote", json={"vote": "bullish"})
    r2 = await client.post(f"/api/v1/polls/{active_poll.id}/vote", json={"vote": "bearish"})
    assert r2.status_code == 200
    data = r2.json()
    # Must be 1 total, not 2
    assert data["results"]["total"] == 1
    assert data["results"]["bearish"] == 1
    assert data["results"]["bullish"] == 0
    assert data["user_vote"] == "bearish"


@pytest.mark.asyncio
async def test_vote_invalid_option(client: AsyncClient, active_poll):
    response = await client.post(
        f"/api/v1/polls/{active_poll.id}/vote",
        json={"vote": "very_bullish"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_vote_nonexistent_poll(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.post(f"/api/v1/polls/{fake_id}/vote", json={"vote": "neutral"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_vote_closed_poll(client: AsyncClient, test_db):
    """Voting on a closed poll should return 400."""
    from app.models.weekly_poll import WeeklyPoll
    now = datetime.now(timezone.utc)
    closed_poll = WeeklyPoll(
        week_number=1,
        year=2000,
        symbol="SPY",
        question="Old poll",
        opens_at=now - timedelta(days=14),
        closes_at=now - timedelta(days=7),
    )
    test_db.add(closed_poll)
    await test_db.commit()
    await test_db.refresh(closed_poll)

    response = await client.post(
        f"/api/v1/polls/{closed_poll.id}/vote",
        json={"vote": "neutral"},
    )
    assert response.status_code == 400
    assert "closed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_vote_shown_in_current_poll(client: AsyncClient, active_poll):
    """After voting, GET /current should reflect the user's vote."""
    await client.post(f"/api/v1/polls/{active_poll.id}/vote", json={"vote": "neutral"})

    response = await client.get("/api/v1/polls/current")
    assert response.status_code == 200
    assert response.json()["user_vote"] == "neutral"
