"""
app/services/strategy_service.py
Business logic for the Strategy Library (P2-STRAT-01).

Public strategies are readable by anyone who is authenticated.
Private strategies are only readable by their owner.
"""
import logging
import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import SavedStrategy
from app.models.user import User
from app.schemas.strategy_models import StrategySaveRequest, StrategyUpdateRequest

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_request_snapshot(payload: StrategySaveRequest) -> dict:
    """Extract the BacktestRequest-equivalent fields into a plain dict for JSON storage."""
    return {
        "symbol": payload.symbol,
        "strategy": payload.strategy,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "parameters": payload.parameters,
        "initial_capital": payload.initial_capital,
        "slippage_pct": payload.slippage_pct,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────────

async def save_strategy(
    db: AsyncSession,
    user: User,
    payload: StrategySaveRequest,
) -> SavedStrategy:
    strategy = SavedStrategy(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        request_snapshot=_build_request_snapshot(payload),
        total_return_pct=payload.total_return_pct,
        annualized_return_pct=payload.annualized_return_pct,
        sharpe_ratio=payload.sharpe_ratio,
        max_drawdown_pct=payload.max_drawdown_pct,
        win_rate_pct=payload.win_rate_pct,
        total_trades=payload.total_trades,
        is_public=payload.is_public,
    )
    db.add(strategy)
    await db.flush()
    await db.refresh(strategy)
    logger.info("Strategy %d '%s' saved by user %s", strategy.id, strategy.name, user.id)
    return strategy


async def list_my_strategies(
    db: AsyncSession,
    user: User,
) -> List[SavedStrategy]:
    result = await db.execute(
        select(SavedStrategy)
        .where(SavedStrategy.user_id == user.id)
        .order_by(SavedStrategy.created_at.desc())
    )
    return list(result.scalars().all())


async def list_public_strategies(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> List[SavedStrategy]:
    """Return all public strategies ordered by Sharpe (best first)."""
    result = await db.execute(
        select(SavedStrategy)
        .where(SavedStrategy.is_public == True)  # noqa: E712
        .order_by(SavedStrategy.sharpe_ratio.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_strategy(
    db: AsyncSession,
    strategy_id: int,
    user: User,
) -> Optional[SavedStrategy]:
    """Return strategy if owned by user OR if it is public."""
    result = await db.execute(
        select(SavedStrategy).where(
            SavedStrategy.id == strategy_id,
            or_(
                SavedStrategy.user_id == user.id,
                SavedStrategy.is_public == True,  # noqa: E712
            ),
        )
    )
    return result.scalar_one_or_none()


async def update_strategy(
    db: AsyncSession,
    strategy_id: int,
    user: User,
    payload: StrategyUpdateRequest,
) -> Optional[SavedStrategy]:
    """Only the owner may update."""
    result = await db.execute(
        select(SavedStrategy).where(
            SavedStrategy.id == strategy_id,
            SavedStrategy.user_id == user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        return None

    if payload.name is not None:
        strategy.name = payload.name
    if payload.description is not None:
        strategy.description = payload.description
    if payload.is_public is not None:
        strategy.is_public = payload.is_public

    await db.flush()
    return strategy


async def delete_strategy(
    db: AsyncSession,
    strategy_id: int,
    user: User,
) -> bool:
    """Only the owner may delete."""
    result = await db.execute(
        select(SavedStrategy).where(
            SavedStrategy.id == strategy_id,
            SavedStrategy.user_id == user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        return False
    await db.delete(strategy)
    await db.flush()
    return True
