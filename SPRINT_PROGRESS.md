# Fin-Eye — Sprint Progress Tracker
> Last updated: Sprint 36 complete

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

## ✅ Sprint 33 — Complete

**Sources:** `todos-v6.md` B5/B6 (signal utils + agreement banner) · `todos-v4.md` Phase 1 (Train Now button) · `todos-v3.md` §15 (price chart + weekly digest)

### Deliverables
- [x] **`signalUtils.ts` shared utility** — `frontend/lib/signalUtils.ts` (NEW): `interpretConfidence(conf)` returning `{ label, colour, description }` for the five tiers (Strong/Moderate/Weak/Uncertain/No signal); `directionConfig(direction)` returning icon, colour, plain-text label. Import in `TimeframeGrid.tsx` and `LLMInsightCard.tsx` to replace duplicated inline logic and align both components on the same palette.
- [x] **Multi-timeframe agreement banner in TimeframeGrid** — `frontend/components/TimeframeGrid.tsx`: text banner above the grid tiles using `signalUtils.ts`; "N of M timeframes agree: UP → stronger signal" / "Timeframes conflict → wait for confirmation"; colour-coded (emerald ≥3 agree, amber split, rose ≥3 disagree). Closes `todos-v6 B5`.
- [x] **Train Now button + designed empty state** — `frontend/components/TimeframeGrid.tsx` (or parent): when `GET /api/v1/technical/train-status/{symbol}` returns `not_started`, render icon + message + `[▶ Train Now]` button → `POST /api/v1/technical/train/{symbol}`; poll status every 5s while `training`; show animated timeframe checklist during training; toast on completion. Closes `todos-v4 Phase 1.3`.
- [x] **Price chart (TradingView widget) on dashboard** — `frontend/components/PriceChart.tsx` (NEW): lightweight TradingView advanced chart widget embedded via script tag; symbol-aware (updates when `activeSymbol` changes); dark-mode themed to match `bg-slate-900`; placed in the dashboard between the GAS widget and the TimeframeGrid. Eliminates the biggest session-exit point.
- [x] **Weekly digest email opt-in** — Backend: `User.weekly_digest` boolean column + migration; `PATCH /auth/me` accepts `weekly_digest`; `job_weekly_digest()` scheduler job (Mondays 07:00 UTC) — for each opted-in user, assembles top-5 GAS movers from their watchlist + macro summary and sends via Resend. Frontend: toggle in `/settings` Preferences section with success feedback.

---

## ✅ Sprint 34 — Complete

**Sources:** `todos-v4.md` Phase 2 (ticker universe) · Phase 3 (bulk seed infrastructure)

### Delivered
- [x] **`tickers_universe` DB table** — `backend/alembic/versions/v4_001_bulk_tables.py`: `symbol`, `name`, `asset_class`, `exchange`, `tr_rank`, `is_active`, `yf_valid`, `added_at`; `uq_ticker_universe_symbol` unique constraint; ORM model `TickerUniverse` in `bulk_ops.py`. Closes `todos-v4 Phase 2.1`.
- [x] **`tickers_predefined.json`** — `backend/data/tickers_predefined.json`: top 1000 TR DE symbols with `symbol`, `name`, `class`, `tr_rank`, `exchange` fields. Closes `todos-v4 Phase 2.2`.
- [x] **`seed_ticker_universe.py`** — `backend/scripts/seed_ticker_universe.py`: upserts via `ON CONFLICT DO UPDATE`, validates via `yf.Ticker().fast_info`, `--skip-validation` and `--symbol` CLI flags. Closes `todos-v4 Phase 2.3`.
- [x] **`bulk_job_runs` table** — Same migration: `job_type`, `scope`, `symbol`, `status`, `reason`, `rows_added`, `started_at`, `completed_at`; indexes on symbol/status/(job_type,created_at). ORM `BulkJobRun` in `bulk_ops.py`. Closes `todos-v4 Phase 3.1`.
- [x] **`bulk_seed_service.py`** — `backend/app/services/bulk_seed_service.py`: append-only idempotent seeder, checks `MAX(trade_date)`, skips < 200 row symbols, logs to `bulk_job_runs`. Closes `todos-v4 Phase 3.2`.
- [x] **Bulk endpoints** — `backend/app/api/v1/endpoints/admin_bulk.py`: `POST /admin/bulk/run-seed`, `GET /admin/bulk/seed-status`, `POST /admin/bulk/run-train`, `GET /admin/bulk/train-status`, `POST /admin/bulk/run-news-seed`, `GET /admin/bulk/news-status`, `GET /admin/bulk/pipeline-overview`, plus `GET /admin/tickers-universe`, `POST /admin/seed/{symbol}`, `GET /admin/ticker-status/{symbol}`. Closes `todos-v4 Phase 3.3–3.5`.

