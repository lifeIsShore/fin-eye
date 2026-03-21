from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from typing import Dict, Any, List, Optional
import pandas as pd
import json
import os
import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.technical_service import (
    compute_technical_consensus,
    compute_and_store_consensus,
)
from app.services.ml_pipeline import (
    run_training_pipeline,
    REGISTRY_FILE,
    TIMEFRAME_HORIZON,
    ARTIFACT_DIR,
)
from app.services.market_data import OHLCVFetcher
from app.db.database import get_db

TIMEFRAMES = list(TIMEFRAME_HORIZON.keys())

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_registry() -> list[dict]:
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
    return os.path.exists(os.path.join(ARTIFACT_DIR, artifact_file))


def _fetch_latest_price_sync(symbol: str) -> Optional[float]:
    try:
        records = OHLCVFetcher.fetch_historical_data(symbol, period="5d", interval="1d")
        if records:
            return float(records[-1].close)
    except Exception as exc:
        logger.debug("Price fetch failed for %s: %s", symbol, exc)
    return None


# ── trained-symbols ───────────────────────────────────────────────────────────

@router.get("/trained-symbols", response_model=List[str])
async def get_trained_symbols() -> List[str]:
    records = _read_registry()
    symbols: set[str] = set()
    for rec in records:
        sym      = rec.get("symbol", "").strip().upper()
        artifact = rec.get("artifact_file", "")
        if sym and _artifact_exists(artifact):
            symbols.add(sym)
    return sorted(symbols)


# ── registry-status ───────────────────────────────────────────────────────────

@router.get("/registry-status")
async def get_registry_status() -> Dict[str, Any]:
    records  = _read_registry()
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

    by_symbol: dict[str, dict] = {}
    for (sym, tf), rec in champions.items():
        if sym not in by_symbol:
            by_symbol[sym] = {
                "symbol": sym, "timeframes_trained": [], "last_trained_at": None,
                "quality_gate": False, "best_sharpe": None, "has_artifacts": False,
            }
        entry    = by_symbol[sym]
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

    return {"total_symbols": len(by_symbol), "symbols": sorted(by_symbol.values(), key=lambda x: x["symbol"])}


# ── train-status/{symbol} ─────────────────────────────────────────────────────

@router.get("/train-status/{symbol}")
async def get_train_status(symbol: str) -> Dict[str, Any]:
    sym     = symbol.upper()
    records = _read_registry()
    sym_records = [r for r in records if r.get("symbol", "").upper() == sym]
    if not sym_records:
        return {"symbol": sym, "status": "not_started", "timeframes": [], "last_trained_at": None, "model_metrics": {}}

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
    best_sharpe: Optional[float]   = None

    for tf, rec in latest.items():
        if _artifact_exists(rec.get("artifact_file", "")):
            trained_timeframes.append({
                "timeframe": tf, "model": rec.get("model_name", "unknown"),
                "sharpe": rec.get("validation_sharpe"), "trained_at": rec.get("trained_at"),
                "quality_gate": rec.get("quality_gate", False),
            })
        t = rec.get("trained_at")
        if t and (last_trained_at is None or t > last_trained_at):
            last_trained_at = t
        s = rec.get("validation_sharpe")
        if s is not None and (best_sharpe is None or s > best_sharpe):
            best_sharpe = s

    return {
        "symbol": sym,
        "status": "trained" if trained_timeframes else "no_artifacts",
        "timeframes": trained_timeframes, "last_trained_at": last_trained_at,
        "model_metrics": {"best_sharpe": best_sharpe, "timeframes_count": len(trained_timeframes)},
    }


# ── train/{symbol} ────────────────────────────────────────────────────────────

