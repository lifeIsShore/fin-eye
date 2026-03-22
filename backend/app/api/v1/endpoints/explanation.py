"""
MVP-EXPL-01: "Why Is This Moving?" explanation panel
MVP-EXPL-02: Conflict Detector between layers
SPRINT-1:    Structured LLM investment manager insight (todos-v5 Phase 3)

GET  /api/v1/explanation/{symbol}/summary
POST /api/v1/explanation/{symbol}/generate-ai      (legacy — flat text, preserved)
POST /api/v1/explanation/{symbol}/generate-insight (new — structured 6-section output)
"""

from __future__ import annotations

import json as _json

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from datetime import date
import redis.asyncio as redis

from app.services.llm_service import (
    get_llm_service,
    get_ollama_service,
    InsightInput,
    MLSignal,
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_llm_response,
)
from app.api.v1.deps import get_current_user
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


# ── New structured insight models (Sprint 1 — todos-v5 Phase 3) ──────────────

class MLSignalInput(BaseModel):
    timeframe: str
    direction: str
    confidence: float
    sharpe: float
    horizon_periods: int = 3
    model_used: str = "unknown"


class GenerateInsightRequest(BaseModel):
    """
    All data the frontend can provide for the structured investment manager insight.
    Only symbol and current_price are required — everything else enhances the output.
    """
    current_price: float = 0.0

    # ML signals per timeframe
    signals: List[MLSignalInput] = []

    # Technical indicators (current values from the last bar)
    rsi_14:        Optional[float] = None
    macd_hist:     Optional[float] = None
    bb_pb:         Optional[float] = None
    atr_pct:       Optional[float] = None
    volume_ratio:  Optional[float] = None
    atr_absolute:  Optional[float] = None  # ATR in price units (for stop/target calc)

    # Macro
    macro_score:   Optional[float] = None
    vix:           Optional[float] = None
    yield_spread:  Optional[float] = None
    macro_regime:  Optional[str]   = None

    # Sentiment
    news_sentiment_1d:  Optional[float] = None
    news_sentiment_7d:  Optional[float] = None
    news_sentiment_30d: Optional[float] = None

    # GAS composite
    gas_score: Optional[float] = None


class InsightSection(BaseModel):
    primary_signal:  str = ""
    entry:           str = ""
    targets:         str = ""
    risk_management: str = ""
    timeframe_split: str = ""
    caution:         str = ""


class GenerateInsightResponse(BaseModel):
    symbol:          str
    sections:        InsightSection
    backend_used:    str   # "ollama" | "groq" | "fallback"
    model_used:      str
    cached:          bool
    error:           Optional[str] = None

    # Pre-computed price targets (so frontend can render the price band)
    expected_price:      Optional[float] = None
    upside_target:       Optional[float] = None
    downside_stop:       Optional[float] = None
    expected_return_pct: Optional[float] = None
    atr_absolute:        Optional[float] = None

    # Consensus summary for the header badge
    agreement_count:    int = 0
    total_timeframes:   int = 0
    dominant_direction: str = "Mixed"


# ─── Helpers ────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "This is educational analysis, not investment advice. "
    "Fin-Eye surfaces data-driven signals to inform your thinking — "
    "always conduct your own research before making any financial decisions."
)


def _direction_label(score: float) -> str:
    if score >= 65: return "Bullish"
    if score <= 35: return "Bearish"
    return "Neutral"