### Activate (run once)
```bash
cd backend
alembic upgrade head
python scripts/seed_ticker_universe.py --skip-validation
# Then trigger from admin panel: POST /api/v1/admin/bulk/run-seed
```

---

## ✅ Sprint 35 — Complete

**Sources:** `todos-v4.md` Phase 4 (bulk train) · Phase 7 (pipeline overview) · Phase 8 (per-ticker panel)

### Delivered
- [x] **Bulk train endpoints** — `admin_bulk.py`: `POST /admin/bulk/run-train` (scope: `untrained_only`|`retrain_all`); `GET /admin/bulk/train-status` (current_symbol, current_timeframe, pct_complete, recent with Sharpe). Closes `todos-v4 Phase 4.1–4.2`.
- [x] **`pipeline-overview` endpoint** — `GET /admin/bulk/pipeline-overview`: ticker_universe stats, seeding/training/news stats, `active_jobs` flags. Closes `todos-v4 Phase 7.1`.
- [x] **`DataPipelineSection` in Settings** — `frontend/app/settings/page.tsx`: admin-only `SectionCard`; OHLCV + ML + news rows with progress bars, Run buttons, live status polling (3s), collapsible failed/skipped lists. Closes `todos-v4 Phase 4.4`.
- [x] **`TickerDataPanel.tsx`** — collapsible per-ticker panel: OHLCV/ML/News 3-state rows with inline action buttons; polls train-status every 5s while training; wired into `frontend/app/page.tsx`. Closes `todos-v4 Phase 4.5`.
- [x] **`api_bulk.ts`** — `frontend/lib/api_bulk.ts`: all typed fetch helpers for pipeline endpoints + DTOs. Closes `todos-v4 Phase 4.3`.

---

## ✅ Sprint 36 — Complete

**Sources:** `todos-v4.md` Phase 5 (news storage · FinBERT pipeline · cron jobs)

### Delivered
- [x] **Extend `news_articles` table** — `alembic/versions/v4_002_news_extend.py`: adds `url`, `sentiment_label`, `finbert_score`, `last_fetched_at`, `fetch_source`; unique constraint `uq_news_symbol_title_ts`; indexes `idx_news_symbol_date`, `idx_news_last_fetched`. Closes `todos-v4 Phase 5.1`.
- [x] **Cache-first news fetcher** — `app/services/news_data.py` rewritten: checks `MAX(last_fetched_at)` within 6h TTL → skips Finnhub; on cache miss: fetches Finnhub, runs FinBERT/VADER, upserts with all new columns. Closes `todos-v4 Phase 5.2`.
- [x] **`sentiment_scorer.py` FinBERT singleton** — `app/services/sentiment_scorer.py`: `ProsusAI/finbert` with batch-64 scoring; lazy-loads on first call; VADER fallback; maps positive→bullish / negative→bearish / neutral→neutral. Closes `todos-v4 Phase 5.3`.
- [x] **Bulk news seed endpoint** — `POST /admin/bulk/run-news-seed` + `GET /admin/bulk/news-status` in `admin_bulk.py`. Closes `todos-v4 Phase 5.4`.
- [x] **Scheduler cron jobs** — `scheduler.py`: `job_news_daily_refresh` (Mon–Fri 06:00 UTC); `job_news_ttl_cleanup` (Sun 02:30 UTC, deletes articles > 365 days). Closes `todos-v4 Phase 5.5–5.6`.

