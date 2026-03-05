"""
app/models/experiment.py

A/B Experimentation models (CORE-EXPERIMENT-01).

Two tables:

  experiments
    — Admin-managed experiment config. Defines name, hypothesis, variants,
      traffic allocation, status, and date window.

  experiment_assignments
    — One row per (experiment, user/anon). Stores the variant they received.
      Written once on first call to GET /experiments/{key}/assign.
      Idempotent: repeat calls return the same variant via the unique constraint.

Design decisions:
  - Deterministic assignment: SHA-256(experiment_id + user_id) % 100 maps
    each user to a traffic bucket deterministically. No randomness after first
    assignment, no DB read needed to reproduce the answer — but we still persist
    it for result queries and audit.
  - Variants stored as JSON array of objects: [{key, name, weight}, ...]
    where weights are integers summing to 100 (percentage points).
  - Results are NOT stored here — they are read from analytics_events by
    grouping on properties["experiment_variant"] for a given experiment_key.
  - user_id FK uses ON DELETE SET NULL (same GDPR pattern as analytics_events).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.db.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # URL-safe identifier used in API calls and event properties
    # e.g. "onboarding_flow_v2", "dashboard_hero_copy"
    key = Column(String(128), unique=True, nullable=False, index=True)

    name = Column(String(256), nullable=False)
    hypothesis = Column(Text, nullable=True)

    # Variants: [{"key": "control", "name": "Control", "weight": 50},
    #            {"key": "treatment", "name": "Treatment", "weight": 50}]
    # Weights are integer percentages summing to 100.
    variants = Column(JSON, nullable=False, default=list)

    # Percentage of eligible users to include (0–100).
    # Users outside the traffic slice always get the control variant.
    traffic_pct = Column(Integer, nullable=False, default=100)

    # draft | running | paused | concluded
    status = Column(String(32), nullable=False, default="draft", index=True)

    # Optional date window — None means "run until manually paused"
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)

    # Free-text notes for the admin dashboard
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} key={self.key!r} status={self.status}>"


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Authenticated user (nullable — anon users are tracked via anon_id)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Anonymous identifier (SHA-256 hash — no raw PII)
    anon_id = Column(String(64), nullable=True)

    # The variant key this user was assigned, e.g. "control" or "treatment"
    variant_key = Column(String(128), nullable=False)

    # When the assignment was first made
    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Whether the user was inside the traffic slice for this experiment
    in_traffic = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        # Core constraint: one assignment per (experiment, user)
        UniqueConstraint(
            "experiment_id", "user_id",
            name="uq_experiment_assignment_user",
        ),
        # Separate constraint for anon users
        UniqueConstraint(
            "experiment_id", "anon_id",
            name="uq_experiment_assignment_anon",
        ),
        # Fast lookup: "what variant is this user in for experiment X?"
        Index("ix_exp_assign_exp_user", "experiment_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExperimentAssignment exp={self.experiment_id} "
            f"user={self.user_id} variant={self.variant_key!r}>"
        )
