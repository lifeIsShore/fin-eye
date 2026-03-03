from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.models.portfolio import Portfolio, PortfolioItem
from app.models.user import User
from app.services.auth import get_current_user
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
def get_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Retrieve all portfolios owned by the current user."""
    return db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()

@router.post("/", response_model=PortfolioResponse)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new portfolio container."""
    portfolio = Portfolio(
        name=portfolio_in.name,
        description=portfolio_in.description,
        user_id=current_user.id
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get a specific portfolio by ID, including its holding composition."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.post("/{portfolio_id}/items", response_model=PortfolioResponse)
def add_portfolio_item(
    portfolio_id: int,
    item_in: PortfolioItemBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Add a new stock or update the weight of an existing stock."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    symbol_upper = item_in.symbol.upper()
    existing_item = db.query(PortfolioItem).filter(
        PortfolioItem.portfolio_id == portfolio_id, 
        PortfolioItem.symbol == symbol_upper
    ).first()

    if existing_item:
        existing_item.weight = item_in.weight
    else:
        new_item = PortfolioItem(
            portfolio_id=portfolio.id,
            symbol=symbol_upper,
            weight=item_in.weight
        )
        db.add(new_item)

    db.commit()
    db.refresh(portfolio)
    return portfolio

@router.delete("/{portfolio_id}/items/{symbol}", response_model=PortfolioResponse)
def remove_portfolio_item(
    portfolio_id: int,
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Remove a stock from a portfolio."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    item = db.query(PortfolioItem).filter(
        PortfolioItem.portfolio_id == portfolio_id, 
        PortfolioItem.symbol == symbol.upper()
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in portfolio")

    db.delete(item)
    db.commit()
    db.refresh(portfolio)
    return portfolio

@router.get("/{portfolio_id}/analysis")
async def get_portfolio_analysis(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Trigger the complex portfolio aggregation math (GAS, Sectors, Diversification)."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    metrics = await calculate_portfolio_analysis(db, portfolio_id)
    if "error" in metrics:
        raise HTTPException(status_code=400, detail=metrics["error"])
        
    return metrics