### Activate (run once)
```bash
cd backend
alembic upgrade head               # applies v4_002_news_extend
pip install transformers torch     # optional — falls back to VADER without it
```

---

## ✅ Sprint 37 — Complete

**Sources:** `todos-v3.md` §2 (grouped nav) · §9 (onboarding) · `todos.md` §10–11
```

### Delivered
- [x] **Grouped sidebar nav** — `Nav.tsx` already grouped into collapsible sections (Core Analysis, Deep Signals, Market Context, Tools, Learn) with badge support and collapse-to-icons mode. Closes `todos-v3 §2 UX-NAV-01`.
- [x] **CMD+K command palette** — `frontend/components/CommandPalette.tsx` (NEW): `⌘K`/`Ctrl+K` global shortcut; fuzzy search over all 24 nav pages + watchlist symbols; keyboard-navigable (↑↓ Enter Esc); jumps to page or sets activeSymbol; mounted in `layout.tsx`. Closes `todos-v3 §2 UX-NAV-02`.
- [x] **`/welcome` onboarding page** — `frontend/app/welcome/page.tsx` (NEW): 3-option goal selector (Learn basics / Trade timing / Research stocks); routes to most relevant feature; sets `has_completed_onboarding` + `onboarding_goal` in localStorage; redirects back if already completed. Closes `todos-v3 §9 UX-ONBOARD-01`.
- [x] **Empty watchlist CTA** — `WatchlistWidget.tsx`: dashed-border interactive card; clicking focuses the add-ticker input; copy "Add your first stock — Track its GAS score, grade & signal here". Closes `todos-v3 §9` + `todos.md §11`.

---

## ✅ Sprint 38: Monetisation & Pro Features (v4.3)
Goal: UX transitions from "free everything" to a tiered model with a 7-day trial.

### Delivered
- [x] **Pro gate with lock icon** (🔒 overlay).
    - [x] Apply to: Walk-Forward panel (backtesting)
    - [x] Apply to: AI Allocator (portfolios)
    - [x] Apply to: Fed Policy page
    - [x] Apply to: Advanced Sentiment
    - [x] Apply to: Indicators page
- [x] **Free 7-day trial flow** (no card required).
    - [x] Backend `User.trial_ends_at` column + migration.
    - [x] `POST /billing/start-trial`.
    - [x] Frontend start-trial button & status banner.
- [x] **Cancellation flow with pause offer**.
    - [x] `/billing/cancel` page with 30-day pause offer.
- [x] **Invoice/receipt download** (Stripe proxy stub).

### Migration note
```bash
alembic revision --autogenerate -m "add_trial_ends_at_to_users"
alembic upgrade head
```

---

## ✅ Sprint 39 — Complete

**Sources:** `todos-v3.md` §19 (Showcase) · §20 (Investment Strategy Planner) · `todos.md` §16

### Deliverables
- [x] **Showcase product preview modal** — `frontend/app/showcase/page.tsx`: each product card gets a "Preview" button opening an embedded Google Sheets / PDF in a modal; clearly watermarked "Sample Only"; `PreviewModal` component with iframe + watermark overlay. Closes `todos-v3 §19 SHOP-V2-01`.
- [x] **Bundle configuration** — Backend: `bundle` flag + `bundle_items[]` on product model; seed at least one bundle ("Investor Bundle" — Portfolio Tracker + Retirement Calculator) with "Save X%" badge. Frontend: bundle cards in Showcase with "What's included" expandable section. Closes `todos-v3 §19 SHOP-V2-03`.
- [x] **"Coming Soon" + Notify me section** — `frontend/app/showcase/page.tsx`: dedicated Coming Soon row for roadmap products (FIRE Calculator, Tax-Loss Harvesting Tracker, Crypto Tax Report, Real Estate Analyzer); `POST /showcase/notify` stores user preference; per-product "Notify me" toggle. Closes `todos-v3 §19 SHOP-ROADMAP-01`.
- [x] **Asset allocation suggester** — `frontend/app/portfolio/allocate/page.tsx` (NEW): inputs: risk profile (from `User.risk_profile`), age, time horizon, currency; output: pie chart + table of suggested asset class weights (equities/bonds/cash/alternatives); always shows educational disclaimer. Closes `todos-v3 §20 PLAN-02`.
- [x] **Sequence of Returns Risk Visualiser** — `frontend/app/portfolio/retirement/page.tsx` (NEW): retirement planning tool; inputs: portfolio size, annual withdrawal, start year; renders three scenario lines (retiring before 2000/2008/2020 crash); shows portfolio survival rate and depletion year per scenario; Recharts `LineChart`; educational disclaimer. Closes `todos-v3 §20 PLAN-05`.

---

## Sprint 40 — Planned

**Sources:** `todos-v4.md` Phase 6 Tier 1 (external data sources — first wave)

### Deliverables
- [ ] **CNN Fear & Greed Index scraper** — `backend/app/services/external/cnn_fear_greed.py` (NEW): polls `https://production.dataviz.cnn.io/index/fearandgreed/graphdata` hourly; stores 0-100 score in a new `external_signals` table (`source`, `signal_name`, `value`, `fetched_at`); exposes `GET /api/v1/macro/fear-greed/cnn`; `fear_greed_norm` feature added to all tickers in `engineer_features()`. Closes `todos-v4 Phase 6 #1`.
- [ ] **Crypto Fear & Greed Index** — `backend/app/services/external/crypto_fear_greed.py` (NEW): polls `https://api.alternative.me/fng/` hourly; stores in `external_signals`; exposes `GET /api/v1/macro/fear-greed/crypto`; `crypto_fear_greed_norm` feature added to crypto tickers only (BTC-USD, ETH-USD). Closes `todos-v4 Phase 6 #2`.
- [ ] **Google Trends via pytrends** — `backend/app/services/external/google_trends.py` (NEW): fetches weekly relative search interest (0-100) per ticker via `pytrends`; `geo='DE'` for TR DE stocks; stores in `external_signals`; `google_trends_norm` feature in `engineer_features()`; cron: daily at 08:00 UTC. Closes `todos-v4 Phase 6 #3`.
- [ ] **Reddit sentiment extension** — `backend/app/services/reddit_service.py` (extend existing): add r/de and r/aktien to existing subreddit list; compute `reddit_mentions_norm` and `reddit_sentiment_norm` per ticker per 24h; store in `external_signals`; cron every 6h. Closes `todos-v4 Phase 6 #4`.
- [ ] **Wikipedia pageviews feature** — `backend/app/services/external/wikipedia_pageviews.py` (NEW): daily article view count per company Wikipedia page; z-score vs 252-day mean → `wikipedia_attention_zscore`; unusual attention (z > 2) flagged; added to `engineer_features()`; cron: daily. Closes `todos-v4 Phase 6 #5`.
- [ ] **`external_signals` DB table** — Alembic migration: `source VARCHAR(30)`, `symbol VARCHAR(20)`, `signal_name VARCHAR(50)`, `value FLOAT`, `raw_json JSONB`, `fetched_at TIMESTAMP`; index on `(symbol, signal_name, fetched_at DESC)`.