def _gas_label(gas: float) -> str:
    if gas >= 80: return "Strong Tailwind"
    if gas >= 60: return "Mild Support"
    if gas >= 40: return "Mixed Signals"
    if gas >= 20: return "Headwind"
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
    scores = {"Technical": tech_score, "Sentiment": sent_score_0_100, "Macro": macro_score}
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
    No auth required — returned data is purely derived from the inputs.
    """
    import json as _json

    sym = symbol.upper()
    signals: list[dict] = []
    if tech_signals:
        try:
            signals = _json.loads(tech_signals)
        except Exception:
            signals = []

    sent_normalised = ((sent_30d + 1) / 2) * 100 if sent_30d is not None else 50.0
    why_bullets  = _build_why_bullets(tech_score, signals, sent_30d, macro_score, macro_label)
    has_conflict, conflicts = _detect_conflicts(tech_score, sent_normalised, macro_score, signals)
    conflict_summary = (
        "No major conflicts detected — layers are broadly aligned."
        if not has_conflict
        else f"{len(conflicts)} conflict(s) detected. Review the signals below carefully."
    )

    today_str = date.today().isoformat()
    cache_key = f"ai_summary:{sym}:{today_str}"
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
    _current_user: object = Depends(get_current_user),
) -> GenerateAIResponse:
    """
    Legacy endpoint — flat 2-3 sentence AI summary. Preserved for backwards compat.
    New code should call /generate-insight instead.
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
        pass

    return GenerateAIResponse(symbol=sym, ai_summary=summary, cached=False)


@router.post("/{symbol}/generate-insight", response_model=GenerateInsightResponse)
async def generate_structured_insight(
    symbol: str,
    request: GenerateInsightRequest,
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: object = Depends(get_current_user),
) -> GenerateInsightResponse:
    """
    Sprint 1 — todos-v5 Phase 3.
    Structured investment manager insight with 6 sections.
    Uses Ollama (primary) → Groq (fallback) → static fallback.
    Redis-cached per symbol per day (key includes dominant direction for cache busting
    if direction flips).
    """
    sym     = symbol.upper()
    service = get_llm_service()

    # ── Build consensus metadata ──────────────────────────────────────────────
    bullish_count = sum(1 for s in request.signals if s.direction == "Bullish")
    bearish_count = sum(1 for s in request.signals if s.direction == "Bearish")
    total_tfs     = len(request.signals)
    agree_count   = max(bullish_count, bearish_count)
    dominant_dir  = (
        "Bullish" if bullish_count > bearish_count else
        "Bearish" if bearish_count > bullish_count else
        "Mixed"
    )

    # ── Pre-compute price targets ─────────────────────────────────────────────
    targets: dict = {}
    if request.current_price > 0 and request.atr_absolute and request.atr_absolute > 0:
        # Use confidence-weighted average expected return from the signals
        expected_return = 0.0
        if request.signals:
            total_w, weighted_ret = 0.0, 0.0
            for s in request.signals:
                w   = max(s.sharpe, 0.1)
                ret = (s.confidence / 100.0 - 0.5) * 0.06  # maps 50% → 0%, 100% → +3%
                if s.direction == "Bearish":
                    ret = -abs(ret)
                weighted_ret += ret * w
                total_w      += w
            expected_return = weighted_ret / total_w if total_w else 0.0

        targets = service.compute_price_targets(
            current_price=request.current_price,
            expected_return=expected_return,
            atr_absolute=request.atr_absolute,
            confidence=agree_count / total_tfs if total_tfs else 0.5,
        )

    # ── Redis cache — per symbol + dominant direction + day ───────────────────
    today_str = date.today().isoformat()
    cache_key = f"insight_v2:{sym}:{dominant_dir}:{today_str}"
    try:
        import json as _json
        cached_raw = await redis_client.get(cache_key)
        if cached_raw:
            cached_data = _json.loads(cached_raw)
            return GenerateInsightResponse(
                symbol=sym,
                sections=InsightSection(**cached_data["sections"]),
                backend_used=cached_data.get("backend_used", "cache"),
                model_used=cached_data.get("model_used", "cached"),
                cached=True,
                error=None,
                agreement_count=agree_count,
                total_timeframes=total_tfs,
                dominant_direction=dominant_dir,
                **{k: targets.get(k) for k in
                   ["expected_price", "upside_target", "downside_stop",
                    "expected_return_pct", "atr_absolute"] if k in targets},
            )
    except Exception:
        pass

    # ── Build InsightInput ────────────────────────────────────────────────────
    ml_signals = [
        MLSignal(
            timeframe=s.timeframe,
            direction=s.direction,
            confidence=s.confidence,
            sharpe=s.sharpe,
            horizon_periods=s.horizon_periods,
            model_used=s.model_used,
        )
        for s in request.signals
    ]

    inp = InsightInput(
        symbol=sym,
        current_price=request.current_price,
        signals=ml_signals,
        agreement_count=agree_count,
        total_timeframes=total_tfs,
        dominant_direction=dominant_dir,
        rsi_14=request.rsi_14,
        macd_hist=request.macd_hist,
        bb_pb=request.bb_pb,
        atr_pct=request.atr_pct,
        volume_ratio=request.volume_ratio,
        macro_score=request.macro_score,
        vix=request.vix,
        yield_spread=request.yield_spread,
        macro_regime=request.macro_regime,
        news_sentiment_1d=request.news_sentiment_1d,
        news_sentiment_7d=request.news_sentiment_7d,
        news_sentiment_30d=request.news_sentiment_30d,
        gas_score=request.gas_score,
        expected_price=targets.get("expected_price"),
        upside_target=targets.get("upside_target"),
        downside_stop=targets.get("downside_stop"),
        expected_return_pct=targets.get("expected_return_pct"),
        atr_absolute=request.atr_absolute,
    )

    # ── Call LLM ──────────────────────────────────────────────────────────────
    out = await service.generate_investment_insight(inp)

    sections = InsightSection(
        primary_signal=out.primary_signal,
        entry=out.entry,
        targets=out.targets,
        risk_management=out.risk_management,
        timeframe_split=out.timeframe_split,
        caution=out.caution,
    )

    # ── Cache the result ──────────────────────────────────────────────────────
    if not out.error:
        try:
            import json as _json
            cache_payload = _json.dumps({
                "sections":     sections.model_dump(),
                "backend_used": out.backend_used,
                "model_used":   out.model_used,
            })
            await redis_client.setex(cache_key, 43200, cache_payload)  # 12h TTL
        except Exception:
            pass

    return GenerateInsightResponse(
        symbol=sym,
        sections=sections,
        backend_used=out.backend_used,
        model_used=out.model_used,
        cached=False,
        error=out.error if out.error else None,
        agreement_count=agree_count,
        total_timeframes=total_tfs,
        dominant_direction=dominant_dir,
        expected_price=targets.get("expected_price"),
        upside_target=targets.get("upside_target"),
        downside_stop=targets.get("downside_stop"),
        expected_return_pct=targets.get("expected_return_pct"),
        atr_absolute=targets.get("atr_absolute"),
    )


