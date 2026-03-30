"""
app/services/scrapers/cnn_fear_greed.py
CNN Fear & Greed Index scraper (Sprint 40 — todos-v4 Phase 6 #1).

Polls the CNN Money dataviz API hourly.
Stores score (0-100) + label in `external_signals` table.
Normalised value (0.0–1.0) exposed as `fear_greed_norm` for ML feature engineering.

Signal stored:
  source="cnn_fear_greed", symbol=NULL, signal_name="fear_greed_score"  → raw 0-100
  source="cnn_fear_greed", symbol=NULL, signal_name="fear_greed_norm"   → 0.0–1.0

Usage:
    fetcher = CnnFearGreedFetcher()
    result  = await fetcher.fetch_and_store(db)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_signal import ExternalSignal

logger = logging.getLogger(__name__)

_CNN_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
_TIMEOUT = 15.0


class CnnFearGreedFetcher:
    """Fetches CNN Fear & Greed score and upserts into external_signals."""

    async def fetch_and_store(self, db: AsyncSession) -> dict[str, Any]:
        """
        Returns:
            {"score": float, "label": str, "norm": float, "stored": True/False}
        """
        raw = await self._fetch_raw()
        if raw is None:
            return {"score": None, "label": None, "norm": None, "stored": False}

        score: float = float(raw.get("score", 0))
        label: str   = raw.get("rating", "unknown")
        norm:  float = round(score / 100.0, 4)
        ts           = datetime.now(timezone.utc)

        db.add(ExternalSignal(
            source="cnn_fear_greed",
            symbol=None,
            signal_name="fear_greed_score",
            value=score,
            raw_json={"label": label, "ts": ts.isoformat()},
            fetched_at=ts,
        ))
        db.add(ExternalSignal(
            source="cnn_fear_greed",
            symbol=None,
            signal_name="fear_greed_norm",
            value=norm,
            raw_json=None,
            fetched_at=ts,
        ))
        await db.commit()
        logger.info("CNN Fear & Greed: score=%.1f (%s), norm=%.4f", score, label, norm)
        return {"score": score, "label": label, "norm": norm, "stored": True}

    async def get_latest(self, db: AsyncSession) -> dict[str, Any] | None:
        """
        Read the most recently stored CNN score without fetching from the API.
        Used by macro endpoints and ML feature engineering.
        """
        from sqlalchemy import select, desc  # noqa: PLC0415
        result = await db.execute(
            select(ExternalSignal)
            .where(
                ExternalSignal.source == "cnn_fear_greed",
                ExternalSignal.signal_name == "fear_greed_score",
            )
            .order_by(desc(ExternalSignal.fetched_at))
            .limit(1)
        )
        row = result.scalars().first()
        if row is None:
            return None
        return {
            "score":      row.value,
            "label":      (row.raw_json or {}).get("label", "unknown"),
            "norm":       round(row.value / 100.0, 4),
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        }

    # ── private ───────────────────────────────────────────────────────────────

    async def _fetch_raw(self) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_CNN_URL, headers={"User-Agent": "fin-eye/1.0"})
                resp.raise_for_status()
                data = resp.json()
                # CNN endpoint returns {"fear_and_greed": {"score": ..., "rating": ...}, ...}
                return data.get("fear_and_greed") or data
        except Exception as exc:
            logger.warning("CNN Fear & Greed fetch failed: %s", exc)
            return None
