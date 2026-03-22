# Fin-Eye — Sprint Progress Tracker
> Last updated: Sprint 10 complete

## Completed Sprints

### ✅ Sprint 0 — Blockers
- LLM service, lightgbm/optuna/shap, MLPrediction model, bug fixes, auth bypass

### ✅ Sprint 1 — LLM Investment Manager
- POST /explanation/{symbol}/generate-insight, LLMInsightCard.tsx, live price endpoint

### ✅ Sprint 2 — Prediction Database
- MLPrediction model + migration, prediction_service, outcome resolver cron

### ✅ Sprint 3 — ML Improvements
- LightGBM + Ensemble, SHAP importance, Prophet removed

### ✅ Sprint 4 — Dev Transparency Layer
- model-details + prediction-stats endpoints, ModelDetailsPanel.tsx (4 tabs)

### ✅ Sprint 5 — Price Targets + Kelly Position Sizing
- Real ATR, model-driven targets, Half-Kelly, PriceTargetCard.tsx

### ✅ Sprint 6 — Optuna Tuning + Drift Alerts + /model-info Deep-Dive
- ModelDriftAlert, drift_service, optuna_tuner, admin_ml endpoints
- scheduler: drift detection + overnight tuning jobs
- frontend/app/model-info/[symbol]/page.tsx (6-tab deep-dive)

### ✅ Sprint 7 — Security Hardening + Dashboard UX Core
- SEC-03/04/05/06: rate limiting, JTI tokens, lockout, security headers
- UX-UI-01/02: Skeletons.tsx, ToastProvider.tsx
- UX-GROWTH-01: GasSparkline.tsx + admin_gas history endpoint

### ✅ Sprint 8 — Dashboard Polish + Backtesting Depth
- app/page.tsx: ErrorBoundary + SectionError + skeleton loaders per section
- components/ErrorBoundary.tsx (NEW)
- backtesting/page.tsx: RiskDisclaimerBar + DrawdownChart + MonthlyHeatmap
- components/GlobalTickerSearch.tsx: live search with debounce + keyboard nav
- backend/app/api/v1/endpoints/symbols.py: GET /api/v1/symbols/search

### ✅ Sprint 9 — Tooltip System + Hedge Disclaimer + api.ts Completions
- components/Tooltip.tsx: Tooltip, InfoTooltip, ScoreTooltip (NEW)
- MarketWeatherWidget: ScoreTooltip on GAS label
- RegimeWidget: ScoreTooltip on both regime tiles + regime/regimeOverride props
- app/hedge/page.tsx: HedgeRiskDisclaimerBar inline disclaimer (targeted patch)
- api.ts: + SymbolResultDto + fetchSymbolSearch()

### ✅ Sprint 10 — Bug Fixes + What Changed Today + New Strategies + Freshness

#### Bug fixes (committed files audit)
- prediction_service.py: sa_int() NameError + func.cast wrong syntax → case((col==True,1),else_=0)
- drift_service.py: same func.cast / case() bugs fixed
- technical.py: backslash line continuation inside dict subscript (syntax error) → extracted variables
- api_price.ts: missing API_BASE_URL constant (ReferenceError at runtime)

#### Backtesting (UX-BACKTEST-01)
- backtesting_service.py: + Mean Reversion strategy (Bollinger Band + RSI oversold bounce)
- backtesting_service.py: + Macro-Responsive strategy (volatility-targeted position sizing)
- backtesting/page.tsx: strategy selector dropdown + strategy-aware parameter fields
  → available as outputs/backtesting_page.tsx

#### What Changed Today (UX-GROWTH-02)
- components/WhatChangedToday.tsx (NEW):
  - Batch-fetches GAS snapshots for all watchlist symbols
  - Shows delta vs previous snapshot with ↑/↓/→ arrows
  - Sorted by biggest absolute move first
  - Clicking a row switches the active dashboard symbol
- admin_gas.py: POST /api/v1/admin/gas/snapshots/batch (NEW public endpoint)
  - Returns latest + previous GAS score per symbol for delta computation

#### Watchlist Overview (POLISH-01)
- app/watchlist-overview/page.tsx (NEW):
  - Grid of GAS cards for all watchlist symbols
  - Sort modes: GAS ↓, GAS ↑, A–Z, Biggest Move
  - Component sub-bars (Tech/Sent/Macro) per card
  - Click to navigate to dashboard with that symbol
- Nav.tsx: Watchlist Overview added to Tools section
  → available as outputs/Nav_final.tsx

#### Data Freshness Indicators (UX-TRUST-01)
- components/FreshnessIndicator.tsx (NEW):
  - Coloured dot: green (<30min) / amber (<60min) / red (stale) / slate (unknown)
  - useFreshness() hook exported for custom use
- app/page.tsx: FreshnessIndicator added to dashboard header for Macro + Sentiment
  → available as outputs/page_dashboard.tsx
- schemas/macro_models.py: MacroLatestResponse + fetched_at?: string | null
- endpoints/macro.py: _build_core_response() injects fetched_at from latest indicator date
- api.ts: MacroLatestDto + fetched_at?: string | null
  → available as outputs/api_final.ts

## Sprint 11 — Remaining (Next)

### High priority
- [ ] GAS History sparkline populates after first nightly precompute run (data-gated)
- [ ] Notification preferences page /settings/notifications (UX-SETTINGS-01)
- [ ] Cross-asset overview row — SPY/QQQ/GLD/TLT/BTC mini GAS row on dashboard
- [ ] WhatChangedToday sentiment freshness — wire sentData fetched_at from backend

### Medium priority
- [ ] Backtesting: strategy description cards in the UI (explain the 3 strategies)
- [ ] /watchlist-overview: add 7-day GAS sparkline per card (reuse GasSparkline component)
- [ ] Data freshness for sentiment: SentimentTimeseriesDto needs fetched_at field

### Data-gated (Sprint 12+)
- [ ] Feature Analysis: regime-conditional accuracy (≥90 days of predictions)
- [ ] Meta-model: "when to trust the base model"

## Files to copy from outputs after this session

```
outputs/api_final.ts          → frontend/lib/api.ts
outputs/page_dashboard.tsx    → frontend/app/page.tsx
outputs/backtesting_page.tsx  → frontend/app/backtesting/page.tsx
outputs/Nav_final.tsx         → frontend/components/Nav.tsx
```

## Manual steps (cumulative)

```bash
# Migrations (only needed once each)
alembic upgrade head    # runs v5_001_ml_predictions + v6_001_model_drift_alerts

# Python deps
pip install slowapi>=0.1.9    # Sprint 7 SEC-03

# No new migrations in Sprint 10.
```

## New files created this session (write directly to these paths)

```
frontend/components/WhatChangedToday.tsx        (NEW)
frontend/components/FreshnessIndicator.tsx       (NEW)
frontend/app/watchlist-overview/page.tsx         (NEW)
```