# ─── Daily Market Brief (Sprint 16) ─────────────────────────────────────────

class DailyBriefRequest(BaseModel):
    macro_score:     float = 50.0
    macro_label:     str   = "Neutral"
    regime:          str   = "unknown"
    sentiment_score: float = 0.0
    gas_score:       float = 50.0


@router.post("/daily-brief/generate-stream")
async def generate_daily_brief_stream(
    request: DailyBriefRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: object = Depends(get_current_user),
) -> StreamingResponse:
    """
    Sprint 16 — SSE-streaming daily market brief.
    Generates a 3-4 paragraph plain-text summary of the current macro/sentiment/regime
    environment. Cached in Redis for 4 hours (key = date + macro_label + regime).
    """
    import datetime as _dt
    hour_block = _dt.datetime.utcnow().hour // 4   # 0-5, changes every 4h
    cache_key  = f"daily_brief:{request.macro_label}:{request.regime}:{hour_block}"

    # Check cache — return pre-generated brief as plain-text SSE
    try:
        cached_brief = await redis_client.get(cache_key)
        if cached_brief:
            async def _cached() -> AsyncGenerator[str, None]:
                # Stream cached text word-by-word for a nicer UX
                words = cached_brief.split()
                chunk: list[str] = []
                for word in words:
                    chunk.append(word)
                    if len(chunk) >= 4:
                        payload = _json.dumps({"token": " ".join(chunk) + " "})
                        yield f"data: {payload}\n\n"
                        chunk = []
                        import asyncio
                        await asyncio.sleep(0.015)
                if chunk:
                    yield f"data: {_json.dumps({'token': ' '.join(chunk)})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(
                _cached(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
    except Exception:
        pass

    # Build the brief prompt
    sent_label = (
        "bullish"        if request.sentiment_score >  0.3  else
        "mildly bullish" if request.sentiment_score >  0.05 else
        "neutral"        if request.sentiment_score > -0.05 else
        "mildly bearish" if request.sentiment_score > -0.3  else
        "bearish"
    )
    regime_clean = request.regime.replace("_", " ")
    gas_desc = (
        "strong tailwind"   if request.gas_score >= 75 else
        "mild support"      if request.gas_score >= 60 else
        "mixed signals"     if request.gas_score >= 40 else
        "headwind"          if request.gas_score >= 25 else
        "high instability"
    )

    system_prompt = (
        "You are a concise, professional market analyst writing a daily market brief "
        "for a financial intelligence platform. Write in 3 clear paragraphs covering: "
        "(1) the macro environment and what it means for markets, "
        "(2) the current sentiment and technical regime, "
        "(3) key risks and opportunities. "
        "Be factual, balanced, and educational. Do NOT give specific buy/sell advice. "
        "Never use markdown, headers, or bullet points — only plain prose."
    )
    user_prompt = (
        f"Today's market data: "
        f"Macro regime is '{request.macro_label}' with a composite score of {request.macro_score:.0f}/100. "
        f"The current market regime classifier shows '{regime_clean}'. "
        f"News sentiment across covered securities is {sent_label} (score: {request.sentiment_score:+.2f}). "
        f"The Global Alignment Score (GAS) — a composite of technical, sentiment and macro signals — is {request.gas_score:.0f}/100, "
        f"indicating {gas_desc}. "
        f"Write the daily brief now."
    )

    ollama_svc = get_ollama_service()
    ollama_alive = await ollama_svc.is_available()

    async def _stream_brief() -> AsyncGenerator[str, None]:
        accumulated = ""
        if ollama_alive:
            async for token in ollama_svc.generate_stream(system_prompt, user_prompt):
                if await req.is_disconnected():
                    return
                accumulated += token
                yield f"data: {_json.dumps({'token': token})}\n\n"
        else:
            # Fallback static brief when Ollama is offline
            fallback = (
                f"The macro environment is currently characterised as '{request.macro_label}' with a composite "
                f"score of {request.macro_score:.0f} out of 100. "
                f"This suggests {'a broadly supportive backdrop for risk assets' if request.macro_score >= 60 else 'meaningful headwinds for equities and risk assets' if request.macro_score < 40 else 'a mixed and cautious environment'}. "
                f"Investors should monitor Federal Reserve guidance, credit spreads, and yield curve dynamics closely.\n\n"
                f"Market sentiment is currently {sent_label}, reflecting the aggregate FinBERT scoring of recent news flow. "
                f"The regime classifier has flagged a '{regime_clean}' environment, which historically corresponds to "
                f"{'higher momentum persistence and lower mean-reversion opportunity' if 'trending' in request.regime else 'more balanced two-way price action'}.\n\n"
                f"The Global Alignment Score of {request.gas_score:.0f} indicates {gas_desc}, combining technical momentum, "
                f"news sentiment, and the macro composite. "
                f"As always, signals should be treated as educational inputs rather than actionable trade recommendations. "
                f"Conduct independent research and consider your own risk tolerance before making any investment decisions."
            )
            accumulated = fallback
            # Stream word-by-word for consistent UX
            import asyncio
            words = fallback.split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i+5]) + " "
                yield f"data: {_json.dumps({'token': chunk})}\n\n"
                await asyncio.sleep(0.02)

        # Cache the completed brief
        if accumulated.strip():
            try:
                await redis_client.setex(cache_key, 14400, accumulated)  # 4h TTL
            except Exception:
                pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream_brief(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{symbol}/generate-insight-stream")
async def generate_insight_stream(
    symbol: str,
    request: GenerateInsightRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
    _current_user: object = Depends(get_current_user),
) -> StreamingResponse:
    """
    Sprint 12 — SSE streaming version of generate-insight.

    Streams tokens from Ollama token-by-token as Server-Sent Events so the
    frontend can populate sections as the model writes them, eliminating the
    15–30 second blank-screen wait.

    SSE event format:
      data: {"type": "meta",  ...consensus + targets...}   \n\n   (first event)
      data: {"type": "token", "text": "..."}               \n\n   (one per token)
      data: {"type": "done",  "cached": false}             \n\n   (final event)
      data: {"type": "error", "message": "..."}            \n\n   (on failure)

    Falls back to the non-streaming endpoint response if Ollama is unavailable.
    """
    sym = symbol.upper()

    # ── Consensus + price target pre-computation (identical to non-stream endpoint) ——
    service = get_llm_service()
    bullish_count = sum(1 for s in request.signals if s.direction == "Bullish")
    bearish_count = sum(1 for s in request.signals if s.direction == "Bearish")
    total_tfs     = len(request.signals)
    agree_count   = max(bullish_count, bearish_count)
    dominant_dir  = (
        "Bullish" if bullish_count > bearish_count else
        "Bearish" if bearish_count > bullish_count else "Mixed"
    )

    targets: dict = {}
    if request.current_price > 0 and request.atr_absolute and request.atr_absolute > 0:
        expected_return = 0.0
        if request.signals:
            total_w, weighted_ret = 0.0, 0.0
            for s in request.signals:
                w   = max(s.sharpe, 0.1)
                ret = (s.confidence / 100.0 - 0.5) * 0.06
                if s.direction == "Bearish":
                    ret = -abs(ret)
                weighted_ret += ret * w
                total_w      += w
            expected_return = weighted_ret / total_w if total_w else 0.0
        targets = service.compute_price_targets(
            current_price=request.current_price,
            expected_return=expected_return,
            atr_absolute=request.atr_absolute,
            confidence=agree_count / total_tfs if total_tfs else 0.5,
        )

    # ── Check Redis cache first — return immediately as a single 'done' event ——
    today_str = date.today().isoformat()
    cache_key = f"insight_v2:{sym}:{dominant_dir}:{today_str}"
    try:
        cached_raw = await redis_client.get(cache_key)
        if cached_raw:
            cached_data = _json.loads(cached_raw)

            async def _cached_stream() -> AsyncGenerator[str, None]:
                meta = _json.dumps({
                    "type": "meta",
                    "agreement_count":    agree_count,
                    "total_timeframes":   total_tfs,
                    "dominant_direction": dominant_dir,
                    "backend_used":       cached_data.get("backend_used", "cache"),
                    "model_used":         cached_data.get("model_used", "cached"),
                    **{k: targets.get(k) for k in
                       ["expected_price", "upside_target", "downside_stop",
                        "expected_return_pct", "atr_absolute"] if k in targets},
                })
                yield f"data: {meta}\n\n"
                # Send full sections as a single content event (cached — no streaming needed)
                sections_payload = _json.dumps({
                    "type":     "sections",
                    "sections": cached_data["sections"],
                })
                yield f"data: {sections_payload}\n\n"
                yield f'data: {{"type": "done", "cached": true}}\n\n'

            return StreamingResponse(
                _cached_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
    except Exception:
        pass

    # ── Build prompt ——
    ml_signals = [
        MLSignal(
            timeframe=s.timeframe, direction=s.direction, confidence=s.confidence,
            sharpe=s.sharpe, horizon_periods=s.horizon_periods, model_used=s.model_used,
        )
        for s in request.signals
    ]
    inp = InsightInput(
        symbol=sym, current_price=request.current_price,
        signals=ml_signals, agreement_count=agree_count,
        total_timeframes=total_tfs, dominant_direction=dominant_dir,
        rsi_14=request.rsi_14, macd_hist=request.macd_hist,
        bb_pb=request.bb_pb, atr_pct=request.atr_pct,
        volume_ratio=request.volume_ratio,
        macro_score=request.macro_score, vix=request.vix,
        yield_spread=request.yield_spread, macro_regime=request.macro_regime,
        news_sentiment_1d=request.news_sentiment_1d,
        news_sentiment_7d=request.news_sentiment_7d,
        news_sentiment_30d=request.news_sentiment_30d,
        gas_score=request.gas_score,
        expected_price=targets.get("expected_price"),
        upside_target=targets.get("upside_target"),
        downside_stop=targets.get("downside_stop"),
        expected_return_pct=targets.get("expected_return_pct"),
        atr_absolute=request.atr_absolute,
    )
    user_prompt = build_user_prompt(inp)

    # ── SSE generator ——
    ollama_svc = get_ollama_service()

    async def _stream_events() -> AsyncGenerator[str, None]:
        # 1 — meta event (consensus, targets, backend)
        meta = _json.dumps({
            "type": "meta",
            "agreement_count":    agree_count,
            "total_timeframes":   total_tfs,
            "dominant_direction": dominant_dir,
            "backend_used":       "ollama",
            "model_used":         ollama_svc.model,
            **{k: targets.get(k) for k in
               ["expected_price", "upside_target", "downside_stop",
                "expected_return_pct", "atr_absolute"] if k in targets},
        })
        yield f"data: {meta}\n\n"

        # 2 — check if client disconnected before we start the expensive call
        if await req.is_disconnected():
            return

        # 3 — stream tokens from Ollama; accumulate full text for caching
        full_text = ""
        ollama_alive = await ollama_svc.is_available()

        if ollama_alive:
            async for token in ollama_svc.generate_stream(SYSTEM_PROMPT, user_prompt):
                if await req.is_disconnected():
                    return
                full_text += token
                yield f"data: {_json.dumps({'type': 'token', 'text': token})}\n\n"

        # 4 — if Ollama was unavailable, fall back to Groq (non-streaming) or static fallback
        if not ollama_alive or not full_text.strip():
            out = await service.generate_investment_insight(inp)
            full_text = out.raw_response
            # Send as a single sections event so the frontend can render immediately
            sections_obj = {
                "primary_signal":  out.primary_signal,
                "entry":           out.entry,
                "targets":         out.targets,
                "risk_management": out.risk_management,
                "timeframe_split": out.timeframe_split,
                "caution":         out.caution,
            }
            sections_payload = _json.dumps({"type": "sections", "sections": sections_obj})
            yield f"data: {sections_payload}\n\n"

            backend_used = out.backend_used
            model_used   = out.model_used
        else:
            backend_used = "ollama"
            model_used   = ollama_svc.model

        # 5 — cache the completed response
        if full_text.strip():
            try:
                parsed = parse_llm_response(full_text, backend_used, model_used)
                cache_payload = _json.dumps({
                    "sections": {
                        "primary_signal":  parsed.primary_signal,
                        "entry":           parsed.entry,
                        "targets":         parsed.targets,
                        "risk_management": parsed.risk_management,
                        "timeframe_split": parsed.timeframe_split,
                        "caution":         parsed.caution,
                    },
                    "backend_used": backend_used,
                    "model_used":   model_used,
                })
                await redis_client.setex(cache_key, 43200, cache_payload)
            except Exception:
                pass

        # 6 — done event
        yield f'data: {{"type": "done", "cached": false}}\n\n'

    return StreamingResponse(
        _stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
