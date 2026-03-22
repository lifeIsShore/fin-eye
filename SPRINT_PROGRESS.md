# Fin-Eye — Sprint Progress Tracker
> Last updated: Sprint 32 complete

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

## ✅ Sprint 11 -- Complete
- [x] Cross-asset overview row (CrossAssetRow.tsx, Market Pulse section on dashboard)
- [x] Sentiment fetched_at backend (sentiment.py derives from max published_at)
- [x] Sentiment fetched_at frontend (SentimentTimeseriesDto.fetched_at, typed prop)
- [x] Watchlist Overview sparklines (GasSparkline in watchlist-overview/page.tsx)
- [x] Notification preferences page /settings/notifications (UX-SETTINGS-01)
- [x] Settings page deep-link to full notification prefs

## ✅ Sprint 12 -- Complete
- [x] Backtesting strategy description cards (STRATEGY_DOCS + StrategyDocPanel)
- [x] Watchlist Overview 7-day GAS sparklines per card
- [x] LLM Insight Card full SSE streaming (useStreamInsight wired, sections appear progressively)
- [x] OllamaBackend.generate_stream() added to llm_service.py
- [x] POST /generate-insight-stream SSE endpoint in explanation.py

## ✅ Sprint 13 -- Complete
- [x] Portfolio GAS Aggregate Banner (PortfolioGasBanner in portfolios/[id]/page.tsx)
- [x] Backend symbol_gas_breakdown (portfolio_service.py uses GAS snapshots + fallback)
- [x] Admin GAS Precompute page (frontend/app/admin/gas/page.tsx -- NEW)
- [x] Explore page (frontend/app/explore/page.tsx -- NEW: heatmap + RRG + quick-links)
- [x] Nav: /explore in sidebar, /admin/gas in admin menu, Zap import

## ✅ Sprint 14 -- Complete
- [x] ArticleList.tsx full redesign: FinBERT chips, source tier badges, time-grouped timeline, filter bar, freshness dots, score magnitude bars
- [x] news-sentiment/page.tsx: FreshnessIndicator on articles header, updated caption
- [x] Backtesting ParameterSweepPanel: N-value sweep, Sharpe/Return/DrawDown metric chart, best-value callout, results table, reference lines
- [x] EarningsCalendarStrip.tsx (NEW): upcoming earnings for watchlist symbols, urgency colour coding, batch API, linked from dashboard sidebar (desktop + mobile)

## ✅ Sprint 15 -- Complete

### Delivered
- [x] **Portfolio vs Benchmark equity chart** -- `PerformanceChart` component in `portfolios/[id]/page.tsx`; period picker (1mo/3mo/6mo/1y/2y/5y); portfolio + benchmark normalised to 100; alpha badge; `backend/app/services/portfolio_performance.py` (NEW); `GET /portfolios/{id}/performance?period=` endpoint added to `portfolios.py`
- [x] **Risk page: Import from Portfolio** -- "Import from Portfolio" dropdown on Portfolio Stress tab fetches saved portfolios from API and pre-fills positions; `Briefcase` icon; auto-normalises weights to 10k total
- [x] **Model-info Regime tab** -- `RegimeSection` component with per-regime accuracy bars, delta vs overall, data-gate warning (<30 predictions), low-sample badges (<10), methodology note; `REGIME_META` map covering 7 regime types; wired as 7th tab on model-info page

## ✅ Sprint 16 -- Complete

### Delivered
- [x] **Daily Market Brief** -- `DailyMarketBrief.tsx` (NEW): SSE-streaming LLM summary card; collapsible; shows macro + sentiment + regime + GAS input badges; 4-hour localStorage cache; typing cursor; fallback static brief when Ollama is offline; `POST /api/v1/explanation/daily-brief/generate-stream` SSE endpoint (Redis 4h cache, word-by-word streaming of cached text); wired into dashboard above cross-asset pulse row
- [x] **Model-info Regime tab** (Sprint 15 carry-over, counted in 15)
- [x] **Risk page portfolio import** (Sprint 15 carry-over, counted in 15)

## ✅ Sprint 17 -- Complete

