"""
app/api/v1/endpoints/portfolios.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.models.portfolio import Portfolio, PortfolioItem
from app.models.user import User
from app.api.v1.deps import get_current_user, get_current_active_verified_user
from app.services.portfolio_service import calculate_portfolio_analysis

router = APIRouter()

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PortfolioItemBase(BaseModel):
    symbol: str
    weight: float

class PortfolioItemResponse(PortfolioItemBase):
    id: int
    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    name: str
    description: str = ""

class PortfolioPatch(BaseModel):
    """All fields optional — only supplied fields are updated."""
    name:            Optional[str]   = None
    description:     Optional[str]   = None
    strategy_tag:    Optional[str]   = None
    risk_tolerance:  Optional[str]   = None
    base_currency:   Optional[str]   = None
    horizon:         Optional[str]   = None
    notes:           Optional[str]   = None
    target_return:   Optional[float] = None
    benchmark:       Optional[str]   = None

class PortfolioResponse(BaseModel):
    id:              int
    name:            str
    description:     Optional[str] = None
    strategy_tag:    Optional[str] = None
    risk_tolerance:  Optional[str] = None
    base_currency:   Optional[str] = "USD"
    horizon:         Optional[str] = None
    notes:           Optional[str] = None
    target_return:   Optional[float] = None
    benchmark:       Optional[str] = None
    items:           List[PortfolioItemResponse] = []
    class Config:
        from_attributes = True


# ── Helper ────────────────────────────────────────────────────────────────────

async def _load_portfolio(db: AsyncSession, portfolio_id: int, user_id) -> Portfolio:
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.items))
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PortfolioResponse])
async def get_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.items))
        .where(Portfolio.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    existing = await db.execute(
        select(Portfolio).where(
            Portfolio.user_id == current_user.id,
            Portfolio.name == portfolio_in.name.strip(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A portfolio named '{portfolio_in.name.strip()}' already exists.",
        )

    portfolio = Portfolio(
        name=portfolio_in.name.strip(),
        description=portfolio_in.description or "",
        user_id=current_user.id,
    )
    db.add(portfolio)
    await db.commit()

    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.items))
        .where(Portfolio.id == portfolio.id)
    )
    return result.scalar_one()


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    return await _load_portfolio(db, portfolio_id, current_user.id)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def patch_portfolio(
    portfolio_id: int,
    patch: PortfolioPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Partial update — only provided fields are written."""
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)

    # Duplicate name check if name is being changed
    if patch.name is not None:
        new_name = patch.name.strip()
        if new_name != portfolio.name:
            dupe = await db.execute(
                select(Portfolio).where(
                    Portfolio.user_id == current_user.id,
                    Portfolio.name == new_name,
                )
            )
            if dupe.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A portfolio named '{new_name}' already exists.",
                )
        portfolio.name = new_name

    for field in ("description", "strategy_tag", "risk_tolerance",
                  "base_currency", "horizon", "notes", "target_return", "benchmark"):
        val = getattr(patch, field)
        if val is not None:
            setattr(portfolio, field, val)

    await db.commit()
    return await _load_portfolio(db, portfolio_id, current_user.id)


@router.post("/{portfolio_id}/items", response_model=PortfolioResponse)
async def add_portfolio_item(
    portfolio_id: int,
    item_in: PortfolioItemBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)
    symbol = item_in.symbol.upper()
    existing = next((i for i in portfolio.items if i.symbol == symbol), None)
    if existing:
        existing.weight = item_in.weight
    else:
        db.add(PortfolioItem(portfolio_id=portfolio.id, symbol=symbol, weight=item_in.weight))
    await db.commit()
    return await _load_portfolio(db, portfolio_id, current_user.id)


@router.delete("/{portfolio_id}/items/{symbol}", response_model=PortfolioResponse)
async def remove_portfolio_item(
    portfolio_id: int,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)
    sym_upper = symbol.upper()
    item = next((i for i in portfolio.items if i.symbol == sym_upper), None)
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in portfolio")
    await db.delete(item)
    await db.commit()
    return await _load_portfolio(db, portfolio_id, current_user.id)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)
    await db.delete(portfolio)
    await db.commit()


@router.get("/{portfolio_id}/analysis")
async def get_portfolio_analysis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    await _load_portfolio(db, portfolio_id, current_user.id)
    metrics = await calculate_portfolio_analysis(db, portfolio_id)
    if "error" in metrics:
        raise HTTPException(status_code=400, detail=metrics["error"])
    return metrics


@router.get("/{portfolio_id}/correlation")
async def get_portfolio_correlation(
    portfolio_id: int,
    period: str = "6mo",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Sprint 19 -- Correlation matrix for portfolio positions.
    Fetches `period` of daily close prices for each symbol and returns
    a pairwise Pearson correlation matrix.

    Response:
    {
      "symbols": ["AAPL", "MSFT", ...],
      "matrix":  [[1.0, 0.82, ...], [0.82, 1.0, ...], ...],
      "period":  "6mo"
    }
    """
    from app.services.portfolio_correlation import calculate_portfolio_correlation  # noqa: PLC0415
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)
    result = await calculate_portfolio_correlation(portfolio, period)
    return result


@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    period: str = "1y",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Sprint 15 P3-PORT-02 -- Portfolio vs benchmark equity curve.
    Returns normalised equity curves (start = 100) for the portfolio
    and its configured benchmark (default SPY) over `period`.
    """
    from app.services.portfolio_performance import calculate_portfolio_performance  # noqa: PLC0415
    portfolio = await _load_portfolio(db, portfolio_id, current_user.id)
    result = await calculate_portfolio_performance(portfolio, period)
    return result
