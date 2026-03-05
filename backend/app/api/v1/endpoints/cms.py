"""
CMS endpoints for managing blog posts.

Access model:
- GET  /api/v1/cms/posts/published  → public (no auth required), returns published posts only
- GET  /api/v1/cms/posts/{id}       → public (published posts); admin sees drafts too
- GET  /api/v1/cms/posts            → admin only, all posts (draft + published)
- POST /api/v1/cms/posts            → admin only, create
- PUT  /api/v1/cms/posts/{id}       → admin only, update
- POST /api/v1/cms/posts/{id}/publish   → admin only, publish
- POST /api/v1/cms/posts/{id}/unpublish → admin only, unpublish
- DELETE /api/v1/cms/posts/{id}     → admin only, hard delete
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import re

from app.db.database import get_db
from app.models.blog import BlogPost
from app.models.user import User
from app.services.auth import get_current_user, require_admin

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:200]


def _ensure_unique_slug(slug: str, db: Session, exclude_id: int | None = None) -> str:
    """Append -2, -3, … to slug until unique."""
    candidate = slug
    counter = 2
    while True:
        q = db.query(BlogPost).filter(BlogPost.slug == candidate)
        if exclude_id:
            q = q.filter(BlogPost.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


# ─── Schemas ────────────────────────────────────────────────────────────────

class BlogPostCreate(BaseModel):
    title: str
    summary: str
    category: str = "General"
    read_time: str = "5 min read"
    author: str = "Fin-Eye Team"
    content_md: str = ""
    slug: Optional[str] = None  # Auto-generated from title if not provided


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    read_time: Optional[str] = None
    author: Optional[str] = None
    content_md: Optional[str] = None
    slug: Optional[str] = None


class BlogPostResponse(BaseModel):
    id: int
    title: str
    slug: str
    summary: str
    category: str
    read_time: str
    author: str
    content_md: str
    status: str
    published_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, post: BlogPost) -> "BlogPostResponse":
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            summary=post.summary,
            category=post.category,
            read_time=post.read_time,
            author=post.author,
            content_md=post.content_md,
            status=post.status,
            published_at=post.published_at.isoformat() if post.published_at else None,
            created_at=post.created_at.isoformat(),
            updated_at=post.updated_at.isoformat(),
        )


class BlogPostSummary(BaseModel):
    """Lightweight version for list views — omits content_md."""
    id: int
    title: str
    slug: str
    summary: str
    category: str
    read_time: str
    author: str
    status: str
    published_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, post: BlogPost) -> "BlogPostSummary":
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            summary=post.summary,
            category=post.category,
            read_time=post.read_time,
            author=post.author,
            status=post.status,
            published_at=post.published_at.isoformat() if post.published_at else None,
            created_at=post.created_at.isoformat(),
            updated_at=post.updated_at.isoformat(),
        )


# ─── Public endpoints ────────────────────────────────────────────────────────

@router.get("/posts/published", response_model=list[BlogPostSummary])
def list_published_posts(db: Session = Depends(get_db)) -> list[BlogPostSummary]:
    """Public endpoint — returns all published posts, newest first."""
    posts = (
        db.query(BlogPost)
        .filter(BlogPost.status == "published")
        .order_by(BlogPost.published_at.desc())
        .all()
    )
    return [BlogPostSummary.from_orm(p) for p in posts]


@router.get("/posts/by-slug/{slug}", response_model=BlogPostResponse)
def get_post_by_slug(slug: str, db: Session = Depends(get_db)) -> BlogPostResponse:
    """Public — returns a single published post by slug. 404 if not published."""
    post = db.query(BlogPost).filter(
        BlogPost.slug == slug,
        BlogPost.status == "published",
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return BlogPostResponse.from_orm(post)


# ─── Admin endpoints ─────────────────────────────────────────────────────────

@router.get("/posts", response_model=list[BlogPostSummary])
def list_all_posts(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[BlogPostSummary]:
    """Admin — returns ALL posts (draft + published), newest first."""
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return [BlogPostSummary.from_orm(p) for p in posts]


@router.get("/posts/{post_id}", response_model=BlogPostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BlogPostResponse:
    """Admin — get any post by ID including drafts."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return BlogPostResponse.from_orm(post)


@router.post("/posts", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    body: BlogPostCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BlogPostResponse:
    """Admin — create a new draft post."""
    base_slug = _slugify(body.slug or body.title)
    unique_slug = _ensure_unique_slug(base_slug, db)

    post = BlogPost(
        title=body.title,
        slug=unique_slug,
        summary=body.summary,
        category=body.category,
        read_time=body.read_time,
        author=body.author,
        content_md=body.content_md,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return BlogPostResponse.from_orm(post)


@router.put("/posts/{post_id}", response_model=BlogPostResponse)
def update_post(
    post_id: int,
    body: BlogPostUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BlogPostResponse:
    """Admin — update any field on a post. Slug is re-slugified if provided."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if body.title is not None:
        post.title = body.title
    if body.summary is not None:
        post.summary = body.summary
    if body.category is not None:
        post.category = body.category
    if body.read_time is not None:
        post.read_time = body.read_time
    if body.author is not None:
        post.author = body.author
    if body.content_md is not None:
        post.content_md = body.content_md
    if body.slug is not None:
        base_slug = _slugify(body.slug)
        post.slug = _ensure_unique_slug(base_slug, db, exclude_id=post_id)

    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return BlogPostResponse.from_orm(post)


@router.post("/posts/{post_id}/publish", response_model=BlogPostResponse)
def publish_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BlogPostResponse:
    """Admin — publish a draft post."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    post.status = "published"
    post.published_at = post.published_at or datetime.utcnow()
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return BlogPostResponse.from_orm(post)


@router.post("/posts/{post_id}/unpublish", response_model=BlogPostResponse)
def unpublish_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BlogPostResponse:
    """Admin — revert a published post back to draft."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    post.status = "draft"
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return BlogPostResponse.from_orm(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Admin — permanently delete a post."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    db.delete(post)
    db.commit()