### Dependencies
```bash
pip install pytrends praw beautifulsoup4
alembic revision --autogenerate -m "add_external_signals"
alembic upgrade head
```

---

## Sprint 41 — Planned

**Sources:** `todos-v3.md` §17–18 (multi-asset expansion · ML improvements) · `todos-v5.md` Phase 4.4 + 7.1

### Deliverables
- [ ] **Crypto symbol expansion** — Add BTC-USD and ETH-USD to the default symbol list (`DEFAULT_SYMBOLS` config); backend: `crypto` asset class handling in `technical_service.py` (no earnings calendar, no sector data — graceful fallback); frontend: asset class badge on ticker header ("Crypto" pill); Crypto Fear & Greed score surfaced on the dashboard for crypto tickers (feeds from Sprint 40 scraper). Closes `todos-v3 §17 ASSET-CRYPTO-01`.
- [ ] **Commodity + FX + ETF symbol expansion** — Add GC=F (Gold), CL=F (Oil), EURUSD=X, GBPUSD=X, USDJPY=X to default list; seasonal sin/cos features in `engineer_features()` for commodities; interest rate differential feature for FX pairs; expand symbol autocomplete dropdown to visually group results by asset class (Equities / ETFs / Crypto / Commodities / Forex). Closes `todos-v3 §17 ASSET-COMMODITY-01`, `ASSET-FOREX-01`.
- [ ] **Optuna hyperparameter tuning** — `backend/app/services/ml_pipeline.py`: `tune_xgboost()` + `tune_lightgbm()` functions using Optuna (30 trials each); gated by `ENABLE_HYPERTUNING=True` in `.env`; runs as a separate overnight scheduler job (`job_overnight_tuning()` at 02:00 UTC); best params stored in model registry JSON for transparency; not run during real-time incremental updates. Closes `todos-v5 Phase 4.4`.
- [ ] **LSTM model as 4th competitor** — `backend/app/services/ml_pipeline.py`: `LSTMWrapper` using PyTorch (already in requirements); sequence length 20 bars; attention mechanism; added to the model competition alongside XGBoost, LightGBM, Logistic; disqualified if accuracy < 0.52 same as others; adds `lstm` to `requirements.txt`. Closes `todos-v3 §18`.
- [ ] **Kelly Criterion position sizing** — Backend: `kelly_fraction()` function in `prediction_service.py` (full Kelly halved, capped at 25%); inputs from prediction DB `live_accuracy`, `avg_return_when_correct`, `avg_return_when_wrong`; exposed via `GET /api/v1/technical/{symbol}/position-sizing`. Frontend: position size suggestion row in `LLMInsightCard.tsx` `[RISK MANAGEMENT]` section — "Suggested position size: ~8% of portfolio (Half-Kelly, based on 59% live win rate)"; Kelly formula shown in tooltip; marked as mathematical suggestion, not advice. Closes `todos-v5 Phase 7.1–7.2`.

