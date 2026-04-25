"""
app/models/showcase.py

ShowcaseProduct  — product cards in the Pro Tools / Showcase section
ShowcaseClick    — lightweight click analytics (views, detail-opens, outbound clicks)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


class ShowcaseProduct(Base):
    __tablename__ = "showcase_products"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    tagline     = Column(String(300), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    # Stored as JSON list of strings, e.g. ["Feature A", "Feature B"]
    features    = Column(JSON, nullable=False, default=list)
    category    = Column(String(100), nullable=False, default="General")
    price_label = Column(String(80), nullable=False, default="Free")
    # Where the "Buy now" / "View" button sends the user
    external_url = Column(String(500), nullable=False)
    preview_url = Column(String(500), nullable=True)
    is_bundle   = Column(Boolean, nullable=False, default=False)
    bundle_items= Column(JSON, nullable=False, default=list)
    is_active   = Column(Boolean, nullable=False, default=True)
    sort_order  = Column(Integer, nullable=False, default=100)

    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow,
                         onupdate=datetime.utcnow, nullable=False)


class ShowcaseClick(Base):
    """
    One row per tracked interaction.
    event_type: "view" | "detail" | "outbound"
    anon_user_id: optional hashed/anonymised user identifier (not the real UUID)
    """
    __tablename__ = "showcase_clicks"

    id            = Column(Integer, primary_key=True, index=True)
    product_id    = Column(Integer, ForeignKey("showcase_products.id",
                           ondelete="CASCADE"), nullable=False, index=True)
    event_type    = Column(String(20), nullable=False)   # view | detail | outbound
    anon_user_id  = Column(String(64), nullable=True)    # anonymised, optional
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class FeatureInterest(Base):
    """
    Records when a user clicks 'Notify Me' on a coming-soon or pro feature.
    """
    __tablename__ = "feature_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=True)
    feature_name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
