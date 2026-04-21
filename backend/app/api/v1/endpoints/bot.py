"""
app/api/v1/endpoints/bot.py
─────────────────────────────────────────────────────────────────────────────
Sprint 47 — Paper Trading Bot API

Routes:
  GET    /bot/config            — get or create bot config
  PATCH  /bot/config            — update settings
  POST   /bot/enable            — enable bot (requires verified + watchlist)
  POST   /bot/disable           — disable bot
  POST   /bot/halt              — kill switch (optionally close all positions)
  POST   /bot/resume            — clear halt flag
  GET    /bot/positions         — open + recent closed positions with unrealised PnL
  GET    /bot/audit-log         — paginated decision log
  GET    /bot/performance       — paper trading summary stats
"""
from __future__ import annotations

import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_verified_user
from app.db.database import get_db
from app.models.bot import BotAuditLog, BotConfig, BotPosition
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.services.bot_service import get_bot_performance

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Paper Trading Bot"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class BotConfigResponse(BaseModel):
    is_enabled: bool
    mode: str
    strategy: str
    min_grade: str
    max_position_pct: float
    max_total_pct: float
    max_sector_pct: float
    daily_loss_limit: float
    portfolio_value: float
    halt_flag: bool
    verbose_logging: bool

    class Config:
        from_attributes = True


class BotConfigUpdate(BaseModel):
    strategy: Optional[str] = None
    min_grade: Optional[str] = None
    max_position_pct: Optional[float] = Field(None, ge=0.05, le=0.25)
    max_total_pct: Optional[float] = Field(None, ge=0.20, le=1.0)
    max_sector_pct: Optional[float] = Field(None, ge=0.10, le=0.60)
    daily_loss_limit: Optional[float] = Field(None, ge=0.01, le=0.20)
    portfolio_value: Optional[float] = Field(None, gt=0)
    verbose_logging: Optional[bool] = None


class BotPositionResponse(BaseModel):
    id: str
    symbol: str
    entry_price: float
    entry_grade: str
    entry_gas: float
    size_usd: float
    position_pct: float
    opened_at: str
    is_open: bool
    current_price: Optional[float] = None
    unrealised_pnl_usd: Optional[float] = None
    unrealised_pnl_pct: Optional[float] = None
    closed_at: Optional[str] = None
    close_price: Optional[float] = None
    close_reason: Optional[str] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None


class BotAuditLogEntry(BaseModel):
    id: str
    logged_at: str
    symbol: Optional[str]
    action: str
    grade: Optional[str]
    gas_score: Optional[float]
    price: Optional[float]
    size_usd: Optional[float]
    reason: str
    regime: Optional[str]


