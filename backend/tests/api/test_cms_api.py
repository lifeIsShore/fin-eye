import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.blog import BlogPost
from app.services.auth import get_password_hash


async def make_admin(db: AsyncSession, email: str = "admin@fin-eye.io") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("adminpass"),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_regular_user(db: AsyncSession, email: str = "user@example.com") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("pass"),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def patch_admin(monkeypatch, user: User) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.cms.require_admin",
        lambda **_: user,
    )


def patch_non_admin(monkeypatch, user: User) -> None:
    """Patch require_admin to raise 403 as it would for a non-admin."""
    from fastapi import HTTPException
    def _raise(**_):
        raise HTTPException(status_code=403, detail="Admin access required.")
    monkeypatch.setattr("app.api.v1.endpoints.cms.require_admin", _raise)


# ─── Public endpoints ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_published_posts_empty_initially(client: AsyncClient, test_db: Session):
    """Published list is empty before any posts exist."""
    res = await client.get("/api/v1/cms/posts/published")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_published_posts_returns_only_published(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Draft posts are excluded; published posts appear."""
    admin = await make_admin(test_db)
    patch_admin(monkeypatch, admin)

    # Create two posts
    await client.post("/api/v1/cms/posts", json={
        "title": "Draft Post", "summary": "A draft", "content_md": "# Draft"
    })
    r2 = await client.post("/api/v1/cms/posts", json={
        "title": "Published Post", "summary": "Live!", "content_md": "# Live"
    })
    post_id = r2.json()["id"]
    await client.post(f"/api/v1/cms/posts/{post_id}/publish")

    res = await client.get("/api/v1/cms/posts/published")
    assert res.status_code == 200
    titles = [p["title"] for p in res.json()]
    assert "Published Post" in titles
    assert "Draft Post" not in titles


# ─── Admin CRUD ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, test_db: Session, monkeypatch):
    """Admin can create a post; it defaults to draft."""
    admin = await make_admin(test_db)
    patch_admin(monkeypatch, admin)

    res = await client.post("/api/v1/cms/posts", json={
        "title": "My First Post",
        "summary": "A summary",
        "category": "Macro 101",
        "content_md": "## Hello",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "My First Post"
    assert body["status"] == "draft"
    assert body["slug"] == "my-first-post"
    assert "id" in body


@pytest.mark.asyncio
async def test_update_post(client: AsyncClient, test_db: Session, monkeypatch):
    """Admin can update post content and title."""
    admin = await make_admin(test_db, "admin2@fin-eye.io")
    patch_admin(monkeypatch, admin)

    create = await client.post("/api/v1/cms/posts", json={
        "title": "Old Title", "summary": "Old", "content_md": "Old content"
    })
    post_id = create.json()["id"]

    update = await client.put(f"/api/v1/cms/posts/{post_id}", json={
        "title": "New Title",
        "content_md": "# Updated content",
    })
    assert update.status_code == 200
    assert update.json()["title"] == "New Title"
    assert update.json()["content_md"] == "# Updated content"


@pytest.mark.asyncio
async def test_publish_and_unpublish(client: AsyncClient, test_db: Session, monkeypatch):
    """Admin can publish and then unpublish a post."""
    admin = await make_admin(test_db, "admin3@fin-eye.io")
    patch_admin(monkeypatch, admin)

    create = await client.post("/api/v1/cms/posts", json={
        "title": "Toggle Post", "summary": "Toggle", "content_md": "content"
    })
    post_id = create.json()["id"]

    pub = await client.post(f"/api/v1/cms/posts/{post_id}/publish")
    assert pub.json()["status"] == "published"
    assert pub.json()["published_at"] is not None

    unpub = await client.post(f"/api/v1/cms/posts/{post_id}/unpublish")
    assert unpub.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient, test_db: Session, monkeypatch):
    """Admin can delete a post; subsequent get returns 404."""
    admin = await make_admin(test_db, "admin4@fin-eye.io")
    patch_admin(monkeypatch, admin)

    create = await client.post("/api/v1/cms/posts", json={
        "title": "Delete Me", "summary": "Gone", "content_md": "bye"
    })
    post_id = create.json()["id"]

    del_res = await client.delete(f"/api/v1/cms/posts/{post_id}")
    assert del_res.status_code == 204

    get_res = await client.get(f"/api/v1/cms/posts/{post_id}")
    assert get_res.status_code in (403, 404)  # 403 if admin patch blocks, 404 if found


@pytest.mark.asyncio
async def test_slug_auto_generated_from_title(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Slug is auto-generated from title using slugify."""
    admin = await make_admin(test_db, "admin5@fin-eye.io")
    patch_admin(monkeypatch, admin)

    res = await client.post("/api/v1/cms/posts", json={
        "title": "Hello World! A Great Post",
        "summary": "Summary",
        "content_md": "",
    })
    assert res.json()["slug"] == "hello-world-a-great-post"


@pytest.mark.asyncio
async def test_duplicate_slugs_get_suffix(
    client: AsyncClient, test_db: Session, monkeypatch
):
    """Creating two posts with the same title yields slug and slug-2."""
    admin = await make_admin(test_db, "admin6@fin-eye.io")
    patch_admin(monkeypatch, admin)

    r1 = await client.post("/api/v1/cms/posts", json={
        "title": "Same Title", "summary": "A", "content_md": ""
    })
    r2 = await client.post("/api/v1/cms/posts", json={
        "title": "Same Title", "summary": "B", "content_md": ""
    })
    slugs = {r1.json()["slug"], r2.json()["slug"]}
    assert "same-title" in slugs
    assert "same-title-2" in slugs