### Delivered
- [x] **Watchlist bulk GAS refresh** -- `WatchlistWidget.tsx`: "Refresh GAS" button in header iterates watchlist symbols and calls `POST /admin/gas/precompute/{symbol}` for each; shows spinner + success/failure message; `RefreshCw` + `Zap` icons; disabled during run
- [x] **Portfolio target return progress bar** -- `TargetReturnProgress` component in `portfolios/[id]/page.tsx`: fetches 1y performance data, computes YTD return, shows progress bar vs pro-rata target (day-of-year / 365 * annual target); on-pace marker line; On Track / Ahead / Behind verdict badge
- [x] **Sentiment keyword cloud** -- `SentimentKeywordCloud.tsx` (NEW): Recharts Treemap of top 40 keywords extracted from article headlines; cell size = frequency; cell colour = aggregate sentiment (emerald/slate/rose); custom cell renderer with labels; stop-word filter; wired into `news-sentiment/page.tsx` between article list and source breakdown

## ✅ Sprint 18 -- Complete

### Delivered
- [x] **Backtesting walk-forward validation** -- `WalkForwardPanel` in `backtesting/page.tsx`; fold selector (3/4/5/6/8); calls `POST /backtesting/walk-forward`; OOS summary strip (total return, avg Sharpe, Sharpe degradation, worst DD); per-fold IS vs OOS Sharpe comparison bars (blue/teal/rose); stitched OOS equity curve (teal line chart); overfitting warning banner when degradation > 0.4 or OOS Sharpe < 0.3; `WalkForwardEngine` in `backtesting_service.py` (expanding-window anchored splits, compounded OOS capital); `POST /backtesting/walk-forward` endpoint; `WalkForwardRequest/Fold/Response` schemas; `runWalkForward()` in `api.ts`
- [x] **Admin analytics funnel drop-off chart** -- replaced `FunnelChart` in `admin/analytics/page.tsx`; now renders SVG waterfall: bars shrink proportionally to user count, grey hatched connector rectangles show users lost between steps, bar colour = green (>60% kept) / amber (30-60%) / red (<30%); drop-off count labels on connectors; legend
- [x] **Explore page macro heat strip** -- `MacroHeatStrip` component in `explore/page.tsx`; fetches `GET /api/v1/macro/latest`; renders 5 FRED indicator tiles (Fed Funds Rate, Unemployment, Yield Spread, CPI YoY, VIX); each tile colour-coded by regime (rose/amber/emerald); click-to-/macro; composite macro score progress bar; section header with score label; skeleton + error states; placed between Sector Rotation and Deep Signal Pages sections

## ✅ Sprint 19 -- Complete

### Delivered
- [x] **Watchlist comparison mode** -- `watchlist-overview/page.tsx`: "Compare" button in header toggles compare mode; instruction banner guides selection; cards get sky/violet border + A/B badge when selected; clicking 2 cards opens `ComparisonPanel` (metric table with edge indicator, dual 7-day GAS sparklines); clicking a selected card deselects it; compare mode fully integrates the existing `ComparisonPanel` component
- [x] **Portfolio correlation matrix** -- `CorrelationMatrix` component in `portfolios/[id]/page.tsx`; `GET /portfolios/{id}/correlation?period=` endpoint; `portfolio_correlation.py` service; period picker (1mo/3mo/6mo/1y); colour-coded Pearson heatmap (emerald = high +ve, rose = high -ve); diagonal = 1.00; symbol labels; colour scale legend; n_days label; methodology note
- [x] **Article topic clusters** -- `ArticleTopicClusters.tsx` (NEW): groups headlines into up to 6 seed-keyword clusters (Earnings, Macro/Fed, Analyst Moves, Products/Innovation, Legal/Regulatory, Market Moves); articles may appear in ≤2 clusters; cluster card shows icon, label, article count, avg sentiment badge, expandable headline list with FinBERT dot colour; "Other" catch-all bucket; coverage % header; wired into `news-sentiment/page.tsx` between keyword cloud and source breakdown

### Data-gated (Sprint 20+)
- [ ] Meta-model: when to trust the base model (>=90 days cross-regime predictions)
- [ ] Regime-conditional backtest overlay (colour equity curve by regime)

## ✅ Sprint 20 -- Complete

