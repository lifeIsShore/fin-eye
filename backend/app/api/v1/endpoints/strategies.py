"""
app/api/v1/endpoints/strategies.py
REST endpoints for the Strategy Library (P2-STRAT-01).

Routes (all auth-protected):
    POST   /strategies               — save a strategy
    GET    /strategies               — list current user's strategies
    GET    /strategies/public        — browse all public strategies
    GET    /strategies/{id}          — get one (own or public)
    PATCH  /strategies/{id}          — update name/description/visibility (owner only)
    DELETE /strategies/{id}          — delete (owner only)
"""
import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.strategy import SavedStrategy
from app.models.user import User
from app.schemas.strategy_models import (
    StrategyListResponse,
    StrategyResponse,
    StrategySaveRequest,
    StrategyUpdateRequest,
)
from app.services.strategy_service import (
    delete_strategy,
    get_strategy,
    list_my_strategies,
    list_public_strategies,
    save_strategy,
    update_strategy,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Serialisation helper ───────────────────────────────────────────────────────

def _to_response(s: SavedStrategy, current_user_id) -> StrategyResponse:
    snap = s.request_snapshot or {}
    return StrategyResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        symbol=snap.get("symbol", ""),
        strategy=snap.get("strategy", "momentum"),
        parameters=snap.get("parameters", {}),
        initial_capital=snap.get("initial_capital", 10_000.0),
        slippage_pct=snap.get("slippage_pct", 0.001),
        start_date=snap.get("start_date"),
        end_date=snap.get("end_date"),
        total_return_pct=s.total_return_pct,
        annualized_return_pct=s.annualized_return_pct,
        sharpe_ratio=s.sharpe_ratio,
        max_drawdown_pct=s.max_drawdown_pct,
        win_rate_pct=s.win_rate_pct,
        total_trades=s.total_trades,
        is_public=s.is_public,
        is_mine=str(s.user_id) == str(current_user_id),
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a strategy",
)
async def create(
    body: StrategySaveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    s = await save_strategy(db, current_user, body)
    await db.commit()
    return _to_response(s, current_user.id)


@router.get(
    "",
    response_model=StrategyListResponse,
    summary="List my saved strategies",
)
async def list_mine(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StrategyListResponse:
    strategies = await list_my_strategies(db, current_user)
    return StrategyListResponse(
        strategies=[_to_response(s, current_user.id) for s in strategies],
        total=len(strategies),
    )


@router.get(
    "/public",
    response_model=StrategyListResponse,
    summary="Browse all public strategies (sorted by Sharpe)",
)
async def list_public(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> StrategyListResponse:
    strategies = await list_public_strategies(db, limit=limit, offset=offset)
    return StrategyListResponse(
        strategies=[_to_response(s, current_user.id) for s in strategies],
        total=len(strategies),
    )


@router.get(
    "/{strategy_id}",
    response_model=StrategyResponse,
    summary="Get a strategy by ID (own or public)",
)
async def get_one(
    strategy_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    s = await get_strategy(db, strategy_id, current_user)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    return _to_response(s, current_user.id)


@router.patch(
    "/{strategy_id}",
    response_model=StrategyResponse,
    summary="Update strategy name, description, or visibility",
)
async def update(
    strategy_id: int,
    body: StrategyUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    s = await update_strategy(db, strategy_id, current_user, body)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    await db.commit()
    return _to_response(s, current_user.id)


@router.delete(
    "/{strategy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a strategy",
)
async def remove(
    strategy_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await delete_strategy(db, strategy_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    await db.commit()
