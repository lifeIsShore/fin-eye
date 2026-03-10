from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.models.portfolio import Portfolio, PortfolioItem
from app.models.user import User
from app.api.v1.deps import get_current_user
from app.services.portfolio_service import calculate_portfolio_analysis

router = APIRouter()

# --- Pydantic Schemas ---

class PortfolioItemBase(BaseModel):
    symbol: str
    weight: float

class PortfolioItemResponse(PortfolioItemBase):
    id: int
    class Config:
        orm_mode = True

class PortfolioCreate(BaseModel):
    name: str
    description: str = None

class PortfolioResponse(PortfolioCreate):
    id: int
    items: List[PortfolioItemResponse] = []
    class Config:
        orm_mode = True

# --- Endpoints ---

@router.get("/", response_model=List[PortfolioResponse])
async def get_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Retrieve all portfolios owned by the current user."""
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new portfolio container."""
    portfolio = Portfolio(
        name=portfolio_in.name,
        description=portfolio_in.description,
        user_id=current_user.id
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get a specific portfolio by ID, including its holding composition."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.post("/{portfolio_id}/items", response_model=PortfolioResponse)
async def add_portfolio_item(
    portfolio_id: int,
    item_in: PortfolioItemBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Add a new stock or update the weight of an existing stock."""
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    symbol_upper = item_in.symbol.upper()
    existing_item_result = await db.execute(
        select(PortfolioItem).where(
            PortfolioItem.portfolio_id == portfolio_id, 
            PortfolioItem.symbol == symbol_upper
        )
    )
    existing_item = existing_item_result.scalar_one_or_none()

    if existing_item:
        existing_item.weight = item_in.weight
    else:
        new_item = PortfolioItem(
            portfolio_id=portfolio.id,
            symbol=symbol_upper,
            weight=item_in.weight
        )
        db.add(new_item)

    await db.commit()
    await db.refresh(portfolio)
    return portfolio

@router.delete("/{portfolio_id}/items/{symbol}", response_model=PortfolioResponse)
async def remove_portfolio_item(
    portfolio_id: int,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Remove a stock from a portfolio."""
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    item_result = await db.execute(
        select(PortfolioItem).where(
            PortfolioItem.portfolio_id == portfolio_id, 
            PortfolioItem.symbol == symbol.upper()
        )
    )
    item = item_result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in portfolio")

    await db.delete(item)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio

@router.get("/{portfolio_id}/analysis")
async def get_portfolio_analysis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Trigger the complex portfolio aggregation math (GAS, Sectors, Diversification)."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    metrics = await calculate_portfolio_analysis(db, portfolio_id)
    if "error" in metrics:
        raise HTTPException(status_code=400, detail=metrics["error"])
        
    return metrics
