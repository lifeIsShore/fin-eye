"""
app/services/experiment_service.py

A/B Experimentation service layer (CORE-EXPERIMENT-01).

Responsibilities:
  - CRUD for Experiment configs (admin)
  - Deterministic variant assignment for users/anon visitors
  - Result computation from the analytics_events table

Assignment algorithm:
  bucket = int(SHA-256(experiment_key + ":" + identity)[:8], 16) % 100

  where identity = str(user_id) for authenticated users,
                   anon_id for anonymous visitors.

  If bucket >= traffic_pct → user is outside the traffic slice → assigned "control"
    and in_traffic=False.
  Otherwise → walk the variant list in definition order, assigning to the first
    variant whose cumulative weight covers the bucket.

  This is:
    - Deterministic:   same user always gets the same variant
    - Stable:          adding new experiments doesn't change assignments in others
    - Reproducible:    no DB read needed to recompute, but we persist for audit
    - Zero collision:  each experiment uses its own key as salt

Result computation:
  Results are built by joining experiment_assignments with analytics_events
  on (user_id, properties["experiment_key"] == experiment.key).
  We count goal_event occurrences per variant as conversions.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent
from app.models.experiment import Experiment, ExperimentAssignment
from app.schemas.experiment_models import (
    AssignmentResponse,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResults,
    ExperimentUpdate,
    VariantMetric,
)

logger = logging.getLogger(__name__)


# ─── Deterministic assignment ─────────────────────────────────────────────────

def _compute_bucket(experiment_key: str, identity: str) -> int:
    """
    Returns an integer in [0, 99] uniquely and deterministically derived
    from the experiment key and user identity string.
    """
    raw = f"{experiment_key}:{identity}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    # Use first 8 hex chars → max value 0xFFFFFFFF = 4294967295
    return int(digest[:8], 16) % 100


def _pick_variant(variants: list[dict[str, Any]], bucket: int) -> dict[str, Any]:
    """
    Walk variants in order, assigning to the first whose cumulative weight
    covers the bucket value.

    Example: variants=[{weight:50, key:"control"}, {weight:50, key:"treatment"}]
      bucket 0–49  → control
      bucket 50–99 → treatment
    """
    cumulative = 0
    for variant in variants:
        cumulative += variant["weight"]
        if bucket < cumulative:
            return variant
    # Fallback safety — should never reach here if weights sum to 100
    return variants[0]


# ─── Assignment ───────────────────────────────────────────────────────────────

async def get_or_create_assignment(
    db: AsyncSession,
    experiment: Experiment,
    *,
    user_id: Optional[uuid.UUID] = None,
    anon_id: Optional[str] = None,
) -> AssignmentResponse:
    """
    Return the existing assignment for this user+experiment, or create one.
    Idempotent: a second call for the same (experiment, user) returns the same variant.

    Priority: user_id > anon_id. One of the two must be provided.
    """
    if user_id is None and anon_id is None:
        raise ValueError("Either user_id or anon_id must be provided.")

    identity = str(user_id) if user_id else anon_id

    # ── Check for existing assignment ────────────────────────────────────────
    if user_id:
        stmt = select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment.id,
            ExperimentAssignment.user_id == user_id,
        )
    else:
        stmt = select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment.id,
            ExperimentAssignment.anon_id == anon_id,
        )

    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        variant_def = _find_variant(experiment.variants, existing.variant_key)
        return AssignmentResponse(
            experiment_key=experiment.key,
            experiment_id=experiment.id,
            variant_key=existing.variant_key,
            variant_name=variant_def.get("name", existing.variant_key),
            in_traffic=existing.in_traffic,
            assigned_at=existing.assigned_at,
        )

    # ── Compute new assignment ────────────────────────────────────────────────
    bucket = _compute_bucket(experiment.key, identity)
    in_traffic = bucket < experiment.traffic_pct

    if in_traffic:
        # Re-bucket within traffic slice to pick variant proportionally
        traffic_bucket = _compute_bucket(experiment.key + ":variant", identity)
        variant = _pick_variant(experiment.variants, traffic_bucket)
    else:
        # Outside traffic slice — always control, not counted in results
        variant = _find_variant(experiment.variants, "control") or experiment.variants[0]

    assignment = ExperimentAssignment(
        experiment_id=experiment.id,
        user_id=user_id,
        anon_id=anon_id if not user_id else None,
        variant_key=variant["key"],
        in_traffic=in_traffic,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)

    logger.debug(
        "Experiment %s: assigned user=%s anon=%s → variant=%s (bucket=%d, in_traffic=%s)",
        experiment.key, user_id, anon_id, variant["key"], bucket, in_traffic,
    )

    return AssignmentResponse(
        experiment_key=experiment.key,
        experiment_id=experiment.id,
        variant_key=variant["key"],
        variant_name=variant.get("name", variant["key"]),
        in_traffic=in_traffic,
        assigned_at=assignment.assigned_at,
    )


def _find_variant(variants: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for v in variants:
        if v.get("key") == key:
            return v
    return {}


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_experiment(
    db: AsyncSession,
    payload: ExperimentCreate,
) -> Experiment:
    existing = await db.execute(
        select(Experiment).where(Experiment.key == payload.key)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Experiment key '{payload.key}' already exists.")

    exp = Experiment(
        key=payload.key,
        name=payload.name,
        hypothesis=payload.hypothesis,
        variants=[v.model_dump() for v in payload.variants],
        traffic_pct=payload.traffic_pct,
        status="draft",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        notes=payload.notes,
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    logger.info("Created experiment key=%s id=%d", exp.key, exp.id)
    return exp


async def get_experiment_by_key(
    db: AsyncSession,
    key: str,
) -> Optional[Experiment]:
    result = await db.execute(select(Experiment).where(Experiment.key == key))
    return result.scalar_one_or_none()


async def list_experiments(
    db: AsyncSession,
    status: Optional[str] = None,
) -> list[Experiment]:
    stmt = select(Experiment).order_by(Experiment.created_at.desc())
    if status:
        stmt = stmt.where(Experiment.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_experiment(
    db: AsyncSession,
    experiment: Experiment,
    payload: ExperimentUpdate,
) -> Experiment:
    if payload.name is not None:
        experiment.name = payload.name
    if payload.hypothesis is not None:
        experiment.hypothesis = payload.hypothesis
    if payload.variants is not None:
        experiment.variants = [v.model_dump() for v in payload.variants]
    if payload.traffic_pct is not None:
        experiment.traffic_pct = payload.traffic_pct
    if payload.starts_at is not None:
        experiment.starts_at = payload.starts_at
    if payload.ends_at is not None:
        experiment.ends_at = payload.ends_at
    if payload.notes is not None:
        experiment.notes = payload.notes
    if payload.status is not None:
        experiment.status = payload.status

    await db.flush()
    await db.refresh(experiment)
    logger.info("Updated experiment key=%s status=%s", experiment.key, experiment.status)
    return experiment


async def delete_experiment(db: AsyncSession, experiment: Experiment) -> None:
    await db.delete(experiment)
    await db.flush()


# ─── Results ─────────────────────────────────────────────────────────────────

async def compute_results(
    db: AsyncSession,
    experiment: Experiment,
    goal_event: str,
    period_days: int = 30,
) -> ExperimentResults:
    """
    Build experiment results by reading from analytics_events.

    Convention: whenever a user who is in an experiment fires any event,
    the frontend includes {"experiment_key": "...", "experiment_variant": "..."} 
    in the event properties. This lets us count conversions per variant
    without a JOIN — just filter analytics_events by those property values.

    For each variant:
      - unique_users  = distinct user_ids that fired ANY event with this variant tag
      - conversions   = distinct user_ids that fired the goal_event with this variant tag
      - total_events  = total event count for this variant
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    variant_metrics: list[VariantMetric] = []

    # Total assigned users (in-traffic only) for context
    total_assigned_result = await db.execute(
        select(func.count(distinct(ExperimentAssignment.user_id))).where(
            ExperimentAssignment.experiment_id == experiment.id,
            ExperimentAssignment.in_traffic.is_(True),
            ExperimentAssignment.user_id.is_not(None),
        )
    )
    total_assigned = total_assigned_result.scalar_one() or 0

    best_rate = -1.0
    winner = None

    for variant in experiment.variants:
        vkey = variant["key"]
        vname = variant.get("name", vkey)

        # Unique users who fired any event tagged with this variant
        unique_result = await db.execute(
            select(func.count(distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.properties["experiment_key"].astext == experiment.key,
                AnalyticsEvent.properties["experiment_variant"].astext == vkey,
                AnalyticsEvent.user_id.is_not(None),
            )
        )
        unique_users = unique_result.scalar_one() or 0

        # Total events for this variant
        total_result = await db.execute(
            select(func.count()).where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.properties["experiment_key"].astext == experiment.key,
                AnalyticsEvent.properties["experiment_variant"].astext == vkey,
            )
        )
        total_events = total_result.scalar_one() or 0

        # Conversions: users who fired the specific goal event
        conv_result = await db.execute(
            select(func.count(distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == goal_event,
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.properties["experiment_key"].astext == experiment.key,
                AnalyticsEvent.properties["experiment_variant"].astext == vkey,
                AnalyticsEvent.user_id.is_not(None),
            )
        )
        conversions = conv_result.scalar_one() or 0

        rate = round(conversions / unique_users * 100, 2) if unique_users > 0 else 0.0

        if unique_users > 0 and rate > best_rate:
            best_rate = rate
            winner = vkey

        variant_metrics.append(VariantMetric(
            variant_key=vkey,
            variant_name=vname,
            unique_users=unique_users,
            total_events=total_events,
            conversions=conversions,
            conversion_rate_pct=rate,
        ))

    # Mark winner as inconclusive if no data or if all variants have 0 conversions
    if best_rate <= 0:
        winner = None
        note = "Not enough data to determine a winner yet."
    elif winner == "control":
        note = "Control is currently leading. Continue running to confirm."
    else:
        note = f"'{winner}' is currently outperforming control. Results are observational — statistical significance not computed."

    return ExperimentResults(
        experiment_id=experiment.id,
        experiment_key=experiment.key,
        experiment_name=experiment.name,
        status=experiment.status,
        goal_event=goal_event,
        period_days=period_days,
        total_assigned_users=total_assigned,
        variants=variant_metrics,
        winner=winner,
        note=note,
    )
