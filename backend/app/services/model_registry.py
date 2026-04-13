"""
app/services/model_registry.py

Model Registry — best-practice rewrite.

Design goals
────────────
1. Clear data model   — ModelRecord carries every field that matters for
                        inference, auditing, and rollback decisions.
2. Explicit lifecycle — each record has a status: "candidate" → "champion"
                        → "retired".  Only one champion per (symbol, timeframe)
                        at a time.  Old champions are automatically retired.
3. Versioned          — every save increments a monotonic version counter per
                        (symbol, timeframe) so you can always reconstruct history.
4. Easy to read       — the JSONL file stays append-only (audit log), but a
                        companion *index* JSON is rewritten on every save so you
                        can open one small file and see the current state at a
                        glance.
5. Minimal coupling   — the public Protocol (ModelRegistry) is unchanged so
                        callers (ml_pipeline.py, technical_service.py) need zero
                        edits.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Protocol

try:
    from filelock import FileLock as _FileLock
    _FILELOCK_AVAILABLE = True
except ImportError:
    _FILELOCK_AVAILABLE = False

from app.services.technical_models import ModelKind, Timeframe, TimeframeWinner

logger = logging.getLogger(__name__)

# ── Status lifecycle ──────────────────────────────────────────────────────────
#   candidate  – just trained, not yet promoted
#   champion   – current best for (symbol, timeframe); used for inference
#   retired    – superseded by a newer champion
RecordStatus = Literal["candidate", "champion", "retired"]


# ── Core data model ───────────────────────────────────────────────────────────

@dataclass
class ModelRecord:
    """
    Everything you need to understand, reproduce, and load a trained model.

    Required fields
    ───────────────
    symbol          Stock or asset ticker (e.g. "AAPL").
    timeframe       Prediction timeframe enum value (e.g. Timeframe.ONE_DAY).
    model_kind      Algorithm used (e.g. ModelKind.XGBOOST).
    sharpe_ratio    Annualised Sharpe on the hold-out validation set.
    accuracy        Classification accuracy on the hold-out validation set.
    trained_at      UTC timestamp of when training completed.

    Lifecycle / audit fields (set automatically by the registry)
    ────────────────────────────────────────────────────────────
    version         Monotonically increasing integer per (symbol, timeframe).
                    Version 1 is the first ever record for that pair.
    status          "candidate" | "champion" | "retired"
    record_id       Stable UUID-like key: "{symbol}_{timeframe}_{version}"

    Optional enrichment
    ───────────────────
    artifact_path   Absolute path to the .joblib / .json model file on disk.
    mlflow_run_id   MLflow run UUID (for UI drill-down).
    quality_gate    True if the model passed MIN_SHARPE + MIN_ACCURACY gates.
    notes           Free-text notes from the training job.
    extra_metrics   Dict of additional metrics (total_return, val_rows, …).
    """

    # Core identity
    symbol: str
    timeframe: Timeframe
    model_kind: ModelKind

    # Performance
    sharpe_ratio: float
    accuracy: float

    # Timestamps
    trained_at: datetime

    # Lifecycle (auto-set by registry — provide defaults for backwards compat)
    version: int = 1
    status: RecordStatus = "candidate"

    # Convenience derived key — set by registry on save
    record_id: str = ""

    # Optional enrichment
    artifact_path: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    quality_gate: bool = True
    notes: str = ""
    extra_metrics: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Auto-derive record_id if not provided
        if not self.record_id:
            self.record_id = (
                f"{self.symbol}_{self.timeframe.value}_{self.version}"
            )

    # ── Serialisation helpers ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timeframe"]  = self.timeframe.value
        d["model_kind"] = self.model_kind.value
        d["trained_at"] = self.trained_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ModelRecord":
        return cls(
            symbol        = d["symbol"],
            timeframe     = Timeframe(d["timeframe"]),
            model_kind    = ModelKind(d["model_kind"]),
            sharpe_ratio  = float(d["sharpe_ratio"]),
            accuracy      = float(d["accuracy"]),
            trained_at    = datetime.fromisoformat(d["trained_at"]),
            version       = int(d.get("version", 1)),
            # Legacy records written before the status field existed have no
            # "status" key. Treat them as "champion" so existing trained models
            # are not silently ignored by all_champions().
            status        = d.get("status", "champion"),
            record_id     = d.get("record_id", ""),
            artifact_path = d.get("artifact_path"),
            mlflow_run_id = d.get("mlflow_run_id"),
            quality_gate  = bool(d.get("quality_gate", True)),
            notes         = str(d.get("notes", "")),
            extra_metrics = d.get("extra_metrics", {}),
        )

    # ── Human-friendly summary ────────────────────────────────────────────────

    def summary(self) -> str:
        gate = "✓" if self.quality_gate else "✗"
        return (
            f"[{self.record_id}] {self.model_kind.value:<12} "
            f"sharpe={self.sharpe_ratio:>7.3f}  acc={self.accuracy:.1%}  "
            f"gate={gate}  status={self.status}"
        )


# ── Protocol (public interface — unchanged from original) ─────────────────────

class ModelRegistry(Protocol):
    """Abstract interface for persisting model metadata."""

    def save_winner(self, record: ModelRecord) -> None: ...
    def list_winners(self) -> List[ModelRecord]: ...
    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]: ...


# ── In-memory implementation (tests / dev) ────────────────────────────────────

class InMemoryModelRegistry:
    """
    Volatile in-memory registry.  Good for unit tests; state is lost on restart.

    Mirrors the same versioning/status logic as JsonlFileModelRegistry so
    behaviour is consistent across implementations.
    """

    def __init__(self) -> None:
        self._records: List[ModelRecord] = []

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _next_version(self, symbol: str, timeframe: Timeframe) -> int:
        existing = [
            r for r in self._records
            if r.symbol == symbol and r.timeframe == timeframe
        ]
        return len(existing) + 1

    def _retire_current_champion(self, symbol: str, timeframe: Timeframe) -> None:
        for r in self._records:
            if r.symbol == symbol and r.timeframe == timeframe and r.status == "champion":
                r.status = "retired"

    # ── Public API ────────────────────────────────────────────────────────────

    def save_winner(self, record: ModelRecord) -> None:
        record.version   = self._next_version(record.symbol, record.timeframe)
        record.record_id = f"{record.symbol}_{record.timeframe.value}_{record.version}"

        self._retire_current_champion(record.symbol, record.timeframe)
        record.status = "champion"

        self._records.append(record)
        logger.debug("InMemoryRegistry: saved %s", record.record_id)

    def list_winners(self) -> List[ModelRecord]:
        return list(self._records)

    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]:
        """Return the current champion (or most recent record) for a timeframe."""
        candidates = [
            r for r in self._records
            if r.timeframe == timeframe
            and (symbol is None or r.symbol == symbol)
        ]
        # Prefer champion; fall back to highest version
        champions = [r for r in candidates if r.status == "champion"]
        if champions:
            return max(champions, key=lambda r: r.version)
        return max(candidates, key=lambda r: r.version) if candidates else None

    # ── Extra convenience queries ─────────────────────────────────────────────

    def get_champion(self, symbol: str, timeframe: Timeframe) -> Optional[ModelRecord]:
        """Return the single active champion for (symbol, timeframe), or None."""
        for r in reversed(self._records):
            if r.symbol == symbol and r.timeframe == timeframe and r.status == "champion":
                return r
        return None

    def history(self, symbol: str, timeframe: Timeframe) -> List[ModelRecord]:
        """Return all records for (symbol, timeframe) sorted oldest → newest."""
        return sorted(
            [r for r in self._records if r.symbol == symbol and r.timeframe == timeframe],
            key=lambda r: r.version,
        )


# ── File-backed implementation ────────────────────────────────────────────────

class JsonlFileModelRegistry:
    """
    Persistent registry backed by two files:

    model_registry.jsonl   — append-only audit log; every save adds one line.
                             Never overwritten, safe to tail/grep.

    model_registry_index.json — rewritten on every save; contains only the
                                 current champion per (symbol, timeframe) plus
                                 a compact summary of all versions.
                                 Open this file to see the state at a glance.

    Both files live in the same directory (default: backend/data/models/).
    """

    def __init__(self, path: str | Path) -> None:
        self.log_path   = Path(path)
        self.index_path = self.log_path.parent / "model_registry_index.json"
        self._lock_path = str(self.log_path) + ".lock"

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def _get_lock(self):
        """Return a file lock context manager, or a no-op if filelock is unavailable."""
        if _FILELOCK_AVAILABLE:
            return _FileLock(self._lock_path)
        import contextlib  # noqa: PLC0415
        return contextlib.nullcontext()

    # ── Internal: read ────────────────────────────────────────────────────────

    def _read_all(self) -> List[ModelRecord]:
        """Read every line from the JSONL log and return all ModelRecords."""
        records: List[ModelRecord] = []
        if not self.log_path.exists():
            return records
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(ModelRecord.from_dict(json.loads(line)))
            except Exception as exc:
                logger.warning("Skipping malformed registry line: %s | %s", line[:80], exc)
        return records

    def _next_version(self, symbol: str, timeframe: Timeframe) -> int:
        existing = [
            r for r in self._read_all()
            if r.symbol == symbol and r.timeframe == timeframe
        ]
        return len(existing) + 1

    # ── Internal: write ───────────────────────────────────────────────────────

    def _append(self, record: ModelRecord) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def _rewrite_retired(self, symbol: str, timeframe: Timeframe) -> None:
        """
        Read the full log, flip any champion for this (symbol, timeframe) to
        'retired', and rewrite the entire log.  Called before adding a new champion.
        """
        records   = self._read_all()
        rewritten = False
        for r in records:
            if r.symbol == symbol and r.timeframe == timeframe and r.status == "champion":
                r.status  = "retired"
                rewritten = True

        if rewritten:
            lines = [json.dumps(r.to_dict()) for r in records]
            self.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _rebuild_index(self, all_records: List[ModelRecord]) -> None:
        """
        Write model_registry_index.json — the human-readable snapshot.

        Structure
        ─────────
        {
          "generated_at": "2025-06-01T12:00:00",
          "champions": {
            "AAPL": {
              "1d": { ...full ModelRecord dict... },
              "1h": { ...full ModelRecord dict... }
            }
          },
          "history": {
            "AAPL_1d": [
              { "version": 1, "model_kind": "logistic", "sharpe_ratio": 0.82,
                "accuracy": 0.54, "status": "retired", "trained_at": "..." },
              { "version": 2, "model_kind": "xgboost",  "sharpe_ratio": 1.12,
                "accuracy": 0.58, "status": "champion", "trained_at": "..." }
            ]
          }
        }
        """
        champions: Dict[str, Dict[str, dict]] = {}
        history:   Dict[str, List[dict]]      = {}

        for r in all_records:
            sym = r.symbol
            tf  = r.timeframe.value
            key = f"{sym}_{tf}"

            # champions section
            if r.status == "champion":
                champions.setdefault(sym, {})[tf] = r.to_dict()

            # history section — compact per-version summary
            history.setdefault(key, []).append({
                "version":      r.version,
                "model_kind":   r.model_kind.value,
                "sharpe_ratio": round(r.sharpe_ratio, 4),
                "accuracy":     round(r.accuracy, 4),
                "quality_gate": r.quality_gate,
                "status":       r.status,
                "trained_at":   r.trained_at.isoformat(),
                "record_id":    r.record_id,
            })

        # Sort each history list by version
        for key in history:
            history[key].sort(key=lambda x: x["version"])

        index = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(all_records),
            "champions": champions,
            "history":   history,
        }
        self.index_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def save_winner(self, record: ModelRecord) -> None:
        """
        Persist a new champion:
        1. Determine next version number.
        2. Retire the current champion for this (symbol, timeframe) in the log.
        3. Append the new champion line.
        4. Rebuild the index JSON.
        """
        with self._get_lock():
            record.version   = self._next_version(record.symbol, record.timeframe)
            record.record_id = f"{record.symbol}_{record.timeframe.value}_{record.version}"

            self._rewrite_retired(record.symbol, record.timeframe)
            record.status = "champion"
            self._append(record)

            all_records = self._read_all()
            self._rebuild_index(all_records)

        logger.info(
            "Registry: saved champion %s  (sharpe=%.3f  acc=%.1%%  gate=%s)",
            record.record_id, record.sharpe_ratio,
            record.accuracy * 100, "✓" if record.quality_gate else "✗",
        )

        # SEC-08: Upload artifact to R2 (async, non-blocking fire-and-forget)
        if record.artifact_path:
            try:
                import asyncio  # noqa: PLC0415
                from app.services.model_storage import upload_model  # noqa: PLC0415
                from pathlib import Path as _Path  # noqa: PLC0415
                _local = _Path(record.artifact_path)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(upload_model(_local))
                except RuntimeError:
                    pass  # No running loop — skip upload silently
            except Exception as _exc:
                logger.debug("R2 upload dispatch failed (non-fatal): %s", _exc)

    def list_winners(self) -> List[ModelRecord]:
        """Return every record in the log (all statuses)."""
        return self._read_all()

    def get_latest_for_timeframe(
        self, timeframe: Timeframe, symbol: Optional[str] = None
    ) -> Optional[ModelRecord]:
        """
        Return the current champion for (symbol, timeframe).
        Falls back to the highest-version record if no champion exists.
        """
        records = self._read_all()
        candidates = [
            r for r in records
            if r.timeframe == timeframe
            and (symbol is None or r.symbol == symbol)
        ]
        champions = [r for r in candidates if r.status == "champion"]
        if champions:
            return max(champions, key=lambda r: r.version)
        return max(candidates, key=lambda r: r.version) if candidates else None

    # ── Extra convenience queries ─────────────────────────────────────────────

    def get_champion(self, symbol: str, timeframe: Timeframe) -> Optional[ModelRecord]:
        """Return the single active champion for (symbol, timeframe), or None."""
        records = self._read_all()
        for r in reversed(records):
            if r.symbol == symbol and r.timeframe == timeframe and r.status == "champion":
                return r
        return None

    def history(self, symbol: str, timeframe: Timeframe) -> List[ModelRecord]:
        """Return all versions for (symbol, timeframe), oldest → newest."""
        return sorted(
            [
                r for r in self._read_all()
                if r.symbol == symbol and r.timeframe == timeframe
            ],
            key=lambda r: r.version,
        )

    def all_champions(self) -> List[ModelRecord]:
        """Return one champion per (symbol, timeframe) — the current production set."""
        return [r for r in self._read_all() if r.status == "champion"]


# ── Convenience helper (called from ml_pipeline.py) ──────────────────────────

def record_winners(
    registry: ModelRegistry,
    winners: List[TimeframeWinner],
    symbol: str,
    trained_at: Optional[datetime] = None,
    notes: str = "",
    artifact_path: Optional[str] = None,
    mlflow_run_id: Optional[str] = None,
    quality_gate: bool = True,
    extra_metrics: Optional[Dict] = None,
) -> None:
    """
    Convert TimeframeWinner objects into ModelRecord entries and save them.

    Parameters
    ──────────
    registry        Any ModelRegistry implementation.
    winners         List of TimeframeWinner results from the training pipeline.
    symbol          Ticker symbol (e.g. "AAPL").
    trained_at      UTC training timestamp; defaults to now.
    notes           Free-text annotation (e.g. "triggered by scheduler").
    artifact_path   Path to the persisted .joblib file.
    mlflow_run_id   MLflow run UUID for UI cross-reference.
    quality_gate    Whether this run passed Sharpe + accuracy gates.
    extra_metrics   Additional metrics dict (val_rows, total_return, …).
    """
    when = trained_at or datetime.utcnow()
    for winner in winners:
        registry.save_winner(
            ModelRecord(
                symbol        = symbol,
                timeframe     = winner.timeframe,
                model_kind    = winner.model_kind,
                sharpe_ratio  = winner.sharpe_ratio,
                accuracy      = winner.accuracy,
                trained_at    = when,
                artifact_path = artifact_path,
                mlflow_run_id = mlflow_run_id,
                quality_gate  = quality_gate,
                notes         = notes,
                extra_metrics = extra_metrics or {},
            )
        )
