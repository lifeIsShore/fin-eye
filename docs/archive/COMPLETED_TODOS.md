# Fin-Eye — Completed Todos Archive
> **Created:** 2026-03-22
> **Purpose:** Items fully implemented across Sprints 0–24. Moved here to keep active todo files clean.
> **Legend:** ✅ = fully implemented · source sprint noted per item

---

## From todos.md (v2 — Original UX Backlog)

### §2 — Educational & Documentation UX
- ✅ **Score Change Explainer banner** — Sprint 22: `app/page.tsx` shows GAS ↑/↓ banner when delta ≥5 pts, with prev→curr, contextual message, dismiss button.

### §3 — General UI/UX Polish
- ✅ **Skeleton Loaders** — Sprint 7: `Skeletons.tsx` component built; layout-accurate skeletons across dashboard sections.
- ✅ **Toast Notification System** — Sprint 7: `ToastProvider.tsx` global top-right toast system; used for train complete, save success, API errors.
- ✅ **Mobile hamburger / drawer nav** — Sprint 7+: `MobileNav` component in `Nav.tsx` with hamburger + full-height drawer for screens below `lg`.

### §4 — Performance & Technical Debt
- ✅ **SWR Error Boundaries** — Sprint 8: `ErrorBoundary.tsx` wrapping each dashboard section; per-section fallback UI.

### §5 — Activation & User Retention
- ✅ **"Aha Moment" — GAS History Sparkline** — Sprint 7: `GasSparkline.tsx` + admin_gas history endpoint. 7-day sparkline on dashboard and watchlist overview.
- ✅ **Email Alert Engine** — Sprint 7+: Threshold-based alerts created, `POST /alerts`, evaluated every 5 min. Email delivery via Resend.
- ✅ **Mini GAS badge on watchlist items** — Sprint 22: `WatchlistWidget.tsx` shows GAS score + `GradeBadge` per watchlist item, polling every 5 min.
- ✅ **"What Changed Today" Dashboard Widget** — Sprint 10: `WhatChangedToday.tsx` batch-fetches GAS snapshots for watchlist symbols, shows delta arrows.
- ✅ **Watchlist Overview page** — Sprint 10: `/watchlist-overview` with GAS cards, sort modes, sparklines, compare mode (Sprint 19).

### §7 — Dashboard Intelligence Upgrades
- ✅ **GAS History Chart (7-day)** — Sprint 7: `GasSparkline.tsx` shows 7-day GAS history.
- ✅ **Cross-Asset Dashboard row** — Sprint 11: `CrossAssetRow.tsx` shows GAS for SPY, QQQ, GLD, TLT, BTC.

### §8 — Backtesting UX Improvements
- ✅ **More Strategy Templates** — Sprint 10: Mean Reversion (Bollinger Band) + Macro-Responsive strategies added.
- ✅ **Monthly Returns Heatmap** — Sprint 8: `MonthlyHeatmap` in `backtesting/page.tsx`.
- ✅ **Drawdown Chart** — Sprint 8: `DrawdownChart` below equity curve in backtesting page.
- ✅ **Walk-Forward Validation Panel** — Sprint 18: `WalkForwardPanel` with fold selector, OOS equity curve, IS vs OOS Sharpe bars.

### §9 — Macro Dashboard Improvements
- ✅ **Fed Meeting Countdown** — Sprint 21: `FomcCountdown` component in `macro/page.tsx` with urgency colour coding (rose/amber/slate) and link to Fed calendar.
- ✅ **Yield Curve Inversion Alert Banner** — Sprint 23: Auto-displays amber banner when `yield_spread_10y_2y < 0`, both Overview and Advanced tabs.

### §13 — Data Quality & Trust
- ✅ **Data Freshness Indicators on every section** — Sprint 10: `FreshnessIndicator.tsx` with green/amber/red dot and "Last updated Xm ago". Applied to macro + sentiment on dashboard.

### §14 — Settings & Personalisation
- ✅ **Notification Preferences page** — Sprint 11: `/settings/notifications` page with email frequency, alert management.
- ✅ **Default Ticker preference** — Sprint 23: `User.default_symbol` DB column + `PATCH /auth/me` + Settings UI + `seedDefaultOnce()` in SymbolContext.

### §16 — Fin-Eye Showcase / Marketplace
- ✅ **Click Analytics on Showcase** — Sprint 13: `trackShowcaseClick()` in `api.ts` + backend analytics endpoint.

### §17 — Admin & Operations
- ✅ **User Lifecycle Dashboard** — Sprint 18: `/admin/analytics` with DAU/WAU/MAU, funnel charts, feature adoption, top tickers.
- ✅ **A/B Experiment Framework** — Sprint 18+: `/admin/experiments` with create/launch/pause/conclude; `assignVariant()` + results endpoint.