### Delivered
- [x] **Live Watchlist Price Tape** -- `components/PriceTape.tsx` (NEW): scrolling strip at top of dashboard polling `GET /technical/{symbol}/price` in parallel for all watchlist symbols every 30s; each tile shows symbol + live price + % change (emerald/rose/slate); clicking a tile switches active symbol; last-updated timestamp; invisible when watchlist empty or logged out; wired into `app/page.tsx`
- [x] **Alerts History Log** -- `GET /api/v1/alerts/history` endpoint (backend); `AlertHistoryResponse` + `AlertHistoryListResponse` schemas; `get_alert_history()` service function; `AlertHistoryDto` + `fetchAlertHistory()` in `lib/api.ts`; tab switcher (🔔 Active / 📋 History) on `alerts/page.tsx`; history table with timestamp, symbol, condition badge, threshold, actual value, delivery channel, and status (Active/Dismissed); lazy-loads only when History tab is opened
- [x] **Prediction Confidence Timeline** -- `HistorySection` in `model-info/[symbol]/page.tsx` now renders a Recharts `LineChart` above the predictions table; x-axis = prediction date (oldest→newest), y-axis = confidence %; coloured dots per point: emerald (correct), rose (wrong), slate (unresolved); dashed 50% baseline + sky-blue average reference line with label; avg confidence badge top-right; confidence column in table now colour-coded (emerald ≥65%, sky ≥55%, amber otherwise)

## ✅ Sprint 21 -- Complete

### Delivered
- [x] **Signal Grade Badge everywhere** -- `components/GradeBadge.tsx` (NEW): reusable A+→F letter grade badge, colour-coded (emerald A+/A, sky B, amber C, orange D, rose F), 4 sizes (xs/sm/md/lg), hover tooltip with grade description + tradeable status, pulsing coloured dot. `GasSnapshotDto` + `GasBatchEntry` extended with `signal_grade/signal_grade_score/signal_tradeable` fields. Badge wired into dashboard header (md size, showTradeable) and every watchlist-overview card (xs size).
- [x] **Recently-viewed symbol quick-switch** -- `hooks/useRecentSymbols.ts` (NEW): tracks last 6 viewed symbols in localStorage, auto-updates on `activeSymbol` change, excludes current symbol. Dashboard shows a "Recent" pill strip below the header; clicking any pill instantly switches symbol.
- [x] **FOMC Countdown widget** -- `app/macro/page.tsx`: `FOMC_DATES_2025_2026` hardcoded schedule, `getNextFomcDate()` helper, `FomcCountdown` component with urgency colour-coding (rose ≤3 days with pulsing dot, amber ≤14 days, slate otherwise), "Fed calendar ↗" external link. Placed at top of both Overview and Advanced views.

## ✅ Sprint 22 -- Complete

### Delivered
- [x] **Grade filter on watchlist overview** -- `app/watchlist-overview/page.tsx`: `GradeFilter` type + `passesGradeFilter()` + `gradeRank()` helpers. Filter pill strip in toolbar: All / A & above / A+ only / B & above / Tradeable. `sorted` memo applies filter before sorting. "Showing N of M symbols (X hidden)" status line with "Clear filter" link. Hidden-by-filter symbols excluded cleanly without breaking compare mode.
- [x] **Mini GAS badge + score on watchlist sidebar** -- `components/WatchlistWidget.tsx`: `fetchGasBatch()` helper + SWR call polling every 5 min. Each list item now shows: symbol name + `<GradeBadge size="xs" showTooltip={false} />` + coloured GAS score number (emerald/amber/rose). Remove button stays visible on hover. No layout breakage on small sidebar.
- [x] **GAS score change explainer banner** -- `app/page.tsx`: `prevGasScoreRef` tracks previous snapshot score per symbol; resets on symbol change. `gasChangeBanner` state set when delta ≥ 5 pts on SWR `onSuccess`. Dismissable banner appears above Daily Market Brief: emerald (improvement) or rose (decline), ↑5/↓5 pts label, prev → curr display, contextual message (moderate vs significant). Clears on symbol switch.

## ✅ Sprint 23 -- Complete

### Delivered
- [x] **Default ticker preference** -- Backend: `default_symbol` column on `User` model; `UpdateProfileRequest.default_symbol` + `UserResponse.default_symbol` in schemas; `update_user_name()` saves it; `PATCH /auth/me` passes it through. Frontend: `updateDefaultSymbol()` in `lib/api.ts`; `User.default_symbol` in `AuthProvider`; `seedDefaultOnce()` in `SymbolContext` (seeds initial symbol from user preference only if no localStorage value); dashboard calls `seedDefaultOnce(user.default_symbol)` on mount; Settings Preferences section has "Default Ticker" input with Save/Clear buttons and success/error feedback.
- [x] **Yield curve inversion alert banner** -- `app/macro/page.tsx`: IIFE renders amber warning banner when `yield_spread_10y_2y < 0`, showing exact spread value, historical context (6-18 month recession lead), and educational disclaimer. Visible on both Overview and Advanced tabs. Silently hidden when spread ≥ 0 or data unavailable.
- [x] **Grade leaderboard on explore page** -- `app/explore/page.tsx`: `GradeLeaderboard` component fetches watchlist via SWR then batch GAS snapshots; sorts by `GRADE_ORDER_EXPLORE` then `gas_score`; renders ranked list with 🥇🥈🥉 medals for top 3, grade badge, weather label, T/S/M coloured dots, GAS score; clicking a row navigates to dashboard with that symbol active; empty/no-watchlist/no-grade states all handled. `fetchLeaderboard()` helper + `LeaderEntry` type added. `Trophy` icon in section header.

