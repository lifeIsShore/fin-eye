from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from typing import Dict, Any, List, Optional
import pandas as pd
import json
import os
import logging

from app.services.technical_service import compute_technical_consensus
from app.services.ml_pipeline import (
    run_training_pipeline,
    REGISTRY_FILE,
    TIMEFRAME_HORIZON,
    ARTIFACT_DIR,
)
from app.services.market_data import OHLCVFetcher

TIMEFRAMES = list(TIMEFRAME_HORIZON.keys())

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_registry() -> list[dict]:
    """Return all JSONL records from the model registry, newest-first."""
    if not os.path.exists(REGISTRY_FILE):
        return []
    records: list[dict] = []
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("Could not read model registry: %s", exc)
    return records


def _artifact_exists(artifact_file: str) -> bool:
    if not artifact_file:
        return False
    path = os.path.join(ARTIFACT_DIR, artifact_file)
    return os.path.exists(path)


# ── trained-symbols ───────────────────────────────────────────────────────────

@router.get("/trained-symbols", response_model=List[str])
async def get_trained_symbols() -> List[str]:
    """
    Returns sorted list of symbols that have at least one trained model
    artifact on disk in the model registry.
    """
    records = _read_registry()
    symbols: set[str] = set()
    for rec in records:
        sym = rec.get("symbol", "").strip().upper()
        artifact = rec.get("artifact_file", "")
        if sym and _artifact_exists(artifact):
            symbols.add(sym)
    return sorted(symbols)


# ── registry-status ───────────────────────────────────────────────────────────

@router.get("/registry-status")
async def get_registry_status() -> Dict[str, Any]:
    """
    Returns an overview of all trained symbols in the model registry.

    Phase 1 — Sprint 1 (todos-v4.md §1.1)
    Used by Settings pipeline panel and the admin overview endpoint.
    """
    records = _read_registry()

    # Group champion (latest per symbol+timeframe) records
    champions: dict[tuple[str, str], dict] = {}
    for rec in records:
        sym = rec.get("symbol", "").strip().upper()
        tf  = rec.get("timeframe", "")
        if not sym or not tf:
            continue
        key = (sym, tf)
        existing = champions.get(key)
        if existing is None or rec.get("trained_at", "") > existing.get("trained_at", ""):
            champions[key] = rec

    # Aggregate per symbol
    by_symbol: dict[str, dict] = {}
    for (sym, tf), rec in champions.items():
        if sym not in by_symbol:
            by_symbol[sym] = {
                "symbol": sym,
                "timeframes_trained": [],
                "last_trained_at": None,
                "quality_gate": False,
                "best_sharpe": None,
                "has_artifacts": False,
            }
        entry = by_symbol[sym]
        artifact = rec.get("artifact_file", "")
        if _artifact_exists(artifact):
            entry["timeframes_trained"].append(tf)
            entry["has_artifacts"] = True
        trained_at = rec.get("trained_at")
        if trained_at and (entry["last_trained_at"] is None or trained_at > entry["last_trained_at"]):
            entry["last_trained_at"] = trained_at
        sharpe = rec.get("validation_sharpe")
        if sharpe is not None and (entry["best_sharpe"] is None or sharpe > entry["best_sharpe"]):
            entry["best_sharpe"] = sharpe
        if rec.get("quality_gate"):
            entry["quality_gate"] = True

    symbols_list = sorted(by_symbol.values(), key=lambda x: x["symbol"])

    return {
        "total_symbols": len(symbols_list),
        "symbols": symbols_list,
    }


# ── train-status/{symbol} ─────────────────────────────────────────────────────