---

## From todos-v3.md (v3 — Prioritised Dev Backlog)

### §1 — Pre-Launch Security
- ✅ **Rate limit auth endpoints (SEC-03)** — Sprint 7: `slowapi` Redis-backed limits on login/register/2FA.
- ✅ **Refresh token rotation + logout blacklist (SEC-04)** — Sprint 7: JTI in tokens, Redis blacklist on logout, rotation on refresh.
- ✅ **Account lockout after failed logins (SEC-05)** — Sprint 7: 10 fails in 15min → 30-min lock in Redis.
- ✅ **Security headers middleware (SEC-06)** — Sprint 7: `SecurityHeadersMiddleware` with CSP, X-Frame-Options, HSTS etc.

### §2 — Navigation
- ✅ **Mobile hamburger / drawer nav** — Built: `MobileNav` in `Nav.tsx`, hamburger icon opens full-height drawer, closes on navigation.
- ✅ **Grouped/collapsible sidebar nav** — Built: `Sidebar` in `Nav.tsx` with sections (Core Analysis, Deep Signals, Market Context, Tools, Learn) + collapse/expand toggle.

### §3 — Dashboard
- ✅ **Skeleton loaders (UX-UI-01)** — Sprint 7: layout-accurate skeleton screens across sections.
- ✅ **Global toast system (UX-UI-02)** — Sprint 7: `ToastProvider.tsx` + `useToast()` hook.
- ✅ **GAS History sparkline (UX-GROWTH-01)** — Sprint 7: `GasSparkline.tsx` + admin history endpoint.
- ✅ **Symbol autocomplete search (POLISH-02)** — Sprint 8: `GlobalTickerSearch.tsx` with debounce, keyboard nav, company name + exchange display.
- ✅ **SWR error boundaries (UX-PERF-01)** — Sprint 8: `ErrorBoundary.tsx`, each section fails independently.
- ✅ **"What Changed Today" widget (UX-GROWTH-02)** — Sprint 10: `WhatChangedToday.tsx` with delta arrows, sorted by biggest move.
- ✅ **Score Change Explainer banner (UX-EDU-03)** — Sprint 22: GAS change ≥5pts banner in `page.tsx` with emerald/rose colouring.

### §4 — Watchlist
- ✅ **Watchlist Overview page (POLISH-01)** — Sprint 10: `/watchlist-overview` with GAS cards, sort modes, sparklines.
- ✅ **Mini GAS badge on watchlist items** — Sprint 22: `WatchlistWidget.tsx` shows GAS + grade per item.
- ✅ **Grade filter on watchlist overview** — Sprint 22: Filter pills (All/A&above/A+only/B&above/Tradeable) on `/watchlist-overview`.

### §6 — Macro Dashboard
- ✅ **Fed Meeting countdown timer (UX-MACRO-01)** — Sprint 21: `FomcCountdown` in macro page.
- ✅ **Yield curve inversion alert banner** — Sprint 23: amber banner auto-shows when spread < 0.

### §7 — Backtesting
- ✅ **More strategy templates (UX-BACKTEST-01)** — Sprint 10: Mean Reversion + Macro-Responsive strategies.
- ✅ **Monthly returns heatmap (UX-BACKTEST-02)** — Sprint 8: `MonthlyHeatmap`.
- ✅ **Drawdown chart (UX-BACKTEST-03)** — Sprint 8: `DrawdownChart`.
- ✅ **Walk-forward validation panel** — Sprint 18: `WalkForwardPanel`.

### §11 — Data Quality & Trust
- ✅ **Data freshness indicators (UX-TRUST-01)** — Sprint 10: `FreshnessIndicator.tsx` on macro + sentiment.

### §13 — Settings & Personalisation
- ✅ **Notification Preferences page (UX-SETTINGS-01)** — Sprint 11: `/settings/notifications`.
- ✅ **Default ticker preference** — Sprint 23: full stack (DB column + endpoint + UI + SymbolContext).
- ✅ **Risk profile quiz (PLAN-01)** — Sprint 24: 5-question quiz → Conservative/Income/Moderate/Aggressive. `User.risk_profile` DB column + full UI.

### §14 — Legal & Compliance
- ✅ **Inline risk disclaimer bars on high-liability pages (UX-LEGAL-01)** — Sprint 8: `RiskDisclaimerBar` in backtesting; `HedgeRiskDisclaimerBar` in hedge page.
- ✅ **GDPR data export and deletion flow (CORE-GDPR-01)** — Sprint 7+: "Request Data Export" + "Delete Account" wired in Settings; backend `/gdpr/export` + `/gdpr/delete` endpoints.