## ✅ Sprint 24 -- Complete

### Delivered
- [x] **Sector breakdown pie chart** -- `portfolios/[id]/page.tsx`: `SectorPieChart` component using Recharts `PieChart`/`Pie`/`Cell`; donut chart (innerRadius 34, outerRadius 56) with 10-colour palette; legend list shows top-6 sectors with coloured dots and % values; `+N more` overflow note; tooltip on hover; replaces old bar-list rendering of `sector_breakdown`. Imports `PieChart, Pie, Cell, Tooltip as ReTooltip` from recharts.
- [x] **Risk profile quiz** -- Full stack: `User.risk_profile` column (backend `models/user.py`); `UpdateProfileRequest.risk_profile` + `UserResponse.risk_profile` schemas; `update_user_name()` service accepts and saves it; `PATCH /auth/me` passes it through. Frontend: `User.risk_profile` in `AuthProvider`; `RiskProfileSection` component with 5-question step-by-step quiz, progress bar, `scoreToProfile()` scoring (Conservative/Income/Moderate/Aggressive by total score 0-15), profile badge with colour coding, plain-English description, retake button. Wired into Settings as its own `SectionCard`.
- [x] **SHAP "What drove this?" panel** -- `app/page.tsx`: `FEATURE_DESCRIPTIONS` map covering 14 common ML feature names with plain-English explanations; `ShapPanel` component — collapsible (closed by default), shows best timeframe by Sharpe, reads `shap_importance` from `model-details` endpoint, renders top-5 SHAP features with violet/sky/slate bars proportional to impact, feature name + SHAP value + description per row; graceful fallback when SHAP not yet computed (shows feature list with "No SHAP yet" badge); sourced via dedicated SWR call `model-details-shap-{symbol}` (separate from model-info page SWR). Placed directly below `TimeframeGrid` inside the Technical Consensus section.

### Migration note (cumulative)
```bash
alembic revision --autogenerate -m "add_default_symbol_risk_profile_to_users"
alembic upgrade head
```

## ✅ Sprint 25 -- Complete

### Delivered
- [x] **Trade log table on backtesting** -- Backend: `TradeRecord` Pydantic schema (`entry_date`, `exit_date`, `entry_price`, `exit_price`, `return_pct`, `holding_days`, `side`); `backtesting_service.py` `run()` now walks the `position` series detecting entry/exit transitions and emits `List[TradeRecord]`; `BacktestResponse.trade_log` field. Frontend: `TradeRecord` interface + `trade_log?`/`benchmark_label?` added to `BacktestResponse` in `lib/api.ts`; `TradeLogTable` component in `backtesting/page.tsx` — collapsible (closed by default), paginated 10 rows/page with ←/→ controls, columns: # / Entry Date / Exit Date / Entry $ / Exit $ / Return % / Days Held, return % colour-coded emerald/rose, W/L summary in header. Rendered below the secondary stats row, above the Parameter Sweep panel.
- [x] **Sentiment trend arrow on news page** -- `news-sentiment/page.tsx`: inline IIFE next to the "Sentiment over last 30 days" heading; sorts `data.series` by date, slices last 7 days (`recent`) and prior 7 days (`prior`), computes average `sentiment_score` for each window, derives `delta = avgRecent - avgPrior`; renders `↑ Improving` (emerald, `TrendingUp` icon) / `↓ Deteriorating` (rose, `TrendingDown` icon) / `— Flat` (slate, `Minus` icon) with delta in scaled pts; threshold 0.02 to suppress noise; silently hidden when fewer than 8 data points or fewer than 4 prior-window points.
- [x] **Benchmark comparison toggle on backtesting** -- Backend: `BacktestRequest.benchmark` field (default `""`); `backtesting_service.py`: when `benchmark` is set and differs from the strategy symbol, fetches that ticker via `OHLCVFetcher`, aligns to the strategy date index via `reindex + ffill`, scales to `initial_capital`, overwrites `benchmark_equity` on the equity curve; `BENCHMARK_LABELS` dict maps SPY/QQQ/BTC-USD/GLD to display names; returns `BacktestResponse.benchmark_label`. Frontend: `benchmark?` field on `BacktestRequest` in `api.ts`; `BenchmarkStrip` pill component in `backtesting/page.tsx` config sidebar (Same Symbol / SPY / QQQ / BTC / GLD), placed below the strategy doc panel; equity curve section heading dynamically shows `result.benchmark_label ?? "Buy & Hold"`; `benchmark` state passed into `runBacktest` request.

