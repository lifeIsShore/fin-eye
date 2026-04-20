"""
tests/api/test_comments_api.py
Sprint 57 — Discussion threads API tests
"""
import uuid
import pytest
from httpx import AsyncClient


# ── Shared mock users ─────────────────────────────────────────────────────────

class _FakeUser:
    id = uuid.uuid4()
    email = "commenter@fin-eye.app"
    username = "commenter"
    is_verified = True
    is_admin = False


class _FakeAdmin:
    id = uuid.uuid4()
    email = "admin@fin-eye.app"
    username = "adminuser"
    is_verified = True
    is_admin = True


FAKE_USER = _FakeUser()
FAKE_ADMIN = _FakeAdmin()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_auth(test_app):
    from app.api.v1.deps import get_current_user, get_optional_user
    test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    test_app.dependency_overrides[get_optional_user] = lambda: FAKE_USER
    yield
    test_app.dependency_overrides.pop(get_current_user, None)
    test_app.dependency_overrides.pop(get_optional_user, None)


# ── GET /comments/{symbol} ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_comments_empty(client: AsyncClient):
    response = await client.get("/api/v1/comments/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["comments"] == []
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_comments_unknown_symbol_still_ok(client: AsyncClient):
    """Symbol lookup should not 404 — just return empty list."""
    response = await client.get("/api/v1/comments/FAKEXYZ")
    assert response.status_code == 200


# ── POST /comments/{symbol} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_comment_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/comments/AAPL",
        json={"body": "This is a valid test comment about AAPL."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["upvotes"] == 0
    assert data["downvotes"] == 0
    assert "***" in data["username"]  # anonymised


@pytest.mark.asyncio
async def test_post_comment_too_short(client: AsyncClient):
    response = await client.post("/api/v1/comments/AAPL", json={"body": "short"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_comment_too_long(client: AsyncClient):
    response = await client.post("/api/v1/comments/AAPL", json={"body": "x" * 501})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_comment_banned_word(client: AsyncClient):
    response = await client.post(
        "/api/v1/comments/AAPL",
        json={"body": "This is a pump and dump scheme, watch out!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_comment_symbol_uppercased(client: AsyncClient):
    """Symbol in the path should be normalised to uppercase."""
    response = await client.post(
        "/api/v1/comments/aapl",
        json={"body": "Lowercase symbol should be normalised to AAPL."},
    )
    assert response.status_code == 201
    assert response.json()["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_posted_comment_appears_in_list(client: AsyncClient):
    body_text = "This comment should appear in the list for TSLA."
    await client.post("/api/v1/comments/TSLA", json={"body": body_text})

    response = await client.get("/api/v1/comments/TSLA")
    assert response.status_code == 200
    bodies = [c["body"] for c in response.json()["comments"]]
    assert body_text in bodies


# ── DELETE /comments/{comment_id} ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_own_comment(client: AsyncClient):
    post_r = await client.post(
        "/api/v1/comments/NVDA",
        json={"body": "Comment that will be deleted by its author."},
    )
    assert post_r.status_code == 201
    comment_id = post_r.json()["id"]

    del_r = await client.delete(f"/api/v1/comments/{comment_id}")
    assert del_r.status_code == 204

    # Should no longer appear in the list
    list_r = await client.get("/api/v1/comments/NVDA")
    bodies = [c["body"] for c in list_r.json()["comments"]]
    assert "Comment that will be deleted by its author." not in bodies


@pytest.mark.asyncio
async def test_delete_other_users_comment_forbidden(client: AsyncClient, test_app):
    """A second user must not be able to delete another user's comment."""
    # Post as FAKE_USER
    post_r = await client.post(
        "/api/v1/comments/MSFT",
        json={"body": "Comment posted by original user, should not be deletable by other."},
    )
    comment_id = post_r.json()["id"]

    # Switch to a different non-admin user
    class _OtherUser:
        id = uuid.uuid4()
        email = "other@fin-eye.app"
        username = "otheruser"
        is_verified = True
        is_admin = False

    from app.api.v1.deps import get_current_user
    test_app.dependency_overrides[get_current_user] = lambda: _OtherUser()

    del_r = await client.delete(f"/api/v1/comments/{comment_id}")
    assert del_r.status_code == 403

    # Restore
    test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER


@pytest.mark.asyncio
async def test_delete_nonexistent_comment(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.delete(f"/api/v1/comments/{fake_id}")
    assert response.status_code == 404


# ── POST /comments/{comment_id}/react ────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_upvote(client: AsyncClient):
    post_r = await client.post(
        "/api/v1/comments/GOOG",
        json={"body": "Solid earnings report, bullish on Google long term."},
    )
    comment_id = post_r.json()["id"]

    react_r = await client.post(
        f"/api/v1/comments/{comment_id}/react", json={"reaction": "up"}
    )
    assert react_r.status_code == 200
    assert react_r.json()["upvotes"] == 1
    assert react_r.json()["downvotes"] == 0


@pytest.mark.asyncio
async def test_react_toggle_removes_vote(client: AsyncClient):
    """Reacting with the same reaction twice should toggle it off."""
    post_r = await client.post(
        "/api/v1/comments/META",
        json={"body": "Testing toggle reaction behaviour for this comment."},
    )
    comment_id = post_r.json()["id"]

    await client.post(f"/api/v1/comments/{comment_id}/react", json={"reaction": "up"})
    r2 = await client.post(f"/api/v1/comments/{comment_id}/react", json={"reaction": "up"})
    assert r2.json()["upvotes"] == 0


@pytest.mark.asyncio
async def test_react_invalid_reaction_type(client: AsyncClient):
    post_r = await client.post(
        "/api/v1/comments/AMD",
        json={"body": "Comment for invalid reaction type test case here."},
    )
    comment_id = post_r.json()["id"]

    react_r = await client.post(
        f"/api/v1/comments/{comment_id}/react", json={"reaction": "love"}
    )
    assert react_r.status_code == 422
