from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.db.database import Base


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
    published_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
