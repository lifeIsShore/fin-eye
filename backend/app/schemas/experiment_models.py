"""
app/schemas/experiment_models.py

Pydantic schemas for CORE-EXPERIMENT-01 A/B experiments.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ─── Variant definition ───────────────────────────────────────────────────────

class VariantDefinition(BaseModel):
    key: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=1, max_length=128)
    weight: int = Field(..., ge=1, le=100, description="Integer percentage weight")


# ─── Experiment CRUD schemas ──────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    key: str = Field(
        ..., min_length=1, max_length=128,
        pattern=r"^[a-z0-9_]+$",
        description="URL-safe identifier, e.g. 'onboarding_flow_v2'",
    )
    name: str = Field(..., min_length=1, max_length=256)
    hypothesis: Optional[str] = None
    variants: list[VariantDefinition] = Field(..., min_length=2)
    traffic_pct: int = Field(default=100, ge=1, le=100)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("variants")
    @classmethod
    def weights_sum_to_100(cls, v: list[VariantDefinition]) -> list[VariantDefinition]:
        total = sum(var.weight for var in v)
        if total != 100:
            raise ValueError(f"Variant weights must sum to 100, got {total}.")
        keys = [var.key for var in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Variant keys must be unique within an experiment.")
        if "control" not in keys:
            raise ValueError("At least one variant must have key 'control'.")
        return v


class ExperimentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    hypothesis: Optional[str] = None
    variants: Optional[list[VariantDefinition]] = None
    traffic_pct: Optional[int] = Field(None, ge=1, le=100)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|running|paused|concluded)$")

    @field_validator("variants")
    @classmethod
    def weights_sum_to_100(cls, v: Optional[list[VariantDefinition]]) -> Optional[list[VariantDefinition]]:
        if v is None:
            return v
        total = sum(var.weight for var in v)
        if total != 100:
            raise ValueError(f"Variant weights must sum to 100, got {total}.")
        return v


class ExperimentResponse(BaseModel):
    id: int
    key: str
    name: str
    hypothesis: Optional[str]
    variants: list[dict[str, Any]]
    traffic_pct: int
    status: str
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─── Assignment schemas ───────────────────────────────────────────────────────

class AssignmentResponse(BaseModel):
    experiment_key: str
    experiment_id: int
    variant_key: str
    variant_name: str
    in_traffic: bool
    assigned_at: datetime


# ─── Results schemas ─────────────────────────────────────────────────────────

class VariantMetric(BaseModel):
    variant_key: str
    variant_name: str
    unique_users: int
    total_events: int
    # Conversion metric — how many users who were assigned this variant
    # also triggered the goal event
    conversions: int
    conversion_rate_pct: float


class ExperimentResults(BaseModel):
    experiment_id: int
    experiment_key: str
    experiment_name: str
    status: str
    goal_event: str       # The analytics event used as conversion goal
    period_days: int
    total_assigned_users: int
    variants: list[VariantMetric]
    winner: Optional[str]   # variant_key of the leader, or None if inconclusive
    note: str               # Human-readable interpretation
