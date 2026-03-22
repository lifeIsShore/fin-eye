"""
app/api/v1/endpoints/allocation.py  — Sprint 27

AI Portfolio Allocation Engine

POST /api/v1/allocation/suggest
  Takes a list of symbols + total capital, fetches their current GAS snapshot
  and signal grade, and returns grade-weighted position sizes with risk caps.

GET  /api/v1/allocation/grade-history/{symbol}
  Returns the last N grade change events for a symbol from signal_grade_history.
  Used by the grade sparkline on watchlist cards and the explore leaderboard.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.signal_grade_history import SignalGradeHistory
from app.services.gas_precompute import get_snapshot_cached

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Grade → max allocation % ──────────────────────────────────────────────────

GRADE_MAX_PCT: dict[str, float] = {
    "A+": 20.0,
    "A":  15.0,
    "B":  10.0,
    "C":   5.0,   # monitoring only
    "D":   0.0,
    "F":   0.0,
}

GRADE_ORDER = ["A+", "A", "B", "C", "D", "F"]


def grade_rank(grade: str) -> int:
    try:
        return GRADE_ORDER.index(grade)
    except ValueError:
        return len(GRADE_ORDER)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AllocationRequest(BaseModel):
    symbols:       list[str] = Field(..., min_length=1, max_length=30)
    total_capital: float     = Field(..., gt=0, description="Total capital in USD")
    min_grade:     str       = Field(default="B", description="Minimum grade to include (A+/A/B/C)")


class PositionSuggestion(BaseModel):
    symbol:          str
    grade:           str
    grade_score:     int | None
    gas_score:       float
    tradeable:       bool
    weight_pct:      float   # % of total capital
    position_usd:    float   # USD amount
    included:        bool    # False = excluded by min_grade filter
    exclusion_reason: str | None


class AllocationResponse(BaseModel):
    total_capital:       float
    min_grade:           str
    positions:           list[PositionSuggestion]
    total_allocated_pct: float
    cash_pct:            float
    cash_usd:            float
    included_count:      int
    excluded_count:      int
    disclaimer:          str


class GradeHistoryPoint(BaseModel):
    recorded_at:     str
    grade:           str
    prev_grade:      str | None
    grade_score:     int | None
    gas_score:       float
    component_scores: dict | None
    tradeable:       str | None


class GradeHistoryResponse(BaseModel):
    symbol:  str
    history: list[GradeHistoryPoint]
    total:   int


# ── Allocation endpoint ───────────────────────────────────────────────────────

@router.post(
    "/suggest",
    response_model=AllocationResponse,
    summary="AI grade-weighted portfolio allocation suggestion",
)
async def suggest_allocation(
    body: AllocationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Fetches the current GAS snapshot + signal grade for each symbol, then
    proposes grade-weighted position sizes subject to per-position caps.

    Algorithm:
    1. Fetch grade for each symbol (from cache → DB → live compute fallback)
    2. Exclude symbols below min_grade or with grade D/F (no allocation)
    3. For included symbols, compute a raw weight proportional to grade cap
    4. Normalise weights so total ≤ 100% (cash remainder kept)
    5. Apply per-position cap from GRADE_MAX_PCT
    """
    symbols = [s.strip().upper() for s in body.symbols if s.strip()]
    min_grade_rank = grade_rank(body.min_grade)

    positions: list[PositionSuggestion] = []

    for sym in symbols:
        try:
            snap = await get_snapshot_cached(sym, db)
        except Exception as exc:
            logger.warning("Snapshot fetch failed for %s: %s", sym, exc)
            snap = None

        if snap is None:
            positions.append(PositionSuggestion(
                symbol=sym, grade="F", grade_score=None, gas_score=50.0,
                tradeable=False, weight_pct=0.0, position_usd=0.0,
                included=False, exclusion_reason="No GAS snapshot available",
            ))
            continue

        grade       = snap.get("signal_grade") or "F"
        grade_score = snap.get("signal_grade_score")
        gas_score   = float(snap.get("gas_score", 50.0))
        tradeable   = bool(snap.get("signal_tradeable", False))
        sym_rank    = grade_rank(grade)

        # Exclude if below min_grade or grade is D/F
        if sym_rank > min_grade_rank or grade in ("D", "F"):
            reason = (
                f"Grade {grade} is below minimum {body.min_grade}"
                if sym_rank > min_grade_rank
                else f"Grade {grade} — no allocation (D/F excluded)"
            )
            positions.append(PositionSuggestion(
                symbol=sym, grade=grade, grade_score=grade_score,
                gas_score=gas_score, tradeable=tradeable,
                weight_pct=0.0, position_usd=0.0,
                included=False, exclusion_reason=reason,
            ))
            continue

        positions.append(PositionSuggestion(
            symbol=sym, grade=grade, grade_score=grade_score,
            gas_score=gas_score, tradeable=tradeable,
            weight_pct=GRADE_MAX_PCT.get(grade, 0.0),  # raw cap, normalised below
            position_usd=0.0,
            included=True, exclusion_reason=None,
        ))

    # Normalise included positions so total ≤ 100%
    included = [p for p in positions if p.included]
    total_raw_pct = sum(p.weight_pct for p in included)

    if total_raw_pct > 0:
        # If raw total > 100, scale down proportionally
        scale = min(1.0, 100.0 / total_raw_pct)
        for p in included:
            p.weight_pct = round(p.weight_pct * scale, 2)
            p.position_usd = round(body.total_capital * p.weight_pct / 100.0, 2)

    total_allocated_pct = round(sum(p.weight_pct for p in included), 2)
    cash_pct  = round(100.0 - total_allocated_pct, 2)
    cash_usd  = round(body.total_capital * cash_pct / 100.0, 2)

    return AllocationResponse(
        total_capital=body.total_capital,
        min_grade=body.min_grade,
        positions=positions,
        total_allocated_pct=total_allocated_pct,
        cash_pct=cash_pct,
        cash_usd=cash_usd,
        included_count=len(included),
        excluded_count=len(positions) - len(included),
        disclaimer=(
            "This is an educational grade-weighted allocation model, not investment advice. "
            "Grades are derived from historical data and ML signals. "
            "Always consult a qualified financial professional before making investment decisions."
        ),
    )


