"""
app/schemas/analytics_models.py

Canonical analytics event taxonomy and Pydantic schemas for CORE-ANALYTICS-01.

Event Naming Convention:
  <noun>_<past_tense_verb>
  Examples: user_signed_up, dashboard_viewed, backtest_run

The EventName enum is the single source of truth for all tracked events.
The frontend and backend both import this taxonomy conceptually — the frontend
sends string event names validated here at the API boundary.

Property guidelines (enforced at service layer):
  - Never include: email, name, IP address, raw user-agent strings
  - Always include: relevant context (symbol, feature variant, etc.)
  - Keep values simple: strings, numbers, booleans
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─── Canonical Event Taxonomy ─────────────────────────────────────────────────

class EventName(str, Enum):
    # ── Acquisition & Activation ──────────────────────────────────────────────
    USER_SIGNED_UP         = "user_signed_up"
    USER_LOGGED_IN         = "user_logged_in"
    USER_LOGGED_OUT        = "user_logged_out"
    CONSENT_ACCEPTED       = "consent_accepted"
    ONBOARDING_TOUR_STARTED  = "onboarding_tour_started"
    ONBOARDING_TOUR_COMPLETED = "onboarding_tour_completed"
    ONBOARDING_TOUR_SKIPPED  = "onboarding_tour_skipped"

    # ── Dashboard & Core Features ─────────────────────────────────────────────
    DASHBOARD_VIEWED       = "dashboard_viewed"
    SYMBOL_SEARCHED        = "symbol_searched"
    SYMBOL_CHANGED         = "symbol_changed"
    WATCHLIST_SYMBOL_ADDED = "watchlist_symbol_added"
    WATCHLIST_SYMBOL_REMOVED = "watchlist_symbol_removed"

    # ── Technical / ML ────────────────────────────────────────────────────────
    TECHNICAL_CONSENSUS_VIEWED = "technical_consensus_viewed"

    # ── Macro ─────────────────────────────────────────────────────────────────
    MACRO_DASHBOARD_VIEWED = "macro_dashboard_viewed"
    MACRO_ADVANCED_VIEWED  = "macro_advanced_viewed"

    # ── Sentiment ─────────────────────────────────────────────────────────────
    SENTIMENT_TAB_VIEWED   = "sentiment_tab_viewed"
    RETAIL_SENTIMENT_VIEWED = "retail_sentiment_viewed"

    # ── Backtesting ───────────────────────────────────────────────────────────
    BACKTEST_RUN           = "backtest_run"
    BACKTEST_STRATEGY_SAVED = "backtest_strategy_saved"
    BACKTEST_STRATEGY_LOADED = "backtest_strategy_loaded"

    # ── Hedging ───────────────────────────────────────────────────────────────
    HEDGING_SIMULATOR_VIEWED = "hedging_simulator_viewed"
    HEDGING_ADVANCED_VIEWED  = "hedging_advanced_viewed"

    # ── Portfolio ─────────────────────────────────────────────────────────────
    PORTFOLIO_CREATED      = "portfolio_created"
    PORTFOLIO_VIEWED       = "portfolio_viewed"

    # ── Alerts ────────────────────────────────────────────────────────────────
    ALERT_CREATED          = "alert_created"
    ALERT_TRIGGERED        = "alert_triggered"

    # ── Content / Learn ──────────────────────────────────────────────────────
    LEARN_TAB_VIEWED       = "learn_tab_viewed"
    BLOG_POST_VIEWED       = "blog_post_viewed"
    CASE_STUDY_VIEWED      = "case_study_viewed"

    # ── Community & Showcase ─────────────────────────────────────────────────
    COMMUNITY_PAGE_VIEWED  = "community_page_viewed"
    SHOWCASE_VIEWED        = "showcase_viewed"
    SHOWCASE_PRODUCT_CLICKED = "showcase_product_clicked"

    # ── Settings / Profile ────────────────────────────────────────────────────
    SETTINGS_PAGE_VIEWED   = "settings_page_viewed"
    PROFILE_UPDATED        = "profile_updated"
    PASSWORD_CHANGED       = "password_changed"

    # ── Billing / Conversion ─────────────────────────────────────────────────
    BILLING_PAGE_VIEWED    = "billing_page_viewed"
    UPGRADE_CTA_CLICKED    = "upgrade_cta_clicked"

    # ── Errors & Performance ─────────────────────────────────────────────────
    API_ERROR_ENCOUNTERED  = "api_error_encountered"


# ─── Funnel definitions — used for dashboard rendering ──────────────────────

ACTIVATION_FUNNEL: list[EventName] = [
    EventName.USER_SIGNED_UP,
    EventName.CONSENT_ACCEPTED,
    EventName.DASHBOARD_VIEWED,
    EventName.MACRO_DASHBOARD_VIEWED,
    EventName.BACKTEST_RUN,
    EventName.HEDGING_SIMULATOR_VIEWED,
]

CONVERSION_FUNNEL: list[EventName] = [
    EventName.BILLING_PAGE_VIEWED,
    EventName.UPGRADE_CTA_CLICKED,
]

FEATURE_ADOPTION_EVENTS: list[EventName] = [
    EventName.BACKTEST_RUN,
    EventName.HEDGING_SIMULATOR_VIEWED,
    EventName.HEDGING_ADVANCED_VIEWED,
    EventName.MACRO_ADVANCED_VIEWED,
    EventName.RETAIL_SENTIMENT_VIEWED,
    EventName.PORTFOLIO_CREATED,
    EventName.ALERT_CREATED,
    EventName.SHOWCASE_PRODUCT_CLICKED,
    EventName.COMMUNITY_PAGE_VIEWED,
]


# ─── API Schemas ──────────────────────────────────────────────────────────────

class TrackEventRequest(BaseModel):
    """
    Payload sent from the frontend to POST /api/v1/analytics/event.
    The backend fills in user_id (from JWT), server timestamp, and validates event_name.
    """
    event_name: str = Field(..., description="Canonical event name from the EventName taxonomy")
    session_id: UUID | None = Field(None, description="Client-generated session UUID")
    anon_id: str | None = Field(None, max_length=64, description="SHA-256 hash for pre-login tracking")
    page: str | None = Field(None, max_length=255, description="Current page path, e.g. /dashboard")
    feature: str | None = Field(None, max_length=128, description="Feature identifier")
    properties: dict[str, Any] = Field(default_factory=dict, description="Event properties — no PII")

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        valid = {e.value for e in EventName}
        if v not in valid:
            raise ValueError(f"Unknown event_name '{v}'. Must be one of: {sorted(valid)}")
        return v

    @field_validator("properties")
    @classmethod
    def strip_pii_keys(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Block obviously PII-bearing keys at the schema layer.
        This is a defence-in-depth measure — the frontend must also be careful.
        """
        blocked = {"email", "name", "password", "ip", "user_agent", "phone", "address"}
        for key in list(v.keys()):
            if key.lower() in blocked:
                del v[key]
        return v