### §16 — Portfolio Page
- ✅ **Portfolio-level weighted GAS (P2-PORT-01)** — Sprint 13: `PortfolioGasBanner` with weighted GAS + symbol breakdown bars.
- ✅ **Correlation heatmap (IND-COMPOSITE-02)** — Sprint 19: `CorrelationMatrix` in portfolio page with Pearson heatmap, period picker, colour scale.
- ✅ **Sector breakdown pie (P2-PORT-01)** — Sprint 24: `SectorPieChart` donut chart with 10-colour palette replacing bar list.

### §18 — ML Improvements
- ✅ **SHAP feature importance panel (ASSET-ML-03)** — Sprint 24: `ShapPanel` collapsible component on dashboard, top-5 SHAP features with bars + plain-English descriptions.
- ✅ **Model drift detection (ASSET-ML-02)** — Sprint 6: `ModelDriftAlert` model + `drift_service.py` + drift detection in outcome resolver. `/admin/ml/drift-report` endpoint + Drift tab on model-info page.

---

## From todos-v4.md (v4 — Bulk Pipeline)

- ✅ **Phase 1.3 — "Not Trained" empty state + Train Now button** — Sprint 0+: `TrainNowEmptyState` in `page.tsx` with ▶ Train Now button, polling, toast on complete.
- ✅ **Phase 4.4 — Settings Data Pipeline section** — Sprint 7+: `DataPipelineSection` in settings (admin-only) with OHLCV seed, ML train, news seed controls + live progress.
- ✅ **Phase 4.5 — Ticker page Run+Train control row** — Sprint 4+: `TickerDataPanel.tsx` shows OHLCV/ML/News status + Fetch/Train/Refresh action buttons.
- ✅ **Phase 7.1 — Pipeline overview endpoint** — Built: `GET /api/v1/admin/bulk/pipeline-overview` in `admin_bulk.py`.
- ✅ **Phase 8.2 — TickerDataPanel component** — Sprint 4: `TickerDataPanel.tsx` collapsible panel with data/model status per ticker.

---

## From todos-v5.md (v5 — UX Clarity + LLM + ML)

### Phase 1 — UX Signal Clarity
- ✅ **1.1 FE — Signal card redesign (Layer 1)** — Built: `TimeframeGrid.tsx` has direction icon, plain-English label, confidence bar, horizon description, confidence interpretation label.
- ✅ **1.1 FE — "What drove this?" expandable section (Layer 2)** — Sprint 24: `ShapPanel` component on dashboard below TimeframeGrid with SHAP bars + feature descriptions.
- ✅ **1.1 FE — Multi-timeframe agreement indicator** — Built: `ConsensusSummary` in `TimeframeGrid.tsx` with agreement bar, bullish/bearish/neutral count, plain-English summary text.

### Phase 2 — Dev Transparency Layer
- ✅ **2.1 BE — Model details endpoint** — Built: `GET /api/v1/technical/{symbol}/model-details` in `technical.py`.
- ✅ **2.2 FE — "⚙ Model Details" panel** — Sprint 4+: `ModelDetailsPanel.tsx` side drawer with Overview/Features/Training/All Models tabs. Link from TimeframeGrid.
- ✅ **2.3 FE — `/model-info/{symbol}` deep-dive page** — Sprint 6: `app/model-info/[symbol]/page.tsx` with 7 tabs (Overview, Features, Training, All Models, History, Drift, Regime).

### Phase 3 — LLM Investment Manager
- ✅ **3.3 BE — LLM persona + system prompt** — Sprint 1+: structured 6-section system prompt in `llm_service.py`.
- ✅ **3.4 FE — LLM insight card** — Sprint 1+: `LLMInsightCard.tsx` with SSE streaming (Sprint 12), progressive section rendering, typing cursor, regenerate button.

### Phase 4 — ML Improvements
- ✅ **4.2 BE — LightGBM as 4th competitor** — Sprint 3: `LightGBMWrapper` in `ml_pipeline.py`, competes alongside Logistic, XGBoost, Ensemble.
- ✅ **4.3 BE — Probability-weighted ensemble** — Sprint 3: `EnsembleWrapper` in `ml_pipeline.py` blends Logistic + XGBoost + LightGBM weighted by Sharpe.
- ✅ **4.5 BE — Remove Prophet from competition** — Sprint 3: Prophet removed from signal competition; moved to macro-only context.

