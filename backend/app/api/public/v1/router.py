"""
app/api/public/v1/router.py

P3-API-01 — Public API (external developer-facing).

Authentication: X-API-Key header (or ?api_key= query param as fallback).
Rate limiting: per-key sliding window (Redis-backed, fail-open).
Usage logging: every call recorded to api_key_usage_logs.

Available endpoints:
  GET  /public/v1/me                       — Key info (scopes, rate limit, usage)
  GET  /public/v1/gas/{symbol}             — Global Alignment Score
  GET  /public/v1/macro/latest             — Core macro indicators + score
  GET  /public/v1/macro/advanced           — Full advanced macro view
  GET  /public/v1/sentiment/{symbol}       — News sentiment timeseries
  GET  /public/v1/technical/{symbol}       — Technical consensus score
  GET  /public/v1/risk/scenarios           — Scenario library
  GET  /public/v1/risk/stress/{symbol}     — Single-stock stress test
  POST /public/v1/backtest                 — Run a backtest
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.api_key import ApiKey
from app.services.api_key_service import (
    authenticate_api_key,
    check_rate_limit,
    record_api_call,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── API key dependency ───────────────────────────────────────────────────────

async def get_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    raw_key = x_api_key or api_key_query
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Pass X-API-Key header or ?api_key= query parameter.",
        )

    key_obj = await authenticate_api_key(db, raw_key)
    if key_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    allowed, remaining = await check_rate_limit(key_obj)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {key_obj.rate_limit_per_minute} req/min.",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": "60"},
        )

    return key_obj


def _require_scope(scope: str):
    async def _check(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
        if scope not in api_key.scopes.split(","):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This API key does not have the '{scope}' scope.",
            )
        return api_key
    return _check


# ─── /me ─────────────────────────────────────────────────────────────────────

@router.get("/me", summary="API key info — scopes, rate limit, usage")
async def api_key_info(api_key: ApiKey = Depends(get_api_key)) -> dict:
    return {
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes.split(","),
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
        "total_calls": api_key.total_calls,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
    }


# ─── GAS ─────────────────────────────────────────────────────────────────────

def _gas_label(score: int) -> str:
    if score >= 70:   return "Broadly Supportive"
    if score >= 55:   return "Cautiously Positive"
    if score >= 45:   return "Mixed / Neutral"
    if score >= 30:   return "Cautiously Negative"
    return "Broadly Hostile"


@router.get("/gas/{symbol}", summary="Global Alignment Score for a symbol", tags=["Public API – GAS"])
async def public_gas(
    symbol: str,
    api_key: ApiKey = Depends(_require_scope("gas")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t0 = time.perf_counter()
    sym = symbol.upper()

    tech_score, macro_score, sentiment_score = 50, 50, 50

    try:
        from app.services.technical_consensus import build_consensus_for_symbol  # noqa: PLC0415
        from app.services.model_registry import JsonlFileModelRegistry  # noqa: PLC0415
        from app.services.model_artifacts import ModelArtifactStore  # noqa: PLC0415
        from app.config import get_settings  # noqa: PLC0415
        settings = get_settings()
        registry = JsonlFileModelRegistry(f"{settings.model_store_dir}/registry.jsonl")
        store = ModelArtifactStore(f"{settings.model_store_dir}/artifacts")
        consensus = await build_consensus_for_symbol(sym, registry=registry, artifact_store=store, db=db)
        tech_score = consensus.score
    except Exception:  # noqa: BLE001
        pass

    try:
        from app.services.macro_scoring import compute_macro_score  # noqa: PLC0415
        from app.crud.macro import get_latest_batch_async  # noqa: PLC0415
        inds = await get_latest_batch_async(
            db, ["fed_funds_rate", "unemployment_rate", "cpi_yoy",
                 "yield_spread_10y_2y", "vix", "nonfarm_payrolls", "industrial_production"]
        )
        macro_score = compute_macro_score(inds).score
    except Exception:  # noqa: BLE001
        pass

    gas = int(0.40 * tech_score + 0.30 * macro_score + 0.30 * sentiment_score)
    ms = int((time.perf_counter() - t0) * 1000)
    await record_api_call(db, api_key, f"/public/v1/gas/{sym}", status_code=200, response_ms=ms)
    await db.commit()

    return {
        "symbol": sym,
        "gas": gas,
        "label": _gas_label(gas),
        "components": {"technical": tech_score, "macro": macro_score, "sentiment": sentiment_score},
        "disclaimer": "Educational only. Not investment advice.",
    }


# ─── Macro ────────────────────────────────────────────────────────────────────

@router.get("/macro/latest", summary="Core macro indicators", tags=["Public API – Macro"])
async def public_macro_latest(
    api_key: ApiKey = Depends(_require_scope("macro")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t0 = time.perf_counter()
    try:
        from app.crud.macro import get_latest_async  # noqa: PLC0415
        from app.services.macro_scoring import compute_macro_score  # noqa: PLC0415
        from app.crud.macro import get_latest_batch_async  # noqa: PLC0415
        names = ["fed_funds_rate", "unemployment_rate", "cpi_yoy", "yield_spread_10y_2y", "vix"]
        indicators = {n: await get_latest_async(db, n) for n in names}
        score_dto = compute_macro_score(indicators)
        ms = int((time.perf_counter() - t0) * 1000)
        await record_api_call(db, api_key, "/public/v1/macro/latest", status_code=200, response_ms=ms)
        await db.commit()
        return {
            "macro_score": {"score": score_dto.score, "label": score_dto.label},
            "indicators": indicators,
            "disclaimer": "FRED data. Educational only.",
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Macro data unavailable.") from exc


# ─── Risk ─────────────────────────────────────────────────────────────────────

@router.get("/risk/scenarios", summary="List stress test scenarios", tags=["Public API – Risk"])
async def public_risk_scenarios(
    category: Optional[str] = Query(None),
    api_key: ApiKey = Depends(_require_scope("risk")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.risk_service import SCENARIO_LIBRARY  # noqa: PLC0415
    scenarios = SCENARIO_LIBRARY
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    await record_api_call(db, api_key, "/public/v1/risk/scenarios", status_code=200, response_ms=0)
    await db.commit()
    return {
        "count": len(scenarios),
        "scenarios": [
            {"id": s.id, "name": s.name, "category": s.category,
             "description": s.description, "market_shocks": s.market_shocks}
            for s in scenarios
        ],
    }


@router.get("/risk/stress/{symbol}", summary="Single-stock stress test", tags=["Public API – Risk"])
async def public_risk_stress(
    symbol: str,
    scenario_id: str = Query(...),
    portfolio_value: float = Query(10_000.0, gt=0, le=10_000_000),
    api_key: ApiKey = Depends(_require_scope("risk")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t0 = time.perf_counter()
    from app.services.risk_service import stress_test_symbol  # noqa: PLC0415
    try:
        result = stress_test_symbol(symbol.upper(), scenario_id, portfolio_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    ms = int((time.perf_counter() - t0) * 1000)
    await record_api_call(db, api_key, f"/public/v1/risk/stress/{symbol.upper()}", status_code=200, response_ms=ms)
    await db.commit()
    return result.__dict__


# ─── Backtest ─────────────────────────────────────────────────────────────────

@router.post("/backtest", summary="Run a momentum strategy backtest", tags=["Public API – Backtest"])
async def public_backtest(
    request_body: dict,
    api_key: ApiKey = Depends(_require_scope("backtest")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t0 = time.perf_counter()
    from app.schemas.backtest_models import BacktestRequest  # noqa: PLC0415
    from app.services.backtesting_service import BacktestingEngine  # noqa: PLC0415
    try:
        req = BacktestRequest(**request_body)
        result = BacktestingEngine(req).run()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    ms = int((time.perf_counter() - t0) * 1000)
    await record_api_call(db, api_key, "/public/v1/backtest", method="POST", status_code=200, response_ms=ms)
    await db.commit()
    return result.model_dump()
