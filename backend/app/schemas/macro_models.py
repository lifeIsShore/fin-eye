"""
app/schemas/macro_models.py
Typed response schemas for all macro endpoints.

Designed so the frontend gets a single, well-shaped contract rather than
loose Dict[str, Any] — this surfaces type errors at the boundary early.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Shared primitives ────────────────────────────────────────────────────────

class IndicatorPoint(BaseModel):
    """A single dated observation for one indicator."""
    date: str
    value: float


class IndicatorLatest(BaseModel):
    """Latest value + metadata for one indicator."""
    value: Optional[float] = None
    date: Optional[str] = None
    interpretation: str


# ─── Core macro dashboard (MVP — kept backward-compatible) ────────────────────

class MacroScoreDto(BaseModel):
    score: float = Field(..., ge=0, le=100)
    label: str  # "Supportive" | "Neutral" | "Stressed"


class MacroLatestResponse(BaseModel):
    """Response for GET /macro/latest — backward-compatible with existing frontend."""
    data: dict[str, IndicatorLatest]
    macro_score: Optional[MacroScoreDto] = None
    # Sprint 10 (UX-TRUST-01): ISO UTC timestamp injected by the endpoint so the
    # frontend FreshnessIndicator can show how stale macro data is.
    fetched_at: Optional[str] = None


# ─── Yield curve ─────────────────────────────────────────────────────────────

class YieldCurvePoint(BaseModel):
    """One tenor's yield (% annualised)."""
    tenor: str           # "2Y", "5Y", "10Y", "30Y"
    tenor_years: int     # 2, 5, 10, 30
    yield_pct: Optional[float] = None
    date: Optional[str] = None


class YieldCurveDto(BaseModel):
    points: List[YieldCurvePoint]
    shape: str           # "Normal" | "Flat" | "Inverted" | "Humped" | "Unavailable"
    shape_description: str
    spread_10y_2y: Optional[float] = None   # key inversion signal
    spread_30y_2y: Optional[float] = None   # longer-term steepness


# ─── Recession probability ───────────────────────────────────────────────────

class RecessionDto(BaseModel):
    """
    Simple recession risk gauge derived from the NBER USREC indicator,
    the yield-curve spread, and labour-market signals.
    """
    probability_pct: float = Field(..., ge=0, le=100)
    label: str           # "Low" | "Elevated" | "High"
    nber_in_recession: bool
    drivers: List[str]   # human-readable factors driving the estimate


# ─── Macro Stress Index ───────────────────────────────────────────────────────

class StressComponentDto(BaseModel):
    name: str
    contribution: float  # points added / subtracted from the 50-base
    description: str


class MacroStressIndexDto(BaseModel):
    """
    Composite 0–100 index.  Higher = more stress / worse macro environment.
    (Inverse of the base MacroScore — stress rises when score falls.)
    """
    index: float = Field(..., ge=0, le=100)
    label: str           # "Low Stress" | "Moderate" | "Elevated" | "High Stress"
    components: List[StressComponentDto]


# ─── Advanced macro dashboard (P2-MACRO-ADV-01) ──────────────────────────────

class LeadingIndicatorsDto(BaseModel):
    nonfarm_payrolls_latest: Optional[float] = None      # thousands
    nonfarm_payrolls_mom: Optional[float] = None         # MoM change
    industrial_production_latest: Optional[float] = None # index level
    industrial_production_yoy: Optional[float] = None   # % change YoY


class MacroAdvancedResponse(BaseModel):
    """Response for GET /macro/advanced — full advanced view."""
    # Core indicators (also present on /latest for easy access)
    core: MacroLatestResponse

    # New advanced components
    yield_curve: YieldCurveDto
    recession: RecessionDto
    stress_index: MacroStressIndexDto
    leading_indicators: LeadingIndicatorsDto


# ─── History endpoint ─────────────────────────────────────────────────────────

class IndicatorHistoryResponse(BaseModel):
    indicator_name: str
    series: List[IndicatorPoint]
    count: int