### Phase 5 — Prediction Database
- ✅ **5.1 DB — ml_predictions table** — Sprint 2: Alembic migration created, full schema with all columns and indexes.
- ✅ **5.2 BE — Prediction storage on inference** — Sprint 2: `store_prediction()` in `prediction_service.py`, deduplication per symbol/timeframe/day.
- ✅ **5.3 BE — Outcome resolver cron** — Sprint 2: APScheduler job resolving outcomes hourly, fills `price_at_outcome/actual_return/was_correct`.
- ✅ **5.4 BE — Live accuracy stats endpoint** — Sprint 2: `GET /api/v1/technical/{symbol}/prediction-stats` with per-timeframe accuracy, regime breakdown, trend.
- ✅ **5.5 BE — Model drift alert** — Sprint 6: `ModelDriftAlert` model + drift detection cron + `/admin/ml/drift-alerts` + Drift tab on model-info.
- ✅ **5.6 FE — Live accuracy in Model Details** — Sprint 6: History tab on model-info page shows last 30 resolved predictions table + confidence timeline chart (Sprint 20).

### Phase 6 — Probabilistic Price Targets
- ✅ **6.2 BE — Price targets endpoint** — Sprint 5: `GET /api/v1/technical/{symbol}/price-targets` returning ATR-based upside/expected/stop levels.
- ✅ **6.1 FE — Price target display** — Sprint 5: `PriceTargetCard.tsx` SVG range chart with upside/expected/stop levels.

### Phase 7 — Position Sizing
- ✅ **7.1 BE — Kelly Criterion computation** — Sprint 5: `kelly_fraction()` in price targets endpoint using live win rate + avg returns.
- ✅ **7.2 FE — Position size suggestion** — Sprint 5: `PriceTargetCard.tsx` shows Half-Kelly % with formula tooltip.

---

## From todos-v6.md (v6 — Pre-flight Blockers)

- ✅ **A1 — LLM Anthropic + Ollama fallback** — Sprint 0: `llm_service.py` rewritten with `AnthropicBackend` primary + `OllamaBackend` fallback.
- ✅ **A2 — model-details, prediction-stats, price-targets endpoints** — Sprint 1+: all three endpoints in `technical.py`.
- ✅ **A3 — MLPrediction model** — Sprint 2: `ml_prediction.py` + Alembic migration.
- ✅ **A4 — lightgbm, optuna, shap, anthropic in requirements.txt** — Sprint 0: all added.
- ✅ **B3 — LLMInsightCard.tsx + dashboard wiring** — Sprint 1+: built and wired.
- ✅ **B4 — ModelDetailsPanel.tsx** — Sprint 4: built with 4 tabs.
- ✅ **B7 — /model-info/{symbol} deep-dive page** — Sprint 6: built with 7 tabs.

---

## Sprints 20–24 Summary (new items not in original todos files)

- ✅ **Sprint 20 — Live Watchlist Price Tape** — `PriceTape.tsx` polling live prices every 30s.
- ✅ **Sprint 20 — Alerts History Log** — `GET /alerts/history` + History tab in alerts page.
- ✅ **Sprint 20 — Prediction Confidence Timeline Chart** — Recharts LineChart in HistorySection of model-info page; coloured dots by correctness.
- ✅ **Sprint 21 — Signal Grade Badge (GradeBadge.tsx)** — Reusable A+→F badge with tooltip, wired to dashboard header + watchlist overview cards.
- ✅ **Sprint 21 — Recently-viewed symbol quick-switch** — `useRecentSymbols.ts` hook + "Recent" pill strip on dashboard.
- ✅ **Sprint 21 — FOMC Countdown widget** — `FomcCountdown` on macro page with urgency colours.
- ✅ **Sprint 22 — Grade filter on watchlist overview** — Filter pills (All/A&above/A+only/B&above/Tradeable).
- ✅ **Sprint 22 — Mini GAS badge + score on watchlist sidebar** — GradeBadge + GAS score per WatchlistWidget item.
- ✅ **Sprint 22 — GAS score change explainer banner** — Dismissable banner on ≥5pt GAS changes.
- ✅ **Sprint 23 — Default ticker preference** — Full stack (DB + endpoint + Settings UI + SymbolContext).
- ✅ **Sprint 23 — Yield curve inversion alert** — Amber banner on macro page when spread < 0.
- ✅ **Sprint 23 — Grade leaderboard on explore page** — `GradeLeaderboard` component with medals, grade badges, component dots.
- ✅ **Sprint 24 — Sector breakdown pie chart** — `SectorPieChart` donut chart in portfolio analytics.
- ✅ **Sprint 24 — Risk profile quiz** — 5-question quiz → 4 profiles, DB column, Settings section.
- ✅ **Sprint 24 — SHAP "What drove this?" panel** — `ShapPanel` on dashboard below TimeframeGrid.
