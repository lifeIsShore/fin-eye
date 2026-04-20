"""
app/services/bot_service.py
─────────────────────────────────────────────────────────────────────────────
Sprint 47 — Paper Trading Bot Decision Engine

evaluate_symbol() is the core — it runs for every bot-enabled user × watchlist
symbol every 15 minutes (aligned after GAS precompute).

Decision matrix:
  HALT FLAG set           → SKIP (log it, do nothing)
  Daily loss > limit      → HALT bot for 24h
  Grade A+/A, no position → BUY (Kelly-sized, capped at max_position_pct)
  Grade D/F, open pos     → SELL (reason: grade_drop)
  Stop-loss hit           → SELL (price < entry - 2×ATR)
  Grade C/B, open pos     → HOLD
  Otherwise               → SKIP

All decisions logged to bot_audit_log (even SKIP/HOLD).
"""
from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import BotAuditLog, BotConfig, BotPosition
from app.models.market import OHLCVDaily
from app.schemas.montecarlo_models import MCAssetParams
from app.services.mc_engine import run_asset_simulation, compute_log_returns

logger = logging.getLogger(__name__)

# Grade ranking: higher = better
GRADE_RANK = {"A+": 7, "A": 6, "B": 5, "C": 4, "D": 3, "F": 1}
MIN_GRADE_TO_SELL = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 1, "F": 1}  # sell on D or F

# ATR multiplier for stop-loss
STOP_LOSS_ATR_MULT = 2.0


@dataclass
class BotDecision:
    action: str          # BUY | SELL | HOLD | SKIP | HALT
    reason: str
    size_usd: float = 0.0
    position_id: Optional[UUID] = None


# ── Grade helpers ──────────────────────────────────────────────────────────────

def _grade_rank(grade: Optional[str]) -> int:
    return GRADE_RANK.get(grade or "", 0)


def _should_sell_grade(grade: Optional[str]) -> bool:
    """True if grade is D or F — bot should exit."""
    return _grade_rank(grade) <= 3


def _grade_passes_min(grade: Optional[str], min_grade: str) -> bool:
    return _grade_rank(grade) >= _grade_rank(min_grade)


# ── Daily PnL check ────────────────────────────────────────────────────────────