@router.post("/train/{symbol}")
async def train_technical_models(
    symbol: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
) -> Dict[str, Any]:
    symbol = symbol.upper()

    def _run_training() -> None:
        for tf in TIMEFRAMES:
            try:
                period  = "730d" if tf == "1h" else "5y"
                records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=tf)
                if len(records) < 200:
                    logger.warning("Not enough data to train %s/%s (%d rows)", symbol, tf, len(records))
                    continue
                df = pd.DataFrame([
                    {"date": r.timestamp, "open": r.open, "high": r.high,
                     "low": r.low, "close": r.close, "volume": r.volume}
                    for r in records
                ]).set_index("date").sort_index()
                run_training_pipeline(symbol, tf, df)
            except Exception as exc:
                logger.error("Background training failed for %s/%s: %s", symbol, tf, exc)

    background_tasks.add_task(_run_training)
    return {
        "message": f"Training initiated in background for {symbol} ({len(TIMEFRAMES)} timeframes).",
        "symbol": symbol, "timeframes_queued": TIMEFRAMES,
        "status": "processing", "estimated_seconds": 120,
    }


# ── /{symbol}/price ───────────────────────────────────────────────────────────

@router.get("/{symbol}/price")
async def get_latest_price(symbol: str) -> Dict[str, Any]:
    """Latest closing price — used by LLM insight card for price targets."""
    sym   = symbol.upper()
    loop  = asyncio.get_running_loop()
    price = await loop.run_in_executor(None, _fetch_latest_price_sync, sym)
    return {"symbol": sym, "price": price, "source": "yfinance" if price is not None else "unavailable"}


# ── /{symbol}/latest ──────────────────────────────────────────────────────────