## ✅ Sprint 26 -- Complete

### User requests (shipped alongside Sprint 26)
- [x] **ArticleList URL click-through** -- Headline titles already had `<a href={article.url}>` in `ArticleCard` from Sprint 14; the missing piece was `sentiment_label` and `finbert_score` not flowing from backend. Fixed in the bug-fix session (`data_models.py` + `sentiment.py`). Added "Click a headline to read the full article ↗" hint in the legend row.
- [x] **ArticleList pagination + page-size selector** -- `ArticleList.tsx`: added `pageSize` state (default 25), `page` state, `paginated` useMemo slice, `totalPages`, `handleFilterChange`/`handlePageSizeChange` helpers that reset page to 0. Pagination footer renders ← `startIdx–endIdx of total` → navigation and a Show 10/25/50/100 per page pill strip. Time-grouping now operates on the current page slice so group headers stay accurate.

### Delivered
- [x] **Regime change notification banner** -- `app/page.tsx`: `prevRegimeRef` + `regimeBanner` state added alongside `prevGasScoreRef`/`gasChangeBanner`. GAS snapshot `onSuccess` callback detects when `data.regime` differs from the previous value and sets the banner. Banner renders below the GAS score change banner: 🟢 emerald for Risk-On flip, 🔴 rose for Risk-Off flip, 🟡 amber for Transitional. Shows `prev → curr` and a plain-English implication sentence. Dismissable with ×. Clears on symbol change.
- [x] **Economic calendar on macro page** -- `EventTimeline` was already wired into both Overview and Advanced tabs via `EventTimeline` component and `<Card><EventTimeline /></Card>` at the bottom of each view. Confirmed present in Overview tab — no new work needed.
- [x] **Designed empty states** -- `app/macro/page.tsx`: error state replaced with centred `Globe` icon + message + "Try again" link; added new `!loading && !error && !basicData` empty state with dashed border, `Globe` icon, description, and "Go to Admin Panel" CTA. `app/news-sentiment/page.tsx`: error state replaced with centred `Newspaper` icon + ticker-specific message; pre-load empty state replaced with dashed-border card with `Newspaper` icon and instruction copy.

## ✅ Sprint 27 -- Complete

### Delivered
- [x] **Mobile nav** -- Already fully implemented (`MobileNav` component with slide-in drawer, section groups, active highlighting) and wired in `layout.tsx`. Confirmed — no additional work needed.
- [x] **Grade persistence + `signal_grade_history` table** -- Already fully implemented: `GasSnapshot` model has `signal_grade`/`signal_grade_score`/`signal_tradeable`/`signal_grade_desc`/`signal_grade_reasons` columns; `SignalGradeHistory` model and `s27_001_signal_grade_history.py` migration exist; `gas_precompute.py` writes a history row on every grade change (compares prev snapshot grade → new grade before upsert); model registered in `__init__.py`. All infrastructure was already in place.
- [x] **AI Portfolio Allocation endpoint** -- `backend/app/api/v1/endpoints/allocation.py` (NEW): `POST /api/v1/allocation/suggest` — takes `symbols[]`, `total_capital`, `min_grade`; fetches GAS snapshot per symbol via `get_snapshot_cached()`; applies grade caps (A+=20%, A=15%, B=10%, C=5%, D/F=0%); normalises weights if total > 100%; returns `AllocationResponse` with per-position breakdown + cash reserve + disclaimer. `GET /api/v1/allocation/grade-history/{symbol}` — returns last N grade change events from `signal_grade_history` table for sparklines. Registered in `main.py`.
- [x] **AI Allocation frontend types** -- `lib/api.ts`: `AllocationRequest`, `PositionSuggestion`, `AllocationResponse`, `GradeHistoryPoint`, `GradeHistoryResponse` interfaces; `fetchAllocationSuggestion()` and `fetchGradeHistory()` functions.
- [x] **`/portfolio/build` page** -- `frontend/app/portfolio/build/page.tsx` (NEW): Config sidebar with capital input, min-grade pill strip (A+/A/B/C), symbol input with Enter-to-add and chip removal, "Load Watchlist" button; empty/loading/result states; `AllocationSummary` (capital bar + cash pct + excluded warning); position table with rank, symbol+GradeBadge, GAS score, weight bar, USD amount, tradeable status; cash reserve row; grade cap reference collapsible; educational disclaimer. `GradeCapReference` component explains the 20/15/10/5% cap system.
- [x] **Nav: AI Allocator** -- Added `{ href: "/portfolio/build", label: "AI Allocator", icon: <Zap> }` to the Tools section in `Nav.tsx`.

