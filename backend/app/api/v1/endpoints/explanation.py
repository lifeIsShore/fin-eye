"""
MVP-EXPL-01: "Why Is This Moving?" explanation panel
MVP-EXPL-02: Conflict Detector between layers

GET  /api/v1/explanation/{symbol}/summary
POST /api/v1/explanation/{symbol}/generate-ai  (requires authenticated user)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
import redis.asyncio as redis

from app.services.llm_service import get_ollama_service
from app.api.v1.deps import get_current_user  # BUG-FIX-3: auth guard
from app.db.redis_client import get_redis

router = APIRouter()


# ─── Response Models ────────────────────────────────────────────────────────


class LayerSummary(BaseModel):
    score: float
    direction: str
    detail: str


class ConflictItem(BaseModel):
    layers: str
    magnitude: str
    message: str


class ExplanationResponse(BaseModel):
    symbol: str
    gas_score: float
    gas_label: str
    why_moving: list[str]
    disclaimer: str
    has_conflict: bool
    conflicts: list[ConflictItem]
    conflict_summary: str
    ai_summary: Optional[str] = None


class GenerateAIRequest(BaseModel):
    tech_score: float = 50.0
    sent_30d: Optional[float] = None
    macro_score: float = 50.0
    gas_score: float = 50.0
    ml_output: Optional[str] = None


class GenerateAIResponse(BaseModel):
    symbol: str
    ai_summary: str
    cached: bool


# ─── Helpers ────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "This is educational analysis, not investment advice. "
    "Fin-Eye surfaces data-driven signals to inform your thinking — "
    "always conduct your own research before making any financial decisions."
)


def _direction_label(score: float) -> str:
    if score >= 65:
        return "Bullish"
    if score <= 35:
        return "Bearish"
    return "Neutral"


def _gas_label(gas: float) -> str:
    if gas >= 80:
        return "Strong Tailwind"
    if gas >= 60:
        return "Mild Support"
    if gas >= 40:
        return "Mixed Signals"
    if gas >= 20:
        return "Headwind"
    return "High Instability"


def _build_why_bullets(
    tech_score: float,
    tech_signals: list[dict],
    sent_30d: Optional[float],
    macro_score: float,
    macro_label: str,
) -> list[str]:
    bullets: list[str] = []

    bullish_tfs = [s for s in tech_signals if s.get("direction") == "Bullish"]
    bearish_tfs = [s for s in tech_signals if s.get("direction") == "Bearish"]
    tf_count    = len(tech_signals)
    tech_dir    = _direction_label(tech_score)

    if tf_count > 0:
        bullets.append(
            f"📈 Technical momentum is {tech_dir.lower()} — "
            f"{len(bullish_tfs)} of {tf_count} timeframes bullish, "
            f"{len(bearish_tfs)} bearish (confidence score: {tech_score:.0f}/100)."
        )
    else:
        bullets.append(
            "📈 Technical models have not been trained for this symbol yet; "
            "technical signals are unavailable."
        )

    if sent_30d is not None:
        sent_label = (
            "strongly positive"  if sent_30d >  0.3  else
            "mildly positive"    if sent_30d >  0.05 else
            "neutral"            if sent_30d > -0.05 else
            "mildly negative"    if sent_30d > -0.3  else
            "strongly negative"
        )
        bullets.append(
            f"📰 News sentiment over the past 30 days is {sent_label} "
            f"(score: {sent_30d:+.2f} on a –1 to +1 scale)."
        )
    else:
        bullets.append(
            "📰 News sentiment data is not available for this symbol currently."
        )

    macro_comment = (
        "This provides a supportive environment for equities." if macro_score >= 60
        else "Macro conditions add headwinds to risk assets."  if macro_score < 40
        else "Macro conditions are broadly neutral."
    )
    bullets.append(
        f"🌐 Macro backdrop is '{macro_label}' (score: {macro_score:.0f}/100). {macro_comment}"
    )

    return bullets


def _detect_conflicts(
    tech_score: float,
    sent_score_0_100: float,
    macro_score: float,
    tech_signals: list[dict],
    tf_agreement_threshold: float = 0.4,
) -> tuple[bool, list[ConflictItem]]:
    conflicts: list[ConflictItem] = []

    scores = {
        "Technical": tech_score,
        "Sentiment": sent_score_0_100,
        "Macro":     macro_score,
    }
    for a, b in [("Technical", "Sentiment"), ("Technical", "Macro"), ("Sentiment", "Macro")]:
        sa, sb = scores[a], scores[b]
        if (sa > 65 and sb < 35) or (sb > 65 and sa < 35):
            conflicts.append(
                ConflictItem(
                    layers=f"{a} vs {b}",
                    magnitude=f"{abs(sa - sb):.0f} points apart ({sa:.0f} vs {sb:.0f})",
                    message=(
                        f"{a} is {_direction_label(sa).lower()} while {b} is "
                        f"{_direction_label(sb).lower()}. "
                        "This divergence suggests elevated uncertainty — exercise extra caution."
                    ),
                )
            )

    if tech_signals:
        bullish_count = sum(1 for s in tech_signals if s.get("direction") == "Bullish")
        bearish_count = sum(1 for s in tech_signals if s.get("direction") == "Bearish")
        total         = len(tech_signals)
        dominant      = max(bullish_count, bearish_count)
        agreement     = dominant / total if total > 0 else 1.0
        if agreement < tf_agreement_threshold:
            conflicts.append(
                ConflictItem(
                    layers="Timeframe Agreement",
                    magnitude=f"{agreement * 100:.0f}% agreement across {total} timeframes",
                    message=(
                        f"Only {dominant} of {total} timeframes agree on direction. "
                        "Low cross-timeframe consensus increases signal uncertainty."
                    ),
                )
            )

    return len(conflicts) > 0, conflicts


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/{symbol}/summary", response_model=ExplanationResponse)
async def get_explanation_summary(
    symbol: str,
    tech_score: float = 50.0,
    sent_30d: Optional[float] = None,
    macro_score: float = 50.0,
    macro_label: str = "Neutral",
    gas_score: float = 50.0,
    tech_signals: str = "",
    redis_client: redis.Redis = Depends(get_redis),
) -> ExplanationResponse:
    """
    Stateless EXPL-01/02 computation from query-param scores.
    No auth required — the data returned is purely derived from the inputs,
    with no sensitive user data involved.
    """
    import json

    sym = symbol.upper()

    signals: list[dict] = []
    if tech_signals:
        try:
            signals = json.loads(tech_signals)
        except Exception:
            signals = []

    sent_normalised = ((sent_30d + 1) / 2) * 100 if sent_30d is not None else 50.0

    why_bullets = _build_why_bullets(
        tech_score=tech_score,
        tech_signals=signals,
        sent_30d=sent_30d,
        macro_score=macro_score,
        macro_label=macro_label,
    )

    has_conflict, conflicts = _detect_conflicts(
        tech_score=tech_score,
        sent_score_0_100=sent_normalised,
        macro_score=macro_score,
        tech_signals=signals,
    )

    conflict_summary = (
        "No major conflicts detected — layers are broadly aligned."
        if not has_conflict
        else f"{len(conflicts)} conflict(s) detected. Review the signals below carefully."
    )

    today_str   = date.today().isoformat()
    cache_key   = f"ai_summary:{sym}:{today_str}"
    cached_summary: Optional[str] = None
    try:
        cached_summary = await redis_client.get(cache_key)
    except Exception:
        pass

    return ExplanationResponse(
        symbol=sym,
        gas_score=round(gas_score, 1),
        gas_label=_gas_label(gas_score),
        why_moving=why_bullets,
        disclaimer=DISCLAIMER,
        has_conflict=has_conflict,
        conflicts=conflicts,
        conflict_summary=conflict_summary,
        ai_summary=cached_summary,
    )


@router.post("/{symbol}/generate-ai", response_model=GenerateAIResponse)
async def generate_ai_summary(
    symbol: str,
    request: GenerateAIRequest,
    redis_client: redis.Redis = Depends(get_redis),
    # BUG-FIX-3: Require a logged-in user so anonymous callers cannot spam
    # the local Ollama instance.  The endpoint is effectively rate-limited
    # to the authenticated user pool.
    _current_user: object = Depends(get_current_user),
) -> GenerateAIResponse:
    """
    On-demand AI summary generation via Ollama.
    Requires authentication to prevent anonymous abuse of the LLM endpoint.
    Checks Redis cache first (24-hour TTL per symbol per day).
    """
    sym       = symbol.upper()
    today_str = date.today().isoformat()
    cache_key = f"ai_summary:{sym}:{today_str}"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return GenerateAIResponse(symbol=sym, ai_summary=cached, cached=True)
    except Exception:
        pass

    summary = await get_ollama_service().get_explanation(
        symbol=sym,
        tech_score=request.tech_score,
        sent_score=request.sent_30d,
        macro_score=request.macro_score,
        gas_score=request.gas_score,
        ml_output=request.ml_output,
    )

    if not summary:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI summary unavailable — Ollama is not running or returned no response. "
                "Start Ollama with: ollama serve"
            ),
        )

    try:
        await redis_client.setex(cache_key, 86400, summary)
    except Exception:
        pass  # Cache failure must never break the response

    return GenerateAIResponse(symbol=sym, ai_summary=summary, cached=False)