@router.get("/train-status/{symbol}")
async def get_train_status(symbol: str) -> Dict[str, Any]:
    """
    Returns per-symbol training state.

    Possible status values:
      - "trained"      — at least one timeframe has a model artifact on disk
      - "not_started"  — no registry entries for this symbol
      - "no_artifacts" — registry entries exist but all .joblib files are missing

    Phase 1 — Sprint 1 (todos-v4.md §1.2)
    Polled by the frontend "Train Now" button and the per-ticker data panel.
    """
    sym = symbol.upper()
    records = _read_registry()

    sym_records = [r for r in records if r.get("symbol", "").upper() == sym]
    if not sym_records:
        return {
            "symbol": sym,
            "status": "not_started",
            "timeframes": [],
            "last_trained_at": None,
            "model_metrics": {},
        }

    # Latest record per timeframe
    latest: dict[str, dict] = {}
    for rec in sym_records:
        tf = rec.get("timeframe", "")
        if not tf:
            continue
        existing = latest.get(tf)
        if existing is None or rec.get("trained_at", "") > existing.get("trained_at", ""):
            latest[tf] = rec

    trained_timeframes: list[dict] = []
    last_trained_at: Optional[str] = None
    best_sharpe: Optional[float] = None

    for tf, rec in latest.items():
        artifact = rec.get("artifact_file", "")
        on_disk  = _artifact_exists(artifact)
        trained_at = rec.get("trained_at")
        sharpe     = rec.get("validation_sharpe")

        if on_disk:
            trained_timeframes.append({
                "timeframe":    tf,
                "model":        rec.get("model_name", "unknown"),
                "sharpe":       sharpe,
                "trained_at":   trained_at,
                "quality_gate": rec.get("quality_gate", False),
            })

        if trained_at and (last_trained_at is None or trained_at > last_trained_at):
            last_trained_at = trained_at
        if sharpe is not None and (best_sharpe is None or sharpe > best_sharpe):
            best_sharpe = sharpe

    status = "trained" if trained_timeframes else "no_artifacts"

    return {
        "symbol":          sym,
        "status":          status,
        "timeframes":      trained_timeframes,
        "last_trained_at": last_trained_at,
        "model_metrics": {
            "best_sharpe":      best_sharpe,
            "timeframes_count": len(trained_timeframes),
        },
    }


# ── train/{symbol} ────────────────────────────────────────────────────────────

@router.post("/train/{symbol}")
async def train_technical_models(
    symbol: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Triggers ML training for all timeframes for a symbol.
    Runs in the background (training is CPU-bound and takes 30–120 seconds).

    Query param ?force=true retrains even if models already exist.
    """
    symbol = symbol.upper()

    def _run_training() -> None:
        for tf in TIMEFRAMES:
            try:
                period  = "730d" if tf == "1h" else "5y"
                records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=tf)
                if len(records) < 200:
                    logger.warning(
                        "Not enough data to train %s/%s (found %d rows)", symbol, tf, len(records)
                    )
                    continue
                df = pd.DataFrame([
                    {
                        "date":   r.timestamp,
                        "open":   r.open,
                        "high":   r.high,
                        "low":    r.low,
                        "close":  r.close,
                        "volume": r.volume,
                    }
                    for r in records
                ])
                df.set_index("date", inplace=True)
                df.sort_index(inplace=True)
                run_training_pipeline(symbol, tf, df)
            except Exception as exc:
                logger.error("Background training failed for %s/%s: %s", symbol, tf, exc)

    background_tasks.add_task(_run_training)

    return {
        "message":           f"Training initiated in background for {symbol} ({len(TIMEFRAMES)} timeframes).",
        "symbol":            symbol,
        "timeframes_queued": TIMEFRAMES,
        "status":            "processing",
        "estimated_seconds": 120,
    }


# ── /{symbol}/latest ──────────────────────────────────────────────────────────

@router.get("/{symbol}/latest")
async def get_latest_technical_consensus(symbol: str) -> Dict[str, Any]:
    """
    Return live technical consensus and 0–100 confidence score.
    Returns a structured "not_trained" response instead of an error when no
    models exist, so the frontend can render the Train Now button cleanly.
    """
    import asyncio

    try:
        loop   = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, compute_technical_consensus, symbol.upper())

        return {
            "symbol":                     result["symbol"],
            "consensus":                  result["consensus_label"],
            "technical_confidence_score": result["consensus_score"],
            "summary":                    f"{result['consensus_label']} based on live ML inference",
            "signals": [
                {
                    "timeframe":        s["timeframe"],
                    "direction":        s["direction"],
                    "confidence":       s["confidence"],
                    "sharpe_weight":    s["validation_sharpe"],
                    "validation_sharpe": s["validation_sharpe"],
                    "model_used":       s["model_used"],
                }
                for s in result["signals"]
            ],
        }

    except ValueError as exc:
        # No trained models — return a clean "not trained" response
        msg = str(exc)
        if "No trained models" in msg or "training pipeline" in msg.lower():
            return {
                "symbol":                     symbol.upper(),
                "consensus":                  "Not trained",
                "technical_confidence_score": 50.0,
                "summary":                    "No ML models trained for this symbol yet.",
                "signals":                    [],
                "not_trained":                True,
            }
        logger.error("Technical consensus error for %s: %s", symbol, exc)
        return {
            "symbol":  symbol.upper(),
            "error":   msg,
            "signals": [],
        }

    except Exception as exc:
        import traceback
        logger.error("Technical consensus error for %s:\n%s", symbol, traceback.format_exc())
        return {
            "symbol":  symbol.upper(),
            "error":   str(exc),
            "signals": [],
        }
