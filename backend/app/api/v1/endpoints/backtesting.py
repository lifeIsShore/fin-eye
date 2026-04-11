from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Optional
import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import AsyncSessionLocal
from app.schemas.backtest_models import (
    BacktestRequest, BacktestResponse,
    WalkForwardRequest, WalkForwardResponse,
    PublishBacktestRequest, LeaderboardEntry, LeaderboardResponse,
)
from app.services.backtesting_service import BacktestingEngine, WalkForwardEngine
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=BacktestResponse, summary="Run a historical backtest")
async def run_backtest(request: BacktestRequest) -> Any:
    """
    Run a strategy backtest based on the request parameters.
    
    * **symbol**: Ticker symbol to test (e.g. AAPL)
    * **strategy**: Strategy name (e.g. "momentum")
    * **parameters**: Strategy-specific params like sma_fast, sma_slow, rsi_threshold
    * **start_date / end_date**: Optional YYYY-MM-DD bounds
    """
    try:
        engine = BacktestingEngine(request)
        response = engine.run()
        return response
    except ValueError as e:
        logger.error(f"Validation error in backtest: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in backtest: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while running the backtest.")


@router.post(
    "/walk-forward",
    response_model=WalkForwardResponse,
    summary="Walk-forward out-of-sample validation",
    description=(
        "Runs a time-series walk-forward validation to estimate out-of-sample "
        "performance. Splits the full history into N anchored IS/OOS windows, "
        "runs the strategy on each, and returns per-fold stats plus a stitched "
        "OOS equity curve. High IS→OOS Sharpe degradation indicates overfitting."
    ),
)
async def run_walk_forward(request: WalkForwardRequest) -> Any:
    try:
        engine = WalkForwardEngine(request)
        return engine.run()
    except ValueError as e:
        logger.error(f"Walk-forward validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in walk-forward: {str(e)}")
        raise HTTPException(status_code=500, detail="Walk-forward validation failed.")


# ── Sprint 44: Public Strategy Leaderboard ────────────────────────

_ANON_RE = None

def _anonymise(username: str | None) -> str:
    """Return first 3 chars + *** e.g. 'joh***'."""
    if not username:
        return "anon***"
    prefix = username[:3].lower()
    return f"{prefix}***"


@router.post(
    "/publish",
    response_model=LeaderboardEntry,
    summary="Publish a backtest result to the community leaderboard",
)
async def publish_backtest(
    payload: PublishBacktestRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Saves the backtest summary to the public leaderboard.
    The user's display name is anonymised (first 3 chars + ***).
    A user can submit multiple times; the highest Sharpe per week is shown.
    """
    from app.models.leaderboard import PublicBacktestRun  # noqa: PLC0415

    async with AsyncSessionLocal() as session:
        run = PublicBacktestRun(
            id=uuid.uuid4(),
            user_id=current_user.id,
            strategy_name=payload.strategy_name,
            symbol=payload.symbol.upper(),
            strategy=payload.strategy,
            start_date=payload.start_date,
            end_date=payload.end_date,
            sharpe_ratio=round(payload.sharpe_ratio, 4),
            total_return_pct=round(payload.total_return_pct, 2),
            max_drawdown_pct=round(payload.max_drawdown_pct, 2),
            total_trades=payload.total_trades,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    return LeaderboardEntry(
        rank=0,  # rank computed by GET /leaderboard
        strategy_name=run.strategy_name,
        symbol=run.symbol,
        strategy=run.strategy,
        sharpe_ratio=run.sharpe_ratio,
        total_return_pct=run.total_return_pct,
        max_drawdown_pct=run.max_drawdown_pct,
        total_trades=run.total_trades,
        username=_anonymise(current_user.name or current_user.email),
        submitted_at=run.submitted_at.date().isoformat(),
    )


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Community strategy leaderboard (top 10 by Sharpe)",
)
async def get_leaderboard(
    period: str = "weekly",   # "weekly" | "alltime"
) -> Any:
    """
    Returns the top 10 publicly submitted backtests sorted by Sharpe ratio.
    period=weekly filters to the last 7 days; period=alltime returns all time.
    """
    from app.models.leaderboard import PublicBacktestRun  # noqa: PLC0415

    async with AsyncSessionLocal() as session:
        q = select(PublicBacktestRun, User).join(
            User, PublicBacktestRun.user_id == User.id, isouter=True
        ).where(PublicBacktestRun.is_active == True)  # noqa: E712

        if period == "weekly":
            since = datetime.now(timezone.utc) - timedelta(days=7)
            q = q.where(PublicBacktestRun.submitted_at >= since)

        q = q.order_by(desc(PublicBacktestRun.sharpe_ratio)).limit(10)
        rows = (await session.execute(q)).all()

    entries = [
        LeaderboardEntry(
            rank=i + 1,
            strategy_name=run.strategy_name,
            symbol=run.symbol,
            strategy=run.strategy,
            sharpe_ratio=run.sharpe_ratio,
            total_return_pct=run.total_return_pct,
            max_drawdown_pct=run.max_drawdown_pct,
            total_trades=run.total_trades,
            username=_anonymise((user.name or user.email) if user else None),
            submitted_at=run.submitted_at.date().isoformat(),
        )
        for i, (run, user) in enumerate(rows)
    ]

    # Next Monday
    today = datetime.now(timezone.utc).date()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    next_monday = (today + timedelta(days=days_until_monday)).isoformat()

    return LeaderboardResponse(
        entries=entries,
        period=period,
        reset_date=next_monday if period == "weekly" else None,
    )