class EventRecordedResponse(BaseModel):
    status: str = "ok"
    event_id: str


# ─── Analytics Dashboard Schemas ──────────────────────────────────────────────

class FunnelStep(BaseModel):
    event_name: str
    label: str
    unique_users: int
    total_occurrences: int
    conversion_from_previous_pct: float | None  # None for the first step


class FunnelReport(BaseModel):
    funnel_name: str
    period_days: int
    steps: list[FunnelStep]


class FeatureAdoptionRow(BaseModel):
    event_name: str
    label: str
    unique_users: int
    total_occurrences: int
    adoption_pct: float  # unique_users / total_signed_up_users * 100


class DailyActiveUsersPoint(BaseModel):
    date: str          # YYYY-MM-DD
    dau: int
    new_users: int


class AnalyticsSummary(BaseModel):
    period_days: int
    total_events: int
    total_signed_up_users: int
    total_active_users: int   # users with at least 1 event in period
    activation_funnel: FunnelReport
    conversion_funnel: FunnelReport
    feature_adoption: list[FeatureAdoptionRow]
    daily_active_users: list[DailyActiveUsersPoint]
    top_pages: list[dict[str, Any]]
    top_symbols: list[dict[str, Any]]


# Human-readable labels for the dashboard
EVENT_LABELS: dict[str, str] = {
    EventName.USER_SIGNED_UP.value:            "Signed Up",
    EventName.USER_LOGGED_IN.value:            "Logged In",
    EventName.CONSENT_ACCEPTED.value:          "Consent Accepted",
    EventName.ONBOARDING_TOUR_STARTED.value:   "Tour Started",
    EventName.ONBOARDING_TOUR_COMPLETED.value: "Tour Completed",
    EventName.DASHBOARD_VIEWED.value:          "Dashboard Viewed",
    EventName.MACRO_DASHBOARD_VIEWED.value:    "Macro Dashboard Viewed",
    EventName.MACRO_ADVANCED_VIEWED.value:     "Advanced Macro Viewed",
    EventName.SENTIMENT_TAB_VIEWED.value:      "Sentiment Tab Viewed",
    EventName.RETAIL_SENTIMENT_VIEWED.value:   "Retail Sentiment Viewed",
    EventName.BACKTEST_RUN.value:              "Backtest Run",
    EventName.BACKTEST_STRATEGY_SAVED.value:   "Strategy Saved",
    EventName.HEDGING_SIMULATOR_VIEWED.value:  "Hedging Simulator Viewed",
    EventName.HEDGING_ADVANCED_VIEWED.value:   "Advanced Hedging Viewed",
    EventName.PORTFOLIO_CREATED.value:         "Portfolio Created",
    EventName.ALERT_CREATED.value:             "Alert Created",
    EventName.LEARN_TAB_VIEWED.value:          "Learn Tab Viewed",
    EventName.BLOG_POST_VIEWED.value:          "Blog Post Viewed",
    EventName.CASE_STUDY_VIEWED.value:         "Case Study Viewed",
    EventName.COMMUNITY_PAGE_VIEWED.value:     "Community Page Viewed",
    EventName.SHOWCASE_PRODUCT_CLICKED.value:  "Showcase Product Clicked",
    EventName.BILLING_PAGE_VIEWED.value:       "Billing Page Viewed",
    EventName.UPGRADE_CTA_CLICKED.value:       "Upgrade CTA Clicked",
}
