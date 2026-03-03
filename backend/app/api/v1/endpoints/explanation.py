"""
MVP-EXPL-01: "Why Is This Moving?" explanation panel
MVP-EXPL-02: Conflict Detector between layers

GET /api/v1/explanation/{symbol}/summary
Returns:
  - bullet-point explanation of current drivers (EXPL-01)
  - conflict detection between layers (EXPL-02)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ─── Response Models ────────────────────────────────────────────────────────


class LayerSummary(BaseModel):
    score: float  # 0–100
    direction: str  # "Bullish", "Neutral", "Bearish"
    detail: str  # human-readable text


class ConflictItem(BaseModel):
    layers: str  # e.g. "Technicals vs Macro"
    magnitude: str  # e.g. "31 points apart"
    message: str


class ExplanationResponse(BaseModel):
    symbol: str
    gas_score: float
    gas_label: str

    # EXPL-01 – "Why is this stock moving?"
    why_moving: list[str]  # bullet points
    disclaimer: str

    # EXPL-02 – Conflict detector
    has_conflict: bool
    conflicts: list[ConflictItem]
    conflict_summary: str  # "No major conflicts detected." or description


# ─── Helpers ────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "This is educational analysis, not investment advice. "
    "Fin-Eye surfaces data-driven signals to inform your thinking—"
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

    # Technical contribution
    bullish_tfs = [s for s in tech_signals if s.get("direction") == "Bullish"]
    bearish_tfs = [s for s in tech_signals if s.get("direction") == "Bearish"]
    tf_count = len(tech_signals)
    tech_dir = _direction_label(tech_score)

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

    # Sentiment contribution
    if sent_30d is not None:
        sent_label = (
            "strongly positive"
            if sent_30d > 0.3
            else "mildly positive"
            if sent_30d > 0.05
            else "neutral"
            if sent_30d > -0.05
            else "mildly negative"
            if sent_30d > -0.3
            else "strongly negative"
        )
        bullets.append(
            f"📰 News sentiment over the past 30 days is {sent_label} "
            f"(score: {sent_30d:+.2f} on a –1 to +1 scale)."
        )
    else:
        bullets.append(
            "📰 News sentiment data is not available for this symbol currently."
        )

    # Macro contribution
    bullets.append(
        f"🌐 Macro backdrop is '{macro_label}' (score: {macro_score:.0f}/100). "
        f"{'This provides a supportive environment for equities.' if macro_score >= 60 else 'Macro conditions add headwinds to risk assets.' if macro_score < 40 else 'Macro conditions are broadly neutral.'}"
    )

    return bullets


def _detect_conflicts(
    tech_score: float,
    sent_score_0_100: float,
    macro_score: float,
    tech_signals: list[dict],
    conflict_threshold: float = 30.0,
    tf_agreement_threshold: float = 0.4,
) -> tuple[bool, list[ConflictItem]]:
    conflicts: list[ConflictItem] = []

    scores = {
        "Technical": tech_score,
        "Sentiment": sent_score_0_100,
        "Macro": macro_score,
    }

    # Pairwise conflict check between layers
    layer_pairs = [
        ("Technical", "Sentiment"),
        ("Technical", "Macro"),
        ("Sentiment", "Macro"),
    ]
    for a, b in layer_pairs:
        sa, sb = scores[a], scores[b]
        diff = abs(sa - sb)
        # Conflict if one is strongly bullish (>65) and other strongly bearish (<35)
        if (sa > 65 and sb < 35) or (sb > 65 and sa < 35):
            dir_a = _direction_label(sa)
            dir_b = _direction_label(sb)
            conflicts.append(
                ConflictItem(
                    layers=f"{a} vs {b}",
                    magnitude=f"{diff:.0f} points apart ({sa:.0f} vs {sb:.0f})",
                    message=(
                        f"{a} is {dir_a.lower()} while {b} is {dir_b.lower()}. "
                        f"This divergence suggests elevated uncertainty — "
                        f"exercise extra caution."
                    ),
                )
            )

    # Timeframe agreement conflict
    if tech_signals:
        bullish_count = sum(1 for s in tech_signals if s.get("direction") == "Bullish")
        bearish_count = sum(1 for s in tech_signals if s.get("direction") == "Bearish")
        total = len(tech_signals)
        dominant = max(bullish_count, bearish_count)
        agreement = dominant / total if total > 0 else 1.0
        if agreement < tf_agreement_threshold:
            conflicts.append(
                ConflictItem(
                    layers="Timeframe Agreement",
                    magnitude=f"{agreement * 100:.0f}% agreement across {total} timeframes",
                    message=(
                        f"Only {dominant} of {total} timeframes agree on direction. "
                        f"Low cross-timeframe consensus increases signal uncertainty."
                    ),
                )
            )

    return len(conflicts) > 0, conflicts


# ─── Endpoint ───────────────────────────────────────────────────────────────


@router.get("/{symbol}/summary", response_model=ExplanationResponse)
async def get_explanation_summary(
    symbol: str,
    tech_score: float = 50.0,
    sent_30d: Optional[float] = None,
    macro_score: float = 50.0,
    macro_label: str = "Neutral",
    gas_score: float = 50.0,
    tech_signals: str = "",  # JSON-encoded list of {timeframe, direction, confidence}
) -> ExplanationResponse:
    """
    Derives the EXPL-01 'Why is this moving?' explanation and the EXPL-02
    conflict detector from pre-computed layer scores passed as query params.

    The frontend passes the already-fetched tech/sentiment/macro data to this
    endpoint so it acts as a pure computation layer without needing its own DB
    queries. This keeps latency low (no extra round-trips) and the endpoint
    stateless.
    """
    import json

    sym = symbol.upper()

    # Parse tech_signals if provided
    signals: list[dict] = []
    if tech_signals:
        try:
            signals = json.loads(tech_signals)
        except Exception:
            signals = []

    # Normalise sentiment to 0–100
    sent_normalised = ((sent_30d + 1) / 2) * 100 if sent_30d is not None else 50.0

    # EXPL-01 – bullet points
    why_bullets = _build_why_bullets(
        tech_score=tech_score,
        tech_signals=signals,
        sent_30d=sent_30d,
        macro_score=macro_score,
        macro_label=macro_label,
    )

    # EXPL-02 – conflict detection
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

    return ExplanationResponse(
        symbol=sym,
        gas_score=round(gas_score, 1),
        gas_label=_gas_label(gas_score),
        why_moving=why_bullets,
        disclaimer=DISCLAIMER,
        has_conflict=has_conflict,
        conflicts=conflicts,
        conflict_summary=conflict_summary,
    )
