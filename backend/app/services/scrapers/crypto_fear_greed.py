"""
app/services/scrapers/crypto_fear_greed.py
Crypto Fear & Greed Index scraper (Sprint 40 — todos-v4 Phase 6 #2).

Polls the Alternative.me Fear & Greed API (free, no key required).
Applies to crypto tickers: BTC-USD, ETH-USD (and any symbol where
`is_crypto(symbol)` returns True).

Signals stored:
  source="crypto_fear_greed", symbol=NULL, signal_name="crypto_fear_greed_score"  → 0-100
  source="crypto_fear_greed", symbol=NULL, signal_name="crypto_fear_greed_norm"   → 0.0–1.0

For crypto-specific tickers the `crypto_fear_greed_norm` feature is added by
`engineer_features()` in ml_pipeline.py.

Usage:
    fetcher = CryptoFearGreedFetcher()
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

_ALTME_URL = "https://api.alternative.me/fng/?limit=1"
_TIMEOUT   = 15.0

# Tickers considered crypto — used by feature builder
CRYPTO_SYMBOLS = frozenset({"BTC-USD", "ETH-USD", "BTC", "ETH"})


def is_crypto(symbol: str) -> bool:
    return symbol.upper() in CRYPTO_SYMBOLS or symbol.upper().endswith("-USD")


class CryptoFearGreedFetcher:
    """Fetches Crypto Fear & Greed score and upserts into external_signals."""

    async def fetch_and_store(self, db: AsyncSession) -> dict[str, Any]:
        raw = await self._fetch_raw()
        if raw is None:
            return {"score": None, "label": None, "norm": None, "stored": False}

        score: float = float(raw.get("value", 0))
        label: str   = raw.get("value_classification", "unknown")
        norm:  float = round(score / 100.0, 4)
        ts           = datetime.now(timezone.utc)

        db.add(ExternalSignal(
            source="crypto_fear_greed",
            symbol=None,
            signal_name="crypto_fear_greed_score",
            value=score,
            raw_json={"label": label, "ts": ts.isoformat()},
            fetched_at=ts,
        ))
        db.add(ExternalSignal(
            source="crypto_fear_greed",
            symbol=None,
            signal_name="crypto_fear_greed_norm",
            value=norm,
            raw_json=None,
            fetched_at=ts,
        ))
        await db.commit()
        logger.info("Crypto Fear & Greed: score=%.1f (%s), norm=%.4f", score, label, norm)
        return {"score": score, "label": label, "norm": norm, "stored": True}

    async def get_latest(self, db: AsyncSession) -> dict[str, Any] | None:
        from sqlalchemy import select, desc  # noqa: PLC0415
        result = await db.execute(
            select(ExternalSignal)
            .where(
                ExternalSignal.source == "crypto_fear_greed",
                ExternalSignal.signal_name == "crypto_fear_greed_score",
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

    async def _fetch_raw(self) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_ALTME_URL, headers={"User-Agent": "fin-eye/1.0"})
                resp.raise_for_status()
                data = resp.json()
                entries = data.get("data", [])
                return entries[0] if entries else None
        except Exception as exc:
            logger.warning("Crypto Fear & Greed fetch failed: %s", exc)
            return None
