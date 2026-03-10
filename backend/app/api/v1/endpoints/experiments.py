"""
app/api/v1/endpoints/experiments.py

A/B Experimentation API endpoints (CORE-EXPERIMENT-01).

Public (optional auth):
  GET  /api/v1/experiments/{key}/assign
    — Returns the variant assignment for the current user (or anon_id).
      Creates the assignment on first call; idempotent thereafter.
      The frontend calls this on app boot for each running experiment,
      then attaches {experiment_key, experiment_variant} to every analytics event.

Admin only:
  GET    /api/v1/experiments                      — list all experiments
  POST   /api/v1/experiments                      — create experiment
  GET    /api/v1/experiments/{key}                — get single experiment
  PATCH  /api/v1/experiments/{key}                — update experiment
  DELETE /api/v1/experiments/{key}                — delete experiment
  POST   /api/v1/experiments/{key}/launch         — set status → running
  POST   /api/v1/experiments/{key}/pause          — set status → paused
  POST   /api/v1/experiments/{key}/conclude       — set status → concluded
  GET    /api/v1/experiments/{key}/results        — compute results from analytics_events
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.schemas.experiment_models import (
    AssignmentResponse,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResults,
    ExperimentUpdate,
)
from app.services.auth import optional_current_user, require_admin
from app.services.experiment_service import (
    compute_results,
    create_experiment,
    delete_experiment,
    get_experiment_by_key,
    get_or_create_assignment,
    list_experiments,
    update_experiment,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Shared helper ────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, key: str):
    exp = await get_experiment_by_key(db, key)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{key}' not found.")
    return exp


# ─── Public: variant assignment ───────────────────────────────────────────────

@router.get(
    "/{key}/assign",
    response_model=AssignmentResponse,
    summary="Get (or create) variant assignment for an experiment",
    description=(
        "Call this on app boot for each running experiment. "
        "Returns the same variant on repeat calls (idempotent). "
        "Anonymous callers must supply ?anon_id=<sha256_hash>."
    ),
)
async def assign_variant(
    key: str,
    anon_id: Optional[str] = Query(None, max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> AssignmentResponse:
    exp = await _get_or_404(db, key)

    if exp.status != "running":
        # Not running — return control without creating an assignment record
        control_variant = next(
            (v for v in exp.variants if v.get("key") == "control"),
            exp.variants[0] if exp.variants else {"key": "control", "name": "Control"},
        )
        return AssignmentResponse(
            experiment_key=exp.key,
            experiment_id=exp.id,
            variant_key=control_variant["key"],
            variant_name=control_variant.get("name", "Control"),
            in_traffic=False,
            assigned_at=exp.created_at,
        )

    user_id = current_user.id if current_user else None

    if user_id is None and not anon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a Bearer token or ?anon_id= query parameter.",
        )

    assignment = await get_or_create_assignment(
        db,
        exp,
        user_id=user_id,
        anon_id=anon_id,
    )
    await db.commit()
    return assignment


# ─── Admin: CRUD ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[ExperimentResponse],
    summary="List all experiments",
    dependencies=[Depends(require_admin)],
)
async def list_all_experiments(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[ExperimentResponse]:
    experiments = await list_experiments(db, status=status_filter)
    return [ExperimentResponse.model_validate(e) for e in experiments]


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new experiment",
    dependencies=[Depends(require_admin)],
)
async def create_new_experiment(
    body: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    try:
        exp = await create_experiment(db, body)
        await db.commit()
        await db.refresh(exp)
        return ExperimentResponse.model_validate(exp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/{key}",
    response_model=ExperimentResponse,
    summary="Get a single experiment by key",
    dependencies=[Depends(require_admin)],
)
async def get_experiment(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    exp = await _get_or_404(db, key)
    return ExperimentResponse.model_validate(exp)


@router.patch(
    "/{key}",
    response_model=ExperimentResponse,
    summary="Update an experiment",
    dependencies=[Depends(require_admin)],
)
async def patch_experiment(
    key: str,
    body: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    exp = await _get_or_404(db, key)
    updated = await update_experiment(db, exp, body)
    await db.commit()
    await db.refresh(updated)
    return ExperimentResponse.model_validate(updated)


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an experiment and all its assignments",
    dependencies=[Depends(require_admin)],
)
async def remove_experiment(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    exp = await _get_or_404(db, key)
    await delete_experiment(db, exp)
    await db.commit()


# ─── Admin: status transitions ────────────────────────────────────────────────

@router.post(
    "/{key}/launch",
    response_model=ExperimentResponse,
    summary="Launch an experiment (draft → running)",
    dependencies=[Depends(require_admin)],
)
async def launch_experiment(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    exp = await _get_or_404(db, key)
    if exp.status not in ("draft", "paused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot launch experiment in status '{exp.status}'.",
        )
    exp.status = "running"
    await db.commit()
    await db.refresh(exp)
    logger.info("Experiment '%s' launched.", exp.key)
    return ExperimentResponse.model_validate(exp)


@router.post(
    "/{key}/pause",
    response_model=ExperimentResponse,
    summary="Pause a running experiment",
    dependencies=[Depends(require_admin)],
)
async def pause_experiment(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    exp = await _get_or_404(db, key)
    if exp.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pause experiment in status '{exp.status}'.",
        )
    exp.status = "paused"
    await db.commit()
    await db.refresh(exp)
    return ExperimentResponse.model_validate(exp)


@router.post(
    "/{key}/conclude",
    response_model=ExperimentResponse,
    summary="Conclude an experiment",
    dependencies=[Depends(require_admin)],
)
async def conclude_experiment(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ExperimentResponse:
    exp = await _get_or_404(db, key)
    exp.status = "concluded"
    await db.commit()
    await db.refresh(exp)
    return ExperimentResponse.model_validate(exp)


# ─── Admin: results ───────────────────────────────────────────────────────────

@router.get(
    "/{key}/results",
    response_model=ExperimentResults,
    summary="Compute experiment results from analytics events",
    dependencies=[Depends(require_admin)],
)
async def get_experiment_results(
    key: str,
    goal_event: str = Query(
        ...,
        description="Analytics event name to use as conversion goal, e.g. 'backtest_run'",
    ),
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> ExperimentResults:
    exp = await _get_or_404(db, key)
    return await compute_results(db, exp, goal_event=goal_event, period_days=period_days)