### Dependencies
```bash
pip install torch  # LSTM
alembic upgrade head  # no new migrations — uses existing model registry
```

---

## Sprint 42 — Planned

**Sources:** `todos-v4.md` Phase 6 Tier 2 (external scrapers — second wave) · `todos-v3.md` §17

### Deliverables
- [ ] **finanzen.net German news scraper** — `backend/app/services/external/finanzen_net.py` (NEW): scrapes German-language headlines from `https://www.finanzen.net/nachrichten/aktien/{symbol}` every 4h using `BeautifulSoup4`; respects `robots.txt`; feeds scraped headlines into `sentiment_scorer.py` (FinBERT); stores in `news_articles` with `fetch_source='finanzen_net'`; German-language headlines especially valuable for TR DE stocks. Closes `todos-v4 Phase 6 #6`.
- [ ] **StockTwits extension** — `backend/app/services/stocktwits_service.py` (extend existing): full `reddit_mentions_norm` + `stocktwits_sentiment_norm` per ticker per 24h stored in `external_signals`; cron every 2h; expose `GET /api/v1/sentiment/{symbol}/social` combining Reddit + StockTwits signals into one response. Closes `todos-v4 Phase 6 #10`.
- [ ] **SEC EDGAR insider transactions** — `backend/app/services/external/sec_edgar.py` (NEW): polls SEC EDGAR Form 4 filings daily; computes `insider_net_sentiment` per symbol (cluster buying = bullish, large selling = bearish); stores in `external_signals`; `insider_net_sentiment` added as ML feature in `engineer_features()`; exposes `GET /api/v1/signals/{symbol}/insider`. Closes `todos-v4 Phase 6 #11`.
- [ ] **OpenInsider aggregated view** — `backend/app/services/external/open_insider.py` (NEW): scrapes `https://openinsider.com/screener?s={symbol}` daily; computes `insider_cluster_buy_score`; stored in `external_signals`; wired into insider endpoint above as a complementary source. Closes `todos-v4 Phase 6 #12`.
- [ ] **Social signals frontend panel** — `frontend/components/SocialSignalsPanel.tsx` (NEW): collapsible panel on the dashboard showing Reddit mentions + sentiment trend, StockTwits bull/bear ratio, insider net sentiment score; coloured bars + delta vs prior week; placed below `WhatChangedToday`. Wires to the new `/sentiment/{symbol}/social` endpoint.

