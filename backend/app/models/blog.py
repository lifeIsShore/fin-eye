from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime, timezone
from app.db.database import Base


def _utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)

    # Metadata
    title = Column(String(300), nullable=False)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    summary = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False, default="General")
    read_time = Column(String(30), nullable=False, default="5 min read")
    author = Column(String(150), nullable=False, default="Fin-Eye Team")

    # Content (raw markdown)
    content_md = Column(Text, nullable=False, default="")

    # Publishing state: "draft" | "published"
    status = Column(String(20), nullable=False, default="draft")
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Use timezone=True so asyncpg can compare these without offset mismatch
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