### Migration note
```bash
alembic upgrade head   # applies s27_001_signal_grade_history if not already run
```

## ✅ Sprint 28 -- Complete

**Source todos:** `todos.md` Phase 2A (grade history sparkline, grade explanation panel) + `todos-v5.md` Phase 1.1 (multi-timeframe agreement banner)

### Delivered
- [x] **Grade history sparkline** -- `components/GradeBadge.tsx`: `GradeSparkline` component (exported) fetches `fetchGradeHistory(symbol, 10)` via SWR, reverses to oldest-first, maps each grade to a numeric value (A+=6...F=1), renders an inline SVG polyline (40×16px) colour-coded by current grade (emerald/sky/amber/rose), with a filled dot at the latest point. Wired into `watchlist-overview/page.tsx` per card (via `GradeSparklineInline` alias) and available on all `GradeBadge` instances via `showSparkline` prop.
- [x] **Grade explanation panel** -- `components/GradeBadge.tsx`: `GradeExplainModal` full-screen modal opened when `clickable` prop is set on `GradeBadge`. Shows: grade letter + score + tradeable status; grade scale (A+–F with threshold pts, current grade highlighted); four scoring component cards (GAS Score 40pts, Component Alignment 30pts, Model Sharpe 20pts, Signal Conviction 10pts) with descriptions + proportion bars; "Why this grade" reasons list (from snapshot `signal_grade_reasons`); `GradeHistoryRow` timeline of last N grade changes with dates; "What improves the grade" educational block; educational disclaimer. New props added to `GradeBadge`: `clickable`, `symbol`, `reasons`, `showSparkline`. Wired with `clickable` + `symbol` on dashboard header badge, watchlist-overview cards, and explore leaderboard entries.
- [x] **Multi-timeframe agreement banner** -- `app/page.tsx`: Inline IIFE above `TimeframeGrid` (only renders when `signals.length > 1`). Computes bullish/bearish/neutral counts, dominant direction, agreement ratio. Four states: Strong agreement ≥80% (green/red), Moderate lean ≥60% (muted green/red), Low conviction (amber), Mixed/split (amber). Shows icon (🟢/🔴/🟡) + message + sub-text + mini per-timeframe coloured bar strip on desktop. Examples: "4/5 timeframes agree: Bullish — Strong cross-timeframe consensus", "Timeframes are split — Wait for alignment".

## ✅ Sprint 29 -- Complete

**Sources:** `todos.md` §4 🔴 + `todos-v3.md` §12 🟠 (Cache-Control headers) · `todos.md` §6 🔴 + `todos-v3.md` §10 🟠 (Billing page) · `todos-v3.md` §3 ⚡ (Background refresh indicator)