### Dependencies
```bash
pip install beautifulsoup4 requests edgar  # if not already installed
```

---

## Sprint 43 — Planned

**Sources:** `todos.md` §2 · §3 · §14 (education UX · UI polish · settings personalisation) · `todos-v3.md` §8 · §13

### Deliverables
- [ ] **Glossary page** — `frontend/app/learn/glossary/page.tsx` (NEW): searchable A–Z glossary of all fin-eye terms (GAS, FinBERT, ATR, Kelly, Sharpe, Regime, SHAP, Walk-Forward, etc.); each entry has term, plain-English definition, and a "See it on dashboard →" deep-link; search filters list live as user types; every technical term across the app links here via `[?]` tooltip anchor. Closes `todos.md §2` + `todos-v3.md §8`.
- [ ] **Interactive onboarding tour update** — `frontend/components/onboarding/GuidedTour.tsx` (extend): add new tour stops for pages added since original tour — Watchlist Overview, Macro (FOMC countdown), Backtesting, Learn Hub, AI Allocator, Explore; fires automatically for `has_completed_tour === false`; "What does this mean?" CTA on GAS widget for cold users. Closes `todos-v3.md §9`.
- [ ] **Dark mode contrast audit** — Run WCAG AA contrast check across all components; fix failing elements (text-slate-500 on bg-slate-900, small labels in TimeframeGrid, badge text); document which tokens were changed; target ≥ 4.5:1 for body text, ≥ 3:1 for large text. Closes `todos.md §3`.
- [ ] **Page transition animations** — `frontend/app/layout.tsx`: add Framer Motion `AnimatePresence` + `motion.div` wrapper with subtle fade+slide (200ms) between route changes; respects `prefers-reduced-motion`. Closes `todos.md §3`.
- [ ] **Currency preference (USD/EUR)** — Backend: `User.currency` column (`'USD'` default) + migration + `PATCH /auth/me`; frontend: currency toggle in Settings Preferences section; `useCurrency()` hook formats all monetary values app-wide (backtesting initial capital, price targets, allocation amounts); EU users no longer see $10,000 friction point. Closes `todos.md §14` + `todos-v3.md §13`.
- [ ] **Compact / expanded view toggle** — Settings: data density toggle stored in `localStorage`; compact mode reduces padding, hides secondary labels, shrinks sparklines; expanded is the default; applies globally via a CSS class on `<body>`. Closes `todos.md §14`.

### Migration note
```bash
alembic revision --autogenerate -m "add_currency_to_users"
alembic upgrade head
```

---

## Sprint 44 — Planned

**Sources:** `todos.md` §4 · §12 · §17 (performance · community · admin ops) · `todos-v3.md` §23–24