async def _get_daily_pnl(db: AsyncSession, user_id: UUID, portfolio_value: float) -> float:
    """Sum of PnL from closed positions opened today."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(BotPosition.pnl_usd), 0.0)).where(
            BotPosition.user_id == user_id,
            BotPosition.is_open == False,  # noqa: E712
            BotPosition.closed_at >= today_start,
        )
    )
    daily_pnl = float(result.scalar() or 0.0)
    return daily_pnl / portfolio_value if portfolio_value > 0 else 0.0


# ── Position helpers ───────────────────────────────────────────────────────────

async def _get_open_position(db: AsyncSession, user_id: UUID, symbol: str) -> Optional[BotPosition]:
    result = await db.execute(
        select(BotPosition).where(
            BotPosition.user_id == user_id,
            BotPosition.symbol == symbol,
            BotPosition.is_open == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def _get_total_deployed(db: AsyncSession, user_id: UUID) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(BotPosition.size_usd), 0.0)).where(
            BotPosition.user_id == user_id,
            BotPosition.is_open == True,  # noqa: E712
        )
    )
    return float(result.scalar() or 0.0)


# ── Kelly sizing ───────────────────────────────────────────────────────────────

def _kelly_size(gas_score: float, portfolio_value: float, max_pct: float) -> float:
    """
    Simplified Half-Kelly based on GAS score as a proxy for edge.
    GAS 80 → ~15% position, GAS 60 → ~5%, below 60 → no entry.
    Capped at max_position_pct.
    """
    if gas_score < 60:
        return 0.0
    edge = (gas_score - 50) / 50.0   # 0.2 at GAS=60, 0.6 at GAS=80
    half_kelly = edge * 0.5           # half kelly
    pct = min(half_kelly, max_pct)
    return round(portfolio_value * pct, 2)


# ── Audit log writer ───────────────────────────────────────────────────────────

async def _log(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    reason: str,
    *,
    symbol: Optional[str] = None,
    grade: Optional[str] = None,
    gas_score: Optional[float] = None,
    confidence: Optional[float] = None,
    price: Optional[float] = None,
    size_usd: Optional[float] = None,
    position_id: Optional[UUID] = None,
    regime: Optional[str] = None,
    macro_score: Optional[float] = None,
) -> None:
    db.add(BotAuditLog(
        user_id=user_id, action=action, reason=reason,
        symbol=symbol, grade=grade, gas_score=gas_score,
        confidence=confidence, price=price, size_usd=size_usd,
        position_id=position_id, regime=regime, macro_score=macro_score,
    ))


# ── Core decision function ─────────────────────────────────────────────────────

async def evaluate_symbol(
    db: AsyncSession,
    user_id: UUID,
    symbol: str,
    config: BotConfig,
    *,
    grade: Optional[str],
    gas_score: float,
    current_price: float,
    confidence: Optional[float] = None,
    regime: Optional[str] = None,
    macro_score: Optional[float] = None,
    atr: Optional[float] = None,
) -> BotDecision:
    """
    Core paper-trading decision function.
    Called every 15 minutes for each user × symbol with latest GAS data.
    """
    # 1. Kill switch
    if config.halt_flag:
        decision = BotDecision(action="SKIP", reason="Bot is halted. Resume from /bot/paper.")
        await _log(db, user_id, "SKIP", decision.reason, symbol=symbol,
                   grade=grade, gas_score=gas_score, price=current_price, regime=regime)
        return decision

    # 2. Daily loss limit check → auto-halt
    daily_pnl_pct = await _get_daily_pnl(db, user_id, config.portfolio_value)
    if daily_pnl_pct < -config.daily_loss_limit:
        config.halt_flag = True
        reason = (f"Daily loss limit breached ({daily_pnl_pct*100:.1f}% vs "
                  f"-{config.daily_loss_limit*100:.0f}% limit). Bot halted.")
        await _log(db, user_id, "HALT", reason, symbol=symbol, gas_score=gas_score, price=current_price)
        return BotDecision(action="HALT", reason=reason)

    # 3. Check existing position
    position = await _get_open_position(db, user_id, symbol)

    # 4. SELL decision: grade dropped to D/F
    if position and _should_sell_grade(grade):
        pnl_usd = round((current_price - position.entry_price) * position.size_units, 2)
        pnl_pct = round((current_price / position.entry_price - 1) * 100, 2)
        position.is_open = False
        position.closed_at = datetime.now(timezone.utc)
        position.close_price = current_price
        position.close_reason = "grade_drop"
        position.pnl_usd = pnl_usd
        position.pnl_pct = pnl_pct
        reason = (f"Grade dropped to {grade} — exiting position. "
                  f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%)")
        await _log(db, user_id, "SELL", reason, symbol=symbol, grade=grade,
                   gas_score=gas_score, price=current_price, size_usd=position.size_usd,
                   position_id=position.id, regime=regime)
        return BotDecision(action="SELL", reason=reason, size_usd=position.size_usd,
                           position_id=position.id)

    # 5. SELL decision: stop-loss hit (price < entry - 2×ATR)
    if position and atr and current_price < (position.entry_price - STOP_LOSS_ATR_MULT * atr):
        pnl_usd = round((current_price - position.entry_price) * position.size_units, 2)
        pnl_pct = round((current_price / position.entry_price - 1) * 100, 2)
        position.is_open = False
        position.closed_at = datetime.now(timezone.utc)
        position.close_price = current_price
        position.close_reason = "stop_loss"
        position.pnl_usd = pnl_usd
        position.pnl_pct = pnl_pct
        reason = (f"Stop-loss triggered at ${current_price:.2f} "
                  f"(entry ${position.entry_price:.2f}, ATR ${atr:.2f}). "
                  f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%)")
        await _log(db, user_id, "SELL", reason, symbol=symbol, grade=grade,
                   gas_score=gas_score, price=current_price, size_usd=position.size_usd,
                   position_id=position.id, regime=regime)
        return BotDecision(action="SELL", reason=reason, size_usd=position.size_usd,
                           position_id=position.id)

    # 6. HOLD: already have position, grade is acceptable
    if position:
        reason = f"Holding {symbol}. Grade: {grade}, GAS: {gas_score:.1f}."
        await _log(db, user_id, "HOLD", reason, symbol=symbol, grade=grade,
                   gas_score=gas_score, price=current_price, position_id=position.id, regime=regime)
        return BotDecision(action="HOLD", reason=reason, position_id=position.id)

    # 7. BUY: no position, grade passes minimum, GAS strong enough
    if not position and _grade_passes_min(grade, config.min_grade) and gas_score >= 60:
        # Check total deployment cap
        total_deployed = await _get_total_deployed(db, user_id)
        deployed_pct = total_deployed / config.portfolio_value if config.portfolio_value > 0 else 1.0
        if deployed_pct >= config.max_total_pct:
            reason = (f"Max total deployment reached ({deployed_pct*100:.0f}% vs "
                      f"{config.max_total_pct*100:.0f}% limit). Skipping {symbol}.")
            await _log(db, user_id, "SKIP", reason, symbol=symbol, grade=grade,
                       gas_score=gas_score, price=current_price, regime=regime)
            return BotDecision(action="SKIP", reason=reason)

        size_usd = _kelly_size(gas_score, config.portfolio_value, config.max_position_pct)
        if size_usd <= 0 or current_price <= 0:
            reason = f"Kelly sizing returned 0 for {symbol} at GAS {gas_score:.1f}."
            await _log(db, user_id, "SKIP", reason, symbol=symbol, grade=grade,
                       gas_score=gas_score, price=current_price)
            return BotDecision(action="SKIP", reason=reason)
            
        # Sprint 56: CVaR gate via Monte Carlo (run in executor — CPU-bound)
        predicted_cvar = 0.0

        ohlcv_result = await db.execute(
            select(OHLCVDaily.close)
            .where(OHLCVDaily.symbol == symbol)
            .order_by(desc(OHLCVDaily.trade_date))
            .limit(126)
        )
        closes = list(reversed(ohlcv_result.scalars().all()))

        if len(closes) < 30:
            logger.warning("Insufficient OHLCV for MC gate on %s (%d days). Skipping CVaR check.", symbol, len(closes))
        else:
            log_returns = compute_log_returns([float(c) for c in closes])
            sigma_annual = float(log_returns.std() * np.sqrt(252))
            mu_annual = float(log_returns.mean() * 252)
            mc_params = MCAssetParams(
                symbol=symbol, starting_value=size_usd,
                mu=mu_annual, sigma=sigma_annual,
                years=30.0 / 365.0, paths=5000, steps_per_year=252, model_type="GBM"
            )
            try:
                loop = asyncio.get_running_loop()
                mc_result = await loop.run_in_executor(None, run_asset_simulation, mc_params)
                predicted_cvar = (mc_result.cvar_95 * size_usd) / config.portfolio_value
            except Exception as exc:
                logger.warning("MC Engine failed for %s: %s", symbol, exc)

        # Downsize or skip if CVaR breaches daily_loss_limit
        if predicted_cvar > config.daily_loss_limit:
            reason = (f"MC Simulator identified extreme CVaR edge-case (Predicted CVaR: "
                      f"{predicted_cvar*100:.1f}% > Limit: {config.daily_loss_limit*100:.1f}%). "
                      f"Rejecting trade despite positive signals.")
            await _log(db, user_id, "SKIP", reason, symbol=symbol, grade=grade,
                       gas_score=gas_score, price=current_price, regime=regime)
            return BotDecision(action="SKIP", reason=reason)

        size_units = round(size_usd / current_price, 6)
        pos = BotPosition(
            user_id=user_id, symbol=symbol,
            entry_price=current_price, entry_grade=grade or "?",
            entry_gas=gas_score, size_units=size_units,
            size_usd=size_usd,
            position_pct=round(size_usd / config.portfolio_value * 100, 2),
        )
        db.add(pos)
        await db.flush()  # get pos.id
        reason = (f"BUY {symbol} at ${current_price:.2f}. "
                  f"Grade: {grade}, GAS: {gas_score:.1f}, Size: ${size_usd:.2f} "
                  f"({pos.position_pct:.1f}% of portfolio).")
        await _log(db, user_id, "BUY", reason, symbol=symbol, grade=grade,
                   gas_score=gas_score, confidence=confidence, price=current_price,
                   size_usd=size_usd, position_id=pos.id, regime=regime, macro_score=macro_score)
        return BotDecision(action="BUY", reason=reason, size_usd=size_usd, position_id=pos.id)

    # 8. SKIP: grade doesn't pass minimum
    reason = (f"Grade {grade} does not meet minimum {config.min_grade}. "
              f"GAS: {gas_score:.1f}. No action.")
    await _log(db, user_id, "SKIP", reason, symbol=symbol, grade=grade,
               gas_score=gas_score, price=current_price, regime=regime)
    return BotDecision(action="SKIP", reason=reason)


# ── Performance summary ────────────────────────────────────────────────────────

async def get_bot_performance(db: AsyncSession, user_id: UUID, config: BotConfig) -> dict:
    """Compute paper trading performance summary for the dashboard."""
    closed = (await db.execute(
        select(BotPosition).where(
            BotPosition.user_id == user_id,
            BotPosition.is_open == False,  # noqa: E712
        ).order_by(BotPosition.closed_at.desc())
    )).scalars().all()

    open_pos = (await db.execute(
        select(BotPosition).where(
            BotPosition.user_id == user_id,
            BotPosition.is_open == True,  # noqa: E712
        )
    )).scalars().all()

    total_pnl = sum(p.pnl_usd or 0.0 for p in closed)
    wins = [p for p in closed if (p.pnl_usd or 0) > 0]
    losses = [p for p in closed if (p.pnl_usd or 0) <= 0]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0

    deployed = sum(p.size_usd for p in open_pos)
    deployed_pct = round(deployed / config.portfolio_value * 100, 1) if config.portfolio_value > 0 else 0.0

    best = max(closed, key=lambda p: p.pnl_usd or 0.0, default=None)
    worst = min(closed, key=lambda p: p.pnl_usd or 0.0, default=None)

    avg_hold_hours = None
    hold_times = [
        (p.closed_at - p.opened_at).total_seconds() / 3600
        for p in closed
        if p.closed_at and p.opened_at
    ]
    if hold_times:
        avg_hold_hours = round(sum(hold_times) / len(hold_times), 1)

    return {
        "total_pnl_usd": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / config.portfolio_value * 100, 2) if config.portfolio_value else 0,
        "win_rate_pct": win_rate,
        "total_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "open_positions": len(open_pos),
        "deployed_usd": round(deployed, 2),
        "deployed_pct": deployed_pct,
        "avg_hold_hours": avg_hold_hours,
        "best_trade_usd": round(best.pnl_usd or 0, 2) if best else None,
        "worst_trade_usd": round(worst.pnl_usd or 0, 2) if worst else None,
    }