### Delivered
- [x] **Cache-Control headers on GAS, macro, and sentiment endpoints** -- `backend/app/api/v1/endpoints/macro.py`: `GET /macro/latest` gets `Cache-Control: public, max-age=60, stale-while-revalidate=300`; `GET /macro/advanced` gets `max-age=120, stale-while-revalidate=600`. `backend/app/api/v1/endpoints/sentiment.py`: `GET /{symbol}/timeseries` gets `max-age=60, stale-while-revalidate=240`. `backend/app/api/v1/endpoints/admin_gas.py`: `GET /snapshots/{symbol}` gets `max-age=60, stale-while-revalidate=300`; `GET /history/{symbol}` gets `max-age=300, stale-while-revalidate=600`. All use FastAPI `Response` parameter injection pattern.
- [x] **Billing page redesign** -- `frontend/app/billing/page.tsx` fully rewritten: monthly/annual toggle (slider switch) with "Save €59.89/year" emerald badge when annual selected; three plan cards (Free/Pro/Institutional) with `PriceDisplay` component showing per-month price (annualised when annual toggle on) and billed-annually callout; annual savings callout banner (only shown in monthly view, click to switch); full feature comparison table with 30+ features across 8 categories (Dashboard, Signals, Macro, Sentiment, Portfolio & Watchlist, Backtesting, Alerts, Enterprise) with Check/X/string cells; three trust signals (Stripe payments, cancel anytime, GDPR); expanded FAQ (5 questions). Payments remain disabled with "Coming Soon" state on buttons.
- [x] **Background refresh indicator on GAS widget** -- `components/MarketWeatherWidget.tsx`: new `isRefreshing` boolean prop (default `false`); when true, a 10×10px `border-t-sky-400 animate-spin` spinner renders absolutely positioned top-right of the GAS score number. `app/page.tsx`: GAS snapshot SWR call now destructures `isValidating: gasValidating`; passed as `isRefreshing={gasValidating && !!gasSnapshot}` (only shows spinner after initial data is present, not during cold load). Users now see a subtle sky-blue spinner whenever SWR silently revalidates the GAS score in the background.

## ✅ Sprint 30 -- Complete

**Sources:** `todos-v3.md` §2 ⚡ (nav badges) · `todos-v3.md` §4 🟠 (auto-alerts on watchlist add) · `todos.md` §2 🟠 + `todos-v3.md` §8 🟠 (Learn Hub redesign)

### Delivered
- [x] **NEW / BETA / AI nav badges** -- `components/Nav.tsx`: `NavBadge` type (`"NEW" | "BETA" | "AI"`), `BADGE_STYLES` colour map (emerald/amber/violet). `NavItem` interface extended with optional `badge` field. Badges assigned: Adv. Sentiment → NEW, Fed Policy → NEW, Indicators → BETA, AI Allocator → AI. Desktop sidebar renders badge as tiny rounded-full pill to the right of the label (hidden when collapsed). Mobile drawer renders same badge inline. Both render only when sidebar is expanded / drawer is open.
- [x] **Auto-create default GAS alerts on watchlist add** -- `backend/app/services/alert_service.py`: `seed_watchlist_alerts(db, user, symbol)` function — idempotent (skips if alert type+threshold already exists for that user+symbol), creates two in-app alerts: `gas_above 65.0` (“Bullish environment opening up”) and `gas_below 35.0` (“Instability zone”). `backend/app/api/v1/endpoints/watchlist.py`: imported and called inside `add_to_watchlist` before `db.commit()`, so both the watchlist item and the alerts are committed atomically. On IntegrityError (race) the rollback discards both safely.
- [x] **Learn Hub redesign** -- `frontend/app/learn/page.tsx` fully rewritten. Six module intro cards always visible above the article grid: GAS Methodology (sky), FinBERT & Sentiment (violet), Technical Consensus (emerald), Conflict Detector (amber), Backtesting Pitfalls (rose), Macro 101 (teal). Each card is clickable — clicking filters the article grid to that module’s category. When a category is active, only the relevant module card(s) show. Category filter pills now show article counts. Case Studies hero banner preserved. Empty state has “View all articles →” fallback. Article grid and all CMS data fetching unchanged.

## ✅ Sprint 31 -- Complete

**Sources:** `todos.md` Phase 2B 🟠 (rebalancing trigger) · `todos-v3.md` §16 🟠 (rebalancing calculator, DCA simulator)

### Delivered
- [x] **Grade-drop rebalancing trigger** -- `backend/app/services/alert_service.py`: `check_and_fire_rebalancing_alerts(db)` — scans `signal_grade_history` for symbols with ≥2-step grade drops, fires `alert_type="rebalance_suggested"` in-app alerts for all watchlist users holding that symbol, 24h cooldown, fully exception-isolated. `backend/app/services/scheduler.py`: `job_rebalancing_alerts()` scheduler job added at `:05/:20/:35/:50` (5 min after GAS precompute at `:00/:15/:30/:45`). `frontend/app/alerts/page.tsx`: dismissable amber banner section for `rebalance_suggested` alerts showing symbol, drop count, action advice, dismiss via `acknowledgeAlert`.
- [x] **Rebalancing calculator** -- `frontend/app/portfolios/[id]/page.tsx`: `RebalancingCalculator` collapsible component — user enters current USD value per position, calculator computes current vs target %, diff %, and BUY/SELL/HOLD action with trade size in USD. Differences < 0.5% = HOLD. Appears when portfolio ≥2 assets.
- [x] **DCA simulator** -- `frontend/app/portfolio/dca/page.tsx` (NEW): fully client-side DCA vs Lump-Sum simulation using OHLCV price data. Inputs: ticker, total amount, DCA frequency (weekly/biweekly/monthly), start/end dates. Computes CAGR, final value, max drawdown for both strategies. Dual-line equity chart, winner banner, stat comparison cards, educational disclaimer.