### Deliverables
- [ ] **Bundle size audit + code splitting** — Run `next build --profile`; identify top contributors (Recharts, Lucide, large page components); apply `next/dynamic` lazy imports to all route pages and heavy components (backtesting, model-info, portfolio); target < 200kB initial JS. Closes `todos.md §4`.
- [ ] **Redis cache warming on startup** — `backend/app/main.py`: `startup_event` pre-warms Redis cache for top 20 most-watched symbols (GAS snapshots + macro latest + sentiment timeseries); ensures first user request after deploy hits cache, not cold DB. Closes `todos.md §4`.
- [ ] **Service Worker / PWA** — `frontend/public/sw.js` (NEW): basic Service Worker caching last-seen dashboard state (GAS snapshot, macro data, watchlist) for offline read; `next-pwa` or manual registration in `_document.tsx`; `manifest.json` with app icons. Closes `todos.md §4`.
- [ ] **Sentry error monitoring** — Fill `SENTRY_DSN` in `.env`; configure Sentry in `frontend/sentry.client.config.ts` + `sentry.server.config.ts`; backend: Sentry SDK in `main.py`; alert on error rate > 1%; breadcrumbs for API calls. Closes `todos.md §17` + `todos-v3.md §24`.
- [ ] **Churn early warning** — `backend/app/services/scheduler.py`: daily job (`job_churn_check()` at 09:00 UTC) — queries users with `last_login < now - 7 days` and `is_pro = True`; creates a `ChurnRisk` flag in admin DB; triggers re-engagement email via Resend ("We miss you — your watchlist has moved"). Closes `todos.md §17`.
- [ ] **Public strategy leaderboard** — `frontend/app/community/leaderboard/page.tsx` (NEW): sorted leaderboard of public backtesting strategies by Sharpe ratio; weekly reset; submit strategy button (marks a backtest run as public); top 10 shown with anonymised username, strategy name, Sharpe, total return, max drawdown. Backend: `is_public` flag on `BacktestRun` model + `GET /backtesting/leaderboard`. Closes `todos.md §12` + `todos-v3.md §23`.
- [ ] **A/B experiment framework** — `frontend/lib/experiments.ts` (NEW): `useExperiment(name)` hook reading feature flags from `GET /api/v1/experiments/assignments`; backend: `experiments` table with name, variant, user_pct rollout; admin UI at `/admin/experiments`; first experiment: onboarding flow variant (goal-selector vs direct dashboard). Closes `todos.md §17` + `todos-v3.md §24`.

---

## Sprint 45 — Planned

**Sources:** `todos.md` §18 · §21 (lifestyle finance content · B2B2C landlord architecture — Phase 3)

### Deliverables
- [ ] **`/lifestyle` hub page** — `frontend/app/lifestyle/page.tsx` (NEW): four content pillars — Tax Residency, Legal Structures, International Banking, Estate & Pension; "Lifestyle" added to nav under Learn; intro cards per pillar with icon + description + CTA. Closes `todos-v3.md §21 NOMAD-01`.
- [ ] **Interactive tax residency comparison table** — `frontend/app/lifestyle/tax-residency/page.tsx` (NEW): 10 countries with columns (income tax rate, capital gains, wealth tax, crypto treatment, days required, FATCA exposure); filter by "no wealth tax" / "territorial" / "crypto-friendly"; sort by any column; FATCA callout banner for US citizens. Closes `todos-v3.md §21 NOMAD-02`.
- [ ] **Legal entity type comparison** — `frontend/app/lifestyle/legal-structures/page.tsx` (NEW): 9 entity structures (sole trader, LTD, GmbH, LLC, holding, trust, foundation, BV, S.A.); interactive "Which fits me?" filter (questions: residency, asset type, privacy need, tax goal); results ranked by fit score. Closes `todos-v3.md §21 NOMAD-03`.
- [ ] **Tenant registration + B2B white-label foundation** — Backend: `tenants` table (`id`, `slug`, `name`, `logo_url`, `accent_colour`, `owner_user_id`); `/advisors/register` flow with invitation tokens; `TenantContext` FastAPI dependency injected into all relevant endpoints; cross-tenant access denied integration test. Frontend: subdomain-based logo + accent colour theming via CSS variable injection. Closes `todos-v3.md §22 B2B-TENANT-01/02` + `B2B-ISOLATION-01`.
- [ ] **Custom GAS weights per advisor** — `frontend/app/admin/gas-weights/page.tsx` (NEW): three sliders (Technical / Macro / Sentiment weight); preset profiles (Macro-Heavy, Technical-Focus, Balanced); weights must sum to 1.0 (enforced client + server); stored on `Tenant` model; `compute_signal_grade()` reads tenant weights when `tenant_id` is present. Closes `todos-v3.md §22 B2B-GAS-WEIGHTS-01`.
- [ ] **Compliance audit log** — Backend: append-only `compliance_audit_logs` table (`tenant_id`, `user_id`, `action`, `resource`, `ip_address`, `timestamp`); middleware writes a row for every authenticated API call in B2B context; `GET /admin/compliance/export` returns paginated CSV. Closes `todos-v3.md §22 B2B-COMPLIANCE-01`.

### Migration note
```bash
alembic revision --autogenerate -m "add_tenants_compliance_audit_logs"
alembic upgrade head
```

---

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
