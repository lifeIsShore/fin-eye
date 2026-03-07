"""
app/services/event_service.py
─────────────────────────────────────────────────────────────────────────────
Economic calendar service — wired to Finnhub Economic Calendar API.

Finnhub endpoint:
  GET https://finnhub.io/api/v1/calendar/economic
  Params: from (YYYY-MM-DD), to (YYYY-MM-DD), token

Response shape (each item):
  {
    "actual":   "0.3",          # reported value (null if not yet released)
    "country":  "US",
    "estimate": "0.3",          # consensus estimate
    "event":    "Core CPI (MoM)",
    "impact":   "high",         # low | medium | high
    "prev":     "0.4",          # previous period
    "time":     "08:30:00",     # local market time
    "unit":     "%",
    "date":     "2026-03-12"
  }

Fallback behaviour:
  If Finnhub is unreachable, has no API key, or returns an error, the service
  falls back to a deterministic mock set so the UI never breaks.

Caching:
  Results are cached in-process for CACHE_TTL_SECONDS (default 3600 s / 1 h)
  to avoid hammering the free-tier rate limit.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from app.config import settings
from app.schemas.event_models import MarketEvent

logger = logging.getLogger(__name__)

_BASE_URL       = "https://finnhub.io/api/v1/calendar/economic"
_TIMEOUT        = 10.0          # seconds
_LOOKAHEAD_DAYS = 14            # fetch next 14 days
_CACHE_TTL_S    = 3_600         # 1 hour in-process cache

# ─── In-process cache ────────────────────────────────────────────────────────
_cache_data: List[MarketEvent] = []
_cache_ts: Optional[datetime]  = None
_cache_is_real: bool           = False  # True only when backed by live Finnhub data

# ─── Impact normalisation map ────────────────────────────────────────────────
_IMPACT_MAP: dict[str, str] = {
    "high":   "High",
    "medium": "Medium",
    "low":    "Low",
    "1":      "Low",
    "2":      "Medium",
    "3":      "High",
}


class EventService:
    """
    Fetches upcoming macroeconomic events from Finnhub Economic Calendar.
    Falls back to deterministic mock data if the API is unavailable or the
    key is missing.
    """

    def __init__(self) -> None:
        self._api_key: str = settings.finnhub_api_key

    # ─── Public interface ─────────────────────────────────────────────────────

    async def get_upcoming_events(
        self,
        country: Optional[str] = None,
        impact:  Optional[str] = None,
    ) -> List[MarketEvent]:
        """
        Return upcoming macro events, optionally filtered by country and impact.

        Args:
            country: 2-letter country code (e.g. "US", "EU", "UK"). Case-insensitive.
            impact:  "Low", "Medium", or "High". Case-insensitive.

        Returns:
            List of MarketEvent objects sorted by date + time ascending.
        """
        events = await self._get_events()

        if country:
            events = [e for e in events if e.country.upper() == country.upper()]

        if impact:
            events = [e for e in events if e.impact.lower() == impact.lower()]

        return sorted(events, key=lambda x: (x.date, x.time or ""))

    # ─── Caching layer ────────────────────────────────────────────────────────

    async def _get_events(self) -> List[MarketEvent]:
        """Return cached events or fetch fresh data."""
        global _cache_data, _cache_ts, _cache_is_real

        now = datetime.utcnow()
        cache_valid = (
            _cache_ts is not None
            and (now - _cache_ts).total_seconds() < _CACHE_TTL_S
            and len(_cache_data) > 0
            and _cache_is_real  # don't serve stale mock data beyond TTL
        )
        if cache_valid:
            logger.debug("EventService: serving %d events from cache", len(_cache_data))
            return _cache_data

        events, is_real = await self._fetch_from_finnhub()

        if is_real:
            _cache_data    = events
            _cache_ts      = now
            _cache_is_real = True

        return events

    # ─── Fetch ────────────────────────────────────────────────────────────────

    async def _fetch_from_finnhub(self) -> tuple[List[MarketEvent], bool]:
        """
        Fetch events from Finnhub.

        Returns:
            (events, is_real) — is_real=False signals mock fallback was used.
        """
        if not self._api_key:
            logger.warning(
                "EventService: FINNHUB_API_KEY not set — using mock data. "
                "Add your free Finnhub key to .env to enable live events."
            )
            return self._generate_mock_events(), False

        today   = datetime.utcnow().date()
        date_to = today + timedelta(days=_LOOKAHEAD_DAYS)

        params = {
            "from":  today.strftime("%Y-%m-%d"),
            "to":    date_to.strftime("%Y-%m-%d"),
            "token": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

        except httpx.TimeoutException:
            logger.warning("EventService: Finnhub timed out — using mock data")
            return self._generate_mock_events(), False
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "EventService: Finnhub HTTP %s — using mock data",
                exc.response.status_code,
            )
            return self._generate_mock_events(), False
        except Exception as exc:
            logger.warning("EventService: Finnhub fetch failed (%s) — using mock data", exc)
            return self._generate_mock_events(), False

        # Finnhub wraps the calendar list under the "economicCalendar" key
        raw_events: list[dict] = (
            data.get("economicCalendar")
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )

        if not raw_events:
            logger.info(
                "EventService: Finnhub returned 0 events for %s–%s — using mock data",
                today, date_to,
            )
            return self._generate_mock_events(), False

        events = self._parse_finnhub_response(raw_events)
        logger.info("EventService: fetched %d live events from Finnhub", len(events))
        return events, True

    # ─── Parsing ──────────────────────────────────────────────────────────────

    def _parse_finnhub_response(self, raw: list[dict]) -> List[MarketEvent]:
        """Convert Finnhub calendar items into MarketEvent schema objects."""
        events: List[MarketEvent] = []
        for item in raw:
            try:
                impact_raw = str(item.get("impact", "")).lower()
                impact     = _IMPACT_MAP.get(impact_raw, "Low")

                # Finnhub uses 2-letter ISO codes; normalise GB → UK for UI consistency
                country = str(item.get("country", "US")).upper()
                if country == "GB":
                    country = "UK"

                # Time format: "08:30:00" — trim seconds for display
                raw_time = item.get("time")
                time_str: Optional[str] = None
                if raw_time:
                    parts    = str(raw_time).split(":")
                    time_str = f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else str(raw_time)

                # Append unit (e.g. "%") to numeric values when present
                unit = item.get("unit", "")

                def _fmt(val: object) -> Optional[str]:
                    if val is None or val == "":
                        return None
                    s = str(val)
                    if unit and not s.endswith(unit):
                        return f"{s}{unit}"
                    return s

                events.append(
                    MarketEvent(
                        id          = str(uuid.uuid4()),
                        date        = str(item.get("date", "")),
                        time        = time_str,
                        title       = str(item.get("event", "Economic Event")),
                        description = None,  # Finnhub doesn't provide descriptions
                        impact      = impact,
                        country     = country,
                        actual      = _fmt(item.get("actual")),
                        estimate    = _fmt(item.get("estimate")),
                        previous    = _fmt(item.get("prev")),
                    )
                )
            except Exception as exc:
                logger.debug("EventService: skipping malformed event item: %s", exc)

        return events

    # ─── Mock fallback ────────────────────────────────────────────────────────

    def _generate_mock_events(self) -> List[MarketEvent]:
        """
        Deterministic mock events offset from today — used when Finnhub is
        unreachable. Dates are always relative so the UI shows plausible
        upcoming events rather than stale fixed dates.
        """
        today = datetime.utcnow()

        blueprints: list[dict] = [
            {
                "title":    "Fed Interest Rate Decision",
                "impact":   "High",
                "country":  "US",
                "delay":    2,
                "time":     "14:00",
                "estimate": "5.25%",
                "previous": "5.50%",
            },
            {
                "title":    "Core CPI (MoM)",
                "impact":   "High",
                "country":  "US",
                "delay":    5,
                "time":     "08:30",
                "estimate": "0.3%",
                "previous": "0.4%",
            },
            {
                "title":    "Non-Farm Payrolls",
                "impact":   "High",
                "country":  "US",
                "delay":    7,
                "time":     "08:30",
                "estimate": "180K",
                "previous": "210K",
            },
            {
                "title":    "ECB Press Conference",
                "impact":   "High",
                "country":  "EU",
                "delay":    1,
                "time":     "14:45",
                "estimate": None,
                "previous": None,
            },
            {
                "title":    "CPI (YoY)",
                "impact":   "Medium",
                "country":  "UK",
                "delay":    8,
                "time":     "07:00",
                "estimate": "3.8%",
                "previous": "4.0%",
            },
            {
                "title":    "GDP Growth Rate (QoQ)",
                "impact":   "High",
                "country":  "CN",
                "delay":    12,
                "time":     "02:00",
                "estimate": "4.5%",
                "previous": "4.7%",
            },
            {
                "title":    "Initial Jobless Claims",
                "impact":   "Medium",
                "country":  "US",
                "delay":    3,
                "time":     "08:30",
                "estimate": "215K",
                "previous": "212K",
            },
            {
                "title":    "Retail Sales (MoM)",
                "impact":   "Medium",
                "country":  "US",
                "delay":    10,
                "time":     "08:30",
                "estimate": "0.5%",
                "previous": "0.6%",
            },
            {
                "title":    "Manufacturing PMI",
                "impact":   "Low",
                "country":  "EU",
                "delay":    4,
                "time":     "10:00",
                "estimate": "48.5",
                "previous": "49.0",
            },
            {
                "title":    "BoJ Policy Rate Decision",
                "impact":   "High",
                "country":  "JP",
                "delay":    9,
                "time":     "03:00",
                "estimate": "0.5%",
                "previous": "0.25%",
            },
        ]

        return [
            MarketEvent(
                id          = str(uuid.uuid4()),
                date        = (today + timedelta(days=bp["delay"])).strftime("%Y-%m-%d"),
                time        = bp["time"],
                title       = bp["title"],
                description = None,
                impact      = bp["impact"],
                country     = bp["country"],
                estimate    = bp["estimate"],
                previous    = bp["previous"],
                actual      = None,
            )
            for bp in blueprints
        ]
