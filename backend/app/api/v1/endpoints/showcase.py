"""
Showcase / Pro Tools endpoints  (CORE-SHOP-01, CORE-SHOP-02)

Public:
  GET  /api/v1/showcase/products            — list active products
  GET  /api/v1/showcase/products/{id}       — single product detail
  POST /api/v1/showcase/products/{id}/click — track a click event

Admin:
  POST   /api/v1/showcase/products          — create product
  PUT    /api/v1/showcase/products/{id}     — update product
  DELETE /api/v1/showcase/products/{id}     — hard delete
  GET    /api/v1/showcase/stats             — per-product click stats
"""

from __future__ import annotations

import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.showcase import ShowcaseClick, ShowcaseProduct
from app.models.user import User
from app.api.v1.deps import get_current_user, require_admin

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProductOut(BaseModel):
    id: int
    title: str
    tagline: str
    description: str
    features: List[str]
    category: str
    price_label: str
    external_url: str
    sort_order: int

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    title: str
    tagline: str = ""
    description: str = ""
    features: List[str] = []
    category: str = "General"
    price_label: str = "Free"
    external_url: str
    sort_order: int = 100


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    category: Optional[str] = None
    price_label: Optional[str] = None
    external_url: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ClickRequest(BaseModel):
    event_type: str          # "view" | "detail" | "outbound"
    anon_user_id: Optional[str] = None   # client may send a hashed id


class StatRow(BaseModel):
    product_id: int
    title: str
    views: int
    details: int
    outbound: int


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _anon_id_from_request(request: Request) -> str:
    """Derive a privacy-safe identifier from IP + User-Agent."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    raw = f"{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ─── Public endpoints ─────────────────────────────────────────────────────────

@router.get("/products", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return active products, sorted by sort_order then title."""
    stmt = select(ShowcaseProduct).where(ShowcaseProduct.is_active == True)  # noqa: E712
    if category:
        stmt = stmt.where(ShowcaseProduct.category == category)
    stmt = stmt.order_by(ShowcaseProduct.sort_order, ShowcaseProduct.title)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single active product by id."""
    result = await db.execute(
        select(ShowcaseProduct).where(
            ShowcaseProduct.id == product_id,
            ShowcaseProduct.is_active == True,  # noqa: E712
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.post("/products/{product_id}/click", status_code=status.HTTP_204_NO_CONTENT)
async def track_click(
    product_id: int,
    body: ClickRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a click event (view | detail | outbound).
    Never fails visibly — analytics must not break the UX.
    """
    if body.event_type not in ("view", "detail", "outbound"):
        return   # silently ignore invalid event types

    # Confirm product exists (don't create orphan rows)
    result = await db.execute(
        select(ShowcaseProduct.id).where(
            ShowcaseProduct.id == product_id,
            ShowcaseProduct.is_active == True,  # noqa: E712
        )
    )
    if not result.scalar_one_or_none():
        return

    anon_id = body.anon_user_id or _anon_id_from_request(request)

    click = ShowcaseClick(
        product_id=product_id,
        event_type=body.event_type,
        anon_user_id=anon_id,
    )
    try:
        db.add(click)
        await db.commit()
    except Exception:
        await db.rollback()
        # Never surface analytics errors to the client


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = ShowcaseProduct(**body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut,
            dependencies=[Depends(require_admin)])
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShowcaseProduct).where(ShowcaseProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ShowcaseProduct).where(ShowcaseProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    await db.delete(product)
    await db.commit()


@router.get("/stats", response_model=List[StatRow],
            dependencies=[Depends(require_admin)])
async def click_stats(db: AsyncSession = Depends(get_db)):
    """Per-product click breakdown: views, detail-opens, outbound clicks."""
    result = await db.execute(
        select(ShowcaseProduct).order_by(ShowcaseProduct.sort_order, ShowcaseProduct.title)
    )
    products = result.scalars().all()

    rows = []
    for p in products:
        count_result = await db.execute(
            select(ShowcaseClick.event_type, func.count(ShowcaseClick.id))
            .where(ShowcaseClick.product_id == p.id)
            .group_by(ShowcaseClick.event_type)
        )
        count_map = {et: c for et, c in count_result.all()}
        rows.append(StatRow(
            product_id=p.id,
            title=p.title,
            views=count_map.get("view", 0),
            details=count_map.get("detail", 0),
            outbound=count_map.get("outbound", 0),
        ))
    return rows