class HaltRequest(BaseModel):
    close_all: bool = False


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_or_create_config(db: AsyncSession, user_id: UUID) -> BotConfig:
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user_id))
    config = result.scalar_one_or_none()
    if config is None:
        config = BotConfig(user_id=user_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def _fetch_current_price(symbol: str) -> Optional[float]:
    """Best-effort live price fetch — returns None on failure."""
    try:
        from app.services.market_data import OHLCVFetcher  # noqa: PLC0415
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5d", interval="1d")
        if records:
            return float(records[-1].close)
    except Exception:
        pass
    return None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/config", response_model=BotConfigResponse)
async def get_config(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> BotConfigResponse:
    config = await _get_or_create_config(db, current_user.id)
    return BotConfigResponse(
        is_enabled=config.is_enabled, mode=config.mode, strategy=config.strategy,
        min_grade=config.min_grade, max_position_pct=config.max_position_pct,
        max_total_pct=config.max_total_pct, max_sector_pct=config.max_sector_pct,
        daily_loss_limit=config.daily_loss_limit,
        portfolio_value=config.portfolio_value, halt_flag=config.halt_flag,
        verbose_logging=config.verbose_logging,
    )


@router.patch("/config", response_model=BotConfigResponse)
async def update_config(
    body: BotConfigUpdate,
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> BotConfigResponse:
    config = await _get_or_create_config(db, current_user.id)
    if body.strategy is not None:
        config.strategy = body.strategy
    if body.min_grade is not None:
        config.min_grade = body.min_grade
    if body.max_position_pct is not None:
        config.max_position_pct = body.max_position_pct
    if body.max_total_pct is not None:
        config.max_total_pct = body.max_total_pct
    if body.max_sector_pct is not None:
        config.max_sector_pct = body.max_sector_pct
    if body.daily_loss_limit is not None:
        config.daily_loss_limit = body.daily_loss_limit
    if body.portfolio_value is not None:
        config.portfolio_value = body.portfolio_value
    if body.verbose_logging is not None:
        config.verbose_logging = body.verbose_logging
    await db.commit()
    return await get_config(current_user, db)


@router.post("/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_bot(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    # Require at least one watchlist item
    wl = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == current_user.id).limit(1)
    )
    if not wl.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add at least one symbol to your watchlist before enabling the bot.",
        )
    config = await _get_or_create_config(db, current_user.id)
    config.is_enabled = True
    config.halt_flag = False
    db.add(BotAuditLog(user_id=current_user.id, action="ENABLE",
                       reason="Bot enabled by user."))
    await db.commit()
    logger.info("Bot enabled for user_id=%s", current_user.id)


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_bot(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    config = await _get_or_create_config(db, current_user.id)
    config.is_enabled = False
    db.add(BotAuditLog(user_id=current_user.id, action="DISABLE",
                       reason="Bot disabled by user. Open positions remain open."))
    await db.commit()


@router.post("/halt", status_code=status.HTTP_204_NO_CONTENT)
async def halt_bot(
    body: HaltRequest,
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Kill switch — sets halt_flag immediately. Optionally closes all open positions at market."""
    from datetime import datetime as _dt, timezone as tz  # noqa: PLC0415
    config = await _get_or_create_config(db, current_user.id)
    config.halt_flag = True

    closed_count = 0
    if body.close_all:
        open_positions = (await db.execute(
            select(BotPosition).where(
                BotPosition.user_id == current_user.id,
                BotPosition.is_open == True,  # noqa: E712
            )
        )).scalars().all()
        for pos in open_positions:
            price = await _fetch_current_price(pos.symbol) or pos.entry_price
            pnl = round((price - pos.entry_price) * pos.size_units, 2)
            pos.is_open = False
            pos.closed_at = _dt.now(tz.utc)
            pos.close_price = price
            pos.close_reason = "manual"
            pos.pnl_usd = pnl
            pos.pnl_pct = round((price / pos.entry_price - 1) * 100, 2)
            closed_count += 1

    reason = (f"Bot halted by user kill switch."
              + (f" Closed {closed_count} open position(s)." if closed_count else ""))
    db.add(BotAuditLog(user_id=current_user.id, action="HALT", reason=reason))
    await db.commit()
    logger.info("Bot halted for user_id=%s (closed=%d)", current_user.id, closed_count)


@router.post("/resume", status_code=status.HTTP_204_NO_CONTENT)
async def resume_bot(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    config = await _get_or_create_config(db, current_user.id)
    config.halt_flag = False
    db.add(BotAuditLog(user_id=current_user.id, action="RESUME",
                       reason="Bot resumed by user."))
    await db.commit()


@router.get("/positions", response_model=List[BotPositionResponse])
async def get_positions(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
    include_closed: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[BotPositionResponse]:
    q = select(BotPosition).where(BotPosition.user_id == current_user.id)
    if not include_closed:
        q = q.where(BotPosition.is_open == True)  # noqa: E712
    q = q.order_by(BotPosition.opened_at.desc()).limit(limit)
    positions = (await db.execute(q)).scalars().all()

    # Batch-fetch current prices for all open positions concurrently (perf fix)
    import asyncio as _asyncio  # noqa: PLC0415
    open_symbols = list({pos.symbol for pos in positions if pos.is_open})
    price_tasks = await _asyncio.gather(*[_fetch_current_price(s) for s in open_symbols], return_exceptions=True)
    price_map = {sym: (p if not isinstance(p, Exception) else None) for sym, p in zip(open_symbols, price_tasks)}

    result = []
    for pos in positions:
        current_price = None
        unreal_pnl = None
        unreal_pct = None
        if pos.is_open:
            current_price = price_map.get(pos.symbol)
            if current_price:
                unreal_pnl = round((current_price - pos.entry_price) * pos.size_units, 2)
                unreal_pct = round((current_price / pos.entry_price - 1) * 100, 2)
        result.append(BotPositionResponse(
            id=str(pos.id), symbol=pos.symbol, entry_price=pos.entry_price,
            entry_grade=pos.entry_grade, entry_gas=pos.entry_gas,
            size_usd=pos.size_usd, position_pct=pos.position_pct,
            opened_at=pos.opened_at.isoformat(), is_open=pos.is_open,
            current_price=current_price, unrealised_pnl_usd=unreal_pnl,
            unrealised_pnl_pct=unreal_pct,
            closed_at=pos.closed_at.isoformat() if pos.closed_at else None,
            close_price=pos.close_price, close_reason=pos.close_reason,
            pnl_usd=pos.pnl_usd, pnl_pct=pos.pnl_pct,
        ))
    return result


@router.get("/audit-log", response_model=List[BotAuditLogEntry])
async def get_audit_log(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    symbol: Optional[str] = Query(default=None),
    include_system: bool = Query(default=True, description="Include system actions (HALT/RESUME/ENABLE/DISABLE) which have no symbol"),
) -> List[BotAuditLogEntry]:
    q = select(BotAuditLog).where(BotAuditLog.user_id == current_user.id)
    if symbol:
        sym = symbol.upper()
        if include_system:
            # symbol matches OR symbol is NULL (system action)
            from sqlalchemy import or_  # noqa: PLC0415
            q = q.where(or_(BotAuditLog.symbol == sym, BotAuditLog.symbol.is_(None)))
        else:
            q = q.where(BotAuditLog.symbol == sym)
    q = q.order_by(BotAuditLog.logged_at.desc()).limit(limit)
    logs = (await db.execute(q)).scalars().all()
    return [
        BotAuditLogEntry(
            id=str(log.id), logged_at=log.logged_at.isoformat(),
            symbol=log.symbol, action=log.action, grade=log.grade,
            gas_score=log.gas_score, price=log.price, size_usd=log.size_usd,
            reason=log.reason, regime=log.regime,
        )
        for log in logs
    ]


@router.get("/performance")
async def get_performance(
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    config = await _get_or_create_config(db, current_user.id)
    return await get_bot_performance(db, current_user.id, config)