# ── AI allocation explainer (Sprint 32) ──────────────────────────────────────────

class AllocationExplainRequest(BaseModel):
    positions: list[PositionSuggestion]
    total_capital: float
    min_grade: str
    cash_pct: float


@router.post(
    "/explain",
    summary="Stream an LLM plain-English explanation of the allocation (Sprint 32)",
)
async def explain_allocation(
    body: AllocationExplainRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """
    Receives the allocation result and streams a concise LLM-generated
    explanation of why each position is sized the way it is.

    Falls back to a static pre-built explanation if Ollama is unavailable.
    """
    import json as _json  # noqa: PLC0415
    from fastapi.responses import StreamingResponse  # noqa: PLC0415
    from app.services.llm_service import get_ollama_service  # noqa: PLC0415

    included = [p for p in body.positions if p.included]
    excluded = [p for p in body.positions if not p.included]

    # Build a structured prompt describing the allocation
    position_lines = "\n".join(
        f"  - {p.symbol}: Grade {p.grade} (GAS {p.gas_score:.0f}) → {p.weight_pct:.1f}% = ${p.position_usd:,.0f}"
        for p in sorted(included, key=lambda x: -x.weight_pct)
    ) or "  (none — all excluded)"

    excluded_lines = ", ".join(
        f"{p.symbol} ({p.grade}: {p.exclusion_reason})"
        for p in excluded
    ) or "none"

    system_prompt = (
        "You are a senior quantitative portfolio manager. "
        "Be concise, direct, and data-driven. "
        "Write 3–5 sentences of plain English. No bullet points. No headers. "
        "Always include a one-sentence risk disclaimer at the end."
    )

    user_prompt = (
        f"Explain the following grade-weighted portfolio allocation to a retail investor.\n\n"
        f"Total Capital: ${body.total_capital:,.0f}\n"
        f"Minimum Grade Filter: {body.min_grade}\n"
        f"Cash Reserve: {body.cash_pct:.1f}%\n\n"
        f"Included Positions:\n{position_lines}\n\n"
        f"Excluded (below grade threshold): {excluded_lines}\n\n"
        "Grade scale: A+ = exceptional (20% cap), A = strong (15%), "
        "B = good (10%), C = monitor-only (5%), D/F = no allocation.\n"
        "GAS (Global Alignment Score): 0-100 composite of Technical ML + Sentiment + Macro.\n\n"
        "Write a 3-5 sentence plain-English explanation of why this portfolio is "
        "weighted this way. Mention the top 1-2 positions by name and explain their grade. "
        "Note the cash reserve if it is above 20%. End with a risk disclaimer."
    )

    async def _stream() -> Any:
        ollama_svc = get_ollama_service()
        ollama_alive = await ollama_svc.is_available()

        full_text = ""
        if ollama_alive:
            try:
                async for token in ollama_svc.generate_stream(system_prompt, user_prompt):
                    full_text += token
                    yield f"data: {_json.dumps({'type': 'token', 'text': token})}\n\n"
            except Exception as exc:
                logger.warning("Ollama allocation explain failed: %s", exc)
                ollama_alive = False

        # Static fallback when Ollama is unavailable
        if not ollama_alive or not full_text.strip():
            # Build a deterministic fallback explanation from the data
            if included:
                top = sorted(included, key=lambda x: -x.weight_pct)[:2]
                top_str = " and ".join(
                    f"{p.symbol} ({p.grade}, GAS {p.gas_score:.0f}, {p.weight_pct:.1f}%)"
                    for p in top
                )
                fallback = (
                    f"This allocation deploys {100 - body.cash_pct:.0f}% of "
                    f"${body.total_capital:,.0f} across {len(included)} position"
                    f"{'s' if len(included) != 1 else ''}, "
                    f"led by {top_str}. "
                    f"Positions are sized by signal grade — higher grades receive larger "
                    f"allocations up to their cap (A+=20%, A=15%, B=10%, C=5%). "
                    f"{f'{body.cash_pct:.0f}% is held in cash' if body.cash_pct >= 20 else 'The remaining cash serves as a liquidity buffer'}. "
                    f"{len(excluded)} symbol{'s were' if len(excluded) != 1 else ' was'} excluded for failing the {body.min_grade}+ grade threshold. "
                    "This is an educational model, not investment advice."
                )
            else:
                fallback = (
                    f"No positions passed the {body.min_grade}+ grade threshold. "
                    "All capital is held in cash. Consider lowering the minimum grade or "
                    "running a fresh GAS precompute to update signal grades. "
                    "This is an educational model, not investment advice."
                )
            for word in fallback.split():
                yield f"data: {_json.dumps({'type': 'token', 'text': word + ' '})}\n\n"

        yield f'data: {{"type": "done"}}\n\n'

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Grade history endpoint ────────────────────────────────────────────────────

@router.get(
    "/grade-history/{symbol}",
    response_model=GradeHistoryResponse,
    summary="Grade change history for a symbol",
)
async def get_grade_history(
    symbol: str,
    limit: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Returns the last `limit` grade change events for a symbol.
    Used to render the 7-day grade sparkline on watchlist cards.
    No auth required — grade history is public read-only data.
    """
    sym = symbol.upper()

    result = await db.execute(
        select(SignalGradeHistory)
        .where(SignalGradeHistory.symbol == sym)
        .order_by(SignalGradeHistory.recorded_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    history = [
        GradeHistoryPoint(
            recorded_at=row.recorded_at.isoformat(),
            grade=row.grade,
            prev_grade=row.prev_grade,
            grade_score=row.grade_score,
            gas_score=row.gas_score,
            component_scores=row.component_scores,
            tradeable=row.tradeable,
        )
        for row in rows
    ]

    return GradeHistoryResponse(symbol=sym, history=history, total=len(history))