## ✅ Sprint 32 -- Complete

**Sources:** `todos.md` Phase 2B 🔴 (AI allocation explainer) · `todos.md` §13 🟠 + `todos-v3.md` §11 🟠 (graceful degradation + data attribution)

### Delivered
- [x] **AI allocation explainer** -- `backend/app/api/v1/endpoints/allocation.py`: `POST /api/v1/allocation/explain` SSE endpoint — receives the allocation result, builds a structured LLM prompt with all position grades/GAS scores/weights/exclusions, streams via Ollama with deterministic static fallback when Ollama is offline. `frontend/app/portfolio/build/page.tsx`: `streamAllocationExplain()` async generator, `useEffect` auto-triggers on every new `result`, streams tokens into a violet `🧠 AI Portfolio Explanation` panel with typing cursor and "Generating…" indicator.
- [x] **Graceful degradation messages** -- `frontend/components/DataSourceStatus.tsx` (NEW): reusable dismissable banner component with `error` / `stale` / `warning` variants; colour-coded icons (WifiOff/Clock/AlertTriangle); shows source name, description, optional raw error message. Wired into `app/page.tsx` (GAS Engine, Sentiment, Macro errors), `app/macro/page.tsx` (replaces old custom error div). Used everywhere a data fetch can silently fail.
- [x] **Data source attribution** -- `frontend/app/macro/page.tsx`: `FRED_SOURCES` map (12 series IDs), `FredAttribution` component renders a clickable `FRED · {SERIES_ID} ↗` link on each `IndicatorCard`. `indicatorKey` prop added to `IndicatorCard`. Both Overview and Advanced tabs pass `indicatorKey={key}` to all `IndicatorCard` instances. Footer disclaimer updated with clickable FRED link and note about hovering for series IDs.

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

---

## ✅ Sprint 12 — Complete

### Delivered
- [x] **Backtesting: Strategy description cards** — `STRATEGY_DOCS` constant + `StrategyDocPanel` collapsible component added to `backtesting/page.tsx`. Replaces one-liner hints with full expandable panel: how-it-works explanation, entry/exit rules (emerald/rose), best-for/watch-out (sky/amber), parameter table with defaults and meanings. Works for all 3 strategies.
- [x] **Watchlist Overview sparklines** — `GasSparkline` imported into `watchlist-overview/page.tsx`; 7-day sparkline inserted per card below component sub-bars, wrapped in `stopPropagation` div.
- [x] **LLM Insight Card streaming** — Full SSE refactor of `LLMInsightCard.tsx`:
  - Removed broken `useSWR` / missing `fetchLLMInsight` import path
  - Wired existing `useStreamInsight` hook (was defined but unused)
  - Sections now appear **progressively** as Ollama tokens arrive — no more 15-30s blank wait
  - Typing cursor on the currently-streaming section
  - Pulsing “Generating…” badge in header during stream
  - Skeleton cards for sections not yet started
  - Price target band appears as soon as `meta` event arrives (before sections complete)
  - Regenerate button disabled during streaming, shows “Generating…” label
  - Backend: `OllamaBackend.generate_stream()` async generator already added to `llm_service.py`
  - Backend: `POST /generate-insight-stream` SSE endpoint already in `explanation.py`

### No new migrations, no new Python deps

## Sprint 13 — Next Up

### High priority
- [ ] Model-info deep-dive: regime-conditional accuracy tab (data-gated — needs ≥90 days of predictions)
- [ ] Dashboard: portfolio-level GAS aggregate — weighted average GAS across watchlist
- [ ] Admin GAS precompute trigger with per-symbol status progress bar

### Medium priority
- [ ] Explore page: sector heatmap + RRG chart surfaced at top level
- [ ] Backtesting: add parameter sweep UI (try N values, show best Sharpe)
- [ ] News sentiment page: article timeline with FinBERT label chips

### Data-gated (Sprint 14+)
- [ ] Meta-model: “when to trust the base model”
- [ ] Feature Analysis: regime-conditional accuracy (≥90 days of predictions)
