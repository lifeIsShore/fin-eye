from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.models.watchlist import WatchlistItem
from app.models.user import User
from app.api.v1.deps import get_current_user

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    added_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_item(cls, item: WatchlistItem) -> "WatchlistItemResponse":
        return cls(
            id=item.id,
            symbol=item.symbol,
            added_at=item.added_at.isoformat() if item.added_at else "",
        )


class WatchlistAddRequest(BaseModel):
    symbol: str


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[WatchlistItemResponse])
async def list_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return all watchlist entries for the current user, ordered newest first."""
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.added_at.desc())
    )
    items = result.scalars().all()
    return [WatchlistItemResponse.from_orm_item(i) for i in items]


@router.post("/", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Add a ticker to the user's watchlist. Silently succeeds if already present."""
    symbol = body.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol cannot be empty.")
    if len(symbol) > 10:
        raise HTTPException(status_code=400, detail="Symbol too long.")

    # Check if already exists — return existing rather than error
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.symbol == symbol,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return WatchlistItemResponse.from_orm_item(existing)

    item = WatchlistItem(user_id=current_user.id, symbol=symbol)
    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        # Race condition — fetch and return the existing row
        result = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.symbol == symbol,
            )
        )
        item = result.scalar_one_or_none()
    return WatchlistItemResponse.from_orm_item(item)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a ticker from the user's watchlist."""
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.symbol == symbol.strip().upper(),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist.")
    await db.delete(item)
    await db.commit()