@router.get("/{symbol}/latest")
async def get_latest_technical_consensus(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return live technical consensus and 0–100 confidence score.
    Sprint 2: also stores each signal in ml_predictions so live accuracy is tracked.
    """
    try:
        result = await compute_and_store_consensus(
            symbol.upper(), db=db,
            macro_score=None, vix=None, market_regime=None,
        )
        return {
            "symbol":                     result["symbol"],
            "consensus":                  result["consensus_label"],
            "technical_confidence_score": result["consensus_score"],
            "summary":                    f"{result['consensus_label']} based on live ML inference",
            "signals": [
                {
                    "timeframe":         s["timeframe"],
                    "direction":         s["direction"],
                    "confidence":        s["confidence"],
                    "sharpe_weight":     s["validation_sharpe"],
                    "validation_sharpe": s["validation_sharpe"],
                    "model_used":        s["model_used"],
                }
                for s in result["signals"]
            ],
        }

    except ValueError as exc:
        msg = str(exc)
        if "No trained models" in msg or "training pipeline" in msg.lower():
            return {
                "symbol": symbol.upper(), "consensus": "Not trained",
                "technical_confidence_score": 50.0,
                "summary": "No ML models trained for this symbol yet.",
                "signals": [], "not_trained": True,
            }
        logger.error("Technical consensus error for %s: %s", symbol, exc)
        return {"symbol": symbol.upper(), "error": msg, "signals": []}

    except Exception as exc:
        logger.error("Technical consensus error for %s:\n%s", symbol, exc)
        return {"symbol": symbol.upper(), "error": str(exc), "signals": []}


# ── /{symbol}/model-details ───────────────────────────────────────────────────

@router.get("/{symbol}/model-details")
async def get_model_details(symbol: str) -> Dict[str, Any]:
    """Full model transparency for the dev details panel (todos-v5 Phase 2.1)."""
    from app.services.ml_pipeline import FEATURES  # noqa: PLC0415

    sym = symbol.upper()
    records = _read_registry()
    sym_records = [r for r in records if r.get("symbol", "").upper() == sym]

    FEATURE_DESCRIPTIONS: dict[str, str] = {
        "ret_1":            "1-period return — previous bar's price change (%)",
        "ret_3":            "3-period return — price change over last 3 bars (%)",
        "ret_5":            "5-period return — price change over last 5 bars (%)",
        "sma_cross_10_20":  "10-SMA / 20-SMA − 1. Positive = short-term trend above medium-term.",
        "sma_cross_20_50":  "20-SMA / 50-SMA − 1. Positive = medium-term trend above long-term.",
        "price_vs_sma50":   "Close / 50-SMA − 1. How far price is from its 50-period average.",
        "rsi_14":           "RSI over 14 periods. >70 = overbought, <30 = oversold.",
        "macd":             "MACD line (EMA12 − EMA26). Positive = short-term momentum above long-term.",
        "macd_hist":        "MACD histogram (MACD − Signal). Positive = bullish momentum building.",
        "bb_width":         "Bollinger Band width = (Upper − Lower) / Middle. Measures volatility.",
        "bb_pb":            "Bollinger Band %B. 0 = at lower band, 1 = at upper band.",
        "atr_pct":          "Average True Range as % of price. Current volatility level.",
        "mom_10":           "10-period momentum — % change over last 10 bars.",
        "mom_20":           "20-period momentum — % change over last 20 bars.",
        "volume_ratio":     "Current volume / 20-period average volume. >1 = above-average activity.",
    }

    timeframes_data: dict[str, dict] = {}
    for rec in sym_records:
        tf = rec.get("timeframe", "")
        if not tf:
            continue
        existing = timeframes_data.get(tf)
        if existing is None or rec.get("trained_at", "") > existing.get("trained_at", ""):
            metrics_raw = rec.get("metrics", {})
            shap_imp    = rec.get("shap_importance") or rec.get("extra_metrics", {}).get("shap_importance")
            timeframes_data[tf] = {
                "winner_model":   rec.get("model_name", "unknown"),
                "shap_importance": shap_imp,
                "all_models": {
                    name: {
                        "accuracy": m.get("accuracy", 0), "sharpe": m.get("sharpe_ratio", -99),
                        "total_return": m.get("total_return", 0),
                        "disqualified": m.get("disqualified", False), "reason": m.get("disqualify_reason"),
                    }
                    for name, m in metrics_raw.items()
                },
                "features_used": [
                    {"name": f, "description": FEATURE_DESCRIPTIONS.get(f, f)}
                    for f in FEATURES
                ],
                "training_info": {
                    "trained_at":            rec.get("trained_at"),
                    "train_rows":            rec.get("diagnostics", {}).get("train_rows"),
                    "val_rows":              rec.get("diagnostics", {}).get("val_rows"),
                    "total_rows":            rec.get("diagnostics", {}).get("total_rows"),
                    "horizon_periods":       rec.get("horizon_periods"),
                    "target_balance_up_pct": rec.get("diagnostics", {}).get("target_balance_up_pct"),
                    "quality_gate_passed":   rec.get("quality_gate", False),
                    "mlflow_run_id":         rec.get("mlflow_run_id"),
                },
                "how_target_was_built": (
                    f"Binary label: 1 if price is higher {rec.get('horizon_periods', 3)} "
                    f"{tf} bars from now, 0 if lower. "
                    "80% of data used for training (chronological split, no lookahead)."
                ),
                "how_sharpe_was_built": (
                    "Sharpe = mean(strategy_returns) / std(strategy_returns) × √252. "
                    "Strategy return = actual return if model predicted UP, else 0."
                ),
            }

    return {"symbol": sym, "timeframes": timeframes_data}


# ── /{symbol}/prediction-stats ────────────────────────────────────────────────

@router.get("/{symbol}/prediction-stats")
async def get_prediction_stats(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Live prediction accuracy from the ml_predictions table (todos-v5 Phase 5.4)."""
    from app.services.prediction_service import get_prediction_stats as _get_stats  # noqa: PLC0415
    return await _get_stats(db, symbol)


# ── /{symbol}/price-targets ───────────────────────────────────────────────────
# Sprint 5 — todos-v5 Phase 6.2: model-driven ATR + expected return

@router.get("/{symbol}/price-targets")
async def get_price_targets(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Sprint 5 — todos-v5 Phase 6.2 + 7.1.

    Model-driven probabilistic price targets:
      - Real ATR from the last 252 daily bars (not a hardcoded 2% estimate)
      - Expected return derived from Sharpe-weighted ML signals
      - Kelly Criterion position sizing from live prediction accuracy
      - Falls back gracefully at each step if data is unavailable

    Also includes Kelly Criterion sizing so the frontend doesn't need a second endpoint.
    """
    from app.services.price_target_service import (  # noqa: PLC0415
        fetch_live_indicators_sync,
        compute_price_targets,
        compute_kelly,
        expected_return_from_signals,
    )
    from app.services.prediction_service import get_prediction_stats  # noqa: PLC0415
    from app.services.technical_service import (  # noqa: PLC0415
        compute_technical_consensus, get_trained_timeframes,
    )

    sym  = symbol.upper()
    loop = asyncio.get_running_loop()

    # ── 1. Live market indicators (ATR, price, 52-week range) ─────────────────
    indicators = await loop.run_in_executor(None, fetch_live_indicators_sync, sym)
    if not indicators or indicators.get("current_price", 0) <= 0:
        return {
            "symbol": sym, "available": False,
            "message": "Could not fetch current price or ATR. Check that yfinance is reachable.",
        }

    current_price = indicators["current_price"]
    atr_14        = indicators["atr_14"]

    # ── 2. ML signal context — expected return from trained models ────────────
    raw_signals:    list[dict] = []
    expected_return = 0.0
    confidence_frac = 0.5
    horizon_label   = "~3 days"

    trained_tfs = await loop.run_in_executor(None, get_trained_timeframes, sym)
    if trained_tfs:
        try:
            consensus = await loop.run_in_executor(None, compute_technical_consensus, sym)
            raw_signals = consensus.get("signals", [])
            expected_return, confidence_frac, horizon_label = expected_return_from_signals(raw_signals)
        except Exception as exc:
            logger.debug("Could not compute consensus for price targets (%s): %s", sym, exc)

    # ── 3. Probabilistic price targets ───────────────────────────────────────
    targets = compute_price_targets(
        current_price=current_price,
        atr_14=atr_14,
        expected_return=expected_return,
        confidence=confidence_frac,
        horizon_label=horizon_label,
    )

    # ── 4. Kelly Criterion from prediction DB ─────────────────────────────────
    kelly: dict = {}
    try:
        stats = await get_prediction_stats(db, sym)
        # Use the best performing timeframe stats, or fallback to 1d
        tf_stats = stats.get("timeframes", {})
        best_tf  = stats.get("best_performing_timeframe") or "1d"
        best_stat = tf_stats.get(best_tf, {})

        win_rate    = best_stat.get("live_accuracy")
        n_resolved  = best_stat.get("total_resolved", 0)
        avg_win     = best_stat.get("avg_return_correct")
        avg_loss    = best_stat.get("avg_return_wrong")

        if win_rate is not None and avg_win is not None and avg_loss is not None and n_resolved >= 10:
            kelly = compute_kelly(
                win_rate=win_rate,
                avg_win_pct=avg_win,
                avg_loss_pct=avg_loss,
                n_resolved=n_resolved,
                source="live",
            )
        else:
            # Fall back to validation accuracy from registry
            records = _read_registry()
            rec_1d = next(
                (r for r in reversed(records)
                 if r.get("symbol", "").upper() == sym and r.get("timeframe") == "1d"),
                None,
            )
            if rec_1d:
                val_acc = rec_1d.get("metrics", {}).get(
                    rec_1d.get("model_name", ""), {}\
                ).get("accuracy", 0.0) or 0.52
                val_ret = rec_1d.get("metrics", {}).get(
                    rec_1d.get("model_name", ""), {}\
                ).get("total_return", 0.0)
                # Rough avg win/loss from validation return and win rate
                avg_win_est  = val_ret / max(val_acc * 100, 1) if val_acc > 0 else 0.02
                avg_loss_est = -val_ret / max((1 - val_acc) * 100, 1) if val_acc < 1 else -0.02
                kelly = compute_kelly(
                    win_rate=max(val_acc, 0.5),
                    avg_win_pct=max(avg_win_est, 0.005),
                    avg_loss_pct=min(avg_loss_est, -0.005),
                    n_resolved=0,
                    source="validation",
                )
    except Exception as exc:
        logger.debug("Kelly computation failed for %s (non-fatal): %s", sym, exc)

    # ── 5. Signal summary for context ────────────────────────────────────────
    signal_summary = []
    for s in raw_signals:
        signal_summary.append({
            "timeframe":  s.get("timeframe"),
            "direction":  s.get("direction"),
            "confidence": s.get("confidence"),
            "sharpe":     s.get("validation_sharpe"),
        })

    return {
        "symbol":        sym,
        "available":     True,
        "current_price": current_price,
        "atr_14":        atr_14,
        "atr_pct":       indicators.get("atr_pct"),
        "high_52w":      indicators.get("high_52w"),
        "low_52w":       indicators.get("low_52w"),
        "pct_from_52w_high": indicators.get("pct_from_52w_high"),
        "pct_from_52w_low":  indicators.get("pct_from_52w_low"),
        "targets":       targets,
        "kelly":         kelly if kelly else None,
        "expected_return":    round(expected_return * 100, 2),
        "model_confidence":   round(confidence_frac * 100, 1),
        "horizon_label":      horizon_label,
        "signals_used":       signal_summary,
        "models_trained":     bool(trained_tfs),
        "disclaimer": (
            "Probabilistic estimates based on ATR and ML model expected return. "
            "Not financial advice. Past model performance does not guarantee future results."
        ),
    }


# ── /{symbol}/kelly ───────────────────────────────────────────────────────────

@router.get("/{symbol}/kelly")
async def get_kelly_sizing(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Sprint 5 — todos-v5 Phase 7.1.

    Standalone Kelly Criterion endpoint for when price targets aren't needed.
    Returns position sizing suggestion based on live prediction accuracy.
    """
    from app.services.price_target_service import compute_kelly  # noqa: PLC0415
    from app.services.prediction_service import get_prediction_stats  # noqa: PLC0415

    sym = symbol.upper()
    try:
        stats    = await get_prediction_stats(db, sym)
        tf_stats = stats.get("timeframes", {})
        best_tf  = stats.get("best_performing_timeframe") or "1d"
        best     = tf_stats.get(best_tf, {})

        win_rate   = best.get("live_accuracy")
        n_resolved = best.get("total_resolved", 0)
        avg_win    = best.get("avg_return_correct")
        avg_loss   = best.get("avg_return_wrong")

        if win_rate is None or avg_win is None or avg_loss is None or n_resolved < 10:
            return {
                "symbol": sym, "available": False,
                "message": (
                    f"Not enough live predictions yet ({n_resolved} resolved). "
                    "Kelly sizing requires at least 10 resolved predictions per timeframe."
                ),
                "n_resolved": n_resolved,
            }

        kelly = compute_kelly(
            win_rate=win_rate, avg_win_pct=avg_win, avg_loss_pct=avg_loss,
            n_resolved=n_resolved, source="live",
        )
        return {"symbol": sym, "available": True, "timeframe_used": best_tf, **kelly}

    except Exception as exc:
        logger.error("Kelly endpoint error for %s: %s", sym, exc)
        return {"symbol": sym, "available": False, "message": str(exc)}


# ── /{symbol}/prediction-history ─────────────────────────────────────────────

@router.get("/{symbol}/prediction-history")
async def get_prediction_history(
    symbol:    str,
    timeframe: str = "1d",
    limit:     int = 30,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Sprint 6 — todos-v6 B7 (deep-dive page).

    Returns the last N resolved predictions for a symbol/timeframe,
    newest first. Used by the /model-info/[symbol] prediction history table.
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.models.ml_prediction import MLPrediction  # noqa: PLC0415

    sym = symbol.upper()
    tf  = timeframe.lower()

    result = await db.execute(
        select(
            MLPrediction.predicted_at,
            MLPrediction.predicted_direction,
            MLPrediction.confidence,
            MLPrediction.price_at_prediction,
            MLPrediction.price_at_outcome,
            MLPrediction.actual_return,
            MLPrediction.was_correct,
        )
        .where(
            MLPrediction.symbol    == sym,
            MLPrediction.timeframe == tf,
            MLPrediction.outcome_resolved_at.isnot(None),
        )
        .order_by(MLPrediction.predicted_at.desc())
        .limit(max(1, min(limit, 200)))
    )
    rows = result.fetchall()
    return [
        {
            "predicted_at":        r.predicted_at.isoformat(),
            "predicted_direction": r.predicted_direction,
            "confidence":          r.confidence,
            "price_at_prediction": r.price_at_prediction,
            "price_at_outcome":    r.price_at_outcome,
            "actual_return":       r.actual_return,
            "was_correct":         r.was_correct,
        }
        for r in rows
    ]
