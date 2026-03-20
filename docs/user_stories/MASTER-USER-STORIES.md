# Fin-Eye — Master User Stories (Extended)
> **Version:** 4.0 — Full implementation detail  
> **Last Updated:** 2026-03-20  
> **Status:** Living document — review at start of each sprint  
> **Source files:** user-stories v1.5 · user-stories v2.0 · prdv3.md · todos.md · codebase audit  
> **Supersedes:** MASTER-USER-STORIES.md v3.0

---

## How To Read This Document

Every story follows this structure:
1. **Story ID + Phase** — unique ID, never recycled
2. **User story** — As [persona], I want [thing] so that [reason]
3. **Acceptance Criteria** — testable, concrete conditions for "done"
4. **Backend Tasks** — specific files, endpoints, models, jobs to create or modify
5. **Frontend Tasks** — specific pages, components, hooks to create or modify
6. **Definition of Done** — the checklist that must all be green before the story is closed

**Status badges:** ✅ Done · 🔄 In Progress · ⬜ Not Started · 🚫 Blocked  
**Phases:** MVP (Weeks 1–12) · Growth (Months 3–6) · Premium (Months 6+) · Pre-Launch Blocker

---

## Personas

| Persona | Profile |
|---|---|
| **Emma** | Finance/economics student. Wants clarity, plain English, no quant jargon. Primary learning goal. |
| **Marco** | Retail / semi-pro trader. Wants actionable signals, timing, and risk management tools. |
| **Alex** | Institutional analyst. Needs bulk analysis, API access, compliance audit trails, PDF reports. |
| **Advisor** | Registered financial advisor. Uses the B2B2C layer to serve clients under their own brand. |

---

## Table of Contents

1. [Dashboard & Market Intelligence](#1-dashboard--market-intelligence)
2. [Conflict Detector & Why Is The Market Moving](#2-conflict-detector--why-is-the-market-moving)
3. [Technical ML Layer & Ensemble](#3-technical-ml-layer--ensemble)
4. [Backtesting Engine](#4-backtesting-engine)
5. [News Sentiment Layer](#5-news-sentiment-layer)
6. [Macro & Economic Layer](#6-macro--economic-layer)
7. [Educational Content & Onboarding](#7-educational-content--onboarding)
8. [Hedging Simulator](#8-hedging-simulator)
9. [Data Infrastructure & Pipelines](#9-data-infrastructure--pipelines)
10. [Portfolio View & Aggregated Insights](#10-portfolio-view--aggregated-insights)
11. [Retail Sentiment Reddit](#11-retail-sentiment-reddit)
12. [Political & Event Tracking](#12-political--event-tracking)
13. [Advanced Hedging & Strategy Library](#13-advanced-hedging--strategy-library)
14. [Advanced Sentiment & Custom Analytics](#14-advanced-sentiment--custom-analytics)
15. [Institutional API & White-Label](#15-institutional-api--white-label)
16. [Risk Management & Scenario Analysis](#16-risk-management--scenario-analysis)
17. [Authentication & Subscription Management](#17-authentication--subscription-management)
18. [Settings Watchlist & Notifications](#18-settings-watchlist--notifications)
19. [Content Management & Community](#19-content-management--community)
20. [Legal Compliance & Privacy](#20-legal-compliance--privacy)
21. [Monitoring Reliability & Ops](#21-monitoring-reliability--ops)
22. [Revenue Showcase & Marketplace](#22-revenue-showcase--marketplace)
23. [Mobile Experience](#23-mobile-experience)
24. [Advanced Macro Intelligence](#24-advanced-macro-intelligence)
25. [Institutional Reporting & Bulk Analysis](#25-institutional-reporting--bulk-analysis)
26. [Professional Content & Education](#26-professional-content--education)
27. [Security Backups & Disaster Recovery](#27-security-backups--disaster-recovery)
28. [Product Analytics & Experimentation](#28-product-analytics--experimentation)
29. [Email Onboarding & Newsletter](#29-email-onboarding--newsletter)
30. [Security Hardening Pre-Launch Blockers](#30-security-hardening-pre-launch-blockers)
31. [Multi-Asset ML Expansion](#31-multi-asset-ml-expansion)
32. [Advanced Indicators](#32-advanced-indicators)
33. [Digital Nomad & Lifestyle Finance Content](#33-digital-nomad--lifestyle-finance-content)
34. [Digital Product Showroom v2](#34-digital-product-showroom-v2)
35. [Investment Strategy Planner](#35-investment-strategy-planner)
36. [B2B2C Landlord Architecture](#36-b2b2c-landlord-architecture)
37. [Product Polish & Gap Closure](#37-product-polish--gap-closure)
38. [UX & Retention](#38-ux--retention)

---

## 1. Dashboard & Market Intelligence

### MVP-DASH-01 — GAS & Market Weather ⬜
**Phase:** MVP  
**As Emma, I want** a single dashboard showing a Global Alignment Score and Market Weather label for a selected stock **so that** I can understand market conditions at a glance without reading raw data.

**Acceptance Criteria**
- Ticker input accepts any valid symbol; defaults to AAPL on first load.
- GAS displayed as a large 0–100 number with a colour ring: green (≥60), amber (40–59), red (<40).
- Market Weather label shown alongside GAS. Labels and thresholds:
  - Strong Tailwind: 80–100
  - Mild Support: 60–79
  - Mixed Signals: 40–59
  - Headwind: 20–39
  - High Instability: 0–19
- GAS refreshes automatically every 60 seconds via SWR. A staleness indicator shows "X min ago".
- When data is loading, a layout-accurate skeleton replaces the GAS widget — no blank/flash.
- If the GAS endpoint returns an error, a fallback card says "Score temporarily unavailable" — the page does not crash.

**Backend Tasks**
- `GET /api/v1/admin/gas/snapshots/{symbol}` — already exists. Confirm it returns `gas_score`, `weather_label`, `regime`, `component_scores`, `computed_at`, `source`.
- `gas_precompute.py` — confirm `_gas_to_weather()` uses the 5-label thresholds (fixed in BUG-009).
- `scheduler.py` — confirm GAS pre-compute job runs every 15 minutes during US market hours (Mon–Fri 13:00–21:00 UTC).
- Redis cache key: `gas:snapshot:{SYMBOL}` with 15-minute TTL.

**Frontend Tasks**
- `components/MarketWeatherWidget.tsx` — already exists. Audit: ensure it renders all 5 weather labels, not 4. Add skeleton loader state. Add `onExplain` callback prop that opens `ScoreExplainPanel`.
- `app/page.tsx` — confirm SWR hook `fetchGasSnapshot(activeSymbol)` with `refreshInterval: 60_000` and `keepPreviousData: true`.
- Add `SnapshotMeta` staleness indicator (already exists in page.tsx — ensure it's visible and colour-coded: green <30min, amber 30–60min, red >60min).
- Wrap `MarketWeatherWidget` in an `ErrorBoundary` with a fallback card.

**Definition of Done**
- [ ] GAS displays for AAPL, TSLA, and a crypto symbol (BTC-USD) without error
- [ ] Market Weather label matches GAS value according to 5-label thresholds
- [ ] Staleness indicator updates every minute
- [ ] Skeleton loader visible during initial load
- [ ] Error boundary prevents full page crash when API is down

---

### MVP-DASH-02 — Regime & Volatility Classification ⬜
**Phase:** MVP  
**As Marco, I want** to see the technical regime (Risk-On / Risk-Off / Range-Bound) and volatility regime on the dashboard **so that** I can calibrate my trading aggressiveness to the current environment.

**Acceptance Criteria**
- Regime label displayed: one of `Risk-On`, `Risk-Off`, `Transitional`.
- Regime is derived from technical score: ≥60 = Risk-On, ≤40 = Risk-Off, between = Transitional.
- VIX-based volatility regime displayed: Low (<15), Medium (15–25), High (>25).
- If regime changes between two refreshes, a subtle "Regime changed X min ago" badge appears for 10 minutes.
- Clicking the regime widget opens a `ScoreExplainPanel` with the technical + volatility breakdown.
- Regime uses the `regime` field from the GAS snapshot where available; falls back to computing from `techScore`.

**Backend Tasks**
- `gas_precompute.py` — `_technical_to_regime(technical_score)` — confirm logic: ≥60 = "Risk-On", ≤40 = "Risk-Off", else "Transitional".
- GAS snapshot response must include `regime` and `component_scores.technical`.
- VIX value available from `GET /api/v1/macro/latest` → `data.vix.value`.

**Frontend Tasks**
- `components/RegimeWidget.tsx` — already exists. Audit: add "Regime changed" badge logic using previous vs current regime stored in a `useRef`. Add `onExplainTechnical` and `onExplainVolatility` callback props.
- `app/page.tsx` — pass `regimeOverride` from GAS snapshot, `vixLevel` from macro data, `techScore` from component scores.

**Definition of Done**
- [ ] Regime label correct for scores above 60, below 40, and between
- [ ] VIX level shown with correct Low/Medium/High label
- [ ] Regime change badge appears when regime flips between two refreshes
- [ ] Clicking widget opens explain panel

---

### MVP-DASH-03 — Multi-Timeframe Technical Signal Grid ⬜
**Phase:** MVP  
**As Emma, I want** to see 1h, 4h, 1d, 1w, 1m technical signals **so that** I can understand if short-term and long-term signals agree or conflict.

**Acceptance Criteria**
- Five timeframe tiles rendered: 1h, 4h (currently active), 1d, 1w, 1m.
- Each tile shows: timeframe label, directional label (Bullish / Neutral / Bearish), confidence score (0–100), model used, and validation Sharpe.
- Colour coding: Bullish = emerald, Bearish = rose, Neutral = amber.
- If a timeframe model is not trained, the tile shows "No model — train first" in a muted state, not a blank or crash.
- Note: Currently only 1h and 4h are trained. 1d, 1w, 1m tiles should gracefully show untrained state until models are added.
- Timeframe grid is wrapped in an error boundary.

**Backend Tasks**
- `GET /api/v1/technical/{symbol}/latest` — returns `signals` array. Each signal: `timeframe`, `direction`, `confidence`, `sharpe_weight`, `model_used`.
- `technical_service.py` — `TIMEFRAMES = ["1h", "4h"]` (confirmed fixed). Future: expand to ["1h", "4h", "1d", "1w", "1mo"] when training pipeline covers those timeframes.
- `generate_timeframe_signal()` — raises `ValueError` if no model exists. `compute_technical_consensus()` gracefully skips failed timeframes.

**Frontend Tasks**
- `components/TimeframeGrid.tsx` — already exists. Audit: ensure it renders all signals from the `signals` array. Add "no model" tile state. Apply consistent colour coding per acceptance criteria.
- `app/page.tsx` — `techData?.signals ?? []` passed to `TimeframeGrid`. Add error message in the timeframe section when `techError` is present.

**Definition of Done**
- [ ] Grid renders for AAPL after training (1h and 4h tiles show real values)
- [ ] Untrained timeframes show graceful "no model" state
- [ ] Colour coding matches Bullish/Bearish/Neutral semantics
- [ ] Error boundary prevents page crash if technical endpoint fails

---

## 2. Conflict Detector & Why Is The Market Moving

### MVP-EXPL-01 — Plain-English Why-Moving Panel ⬜
**Phase:** MVP  
**As Emma, I want** a plain-English explanation of why the selected stock is in its current state **so that** I can connect technical, sentiment, and macro drivers without quant expertise.

**Acceptance Criteria**
- Panel shows 3 bullet points: one each for technical, sentiment, and macro contributions.
- Each bullet references actual current values (e.g. "4 of 5 timeframes bullish", "30-day sentiment: +0.42").
- If a data source is unavailable, the bullet says "data not yet available" — it never shows raw error text.
- Panel always ends with a non-advisory disclaimer line.
- Panel updates when `activeSymbol` changes.

**Backend Tasks**
- No new endpoint needed. `buildWhyBullets()` logic already in `app/page.tsx` — this is a pure frontend concern.
- Ensure `GET /api/v1/technical/{symbol}/latest`, `GET /api/v1/sentiment/{symbol}/timeseries`, and `GET /api/v1/macro/latest` all return the values needed to populate the bullets.

**Frontend Tasks**
- `components/WhyMovingPanel.tsx` — already exists. Audit: ensure it renders `bullets` array correctly, always shows disclaimer, handles empty bullets array.
- `app/page.tsx` — `buildWhyBullets()` function — already implemented. Audit null-safety for each data source.

**Definition of Done**
- [ ] Panel shows 3 bullets with real values after DB is seeded
- [ ] "Data not yet available" shown when a data source is empty (not an error)
- [ ] Disclaimer always visible
- [ ] Panel updates immediately when symbol is changed

---

### MVP-EXPL-02 — Conflict Detector ⬜
**Phase:** MVP  
**As Marco, I want** conflict alerts when layers disagree **so that** I am warned about unstable environments before acting.

**Acceptance Criteria**
- Conflict detected when: any two of Technical/Sentiment/Macro diverge by >30 points, OR timeframe agreement < 40%.
- Conflict block shows: conflicting layers named, magnitude of divergence in points, a caution message.
- Multiple conflicts listed separately (e.g. "Technical vs Macro" and "Technical vs Sentiment" are two rows).
- "No major conflicts detected" shown (with a green indicator) when all layers agree.
- Conflict block is visually distinct but not alarmist — uses amber/orange, not red.

**Backend Tasks**
- No new endpoint. `detectConflicts()` logic is in `app/page.tsx`. Review and confirm threshold logic: `(sa > 65 && sb < 35) || (sb > 65 && sa < 35)` for layer pairs. Timeframe agreement: `dominant / signals.length < 0.4`.

**Frontend Tasks**
- `components/ConflictDetector.tsx` — already exists. Audit: ensure it handles `conflicts: []` gracefully, renders multiple conflicts as a list, uses correct colour (amber not red).
- `app/page.tsx` — `detectConflicts()` — confirm `sentScore0100` mapping `((sent30d ?? 0) + 1) / 2 * 100`.

**Definition of Done**
- [ ] Conflict correctly detected for a symbol where technical and macro diverge
- [ ] "No conflicts" state shows correctly when all layers are aligned
- [ ] Multiple conflicts each shown as separate rows
- [ ] Amber/orange colour used, not red

---

## 3. Technical ML Layer & Ensemble

### MVP-TECH-01 — Four-Model Competition Per Timeframe ⬜
**Phase:** MVP  
**As a backend/ML engineer, I want** four competing models trained per timeframe with the winner selected by Sharpe ratio **so that** the technical consensus is based on risk-adjusted performance.

**Acceptance Criteria**
- Training pipeline runs for: LSTM with attention, XGBoost, Logistic Regression, Prophet — per timeframe.
- Feature set (25 features): `ret_1`, `sma_cross_10_20`, `sma_cross_20_50`, `rsi_14`, `macd`, `macd_hist`, `bb_width`, `bb_pb`, `mom_10`, `mom_20`, plus sentiment features, macro features (VIX, yield spread, Fed rate), temporal features (day-of-week, month).
- Walk-forward split: 80% train / 20% validation (time-ordered, no shuffling).
- Each model evaluated on: Sharpe ratio, accuracy. Winner = highest Sharpe.
- Model registry (`backend/data/models/model_registry.jsonl`) updated with: symbol, timeframe, model_name, trained_at, artifact_file, validation_sharpe, metrics.
- Training triggered via `POST /api/v1/technical/train/{symbol}`. Runs in background.
- Note: Currently only XGBoost, Logistic, and Prophet are implemented. LSTM is missing (BUG-006) — add as a future task.

**Backend Tasks**
- `services/ml_pipeline.py` — current state: `LogisticWrapper`, `XGBoostWrapper`, `ProphetWrapper`. Add `LSTMWrapper` using PyTorch (already in requirements). Minimum: 64-unit LSTM → Dense → sigmoid.
- `services/ml_pipeline.py` — `run_training_pipeline()` — confirm all three (four) models compete, winner saved with full metadata.
- `services/feature_builder.py` — audit feature set. Ensure sentiment score (30d avg) and macro values (VIX, yield spread) are included as features when available.
- `api/v1/endpoints/technical.py` — `POST /train/{symbol}` — confirm async background task, returns `{"status": "processing"}` immediately.
- Artifact storage: currently `backend/data/models/{symbol}_{tf}_winner.joblib`. Plan to migrate to R2/S3 (SEC-08).

**Frontend Tasks**
- No direct frontend needed. Training is triggered from curl / admin panel.
- Training status can be monitored via `GET /api/v1/technical/{symbol}/latest` — if no model exists, signals array is empty.

**Definition of Done**
- [ ] Training runs for at least XGBoost and Logistic for AAPL 1h without error
- [ ] Registry file updated after training
- [ ] `POST /train/AAPL` returns 200 with `"status": "processing"`
- [ ] `GET /technical/AAPL/latest` returns real signals after training completes

---

### MVP-TECH-02 — Technical Confidence Score Consensus ⬜
**Phase:** MVP  
**As Marco, I want** the timeframe predictions aggregated into a single Technical Confidence Score **so that** I can see how aligned the technical picture is overall.

**Acceptance Criteria**
- Each timeframe signal weighted by its validation Sharpe (min 0.1 to avoid negatives).
- Weighted consensus mapped: raw (−1 to +1) → score (0 to 100) via `(raw + 1) / 2 * 100`.
- Score bands: Strong Bullish ≥80, Bullish Focus ≥60, Mixed/Neutral ≥40, Bearish Focus ≥20, Strong Bearish <20.
- API returns `technical_confidence_score` and `consensus` label.
- If zero timeframe models exist, API returns structured error (not 500) with message to train first.

**Backend Tasks**
- `services/technical_service.py` — `compute_technical_consensus()` — already implemented. Confirm Sharpe weighting, score mapping, label bands.
- `api/v1/endpoints/technical.py` — `GET /{symbol}/latest` — confirm returns `technical_confidence_score`, `consensus`, `signals[]`.
- Confirm `TIMEFRAMES = ["1h", "4h"]` (fixed). Confirm 4h inference uses 1h data + resample (fixed).

**Frontend Tasks**
- `app/page.tsx` — `techScore = gasSnapshot?.component_scores?.technical ?? techData?.technical_confidence_score ?? 50` — confirm correct fallback chain.
- `components/TimeframeGrid.tsx` — renders signals from API. Score displayed as `{techScore.toFixed(1)} / 100` in the technical consensus header.

**Definition of Done**
- [ ] Consensus score reflects weighted average of trained timeframes
- [ ] Label correctly reflects score band
- [ ] Score displayed in dashboard Technical Consensus widget
- [ ] Zero-model error returns structured JSON, not 500

---

## 4. Backtesting Engine

### MVP-BACK-01 — Momentum Strategy Backtest ⬜
**Phase:** MVP  
**As Marco, I want** to run a backtest of a momentum strategy on a chosen stock **so that** I can see historical performance with realistic statistics.

**Acceptance Criteria**
- Backtesting page allows user to: select symbol, choose "Momentum" template, adjust SMA fast/slow lengths and RSI threshold.
- Backtest uses at least 5 years of daily OHLCV data.
- Output: total return %, annualised return %, Sharpe ratio, Sortino ratio, max drawdown %, win rate %, recovery factor, total trades.
- Equity curve chart rendered with a buy-and-hold benchmark line.
- Slippage: 0.1% per trade. Spread: 5bp.
- Results page shows initial capital, symbol, strategy name, parameter values used.
- Backtest request validated: start_date must be before end_date, date range ≥ 1 year, no future dates (BUG-018 fixed).

**Backend Tasks**
- `services/backtesting_service.py` — `BacktestingEngine` + `_run_momentum_strategy()` — already implemented. Audit: ensure SMA fast/slow are read from `request.parameters`, not hardcoded.
- `schemas/backtest_models.py` — `BacktestRequest` — validation fixed (BUG-018). Confirm validators active.
- `api/v1/endpoints/backtesting.py` — confirm `POST /api/v1/backtest` endpoint exists and is wired.
- Add `Mean Reversion` strategy: buy when `close < lower_bb` (2σ below 20-day SMA), exit when price returns to SMA. Parameters: `bb_period` (default 20), `bb_std` (default 2).
- Add `Macro-Responsive` strategy: go long only when `macro_score > 60` AND 50-day SMA is rising. Exit when macro_score < 40. Parameters: `macro_threshold_entry` (default 60), `macro_threshold_exit` (default 40), `sma_period` (default 50).

**Frontend Tasks**
- `app/backtesting/page.tsx` — audit: strategy selector dropdown, parameter input fields, submit button.
- Build equity curve chart component using Recharts `LineChart`. Two lines: strategy equity and buy-and-hold benchmark.
- Build stats table displaying all 8 metrics with colour coding (positive = green, negative = red).
- Add loading state (skeleton) during backtest computation.
- Export button: CSV of equity curve + stats (POLISH-04).

**Definition of Done**
- [ ] Momentum backtest runs for AAPL 2019–2024 and returns real metrics
- [ ] Equity curve renders with benchmark line
- [ ] Invalid date range returns validation error (not 500)
- [ ] Mean Reversion strategy available as template
- [ ] Macro-Responsive strategy available as template

---

### MVP-BACK-02 — Overfitting Warnings ⬜
**Phase:** MVP  
**As Emma, I want** clear overfitting warnings **so that** I don't over-trust impressive historical results.

**Acceptance Criteria**
- A non-dismissable warning block always visible on backtest results page, explaining: backtest ≠ live trading, typical Sharpe degradation of ~50% live vs backtest, data-snooping bias.
- If Sharpe ratio > 1.2: additional "possible overfitting" warning shown in amber.
- If max drawdown > 40%: "High drawdown risk" warning shown.
- If total trades < 20: "Insufficient trades for statistical significance" warning shown.
- All warnings link to `/learn/backtesting-pitfalls` article.

**Backend Tasks**
- `schemas/backtest_models.py` — `BacktestResponse` — `overfitting_warning: bool` field already exists.
- Extend: add `warnings: List[str]` field to `BacktestResponse`. Populate in `BacktestingEngine.run()` based on Sharpe > 1.2, drawdown > 40%, trades < 20.

**Frontend Tasks**
- `components/OverfittingWarning.tsx` — already exists. Audit: ensure it always renders (not just when `overfitting_warning=True`), shows the standard educational block regardless.
- Render `warnings` list from API response as additional amber alert boxes.
- Add link to `/learn/backtesting-pitfalls` in the warning block.

**Definition of Done**
- [ ] Standard warning block always visible on results page
- [ ] Sharpe > 1.2 triggers additional overfitting warning
- [ ] `warnings` array populates correctly from backend
- [ ] Link to learn article present

---

## 5. News Sentiment Layer

### MVP-SENT-01 — Sentiment Timeseries Chart ⬜
**Phase:** MVP  
**As Emma, I want** a time-series chart of news sentiment for a stock **so that** I can visually understand whether news flow has been improving or worsening.

**Acceptance Criteria**
- Sentiment timeseries chart shows 30-day daily sentiment scores as a bar or line chart.
- Current 1d / 7d / 30d aggregate values displayed above the chart as KPI cards.
- Article list below chart: title, source, publication date/time, sentiment score (colour-coded), and a clickable link to the full article at the source (UX-NEWS-01).
- Pagination: 10 articles per page with page selector (UX-NEWS-02).
- Sentiment score displayed as a −1 to +1 raw value AND a 0–100 normalised value.
- Page updates when symbol is changed.

**Backend Tasks**
- `GET /api/v1/sentiment/{symbol}/timeseries` — confirm it returns `sentiment_30d`, `sentiment_7d`, `sentiment_1d`, and a `timeseries` array of `{date, score}` objects.
- `GET /api/v1/sentiment/{symbol}/articles` — confirm it returns paginated articles with `title`, `source`, `url`, `published_at`, `sentiment_score`. Add `page` and `page_size` query params if missing.
- `services/sentiment_service.py` — confirm `url` field is stored in `NewsArticle` model and returned in the response.

**Frontend Tasks**
- `app/news-sentiment/page.tsx` — audit full page. Add pagination component. Ensure each article card renders a clickable external link (`target="_blank" rel="noopener"`).
- `components/SentimentChart.tsx` — already exists. Audit: ensure 30-day bar chart renders correctly. Add trend arrow (↑/↓) comparing current 7d to prior 7d average (UX-NEWS-04).
- `components/ArticleList.tsx` — already exists. Add external link. Add sentiment badge with colour coding.

**Definition of Done**
- [ ] Chart renders with real data after news seeding
- [ ] 1d/7d/30d cards show real values
- [ ] Articles have clickable links to original sources
- [ ] Pagination works (10 per page)
- [ ] Trend arrow correct (↑ when 7d improving vs prior 7d)

---

### MVP-SENT-02 — News Source Breakdown ⬜
**Phase:** MVP  
**As Marco, I want** to see which news sources are driving sentiment **so that** I can assess whether the narrative is broad-based or from a few outlets.

**Acceptance Criteria**
- Source breakdown table/chart shows: source name, article count, % positive, % negative, % neutral, average sentiment score.
- Data covers the last 30 days.
- Sorted by article count descending by default.
- Filter by sentiment (UX-NEWS-03): buttons for "All / Bullish / Bearish / Neutral" that filter both the article list and source table.
- Sort controls: by date, by sentiment score.

**Backend Tasks**
- `GET /api/v1/sentiment/{symbol}/sources` — implement if not exists. Query `news_articles` grouped by `source`, aggregated over last 30 days. Returns array of `{source, count, avg_score, pct_positive, pct_negative, pct_neutral}`.
- Add `sentiment_filter` query param (`positive | negative | neutral | all`) to the articles endpoint.

**Frontend Tasks**
- `components/SourceBreakdownTable.tsx` — already exists. Audit: ensure it renders all columns, sorts correctly.
- Add filter button row (All / Bullish / Bearish / Neutral) to `app/news-sentiment/page.tsx`. Wire to article list and source table simultaneously.
- Add sort controls: date asc/desc, sentiment high/low.

**Definition of Done**
- [ ] Source table shows real source names after news seeding
- [ ] Filter buttons correctly filter both article list and source table
- [ ] Table sorts correctly by count and sentiment

---

## 6. Macro & Economic Layer

### MVP-MACRO-01 — Macro Dashboard Indicators ⬜
**Phase:** MVP  
**As Marco, I want** a macro dashboard showing Fed rate, CPI, unemployment, 2–10 spread, and VIX **so that** I can frame stock signals within the broader economic environment.

**Acceptance Criteria**
- Each indicator displayed as a KPI card: current value, date of last update, a colour-coded arrow (up/down vs previous reading), and a short plain-English interpretation.
- Indicators: Fed Funds Rate, CPI YoY %, Unemployment Rate %, 10Y–2Y Yield Spread (bps), VIX.
- All values sourced from FRED via `GET /api/v1/macro/latest`.
- "Last updated: X hours ago" shown per indicator with colour coding (green <24h, amber 24–48h, red >48h).
- When FRED data is unavailable, each card shows "Data temporarily unavailable" — not blank, not an error.
- Yield curve chart (2Y/5Y/10Y/30Y) rendered as a line chart showing current curve shape.

**Backend Tasks**
- `GET /api/v1/macro/latest` — confirm returns all required indicators with `value`, `date`, `series_id`.
- `services/macro_data.py` — `MacroFetcher.fetch_and_store()` — confirm FEDFUNDS, CPIAUCSL, UNRATE, T10Y2Y, VIXCLS, DGS2, DGS5, DGS10, DGS30 are all fetched and stored.
- `services/macro_scoring.py` — `compute_yield_curve()` — already implemented. Confirm 4-point curve (2Y/5Y/10Y/30Y) returned.
- Add `GET /api/v1/macro/yield-curve` endpoint if not already a dedicated route.

**Frontend Tasks**
- `app/macro/page.tsx` — audit full page. Add KPI cards for each indicator. Add colour-coded arrows. Add "data age" freshness indicator.
- Add yield curve chart component using Recharts `LineChart`. X-axis: tenor years (2/5/10/30), Y-axis: yield %.
- Add short interpretation text per indicator (template strings: if CPI > 4%, "CPI elevated — Fed likely to remain restrictive").
- **Fed meeting countdown timer** (UX-MACRO-01): calculate days to next FOMC meeting. Store next FOMC dates as a static array (they are published 1 year in advance). Display "Next Fed Decision in X days" prominently.
- **Economic calendar** (UX-MACRO-02): render upcoming events from `GET /api/v1/events` as a 2-week forward list with event name, date, expected value, prior value.

**Definition of Done**
- [ ] All 5 indicators show real values after macro seeding
- [ ] Freshness indicator shows correct age
- [ ] Yield curve chart renders
- [ ] FOMC countdown correct
- [ ] Economic calendar shows upcoming events

---

### MVP-MACRO-02 — Macro Score ⬜
**Phase:** MVP  
**As Emma, I want** a simple Macro Score (0–100) and a human-readable label **so that** I understand the macro backdrop at a glance.

**Acceptance Criteria**
- Macro Score (0–100) displayed on both the main dashboard and the Macro tab.
- Labels: "Supportive" (≥70), "Neutral" (40–69), "Stressed" (<40).
- Score computed from FRED indicators using the `compute_macro_score()` function (already implemented in `macro_scoring.py`).
- Score component breakdown visible on the Macro tab: each indicator's contribution shown.
- Score updates daily after FRED data refresh at 08:00 UTC.

**Backend Tasks**
- `services/macro_scoring.py` — `compute_macro_score()` — already implemented. Returns `MacroScoreDto(score, label)`.
- `GET /api/v1/macro/latest` — ensure `macro_score` object included in response with `score` and `label`.
- `GET /api/v1/macro/score-breakdown` — add if not exists. Returns list of `{indicator, contribution, description}` showing each indicator's contribution to the score.

**Frontend Tasks**
- `app/page.tsx` — `macroScore = gasSnapshot?.component_scores?.macro ?? macroData?.macro_score?.score ?? 50` — confirm fallback chain.
- `app/macro/page.tsx` — add Macro Score KPI card prominently at the top. Add score breakdown component below (accordion or table showing each indicator's contribution).

**Definition of Done**
- [ ] Score shows real value (not 50.0) after macro seeding
- [ ] Label correct for score ranges
- [ ] Breakdown visible on Macro tab
- [ ] Score shown on main dashboard

---

## 7. Educational Content & Onboarding

### MVP-LEARN-01 — Learn / Blog Section ⬜
**Phase:** MVP  
**As Emma, I want** a Learn/Blog section with educational posts **so that** I can build structured knowledge about macro, regimes, and backtesting.

**Acceptance Criteria**
- `/learn` page shows a list of published posts: title, short summary, read-time estimate, publish date, category tag.
- At least 6 initial posts available at launch covering: Macro 101, GAS Explained, Backtesting Pitfalls, Sentiment Basics, Regime Shifts, Reading Yield Curves.
- Each post page includes: full content, author, date, read time, standard disclaimer at top and bottom.
- Categories: Macro 101 · Backtesting · Sentiment · GAS · Regime · Yield Curves.
- Glossary page at `/learn/glossary`: searchable A–Z list of terms. Each term has: name, plain-English definition, and a "Learn more" link to the relevant article.
- All content navigable without login (public).

**Backend Tasks**
- `models/blog.py` — `BlogPost` model with: `id`, `title`, `slug`, `summary`, `content` (markdown), `author`, `category`, `published_at`, `read_time_minutes`, `is_published`.
- `api/v1/endpoints/cms.py` — `GET /api/v1/cms/posts` — returns paginated list of published posts. `GET /api/v1/cms/posts/{slug}` — returns single post.
- Seed at least 6 initial posts either via a seed script or the admin CMS.
- `GET /api/v1/cms/glossary` — returns list of `{term, definition, related_slug}`.

**Frontend Tasks**
- `app/learn/page.tsx` — blog post list with category filter tabs. Cards with title, summary, read time, date, category badge.
- `app/learn/[slug]/page.tsx` — individual post page. Render markdown content. Disclaimer at top and bottom.
- `app/learn/glossary/page.tsx` — searchable glossary. Filter by letter or keyword. Each entry expandable.
- Add "Learn more" links from dashboard tooltips to relevant glossary entries.

**Definition of Done**
- [ ] 6+ posts visible at `/learn` after seeding
- [ ] Individual post renders markdown correctly
- [ ] Glossary searchable and linked from dashboard
- [ ] Disclaimer present on every article page
- [ ] Category filter works

---

### MVP-ONBOARD-01 — Guided In-App Tour ⬜
**Phase:** MVP  
**As a new user, I want** a short in-app tour **so that** I don't feel lost on first login.

**Acceptance Criteria**
- Tour triggers automatically on first login (checked via `user.has_completed_tour` flag in DB).
- Tour steps (4–6): GAS score explanation → Market Weather → Timeframe Grid → Why Moving panel → Learn tab link → Conflict Detector.
- Each step has a tooltip with: title, 2–3 sentence explanation, a "Next" button and a "Skip" button.
- Tour can be re-launched from Settings → "Restart Tour".
- Tour completion state stored on user record in DB (`users.has_completed_tour = True`).
- Tour works correctly on mobile (tooltips anchor to elements, don't overflow viewport).

**Backend Tasks**
- `models/user.py` — add `has_completed_tour: bool = False` column.
- `PUT /api/v1/auth/tour-complete` — sets `has_completed_tour = True` for the current user.
- Alembic migration for the new column.

**Frontend Tasks**
- `components/onboarding/GuidedTour.tsx` — already exists. Audit: check it reads `user.has_completed_tour`. Ensure it calls `PUT /auth/tour-complete` on completion or skip.
- Add tour steps for pages added after the tour was originally written: Watchlist Overview, Macro (Fed countdown), Learn Hub.
- Add "Restart Tour" button to `app/settings/page.tsx` that resets the tour state and re-triggers.
- Ensure all tour target elements have the correct CSS classes (`tour-gas-score`, `tour-regime`, `tour-timeframes`, `tour-why-moving`, `tour-learn-tab`).

**Definition of Done**
- [ ] Tour fires on first login for a new user
- [ ] Does NOT fire on subsequent logins
- [ ] All 6 steps render correctly with correct anchors
- [ ] Completion stored in DB
- [ ] "Restart Tour" in Settings re-triggers correctly

---

### UX-ONBOARD-01 — "Start Here" Welcome Page ⬜
**Phase:** MVP  
**As a new user, I want** a focused `/welcome` page after email confirmation **so that** my first experience is personalised, not overwhelming.

**Acceptance Criteria**
- After email verification, user is redirected to `/welcome` (not the full dashboard).
- Welcome page asks: "What's your primary goal?" with three options:
  1. "Learn how markets work" → links to `/learn/gas-explained`
  2. "Improve my trade timing" → links to `/` (dashboard) with AAPL pre-loaded
  3. "Research stocks in depth" → links to `/backtesting`
- User's goal choice stored as `user.onboarding_goal` in DB.
- After choosing, user is routed to the appropriate page.
- Welcome page not shown again after the first visit (checked via `user.has_seen_welcome`).

**Backend Tasks**
- `models/user.py` — add `onboarding_goal: Optional[str]`, `has_seen_welcome: bool = False`.
- `PUT /api/v1/auth/onboarding-goal` — stores goal and sets `has_seen_welcome = True`.
- Alembic migration.

**Frontend Tasks**
- `app/welcome/page.tsx` — new page. Three large clickable cards. Call `PUT /auth/onboarding-goal` on click.
- Auth redirect logic: after email verification success, redirect to `/welcome` instead of `/`.
- Check `user.has_seen_welcome` on load — if true, redirect to `/`.

**Definition of Done**
- [ ] New user sees `/welcome` after email verification
- [ ] Returning user does NOT see `/welcome`
- [ ] Goal choice stored in DB
- [ ] Each option routes to correct page

---

## 8. Hedging Simulator

### MVP-HEDGE-01 — Basic Hedging Simulator ⬜
**Phase:** MVP  
**As Marco, I want** to simulate a stock + protective put or stock + short ETF hedge **so that** I can see how hedging would have changed drawdowns historically.

**Acceptance Criteria**
- User selects: stock symbol, hedge type (protective put OR short inverse ETF), hedge size (% of position), and a historical scenario (e.g. 2020 COVID crash, 2022 bear market).
- Output: Beta of stock vs S&P 500, correlation between stock and hedge instrument, max drawdown reduction (%), estimated annual hedge cost (% of portfolio), before/after equity curve chart.
- Payoff diagram: shows P&L for stock alone and stock + hedge if the stock falls by −10%, −20%, −30%.
- Results include a disclaimer: "Estimated cost and protection are based on historical data. Actual options pricing varies. This is not financial advice."
- If insufficient OHLCV data is available for the symbol, a clear message is shown.

**Backend Tasks**
- `services/hedging_service.py` — already exists. Audit: confirm `compute_beta()`, `compute_correlation()`, `estimate_put_cost()`, `simulate_hedge_backtest()` are implemented.
- `api/v1/endpoints/hedging.py` — `POST /api/v1/hedge/simulate` — confirm it accepts `{symbol, hedge_type, hedge_size_pct, scenario}` and returns the required fields.
- Add scenario presets as a static config: `2020_covid` (2020-02-19 to 2020-03-23), `2022_bear` (2022-01-01 to 2022-10-13), `2008_gfc` (2008-09-01 to 2009-03-09).

**Frontend Tasks**
- `app/hedge/page.tsx` — audit full page. Add scenario selector dropdown. Add hedge type radio buttons. Add hedge size slider (10–100% of position, default 50%).
- Build before/after equity curve using Recharts. Build payoff diagram using `BarChart`.
- Show all output metrics in a results panel below the chart.
- Display disclaimer prominently below results.

**Definition of Done**
- [ ] Beta and correlation computed correctly for AAPL vs SPY
- [ ] Before/after equity curve renders for 2020 COVID scenario
- [ ] Payoff diagram shows correct P&L at −10/−20/−30%
- [ ] Disclaimer always visible
- [ ] Insufficient data error shown cleanly

---

## 9. Data Infrastructure & Pipelines

### MVP-DATA-01 — Data Pipeline Robustness ⬜
**Phase:** MVP  
**As a backend engineer, I want** robust, monitored pipelines for OHLCV, news, macro, and sentiment data **so that** models and dashboards always have fresh, consistent inputs.

**Acceptance Criteria**
- OHLCV daily pipeline: runs weekdays at 18:05 UTC. Fetches 5 years of daily data for all 18 default symbols. Upserts to `ohlcv_daily` table.
- OHLCV intraday pipeline: runs weekdays hourly 13:15–21:15 UTC. Fetches 1h bars (last 730 days), resamples to 4h. Upserts to `ohlcv_intraday` table.
- FRED macro pipeline: runs daily at 08:00 UTC. Fetches 11 FRED series. Upserts to `macro_indicators` table.
- News + sentiment pipeline: runs weekdays every 4 hours. Fetches Finnhub news, scores with VADER, stores in `news_articles` and `sentiment_aggregates`.
- Each pipeline: logs success/failure counts, writes to `pipeline_run_log`, sends Slack alert on failure if `SLACK_ERROR_WEBHOOK_URL` configured.
- Manual trigger endpoints: `POST /api/v1/data/fetch/ohlcv`, `POST /api/v1/data/fetch/macro`, `POST /api/v1/data/fetch/news`.
- Redis cache: GAS snapshots at 15-min TTL. Sentiment aggregates at daily TTL. Macro score at daily TTL.
- Validation on ingest: high < low → rejected with warning. Close ≤ 0 → rejected. Volume < 0 → rejected.

**Backend Tasks**
- `services/scheduler.py` — all 10 jobs confirmed (fetch_ohlcv_daily, fetch_ohlcv_intraday, fetch_macro, fetch_news, gas_precompute, alert_email_notifications, onboarding_day3, onboarding_day7, weekly_digest, backup_db).
- `services/ohlcv_fetcher.py` — `OHLCVFetcher.validate_row()` — already implemented. Ensure validation called on every inserted row.
- `services/metrics.py` — `record_pipeline_run()` — already implemented. Confirm each pipeline calls it.
- Add Slack alert in `job_fetch_ohlcv_daily` error handler: `if settings.slack_error_webhook_url: post_slack_alert(...)`.
- `models/market.py` — confirm `volume` column is `BigInteger` (migration BUG-011 must be applied).

**Frontend Tasks**
- Admin Ops dashboard (`/admin/ops`) — show pipeline run history: job name, last run time, last run status, rows processed.

**Definition of Done**
- [ ] All 18 symbols have OHLCV data after manual trigger
- [ ] FRED macro data present in DB after manual trigger
- [ ] News + sentiment data present after manual trigger
- [ ] Pipeline failure writes to metrics and sends Slack alert
- [ ] Volume column is BigInteger (migration applied)

---

## 10. Portfolio View & Aggregated Insights

### P2-PORT-01 — Portfolio Management ⬜
**Phase:** Growth  
**As Marco, I want** to create and manage a portfolio of stocks **so that** I can see GAS and risk at the portfolio level, not just per-symbol.

**Acceptance Criteria**
- User can create a named portfolio, add/remove symbols, and set position sizes (% weight or notional value).
- Portfolio view shows: portfolio name, total value, weighted average GAS score (weighted by position size), sector breakdown (pie chart), diversification score (0–100 based on average pairwise correlation).
- Each holding shown as a row: symbol, company name, weight %, individual GAS, regime, colour indicator.
- Weighted GAS updates when individual GAS snapshots are refreshed.
- Diversification score: 100 = perfectly uncorrelated, 0 = all holdings perfectly correlated. Uses 30-day rolling correlation matrix.
- Maximum 10 holdings per portfolio (Free tier). Unlimited for Pro.

**Backend Tasks**
- `models/portfolio.py` — `Portfolio` (id, user_id, name, created_at) and `PortfolioHolding` (id, portfolio_id, symbol, weight_pct, notional_value) — confirm schema.
- `GET /api/v1/portfolios` — list user's portfolios.
- `POST /api/v1/portfolios` — create portfolio.
- `POST /api/v1/portfolios/{id}/holdings` — add holding.
- `DELETE /api/v1/portfolios/{id}/holdings/{symbol}` — remove holding.
- `GET /api/v1/portfolios/{id}/analytics` — returns: weighted_gas, sector_breakdown, diversification_score, holdings with individual GAS.
- Diversification score computation: fetch 30-day OHLCV for all holdings, compute correlation matrix, average off-diagonal absolute values, invert (1 - avg_corr) * 100.

**Frontend Tasks**
- `app/portfolios/page.tsx` — audit existing page. Add: portfolio creation modal, holdings management table with weight input, weighted GAS display, sector pie chart, diversification score gauge.
- Rebalancing calculator link: "Rebalance this portfolio" → navigates to `/portfolios/{id}/rebalance` (PLAN-03).

**Definition of Done**
- [ ] Portfolio created, holding added/removed — persists across sessions
- [ ] Weighted GAS shown and updates when snapshots refresh
- [ ] Sector breakdown pie renders
- [ ] Diversification score computed and displayed
- [ ] Free tier 10-holding limit enforced

---

## 11. Retail Sentiment Reddit

### P2-RET-01 — Reddit Retail Sentiment ⬜
**Phase:** Growth  
**As Marco, I want** to see Reddit mention volume and sentiment for my stock **so that** I can spot overheated retail narratives.

**Acceptance Criteria**
- For a selected symbol: 30-day daily mention count chart, sentiment breakdown (% positive/neutral/negative), top 5 most bullish and top 5 most bearish recent comments (with subreddit, upvote count, timestamp).
- Retail Sentiment Score (0–100) shown: 0 = very bearish mentions, 50 = neutral, 100 = very bullish.
- Mention volume spike detection: if today's mentions are >2x the 30-day average, show an "Unusual activity" badge.
- Data sourced from: r/stocks, r/wallstreetbets, r/investing, r/SecurityAnalysis via PRAW.
- If Reddit API credentials are not configured, page shows "Reddit sentiment not configured" gracefully.

**Backend Tasks**
- `services/reddit_service.py` — already exists. Audit: confirm symbol-to-ticker mention extraction, VADER scoring of posts/comments, upsert to `social_sentiment` table (or equivalent).
- Add scheduled job `job_fetch_reddit` to `scheduler.py`: runs daily at 09:00 UTC.
- `GET /api/v1/sentiment/{symbol}/reddit` — returns: `daily_mentions[]`, `sentiment_breakdown`, `top_bullish[]`, `top_bearish[]`, `retail_score`, `has_spike`.
- Require `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` configured; return graceful 503 if missing.

**Frontend Tasks**
- `app/sentiment/page.tsx` — audit existing Retail Sentiment page. Add: 30-day mention chart, sentiment breakdown bar, top comments section, Retail Score card, "Unusual activity" badge.
- If Reddit data unavailable, show "Reddit sentiment not configured — add API credentials to enable this feature."

**Definition of Done**
- [ ] Mention chart renders with real data when credentials configured
- [ ] Retail Score computed and displayed
- [ ] Unusual activity badge triggers correctly
- [ ] Graceful fallback when credentials missing

---

## 12. Political & Event Tracking

### P2-EVENT-01 — Economic Event Calendar ⬜
**Phase:** Growth  
**As Emma, I want** an event calendar with upcoming macro and political events **so that** I understand when volatility is likely to increase.

**Acceptance Criteria**
- Events calendar shows 30 days forward: event name, date, country/region, category (Fed/ECB/NFP/CPI/Elections/Earnings), expected value, prior value (where applicable).
- Upcoming events sorted by date. Past events (last 7 days) shown with colour coding (green = beat expectations, red = missed).
- Clicking an event shows: brief description, historical impact (average % move in SPY or relevant index on event day over last 5 years), and a link to more context.
- "High impact" events tagged with a yellow ⚡ badge.

**Backend Tasks**
- `models/` — add `EconomicEvent` model: `id`, `event_name`, `event_date`, `country`, `category`, `expected_value`, `prior_value`, `actual_value`, `impact_level` (high/medium/low).
- Event sources: FOMC dates (static array, published annually), earnings from Finnhub `/earnings/calendar`, economic releases from a free calendar API (e.g. TradingEconomics limited free tier or hard-coded schedule).
- `GET /api/v1/events` — paginated event list with `from_date`, `to_date`, `category` filter params.
- Historical impact computation: for Fed/CPI/NFP events, compute average SPY 1-day return on event days over last 5 years using existing OHLCV data.

**Frontend Tasks**
- `app/macro/page.tsx` — add economic calendar component in a collapsible section or tab. Render events in a table or timeline format.
- Event detail modal: on click, show description + historical impact.
- Also used in `app/earnings/page.tsx` for earnings-specific events.

**Definition of Done**
- [ ] Calendar shows at least 10 upcoming events after implementation
- [ ] FOMC dates correctly populated for the next 12 months
- [ ] Historical impact shown for Fed and NFP events
- [ ] Past events colour-coded by beat/miss

---

## 13. Advanced Hedging & Strategy Library

### P2-HEDGE-ADV-01 — Multi-Leg Hedging Strategies ⬜
**Phase:** Growth  
**As Marco, I want** to test multi-leg strategies (collars, stock + put + short ETF) **so that** I can find cost-effective risk reduction.

**Acceptance Criteria**
- Hedging simulator extends to support: Collar (long stock + long put + short call), Stock + Put + Short ETF (3-leg), Beta-neutral pair (long stock + short index).
- Each strategy: configurable strike distance (% OTM), expiry, hedge size (%).
- Outputs: equity curves for unhedged vs each hedged strategy, max drawdown difference, hedge cost over period, payoff diagram at expiry.

**Backend Tasks**
- `services/hedging_service.py` — extend to support multi-leg strategy computation.
- `POST /api/v1/hedge/simulate` — add `strategy_type` param: `protective_put | short_etf | collar | beta_neutral`.
- Add `compute_collar_payoff()`, `compute_beta_neutral_payoff()` functions.

**Frontend Tasks**
- `app/hedge/page.tsx` — add strategy type selector. Add multi-leg parameter inputs (strike for put, strike for call in collar). Add comparison chart showing all strategies simultaneously.

**Definition of Done**
- [ ] Collar strategy returns correct payoff diagram
- [ ] 3-leg strategy (stock + put + ETF) computed correctly
- [ ] All strategies plotted on same comparison chart

---

### P2-STRAT-01 — Strategy Library ⬜
**Phase:** Growth  
**As Emma and Marco, I want** a strategy library where I can browse, save, and share backtested strategies **so that** I don't start from scratch every time.

**Acceptance Criteria**
- Strategy library page: shows platform templates + user-saved strategies.
- Each strategy card: name, description, key params, last backtest metrics (Sharpe, max DD, win rate).
- User can save a configured strategy with a custom name.
- User can load a saved strategy (pre-fills the backtesting form).
- Optional: public strategies with a "most popular" leaderboard sorted by Sharpe ratio (with weekly reset).

**Backend Tasks**
- `models/strategy.py` — `Strategy` model: `id`, `user_id`, `name`, `description`, `strategy_type`, `parameters` (JSON), `is_public`, `last_sharpe`, `created_at`.
- `GET /api/v1/strategies` — user's strategies + platform templates.
- `POST /api/v1/strategies` — save strategy.
- `GET /api/v1/strategies/leaderboard` — public strategies sorted by Sharpe.

**Frontend Tasks**
- `app/backtesting/page.tsx` — add "Save Strategy" button after running a backtest. Add "Load Strategy" dropdown to pre-fill form.
- New `app/strategies/page.tsx` — strategy library with search, filter by type, sort by metric.

**Definition of Done**
- [ ] Strategy saved after backtest run
- [ ] Saved strategy loads correctly into backtest form
- [ ] Leaderboard shows at least platform templates
- [ ] Public strategies visible to other users when `is_public = True`

---

## 14. Advanced Sentiment & Custom Analytics

### P3-SENT-ADV-01 — Multi-Source Advanced Sentiment ⬜
**Phase:** Premium  
**As Alex, I want** integrated sentiment from Twitter/X, earnings call transcripts, and Google Trends **so that** I get a complete picture of crowd and management tone.

**Acceptance Criteria**
- Advanced Sentiment page shows combined score broken down by: News (Finnhub), Reddit, Twitter/X (if credentials), Earnings Transcripts (if available).
- Source comparison chart: all sources plotted on same timeline over 30 days.
- Earnings transcript sentiment: management tone score (positive/negative/neutral) extracted from last 2 earnings calls.
- Google Trends integration: search interest index (0–100) for company name + ticker over last 90 days.

**Backend Tasks**
- `services/adv_sentiment_service.py` — already exists. Audit: confirm it handles the multi-source aggregation.
- Add `StockTwitsService` as a fallback if Twitter/X credentials unavailable.
- Add `GoogleTrendsService` using `pytrends` library.
- Add `EarningsTranscriptService`: download transcripts from Finnhub `/stock/transcripts` endpoint.

**Frontend Tasks**
- `app/sentiment-adv/page.tsx` — audit full page. Add source breakdown comparison chart. Add earnings transcript sentiment panel.

**Definition of Done**
- [ ] Multi-source score breakdown renders
- [ ] Google Trends chart renders for AAPL
- [ ] Earnings transcript sentiment shows for last 2 calls

---

### P3-ANALYTICS-01 — No-Code Indicator Builder ⬜
**Phase:** Premium  
**As Alex, I want** a no-code indicator builder **so that** I can design and test custom signals without writing code.

**Acceptance Criteria**
- Indicator builder UI: select primitives (RSI, MACD, SMA, etc.) from a dropdown and combine with math operators (+, −, ×, ÷, ratio).
- Real-time preview chart showing the custom indicator on 1 year of AAPL OHLCV data.
- Validation: division by zero raises a warning. Invalid expressions cannot be submitted.
- Custom indicator can be saved under a name and used in the backtesting strategy form as an entry/exit signal.

**Backend Tasks**
- `models/custom_indicator.py` — already exists. Audit schema.
- `services/indicator_service.py` — add expression evaluator using `pandas` operations (no `eval()` for security).
- `POST /api/v1/indicators/preview` — takes expression + symbol, returns timeseries of indicator values for preview chart.
- `POST /api/v1/indicators` — save custom indicator.

**Frontend Tasks**
- `app/indicators/page.tsx` — audit existing page. Add expression builder UI with primitive dropdown and operator buttons. Add preview chart. Add save button.

**Definition of Done**
- [ ] Custom indicator created from RSI + SMA combination
- [ ] Preview chart renders correctly
- [ ] Saved indicator available in backtesting strategy form

---

## 15. Institutional API & White-Label

### P3-API-01 — Public REST API ⬜
**Phase:** Premium  
**As Alex, I want** an authenticated REST API **so that** I can integrate Fin-Eye data into my own portfolio tools.

**Acceptance Criteria**
- API endpoints: `GET /public/v1/gas/{symbol}`, `GET /public/v1/macro/latest`, `GET /public/v1/sentiment/{symbol}`, `GET /public/v1/regime/{symbol}/history`.
- Auth: API key in `Authorization: Bearer {key}` header or `X-API-Key` header.
- Rate limiting: 300 req/hour per API key (enforced via Redis counter).
- Response includes: `data`, `meta.generated_at`, `meta.symbol`, `meta.source`.
- Invalid API key returns `401`. Rate limit exceeded returns `429` with `X-RateLimit-Reset` header.
- API key management: users generate keys from Settings. Keys can be revoked. Usage stats visible.

**Backend Tasks**
- `api/public/v1/router.py` — already exists. Audit endpoints. Add rate limiting middleware.
- `models/api_key.py` — `APIKey` model — already exists. Confirm: `key_hash`, `user_id`, `name`, `created_at`, `last_used_at`, `request_count`.
- `api/v1/endpoints/api_keys.py` — `POST /api/v1/api-keys` (create), `GET /api/v1/api-keys` (list), `DELETE /api/v1/api-keys/{id}` (revoke) — confirm all exist.
- Redis counter: key `rate:{api_key_hash}:{hour_bucket}`, expires at end of hour.

**Frontend Tasks**
- `app/settings/page.tsx` — add "API Keys" section: list existing keys (name, created, last used, request count), "Generate New Key" button (shows key once on creation), "Revoke" button.

**Definition of Done**
- [ ] API key generated from Settings
- [ ] `GET /public/v1/gas/AAPL` returns correct data with valid key
- [ ] `401` returned for invalid key
- [ ] `429` returned after 300 requests/hour
- [ ] Key revocation works immediately

---

### P3-WHITELABEL-01 — White-Label Dashboard ⬜
**Phase:** Premium  
**As Alex, I want** a white-label dashboard **so that** I can share analysis with clients under my firm's branding.

**Acceptance Criteria**
- White-label config: custom logo URL, primary accent colour (hex), firm name, custom domain/subdomain.
- When a user accesses via a white-label subdomain: Fin-Eye logo replaced by client logo, accent colour applied via CSS custom properties, firm name in page titles.
- "Powered by Fin-Eye" in footer — cannot be removed.
- Same functionality as standard dashboard.
- Configuration managed via admin panel.

**Backend Tasks**
- This is partially covered by B2B-TENANT-01/02. See Section 36 for full implementation tasks.
- `GET /api/v1/tenant/config` — returns branding config for the current subdomain.

**Frontend Tasks**
- On app init: check `window.location.hostname` against known tenant subdomains. Fetch tenant config. Apply CSS custom properties (`--accent-color`, `--logo-url`).

**Definition of Done**
- [ ] Tenant subdomain renders with custom logo and colour
- [ ] "Powered by Fin-Eye" visible in footer
- [ ] Standard functionality unchanged

---

## 16. Risk Management & Scenario Analysis

### P3-RISK-01 — Scenario & Stress Testing ⬜
**Phase:** Premium  
**As Alex, I want** scenario and stress-test tools **so that** I can explain portfolio risks to stakeholders.

**Acceptance Criteria**
- Scenarios available: 2008 GFC (2008-09 to 2009-03), 2020 COVID crash (2020-02 to 2020-03), 2022 bear market (2022-01 to 2022-10), custom (user-defined date range).
- For a selected portfolio, each scenario shows: estimated portfolio return, max drawdown, worst single day, best single day, VaR (95%), CVaR (expected shortfall).
- Results shown as a comparison table (portfolio vs SPY benchmark) and an equity curve chart.
- Custom shock: user defines a hypothetical % change to each asset class (e.g. "equities −30%, bonds +10%, gold +15%").

**Backend Tasks**
- `services/risk_service.py` — already exists. Audit: confirm `run_historical_scenario()` and `run_custom_shock()` functions.
- `api/v1/endpoints/risk.py` — `POST /api/v1/risk/scenario` — accepts `{portfolio_id, scenario_type, custom_params}`.
- Pre-compute scenario results for all default symbols nightly to speed up response.
- VaR calculation: 95% confidence, rolling 30-day window of daily returns.

**Frontend Tasks**
- `app/risk/page.tsx` — audit existing page. Add scenario selector with presets + custom option. Add comparison table. Add equity curve chart. Add CVaR/VaR display.

**Definition of Done**
- [ ] 2020 COVID scenario computed correctly for AAPL portfolio
- [ ] Custom shock correctly applied
- [ ] VaR/CVaR computed and displayed
- [ ] Comparison vs SPY benchmark visible

---

## 17. Authentication & Subscription Management

### CORE-AUTH-01 — User Authentication ⬜
**Phase:** MVP  
**As any user, I want** to sign up, log in, and log out securely **so that** my data is protected.

**Acceptance Criteria**
- Sign-up: email + password. Password must be ≥8 chars, contain 1 number and 1 special char. Hashed with bcrypt. Confirmation email sent.
- Login: email + password → access token (JWT, 30 min expiry) + refresh token (JWT, 7 days). Tokens returned as JSON (not cookies, for SPA compatibility).
- Logout: refresh token added to Redis blocklist (SEC-04).
- Password reset: "Forgot password" → email with reset link (expires 1 hour). Reset page accepts new password.
- Account lockout: 10 failed login attempts → 30-min lock (SEC-05).
- Email verification required before accessing protected features (SEC-07).
- Auth state managed in frontend via `AuthProvider.tsx` context.

**Backend Tasks**
- `api/v1/auth/` — `POST /register`, `POST /login`, `POST /logout`, `POST /refresh`, `POST /forgot-password`, `POST /reset-password`, `POST /verify-email`.
- `services/auth_service.py` — all auth operations.
- `core/security.py` — `create_access_token()`, `decode_token()`, `hash_password()`, `verify_password()`.
- Implement SEC-03 rate limiting on login/register/2FA endpoints.
- Implement SEC-04 refresh token rotation.
- Implement SEC-05 lockout.
- Implement SEC-07 `is_verified` enforcement.

**Frontend Tasks**
- `app/auth/` — login page, register page, forgot-password page, reset-password page, verify-email page.
- `components/AuthProvider.tsx` — already exists. Audit: confirm token refresh logic, logout clears tokens, user state populated correctly.
- Route guard: all non-public routes redirect to `/auth/login` if not authenticated.

**Definition of Done**
- [ ] Register → verification email sent → verify → login works
- [ ] Refresh token rotates on each use
- [ ] Logout blacklists the refresh token
- [ ] 10 failed logins triggers 30-min lockout
- [ ] Unverified user blocked from watchlist, backtesting, GAS fetch

---

### CORE-SUB-01 — Upgrade to Pro ⬜
**Phase:** MVP  
**As a Free user, I want** to upgrade to Pro via a simple payment flow **so that** I can unlock real-time features.

**Acceptance Criteria**
- Billing page shows: Free vs Pro feature comparison table, monthly/annual toggle, Pro price (€14.99/mo or €10.99/mo annual), "Most Popular" badge on Pro, "Upgrade" button.
- Annual plan shows: "Save €48/year" in concrete terms, not just a %.
- Clicking Upgrade → Stripe Checkout session created → redirect to Stripe → on success, user `is_pro = True`, access granted immediately.
- On Stripe payment failure: user stays Free, error shown, no partial state.
- 7-day free trial: no credit card required to start. Card required to continue after 7 days.
- Pro-only features show a 🔒 lock icon for Free users (UX-MONETISE-01).

**Backend Tasks**
- `POST /api/v1/billing/create-checkout-session` — creates Stripe Checkout session, returns `checkout_url`.
- `POST /api/v1/billing/webhook` — handles Stripe webhook events: `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_failed`.
- `models/user.py` — `is_pro: bool`, `stripe_customer_id: str`, `subscription_id: str`, `trial_ends_at: datetime`.
- Webhook must verify `Stripe-Signature` header before processing.

**Frontend Tasks**
- `app/billing/page.tsx` — audit existing page. Add feature comparison table. Add monthly/annual toggle with savings callout. Add "Upgrade" button wired to checkout session endpoint.
- Add 🔒 lock overlay component for Pro-gated features. Apply to: unlimited watchlist, backtesting history > 30 days, API access, advanced sentiment.

**Definition of Done**
- [ ] Free user completes Stripe checkout and becomes Pro
- [ ] `is_pro = True` set immediately after webhook received
- [ ] Pro-only features unlocked after upgrade
- [ ] Lock icons visible on Pro-gated features for Free users
- [ ] 7-day trial activates without credit card

---

### CORE-SUB-02 — Manage Subscription ⬜
**Phase:** MVP  
**As a Pro user, I want** to view and cancel my subscription **so that** I feel in control.

**Acceptance Criteria**
- Settings/Billing shows: plan name, billing period (monthly/annual), next renewal date, invoice history (last 6 invoices as downloadable PDFs).
- Cancel button: 2 clicks (confirm modal). After cancellation, access continues until end of billing period.
- Cancellation flow includes: 1-question survey ("Why are you leaving?") + offer to pause for 1 month free.
- Paused account: no billing for 1 month, Pro access maintained.
- After pause or cancellation, user can re-subscribe from the billing page.

**Backend Tasks**
- `GET /api/v1/billing/subscription` — returns current plan, status, renewal_date, trial_end.
- `POST /api/v1/billing/cancel` — cancels at end of period via Stripe API.
- `POST /api/v1/billing/pause` — pauses subscription for 1 billing cycle.
- `GET /api/v1/billing/invoices` — returns list of Stripe invoices with PDF URLs.
- Store cancellation reason in `subscription_cancellations` table.

**Frontend Tasks**
- `app/billing/page.tsx` — add subscription status card. Add cancel button with confirmation modal. Add pause offer in cancellation flow. Add invoice list with download links.

**Definition of Done**
- [ ] Subscription status shows correct plan and renewal date
- [ ] Cancel flow completes and subscription ends at period end
- [ ] Pause offer shown in cancellation flow
- [ ] Invoice PDFs downloadable

---

## 18. Settings Watchlist & Notifications

### CORE-WATCH-01 — Watchlist ✅ Done (2026-03-05)
**Phase:** MVP  
**As Marco, I want** to maintain a watchlist of favourite stocks **so that** I can quickly switch between instruments.

**Status:** Done. The watchlist exists and is wired to the backend.  
**Remaining gaps:**
- [ ] Mini GAS score badge next to each watchlist item (UX — todos.md §5)
- [ ] Drag-to-reorder watchlist items
- [ ] Auto-create default alert rules when a symbol is added (POLISH-03)

---

### CORE-NOTIF-01 — GAS & Regime Alerts ⬜
**Phase:** MVP  
**As Marco, I want** to receive alerts when GAS or regimes cross important thresholds **so that** I can react without staring at the screen all day.

**Acceptance Criteria**
- User can configure alert rules: `GAS > X`, `GAS < X`, `Regime changes to [Risk-On/Risk-Off]`.
- Default rules auto-created when a symbol is added to watchlist: GAS < 35 and GAS > 65.
- Delivery channel: email (initial). Push notifications as Phase 3.
- Email alert includes: symbol, current GAS, previous GAS, trigger condition, timestamp, dashboard link.
- Alert de-duplication: max 1 alert per symbol per 4-hour window (stored in Redis).
- Alert evaluation runs every 5 minutes during market hours via APScheduler.
- Users can view, edit, and delete their alert rules from `/alerts`.

**Backend Tasks**
- `models/alert.py` — `Alert` model: `id`, `user_id`, `symbol`, `condition_type`, `threshold`, `is_active`, `last_triggered_at`, `delivery_channel`.
- `services/alert_service.py` — `evaluate_all_email_alerts()` — already exists. Audit: confirm de-duplication via Redis key `alert:dedup:{alert_id}:{4h_bucket}`.
- Auto-create rules: in `watchlist_service.add_symbol()`, after adding to watchlist, create two `Alert` rows.
- `api/v1/endpoints/alerts.py` — `GET /api/v1/alerts`, `POST /api/v1/alerts`, `PUT /api/v1/alerts/{id}`, `DELETE /api/v1/alerts/{id}`.

**Frontend Tasks**
- `app/alerts/page.tsx` — audit existing page. Ensure it shows all alert rules, allows editing thresholds, allows deleting rules.
- Notification Preferences section in `app/settings/page.tsx` (UX-SETTINGS-01): alert thresholds, email frequency, default ticker, preferred timezone.

**Definition of Done**
- [ ] Alert rule created manually and via watchlist auto-create
- [ ] Email sent when GAS crosses threshold
- [ ] De-duplication prevents duplicate emails within 4 hours
- [ ] Alert rules visible and editable in `/alerts`

---

## 19. Content Management & Community

### CORE-CMS-01 & CORE-CMS-02 — Blog Admin & CMS ⬜
**Phase:** MVP  
**As a content admin, I want** to create, edit, and publish blog posts via an admin interface **so that** I can keep content fresh without code changes.

**Acceptance Criteria**
- Admin panel accessible only to users with `is_admin = True`.
- Post list table: title, status (Draft/Published), category, publish date, edit/delete actions.
- Markdown editor with live preview. Fields: title, slug (auto-generated from title, editable), summary, content (markdown), category, read_time_minutes, cover image URL.
- Save as draft (immediately). Publish (sets `is_published = True`, `published_at = now()`). Unpublish reverts to draft.
- Slug must be unique. If duplicate slug submitted, auto-append `-2`, `-3` etc.
- All posts auto-include the standard disclaimer in the rendered template (not the markdown content).

**Backend Tasks**
- `models/blog.py` — `BlogPost` model — confirm all fields. Add `is_published`, `published_at`, `cover_image_url`.
- `api/v1/endpoints/cms.py` — admin CRUD: `GET /api/v1/cms/posts` (all, including drafts for admin), `POST /api/v1/cms/posts`, `PUT /api/v1/cms/posts/{id}`, `DELETE /api/v1/cms/posts/{id}`. Apply `require_admin` dependency.
- Public read: `GET /api/v1/cms/posts` (published only), `GET /api/v1/cms/posts/{slug}`.

**Frontend Tasks**
- `app/admin/` — admin panel directory exists. Add `app/admin/cms/page.tsx` — post list. Add `app/admin/cms/[id]/edit/page.tsx` — markdown editor using a library like `react-markdown` + textarea.
- Protect all `/admin/*` routes: redirect to `/` if `!user.is_admin`.

**Definition of Done**
- [ ] Admin creates and publishes a post
- [ ] Published post appears at `/learn`
- [ ] Draft not visible to non-admin users
- [ ] Slug unique validation works
- [ ] Disclaimer auto-injected in rendered post

---

### CORE-COMM-01 — Community Integration ⬜
**Phase:** Growth  
**As Emma, I want** a community space **so that** I can discuss ideas with others.

**Acceptance Criteria**
- `/community` page links clearly to the primary community platform (Discord or Reddit). Link is prominent and not buried.
- Access gated by login (non-logged-in users see a "Log in to access the community" prompt).
- If a Discord server exists: deep links to relevant channels (#macro-101, #strategy-discussion, #fin-eye-help).
- Community page also shows: recent blog posts (last 3), a "Bull vs Bear" weekly poll (UX), and links to the strategy leaderboard.

**Frontend Tasks**
- `app/community/page.tsx` — audit existing page. Add Discord/Reddit link prominently. Add login gate. Add channel links. Add weekly poll component (UX).

**Definition of Done**
- [ ] Community link routes to correct platform
- [ ] Non-logged-in user sees login prompt
- [ ] Channel deep links work

---

## 20. Legal Compliance & Privacy

### CORE-LEGAL-01 — Consent Gate & Legal Pages ✅ Done (2026-03-05)
Consent gate implemented. Legal pages exist. Consent stored in DB with version + timestamp.

**Remaining gap:**
- [ ] Cookie consent actually blocks analytics (PostHog/Mixpanel) until consent given. Verify `ConsentGate.tsx` fires analytics initialisation only after user accepts.

---

### CORE-GDPR-01 — GDPR Data Export & Deletion ⬜
**Phase:** MVP  
**As an EU user, I want** to export or delete my data **so that** my GDPR rights are respected.

**Acceptance Criteria**
- Settings page has "Request Data Export" button: generates a ZIP of user's data (profile, watchlist, portfolios, alerts, backtest history, blog comments). Delivered by email within 48 hours.
- "Delete My Account" button: confirmation modal with "I understand this is permanent" checkbox. On confirm: user marked `is_deleted = True`, PII anonymised (email → `deleted_{id}@fin-eye.local`, name cleared), all user-linked data deleted within 30 days.
- Confirmation email sent on both export request and deletion request.
- Deleted user cannot log in. Their anonymised records remain for audit purposes.

**Backend Tasks**
- `api/v1/endpoints/gdpr.py` — `POST /api/v1/gdpr/export-request`, `POST /api/v1/gdpr/delete-request` — already exist. Audit implementation completeness.
- Add async job: `job_process_gdpr_requests()` — runs nightly, processes pending export/deletion requests.
- `models/user.py` — confirm `is_deleted: bool` field. Add `deletion_requested_at: datetime`.

**Frontend Tasks**
- `app/settings/page.tsx` — add Data & Privacy section: "Export My Data" button, "Delete My Account" button with confirmation modal.
- Show "Deletion scheduled — your data will be removed within 30 days" message after deletion requested.

**Definition of Done**
- [ ] Export request triggers confirmation email
- [ ] Deletion request anonymises PII within 30 days
- [ ] Deleted user cannot log in
- [ ] Settings UI has both buttons with confirmation flows

---

## 21. Monitoring Reliability & Ops

### CORE-OPS-01 — Observability & Alerting ⬜
**Phase:** MVP  
**As the Fin-Eye operator, I want** observability over key services **so that** I can detect outages and model failures early.

**Acceptance Criteria**
- Health endpoint `GET /api/v1/health` returns: `status`, `database`, `redis`, `scheduler_jobs` (count and last run times).
- Metrics endpoint `GET /api/v1/ops/metrics` returns: request counts, error rates, average latency, pipeline run history, GAS precompute success rate.
- Ops dashboard at `/admin/ops`: shows all pipeline run history, scheduler job statuses, error rates, current GAS cache hit rate.
- Sentry DSN configured: frontend JS errors and backend exceptions captured automatically.
- Slack webhook: `SLACK_ERROR_WEBHOOK_URL` — send alert when: any pipeline fails, error rate > 1%, GAS precompute fails for > 3 symbols.

**Backend Tasks**
- `api/v1/health.py` — `GET /api/v1/health` — confirm it checks DB connection, Redis ping, scheduler job count.
- `api/v1/endpoints/ops.py` — `GET /api/v1/ops/metrics`, `GET /api/v1/ops/jobs`, `GET /api/v1/ops/alerts` — confirm all implemented.
- Add Sentry initialisation to `main.py`: `sentry_sdk.init(dsn=settings.sentry_dsn)` (only if `SENTRY_DSN` configured).
- Add Slack alert function: `post_slack_error(message, context)` called from scheduler job error handlers.

**Frontend Tasks**
- `app/admin/ops/page.tsx` — audit existing page. Ensure all pipeline run history visible. Add error rate sparkline. Add scheduler job status table with last run time and status.
- Add Sentry browser SDK to `app/layout.tsx` (after consent given).

**Definition of Done**
- [ ] Health endpoint returns correct DB/Redis status
- [ ] Ops dashboard shows pipeline history
- [ ] Sentry captures a test error
- [ ] Slack alert fires on simulated pipeline failure

---

## 22. Revenue Showcase & Marketplace

### CORE-SHOP-01 & CORE-SHOP-02 — Digital Product Showcase ⬜
**Phase:** MVP  
**As a Pro user, I want** a curated digital products marketplace **so that** I can discover tools that complement Fin-Eye.

**Acceptance Criteria**
- `/showcase` page: grid of product cards. Each card: title, short description (≤ 80 chars), category badge (Portfolio Tools, Planning Tools, Tax Tools, etc.), price, star rating + review count, "Preview" button, "Buy Now" button.
- Clicking "Buy Now": opens LemonSqueezy checkout in new tab with `utm_source=terminal&utm_medium=showcase&utm_campaign={product_id}` appended.
- Click stats tracked: product views, detail modal opens, outbound clicks — stored in `product_click_events` table.
- Bundle section at top of page: at least 1 bundle with "Save X%" badge and expandable "What's included".
- "Coming Soon" section at bottom: roadmap products with "Notify me" buttons.
- Product detail modal: longer description, features bullet list, preview (embedded sheet/PDF), "Gift this" option.

**Backend Tasks**
- `models/showcase.py` — `ShowcaseProduct` model: `id`, `title`, `description`, `long_description`, `price`, `category`, `lemon_squeezy_variant_id`, `preview_url`, `status` (live|coming_soon), `rating`, `review_count`, `is_bundle`, `bundle_items` (JSON).
- `GET /api/v1/showcase/products` — public endpoint, returns published products.
- `POST /api/v1/showcase/products/{id}/click` — records click event.
- `POST /api/v1/showcase/products/{id}/notify-me` — stores `(user_id, product_id)` in `product_notifications` table.
- Seed at minimum: 3 live products + 1 bundle + 3 coming-soon products.

**Frontend Tasks**
- `app/showcase/page.tsx` — audit existing page. Add bundle section at top, product grid, coming-soon section at bottom.
- Product card component: all fields from above. Preview modal. "Gift this" toggle on detail view.

**Definition of Done**
- [ ] Product grid renders with at least 3 products
- [ ] "Buy Now" redirects to LemonSqueezy with correct UTM params
- [ ] Click events stored in DB
- [ ] Bundle card shows "Save X%" badge
- [ ] "Notify me" for coming-soon stores preference

---

## 23. Mobile Experience

### P3-MOBILE-01 — Responsive Mobile Dashboard ⬜
**Phase:** Premium  
**As Marco, I want** a mobile-friendly dashboard **so that** I can check GAS and alerts on the go.

**Acceptance Criteria**
- Dashboard functional and readable at 375px (iPhone SE) without horizontal scroll.
- Navigation: hamburger icon → full-height drawer with all nav items grouped (UX-UI-04).
- GAS widget, regime widget, and conflict detector all visible on first mobile viewport without scrolling.
- Timeframe grid: scrollable horizontally on mobile.
- Touch targets: all buttons ≥ 44×44px.
- Charts scale correctly on mobile (no overflow, readable axes).

**Backend Tasks**
- No backend changes needed.

**Frontend Tasks**
- `components/Nav.tsx` — add hamburger menu for `<md` breakpoint. Drawer slides in from left.
- `app/page.tsx` — adjust grid from `lg:grid-cols-2` to single column on mobile. Ensure GAS + Regime visible above fold.
- `components/TimeframeGrid.tsx` — add `overflow-x-auto` wrapper on mobile.
- Test all charts (Recharts) for mobile overflow. Add `ResponsiveContainer` where missing.
- Run WCAG AA contrast audit for both dark and light modes on mobile.

**Definition of Done**
- [ ] Dashboard renders without horizontal scroll at 375px
- [ ] Hamburger nav opens correctly
- [ ] All touch targets ≥ 44px
- [ ] Charts don't overflow on mobile

---

## 24. Advanced Macro Intelligence

### P2-MACRO-ADV-01 — Macro Stress Index & Advanced Indicators ⬜
**Phase:** Growth  
**As Marco, I want** a deeper macro view with yield curves, recession probability, and a Macro Stress Index **so that** I can judge when regimes are changing.

**Acceptance Criteria**
- Full yield curve chart: 4 points (2Y/5Y/10Y/30Y) as a line chart with the current curve and a 1-year-ago curve for comparison.
- Recession probability gauge (0–100%): computed from yield spread, unemployment trend, industrial production.
- Macro Stress Index (0–100): composite of VIX, yield curve inversion, CPI, unemployment, Fed rate. Higher = more stressed.
- Advanced Macro tab or expandable "Advanced" section on the Macro page.
- Each chart labelled with plain-language explanation of what the indicator signals.

**Backend Tasks**
- `services/macro_scoring.py` — `compute_macro_stress_index()` — already implemented. Confirm it returns `MacroStressIndexDto(index, label, components[])`.
- `services/macro_scoring.py` — `compute_recession_risk()` — already implemented. Confirm it returns `RecessionDto(probability_pct, label, drivers[])`.
- `GET /api/v1/macro/stress-index` — expose the stress index endpoint if not already.
- `GET /api/v1/macro/recession-risk` — expose recession probability endpoint.
- Historical yield curve: store daily snapshots of the 4-point curve in a `yield_curve_snapshots` table. Query 1-year-ago point for comparison.

**Frontend Tasks**
- `app/macro/page.tsx` — add "Advanced" tab or expandable section. Add yield curve comparison chart (current vs 1Y ago). Add Macro Stress Index gauge (0–100 arc chart). Add Recession Probability meter. Add stress component breakdown table.

**Definition of Done**
- [ ] Yield curve comparison chart renders with real FRED data
- [ ] Stress Index shows non-50 value after macro seeding
- [ ] Recession probability displayed with component drivers listed
- [ ] "What this means" text visible for each advanced indicator

---

## 25. Institutional Reporting & Bulk Analysis

### P3-BULK-01 — Bulk Ticker Analysis ⬜
**Phase:** Premium  
**As Alex, I want** to run bulk analysis for 50+ stocks at once **so that** I can assess risk across a full portfolio efficiently.

**Acceptance Criteria**
- Bulk analysis endpoint accepts a list of up to 100 ticker symbols.
- Returns for each: GAS score, regime, component scores, active conflicts, weather label.
- Response time < 5 seconds for 50 symbols (uses pre-computed GAS snapshots from Redis/DB).
- Results exportable as CSV and Excel.
- UI: textarea input for ticker list (comma or newline separated). Results table with sorting. Export buttons.

**Backend Tasks**
- `POST /api/v1/admin/gas/bulk` — new endpoint. Accept `{"symbols": ["AAPL", "MSFT", ...]}`. Fetch all GAS snapshots in batch. Return array.
- `GET /api/v1/admin/gas/snapshots` (existing) — ensure it supports `symbols` query param for batch filtering.
- CSV export: return `Content-Type: text/csv` with proper headers. Excel: use `openpyxl` to generate `.xlsx`.

**Frontend Tasks**
- New `app/explore/page.tsx` (directory exists). Add bulk input textarea. Add results table. Add CSV/Excel export buttons.

**Definition of Done**
- [ ] 50-symbol bulk request returns in < 5 seconds
- [ ] CSV export produces correct file
- [ ] Excel export produces correct file
- [ ] Results sortable by GAS, regime, weather label

---

### P3-REPORT-01 — Client-Ready PDF Reports ⬜
**Phase:** Premium  
**As Alex, I want** client-ready PDF/Excel reports **so that** I can share insights with non-technical stakeholders.

**Acceptance Criteria**
- Report includes: portfolio-level GAS, sector breakdown, top 5 holdings by GAS, stress test summary, macro environment summary, Fin-Eye logo, generated timestamp, standard disclaimer.
- PDF generated server-side (consistent formatting regardless of client browser).
- Excel export: separate tabs for holdings, macro indicators, stress test results.
- Report generation queued as a background job for large reports. User notified by email when ready.

**Backend Tasks**
- Install `weasyprint` or `reportlab` for server-side PDF generation.
- `POST /api/v1/portfolios/{id}/report` — queues report generation job. Returns `{"job_id": "..."}`.
- `GET /api/v1/portfolios/{id}/report/{job_id}` — returns report status + download URL when ready.
- Report template: Jinja2 HTML template rendered by weasyprint. Include Fin-Eye branding and disclaimer.
- Excel: `openpyxl` workbook with 3 sheets.

**Frontend Tasks**
- Add "Generate Report" button on portfolio page. Show "Generating..." spinner. When ready, show download button.
- Toast notification when report is ready (if user navigated away).

**Definition of Done**
- [ ] PDF report generates with correct data
- [ ] PDF includes logo, timestamp, disclaimer
- [ ] Excel export has correct sheet structure
- [ ] Email notification sent when async report is complete

---

## 26. Professional Content & Education

### P2-CONTENT-ADV-01 — Case Studies ⬜
**Phase:** Growth  
**As Emma, I want** case studies showing how GAS and macro indicators looked during historical crises **so that** I can see the framework in action on real history.

**Acceptance Criteria**
- At least 2 detailed case studies published: "2008 Financial Crisis" and "2020 COVID Crash".
- Each case study includes: what GAS would have shown during the event (reconstructed from historical data), how each layer behaved, key dates and price levels, lessons learned.
- Clearly marked as "Historical Analysis — Hindsight Only — Not Predictive."
- Case studies link to the relevant macro indicators and sentiment charts.

**Backend Tasks**
- No new backend needed. Case studies published via CMS as blog posts in the "Case Studies" category.

**Frontend Tasks**
- Ensure `/learn` category filter includes "Case Studies".
- Case study template: timeline component showing key events with dates and GAS score at each point.

**Definition of Done**
- [ ] 2008 and 2020 case studies published and accessible
- [ ] Hindsight disclaimer prominent
- [ ] Timeline component renders key events

---

## 27. Security Backups & Disaster Recovery

### CORE-SEC-01 — Two-Factor Authentication ⬜
**Phase:** MVP  
**As a security-conscious user, I want** optional 2FA **so that** I can reduce the risk of unauthorised access.

**Acceptance Criteria**
- Settings page: "Enable 2FA" button. Shows QR code for TOTP app (Google Authenticator, Authy). User must enter first TOTP code to confirm setup.
- Login flow: after password check, if 2FA enabled, prompt for 6-digit TOTP code. Max 5 attempts before lockout.
- Backup codes: 10 single-use backup codes generated on setup. Displayed once. User can regenerate from Settings.
- Disabling 2FA requires current password + 2FA code confirmation.

**Backend Tasks**
- `services/totp_service.py` — already exists. Audit: confirm `generate_secret()`, `get_qr_code()`, `verify_totp()`, `generate_backup_codes()`.
- `PUT /api/v1/auth/2fa/enable`, `PUT /api/v1/auth/2fa/disable`, `POST /api/v1/auth/2fa/verify`.
- `models/user.py` — `totp_secret_encrypted`, `totp_enabled`, `totp_backup_codes` (encrypted JSON array).

**Frontend Tasks**
- `app/settings/page.tsx` — 2FA section: "Enable 2FA" button → QR code modal → verify code → show backup codes.
- `app/auth/login/page.tsx` — after password check, if `requires_2fa` in response, show 2FA code input.

**Definition of Done**
- [ ] 2FA setup flow works end-to-end
- [ ] TOTP codes verified correctly
- [ ] Backup codes work as one-time codes
- [ ] Login prompts for 2FA when enabled

---

### CORE-SEC-02 — Automated Backups ⬜
**Phase:** MVP  
**As the operator, I want** encrypted automated backups **so that** we can recover from data loss.

**Acceptance Criteria**
- Daily PostgreSQL backup at 02:00 UTC. Backup stored encrypted (AES-256) in a separate location (S3/R2).
- Backup retention: 30 daily, 12 weekly, 3 monthly.
- Restore procedure documented and tested (dry run) at least quarterly.
- Backup success/failure logged. Alert sent on failure.

**Backend Tasks**
- `scripts/backup/backup_db.py` — already referenced in scheduler. Audit: confirm it produces a compressed SQL dump, encrypts it, and uploads to S3/R2.
- `job_backup_db()` in `scheduler.py` — fires at 02:00 UTC daily. Already configured.
- Add S3/R2 lifecycle rule for retention policy (30/12/3 rotation).
- Document restore procedure in `docs/backup-runbook.md` (file already exists — audit and update).

**Definition of Done**
- [ ] Daily backup job runs and produces an encrypted file in S3/R2
- [ ] Restore procedure documented and tested
- [ ] Alert fires on backup failure

---

## 28. Product Analytics & Experimentation

### CORE-ANALYTICS-01 — Activation & Funnel Tracking ⬜
**Phase:** MVP  
**As the product owner, I want** instrumented key product events **so that** I can measure activation, engagement, and conversion.

**Acceptance Criteria**
- Events tracked (minimum): `signup_completed`, `email_verified`, `first_ticker_searched`, `gas_explain_opened`, `first_backtest_run`, `macro_page_visited`, `watchlist_item_added`, `pro_upgrade_started`, `pro_upgrade_completed`, `subscription_cancelled`.
- Analytics fires only AFTER consent given (CORE-LEGAL-01).
- Events visible in PostHog dashboard with properties: `user_id`, `symbol` (where applicable), `timestamp`, `plan` (free/pro).
- Admin analytics page (`/admin/analytics`) shows: DAU/WAU/MAU, free vs Pro ratio, top tickers searched, feature adoption by page, upgrade funnel conversion %.

**Backend Tasks**
- `services/analytics_service.py` — `track_event(user_id, event_name, properties)` — already exists. Audit: confirm it sends to PostHog via HTTP API (not SDK, to work server-side).
- Call `track_event` from: auth service (signup, verification), technical endpoint (first inference per user), backtesting endpoint (first backtest), billing endpoint (upgrade started/completed).

**Frontend Tasks**
- `app/layout.tsx` — initialise PostHog SDK after consent. Track page views automatically.
- Call `posthog.capture()` from: GAS explain panel open, macro page load, watchlist add, first ticker search.
- `app/admin/analytics/page.tsx` — audit existing page. Wire to `GET /api/v1/analytics/summary`.

**Definition of Done**
- [ ] `signup_completed` event appears in PostHog after test registration
- [ ] Events not fired before consent
- [ ] Admin analytics page shows DAU/WAU/MAU from real data
- [ ] Upgrade funnel visible in PostHog

---

### CORE-EXPERIMENT-01 — A/B Testing Framework ⬜
**Phase:** Growth  
**As the product team, I want** simple A/B tests on onboarding and messaging **so that** we can improve activation iteratively.

**Acceptance Criteria**
- Users assigned to variant on first load (assignment stored in DB + cookie, consistent across sessions).
- Initial experiments: (A) Dashboard-first vs Welcome-page-first onboarding. (B) GAS "Explain" button copy: "What does this mean?" vs "Explain this score".
- Variant exposure tracked as an analytics event `experiment_exposure {experiment_id, variant}`.
- Results viewable in admin experiments dashboard.

**Backend Tasks**
- `models/experiment.py` — `Experiment`, `ExperimentVariant`, `UserExperimentAssignment` — confirm models exist.
- `GET /api/v1/experiments/{experiment_id}/assignment` — returns variant for current user.
- `api/v1/endpoints/experiments.py` — admin CRUD for experiments.

**Frontend Tasks**
- `app/admin/experiments/page.tsx` — audit existing page. Add experiment creation form. Show assignment distribution and conversion rates per variant.
- Hook `useExperiment(experimentId)` — fetches and caches assignment. Used in components to conditionally render variants.

**Definition of Done**
- [ ] User consistently assigned same variant across sessions
- [ ] Variant exposure tracked in PostHog
- [ ] Admin page shows at least one experiment with variant distribution

---

## 29. Email Onboarding & Newsletter

### CORE-EMAIL-01 — Onboarding Email Sequence ⬜
**Phase:** MVP  
**As a new user, I want** a short onboarding email sequence **so that** I learn how to get value from Fin-Eye in my first weeks.

**Acceptance Criteria**
- 4-email sequence triggered by events:
  - Day 0: Welcome email (sent immediately after email verification). Introduces GAS, links to dashboard.
  - Day 3: "Have you tried backtesting?" (triggers if no backtest run). Links to `/backtesting`.
  - Day 7: "Understand the macro backdrop" (triggers if macro page not visited). Links to `/macro`.
  - Day 14: "Your week in review" (triggers regardless). Summarises top macro changes.
- All emails: Fin-Eye branding, unsubscribe link, standard disclaimer, mobile-responsive.
- Users can opt out of non-transactional emails from Settings or email footer link.

**Backend Tasks**
- `services/onboarding_email_service.py` — `run_onboarding_day3_batch()`, `run_onboarding_day7_batch()` — already exist. Audit: confirm they query users who haven't completed the relevant action.
- `models/email_preference.py` — `EmailPreference` with `user_id`, `onboarding_enabled`, `digest_enabled`, `alerts_enabled` — confirm model exists.
- `job_onboarding_day3` and `job_onboarding_day7` in scheduler — already configured.
- Integrate with Resend: `RESEND_API_KEY` must be configured. HTML email templates using Jinja2.

**Frontend Tasks**
- `app/settings/page.tsx` — email preferences section: toggle for onboarding emails, digest, alert emails.
- `app/unsubscribe/page.tsx` — already exists. Audit: confirm it sets `onboarding_enabled = False` in DB.

**Definition of Done**
- [ ] Welcome email sent immediately after verification
- [ ] Day 3 email sent to users who haven't run a backtest
- [ ] Unsubscribe link works and updates DB
- [ ] Emails render correctly on mobile

---

### CORE-EMAIL-02 — Weekly Digest ⬜
**Phase:** Growth  
**As an engaged user, I want** an optional weekly digest **so that** I stay informed without logging in every day.

**Acceptance Criteria**
- Digest sent every Monday at 08:00 UTC to opted-in users.
- Content: top 3 macro changes this week (indicator + direction + magnitude), top 3 watchlist symbols by GAS change, 2 recent blog posts, one "Did you know?" product tip.
- Bi-weekly option: send every other Monday (week number % 2 == 0).
- Unsubscribe from Settings or email footer.

**Backend Tasks**
- `services/onboarding_email_service.py` — `run_weekly_digest_batch()` — already exists. Audit: confirm it compiles the digest content from real DB data (not hardcoded).
- `job_weekly_digest` in scheduler — already configured for Monday 08:00 UTC.

**Frontend Tasks**
- Settings digest opt-in toggle (part of CORE-EMAIL-01 settings UI).

**Definition of Done**
- [ ] Digest sent to opted-in users on Monday
- [ ] Content includes real macro changes and watchlist data
- [ ] Unsubscribe works

---

## 30. Security Hardening Pre-Launch Blockers

> All stories in this section must be completed before any public traffic is sent to the application.

### SEC-01 — Secret Rotation ⬜ 🔴 BLOCKER
**As the platform operator, I want** all production secrets rotated and removed from version control.

**Implementation Tasks**
- Rotate: `FINNHUB_API_KEY`, `FRED_API_KEY`, `JWT_SECRET` (generate new 64-char hex), TOTP Fernet key.
- Run: `git grep -r "d6ldde9r"` and similar to confirm no real keys in git history. If found, use `git-filter-repo` to purge.
- Confirm `backend/.env` in `.gitignore`: `git check-ignore -v backend/.env`.
- Create `backend/.env.example` with placeholder values: `FINNHUB_API_KEY=your_key_here`.
- All deployment environments use environment variable injection or a secret manager — never committed `.env`.

**Definition of Done**
- [ ] All 4 secrets rotated
- [ ] `git grep` returns no real key values
- [ ] `.env.example` exists with placeholders
- [ ] `.env` confirmed in `.gitignore`

---

### SEC-02 — Production Config Lockdown ⬜ 🔴 BLOCKER
**Implementation Tasks**
- Add deployment checklist file `docs/DEPLOY-CHECKLIST.md`: verify `REQUIRE_AUTH=True`, `DEBUG=False`, `ALLOWED_ORIGINS=["https://app.fin-eye.com"]` before every production deploy.
- Add CI check: GitHub Action step that reads `.env.production.example` and fails if `DEBUG=True` is present.

**Definition of Done**
- [ ] Deployment checklist exists
- [ ] CI check fails build if `DEBUG=True` in production config

---

### SEC-03 — Auth Rate Limiting ⬜ 🔴 BLOCKER
**Implementation Tasks**
- `pip install slowapi`.
- `main.py` — add `Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)` to app state.
- Apply `@limiter.limit("10/minute")` to `POST /auth/login`.
- Apply `@limiter.limit("5/minute")` to `POST /auth/register`.
- Apply `@limiter.limit("5/minute")` to `POST /auth/2fa/verify`.
- Write integration tests: assert 429 on 11th login request within 1 minute.

**Definition of Done**
- [ ] Login returns 429 after 10 requests/minute
- [ ] Register returns 429 after 5 requests/minute
- [ ] Tests pass

---

### SEC-04 — Refresh Token Rotation ⬜ 🔴 BLOCKER
**Implementation Tasks**
- Add `jti: str` (UUID) field to refresh token JWT payload.
- On `/auth/login`: generate JTI, store in Redis `refresh:{jti}` with 7-day TTL.
- On `/auth/refresh`: verify JTI in Redis (not expired, not blacklisted). Delete old JTI. Generate new JTI. Issue new tokens.
- On `/auth/logout`: add current JTI to Redis `blocklist:{jti}` with 7-day TTL. Delete from active store.
- Auth middleware: for each access token, check if its refresh JTI is in the blocklist.

**Definition of Done**
- [ ] Refresh token works on first use
- [ ] Old refresh token rejected after rotation
- [ ] Logged-out tokens rejected

---

### SEC-05 — Account Lockout ⬜ 🔴 BLOCKER
**Implementation Tasks**
- After each failed login, increment Redis key `lockout:{email}:{ip}` with 15-minute sliding window.
- If counter ≥ 10: set `locked:{email}` key with 30-minute TTL. Return `403` with "Account locked until {time}".
- On successful login: delete `lockout:{email}:{ip}` counter.
- Admin endpoint `POST /api/v1/admin/users/{id}/unlock` — deletes lock key.

**Definition of Done**
- [ ] 10th failed attempt returns 403 with lock message
- [ ] Lock expires after 30 minutes automatically
- [ ] Successful login resets counter
- [ ] Admin unlock works

---

### SEC-06 — Security Headers ⬜ 🔴 BLOCKER
**Implementation Tasks**
- Create `app/middleware/security_headers_middleware.py` with `SecurityHeadersMiddleware(BaseHTTPMiddleware)`.
- Set headers: `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`.
- Register in `main.py`: `app.add_middleware(SecurityHeadersMiddleware)`.
- Integration test: `assert response.headers["X-Frame-Options"] == "DENY"`.

**Definition of Done**
- [ ] All 5 headers present on every response
- [ ] No existing functionality broken by CSP
- [ ] Integration test passes

---

### SEC-07 — Email Verification Enforcement ⬜ 🔴 BLOCKER
**Implementation Tasks**
- `services/auth.py` — add `get_current_active_verified_user` dependency: checks `user.is_verified == True`.
- Replace `get_current_user` with `get_current_active_verified_user` in all sensitive endpoint dependencies: watchlist, backtesting, GAS precompute, portfolio, alerts, API keys, settings.
- Verification email: sent on registration. Contains link `GET /api/v1/auth/verify-email?token={token}` (token expires 24h).
- "Resend Verification Email" button on Settings page and on the "unverified" banner shown in dashboard.

**Definition of Done**
- [ ] Unverified user gets 403 on `/api/v1/watchlist`
- [ ] Verification link works and sets `is_verified = True`
- [ ] Resend button available in Settings
- [ ] Token expires after 24h

---

### SEC-08 — Model Artifacts to Cloud Storage ⬜ 🔴 BLOCKER
**Implementation Tasks**
- Configure Cloudflare R2 (or S3): `MODEL_STORE_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`.
- `services/ml_pipeline.py` — after `joblib.dump(model, local_path)`, call `r2_client.upload_file(local_path, bucket, key)`.
- `services/technical_service.py` — `load_model_instance()`: if local file not found, attempt R2 download before raising.
- Remove `model_store/` directory from repository. Add to `.gitignore`.
- On fresh deploy with empty local filesystem: models download from R2 on first inference call.

**Definition of Done**
- [ ] After training, model artifact uploaded to R2
- [ ] Inference works after deleting local `model_store/`
- [ ] `model_store/` not in repository

---

## 31. Multi-Asset ML Expansion

### ASSET-CRYPTO-01 — Crypto Symbol Support ⬜
**Phase:** Growth  
**As Marco, I want** to analyse BTC, ETH, and major crypto using the same GAS framework as equities.

**Acceptance Criteria**
- BTC-USD, ETH-USD, BNB-USD available in symbol selector under "Crypto" category.
- OHLCV ingested from Binance REST API on a 24/7 schedule (no market-hours restriction).
- Crypto Fear & Greed Index (from alternative.me API) shown as a supplementary indicator panel.
- GAS computed normally for crypto symbols.
- ML training available for crypto symbols via `POST /api/v1/technical/train/{symbol}`.

**Backend Tasks**
- `services/ohlcv_fetcher.py` — add `fetch_crypto_ohlcv(symbol)` using Binance REST API (`GET /api/v3/klines`). Add to `CRYPTO_SYMBOLS` list.
- Crypto symbols exempt from `day_of_week="mon-fri"` restriction in intraday scheduler job.
- `GET /api/v1/crypto/fear-greed` — new endpoint. Fetches from `https://api.alternative.me/fng/` (free, no key needed).
- Add BTC-USD, ETH-USD, BNB-USD to `OHLCV_SYMBOLS_DEFAULT` or to a separate `CRYPTO_SYMBOLS_DEFAULT` env var.

**Frontend Tasks**
- Symbol selector: add "Crypto" category grouping. Show BTC-USD, ETH-USD, BNB-USD.
- Dashboard — crypto symbols: add "Crypto Fear & Greed" supplementary panel below the main GAS when a crypto symbol is selected.

**Definition of Done**
- [ ] BTC-USD selectable and GAS computed
- [ ] Fear & Greed Index shown for BTC-USD
- [ ] 24/7 intraday ingestion (not restricted to market hours)

---

### ASSET-ML-02 — Model Drift Detection ⬜
**Phase:** Growth  
**As the ML engineer, I want** drift detection and Bayesian optimisation **so that** model quality is monitored systematically.

**Implementation Tasks**
- Add `optuna` to `requirements.txt`.
- Wrap model training in `optuna.create_study()`. Optimise XGBoost `max_depth`, `learning_rate`, `n_estimators`.
- Create `model_performance_log` table: `id`, `symbol`, `timeframe`, `model_name`, `prediction_date`, `predicted_direction`, `actual_direction`, `correct` (bool).
- Daily job `job_evaluate_model_predictions()`: for each prediction made yesterday, compare to actual price movement, write to `model_performance_log`.
- Compute rolling 30-day live Sharpe per model. If live Sharpe < 0.8 × training Sharpe: send Slack alert.
- `GET /admin/ml/drift-report` — returns per-model drift metrics.

**Definition of Done**
- [ ] Optuna optimisation runs during training
- [ ] `model_performance_log` populated daily
- [ ] Drift alert fires when Sharpe degrades >20%
- [ ] Drift report endpoint returns correct data

---

### ASSET-ML-03 — SHAP Feature Importance Panel ⬜
**Phase:** Growth  
**As Marco, I want** a "What's driving this signal?" panel **so that** I understand which features are most responsible for today's GAS.

**Implementation Tasks**
- Add `shap` to `requirements.txt`.
- After XGBoost inference, compute `shap.TreeExplainer(model).shap_values(X_latest)`. Extract top 5 features by absolute SHAP value.
- Map internal feature names to human-readable labels: `ret_1` → "1-day Return", `rsi_14` → "RSI (14)", etc.
- Include `top_features: [{name, value, shap_contribution, direction}]` in the GAS API response.
- If winner is not XGBoost (e.g. Logistic), return `top_features: null` with `explanation_available: false`.

**Frontend Tasks**
- Add collapsible "What's driving this?" panel below the Technical Consensus section on the dashboard. Show top 5 features as horizontal bar chart (green = positive contribution, red = negative).

**Definition of Done**
- [ ] SHAP values computed for AAPL XGBoost winner
- [ ] Top 5 features in API response
- [ ] Bar chart renders in dashboard
- [ ] "Explanation not available" shown gracefully for non-tree models

---

## 32. Advanced Indicators

### IND-TIER1-01 — 12 New Technical Indicators ⬜
**Phase:** Growth  
**Implementation Tasks**
- Add to `services/indicator_service.py` (pure pandas, no new pip deps):
  - `williams_r(high, low, close, period=14)` — Williams %R
  - `keltner_channels(high, low, close, ema_period=20, atr_period=10)` — returns upper, middle, lower
  - `parabolic_sar(high, low, step=0.02, max_step=0.2)` — SAR values
  - `adx(high, low, close, period=14)` — Average Directional Index
  - `cmf(high, low, close, volume, period=20)` — Chaikin Money Flow
  - `donchian_channels(high, low, period=20)` — upper, lower
  - `mfi(high, low, close, volume, period=14)` — Money Flow Index
  - `trix(close, period=15)` — TRIX oscillator
  - `ichimoku(high, low, close)` — returns tenkan, kijun, senkou_a, senkou_b, chikou
  - `dema(close, period=14)` — Double EMA
  - `tema(close, period=14)` — Triple EMA
  - `ultimate_oscillator(high, low, close, p1=7, p2=14, p3=28)` — Ultimate Oscillator
  - `elder_ray(high, low, close, period=13)` — Bull Power, Bear Power
- Unit test for each: verify output against a known reference dataset (use pandas-ta values as reference).
- Add Glossary entries for each indicator (via CMS).

**Definition of Done**
- [ ] All 12 indicators pass unit tests
- [ ] All accessible from custom indicator builder
- [ ] Glossary entries created for all 12

---

### IND-COMPOSITE-01 — Fin-Eye Proprietary Composite Indicators ⬜
**Phase:** Growth  
**Implementation Tasks**
- Create `services/composite_indicator_service.py`.
- Implement:
  - `gas_weighted_rsi(close, gas_score, period=14)` — RSI multiplied by `gas_score / 100` to scale signal strength.
  - `macro_sentiment_divergence(macro_score, sentiment_score, window=30)` — `|macro - sentiment|` with rolling z-score.
  - `regime_conditioned_bollinger(close, vix, bb_period=20, bb_std=2)` — BB width × `(vix / 20)` regime factor.
  - `smart_money_index(open_prices, close_prices)` — computes ratio of last 30-min session performance vs first 30-min.
- Label all four as "Fin-Eye Proprietary" in the UI with a tooltip explaining uniqueness.
- All four accessible from the custom indicator builder and backtesting.

**Definition of Done**
- [ ] All 4 composites compute without error on AAPL data
- [ ] "Fin-Eye Proprietary" label and tooltip visible in UI
- [ ] Available in backtesting strategy form

---

### IND-COMPOSITE-02 — Cross-Asset Correlation Heatmap ⬜
**Phase:** Growth  
**Implementation Tasks**
- Backend: `GET /api/v1/portfolios/correlation-matrix` — fetch 30-day daily OHLCV for all watchlist symbols, compute pairwise correlation matrix, return as 2D array with symbol labels.
- Diversification Score: `(1 - mean(|off_diagonal_correlations|)) * 100`.
- Frontend: `app/portfolios/page.tsx` — add correlation heatmap tab. Use a custom Recharts or D3 heatmap cell grid. Colour scale: −1 = deep red, 0 = white/grey, +1 = deep green. Hover shows exact correlation value + sparkline of both assets.
- Heatmap refreshes when watchlist changes.

**Definition of Done**
- [ ] Heatmap renders for a 5-symbol watchlist
- [ ] Diversification Score computed correctly
- [ ] Hover shows correct correlation value and sparkline
- [ ] Updates when symbols added/removed from watchlist

---

## 33. Digital Nomad & Lifestyle Finance Content

### NOMAD-01 — Lifestyle Finance Hub ⬜
**Phase:** Growth  
**Implementation Tasks**
- New route `app/lifestyle/page.tsx` — hub page with 4 pillar cards: Tax Residency, Legal Structures, International Banking, Estate & Pension Planning.
- Add "Lifestyle" to Nav under "Learn" dropdown.
- Reusable `LifestyleDisclaimer` component: "All content is for educational and informational purposes only. This is not legal or tax advice. Consult a qualified professional."
- Auto-inject disclaimer on all `/lifestyle/*` page templates.

### NOMAD-02 — Tax Residency Comparison Table ⬜
**Implementation Tasks**
- Seed JSON config: `data/lifestyle/tax-residency.json` with 10 countries × fields (personal_income_tax_rate, capital_gains_tax_rate, min_stay_days, setup_cost_eur, suitability_tags[]).
- `app/lifestyle/tax-residency/page.tsx` — interactive sortable/filterable table. Filter by: CGT rate (0% only toggle), min stay < 90 days toggle. Sort by any column.
- FATCA callout component: fixed banner at top for US citizens.
- "Key Concepts" accordion: tax residency vs permanent residency, OECD BEPS substance, double taxation treaties.

### NOMAD-03 — Legal Entity Type Comparison ⬜
**Implementation Tasks**
- Seed JSON config: `data/lifestyle/legal-structures.json` with 9 structures × fields.
- Interactive "Which structure fits me?" filter: inputs are founder_residency (EU/US/Other) and primary_income_type (Employment/Consulting/Investment/IP). Filters table rows.
- Turkish founder callout: separate highlighted section showing the UAE/Cyprus pathway with step-by-step sequence.

### NOMAD-04 — International Banking Guide ⬜
**Implementation Tasks**
- `app/lifestyle/investment-abroad/page.tsx` — accordion-style practical guide. Sections: Multi-currency banking, Investment accounts, Crypto custody, Health insurance, Pension vehicles.
- All external service links informational, no affiliate links without disclosure.

**Definition of Done (all NOMAD)**
- [ ] Hub page renders at `/lifestyle` with 4 pillar cards
- [ ] Tax residency table sortable and filterable
- [ ] Legal entity filter works correctly
- [ ] All pages include disclaimer
- [ ] "Lifestyle" in navigation under Learn

---

## 34. Digital Product Showroom v2

### SHOP-V2-01 — Product Preview ⬜
**Implementation Tasks**
- Add `preview_url: Optional[str]` to `ShowcaseProduct` model.
- Preview modal: renders Google Sheets embed (`<iframe src="{preview_url}">`) or PDF viewer. Watermark label "Sample / Preview Only" overlaid.
- "Preview" button disabled state when `preview_url` is null.

### SHOP-V2-02 — Gift Purchase ⬜
**Implementation Tasks**
- "Gift this" toggle on product detail. Reveals `recipient_email` input.
- On LemonSqueezy checkout creation, pass `checkout_data.email = recipient_email` when gift toggle active.
- Gifter receives confirmation email: "You gifted [Product Name] to [recipient_email]."
- On delivery failure, gifter notified within 24h via email.

### SHOP-V2-03 — Bundle Configuration ⬜
**Implementation Tasks**
- Add `is_bundle: bool`, `bundle_items: JSON` (list of product IDs), `bundle_savings_eur: Decimal` to product model.
- Bundle card: "Save €X" badge. "What's included" expandable section listing each product with individual description.
- Bundle at top of showcase grid (sorted by `is_bundle DESC` then `created_at ASC`).

### SHOP-V2-04 — Star Ratings ⬜
**Implementation Tasks**
- Add `rating: Decimal` (1.0–5.0), `review_count: int` to product model.
- Admin seeding endpoint: `PUT /api/v1/admin/showcase/{id}/rating` — sets rating and review_count manually.
- "No reviews yet" rendered when `review_count == 0`.

### SHOP-ROADMAP-01 — Coming Soon + Notify Me ⬜
**Implementation Tasks**
- `status` field on product model: `live | coming_soon`.
- "Coming Soon" section at bottom of Showcase page. "Notify me" button → stores `(user_id, product_id)` in `product_notifications`.
- Admin "Publish" action: sets `status = live`. Triggers batch job sending email to all users in `product_notifications` for that product.

**Definition of Done (all SHOP v2)**
- [ ] Preview modal works with a real Google Sheets embed
- [ ] Gift flow sends to recipient email
- [ ] Bundle shows "Save €X" badge
- [ ] Star ratings display on all cards
- [ ] Coming Soon section visible with Notify Me working

---

## 35. Investment Strategy Planner

### PLAN-01 — Risk Profile Quiz ⬜
**Implementation Tasks**
- 5 questions (stored as JSON config): investment horizon, reaction to −20% drop, income stability, emergency fund presence, primary goal.
- Scoring logic maps answers to profile: Aggressive (high risk tolerance, long horizon), Moderate, Conservative (low risk, short horizon), Income (dividend/yield focused).
- `PUT /api/v1/auth/risk-profile` — stores profile on user record.
- GAS alert thresholds auto-adjusted: Aggressive → alert at GAS < 25, Moderate → < 35, Conservative → < 45, Income → < 40.
- Quiz accessible from dashboard "Personalise" button and from Settings.
- Profile shows in Settings with "Retake Quiz" option.

### PLAN-02 — Asset Allocation Suggester ⬜
**Implementation Tasks**
- Allocation matrices stored in JSON config: `data/strategy-planner/allocations.json`. Keyed by `{profile}_{age_band}_{horizon_band}`.
- `POST /api/v1/plan/allocation` — accepts `{profile, age, horizon_years, currency}`. Returns allocation percentages per asset class.
- Frontend: pie chart (Recharts `PieChart`) + breakdown table. Disclaimer always visible below output.

### PLAN-03 — Rebalancing Calculator ⬜
**Implementation Tasks**
- `POST /api/v1/plan/rebalance` — accepts `{holdings: [{symbol, current_value}], target_allocation: [{symbol, target_pct}]}`. Returns `[{symbol, current_pct, target_pct, delta_pct, suggested_action, approximate_trade_value}]`.
- Frontend: holdings input table (symbol + current value). Target allocation input (% per symbol). Output table with Buy/Sell/Hold labels. CSV export button.
- Link from Portfolio page: "Rebalance this portfolio" pre-fills the form with current portfolio holdings.

### PLAN-04 — DCA Simulator ⬜
**Implementation Tasks**
- `POST /api/v1/plan/dca-simulation` — accepts `{symbol, amount_per_period, frequency, start_date, end_date}`. Fetches daily OHLCV, simulates DCA purchases, simulates lump-sum (same total invested on start_date). Returns equity curves for both + stats.
- Frontend: parameter form + side-by-side equity curve (Recharts `LineChart` with two series) + stats comparison table.

### PLAN-05 — Sequence of Returns Risk Visualiser ⬜
**Implementation Tasks**
- `POST /api/v1/plan/sequence-risk` — accepts `{starting_value, annual_withdrawal, expected_annual_return, duration_years}`. Runs 3 historical sequences: retiring in 2000, 2008, 2020. Returns 3 equity curves + survival rate.
- Portfolio survival rate: % of historical sequences where balance > 0 at end of duration.
- Frontend: 3 overlapping equity curves. Portfolio survival rate badge. Plain-English sequence risk explanation always visible.

### PLAN-06 — Bond Ladder Builder ⬜
**Implementation Tasks**
- `POST /api/v1/plan/bond-ladder` — accepts `{total_capital, rungs, start_year, currency}`. Fetches current Treasury yields from FRED (DGS1, DGS2, DGS5, DGS7, DGS10, DGS20, DGS30). Returns per-rung: year, capital, yield, estimated_annual_income.
- Frontend: table + horizontal bar chart (capital per rung). Link to Macro Dashboard yield curve. Disclaimer below output.

**Definition of Done (all PLAN)**
- [ ] Risk profile quiz assigns correct profile to test answers
- [ ] Asset allocation pie chart renders with real profile output
- [ ] Rebalancing calculator output correct for a 3-symbol portfolio
- [ ] DCA simulation side-by-side chart renders
- [ ] Sequence risk shows 3 scenario curves
- [ ] Bond ladder table + chart renders with real FRED data

---

## 36. B2B2C Landlord Architecture

### B2B-TENANT-01 — Tenant Registration & Client Invitation ⬜
**Phase:** Premium  
**Implementation Tasks**
- Alembic migration: create `tenants` table (`id UUID`, `slug VARCHAR UNIQUE`, `name`, `logo_url`, `brand_colour`, `subdomain`, `ai_narrator_config JSON`, `subscription_tier`, `created_at`).
- Alembic migration: create `tenant_memberships` table (`id`, `tenant_id`, `user_id`, `role` [advisor|client], `invited_at`, `joined_at`).
- Alembic migration: add nullable `tenant_id` FK to `Portfolio`, `Watchlist`, `Alert` tables.
- `POST /advisors/register` — create Tenant + Advisor user. Validate subdomain is URL-safe, unique, not a reserved path.
- `POST /advisors/invite` — generate invitation token, create `tenant_memberships` row with null `joined_at`. Send invitation email.
- `POST /advisors/accept-invitation?token={token}` — validates token, links user to tenant, sets `joined_at`.

### B2B-TENANT-02 — Tenant Branding ⬜
**Implementation Tasks**
- On app init: `GET /api/v1/tenant/config?subdomain={window.location.hostname}`. Returns tenant branding or null for B2C.
- Apply via CSS custom properties: `document.documentElement.style.setProperty('--accent', tenant.brand_colour)`.
- Logo: replace `<h1>Fin-Eye</h1>` in `layout.tsx` with `<img src={tenant.logo_url}>` when tenant config present.
- Footer: "Powered by Fin-Eye" always shown regardless of tenant config.

### B2B-ISOLATION-01 — Tenant Data Isolation ⬜
**Implementation Tasks**
- `TenantContext` dataclass: `user_id`, `tenant_id` (nullable), `role`.
- FastAPI dependency `get_tenant_context(current_user, request)` — reads subdomain from request, resolves tenant_id.
- All Portfolio, Watchlist, Alert, GAS queries: add `.where(table.tenant_id == ctx.tenant_id)`.
- Composite indexes: `CREATE INDEX ON portfolios (tenant_id, user_id)`, same for watchlist and alert.
- Integration test: advisor_A JWT cannot retrieve portfolio belonging to tenant_B.

### B2B-NARRATOR-01 — Configurable AI Narrator ⬜
**Implementation Tasks**
- `tenants.ai_narrator_config` JSON schema: `{tone, persona_label, brand_name, advisor_name, forbidden_topics[], max_words}`.
- Jinja2 template `prompts/narrator.j2`: renders system prompt from config. Hard-coded disclaimer block at end that Jinja2 cannot override.
- `services/explanation.py` — load narrator config from tenant context. Render prompt from template. Pass to Groq/OpenAI.
- Default config (B2C, tenant_id = null): existing Fin-Eye narration unchanged.

### B2B-GAS-WEIGHTS-01 — Custom GAS Weights Per Advisor ⬜
**Implementation Tasks**
- `tenants.gas_weight_profile` JSON: `{technical_weight, macro_weight, sentiment_weight}`.
- Pydantic validator: `assert abs(tech + macro + sent - 1.0) < 0.001`.
- `compute_gas_for_symbol()` — accept optional `weights` param. Use tenant weights if `tenant_id` present.
- Preset profiles: Macro-Focused (0.20/0.55/0.25), Momentum Trader (0.60/0.20/0.20), Balanced (0.40/0.30/0.30).
- Log weights used in `compliance_audit_logs` per computation.

### B2B-COMPLIANCE-01 — Compliance Audit Log ⬜
**Implementation Tasks**
- Alembic migration: `compliance_audit_logs` table — append-only (`INSERT` only, no `UPDATE`/`DELETE` via application). Columns: `id`, `client_user_id`, `advisor_tenant_id`, `event_type`, `symbol`, `score_value`, `gas_weights_used` JSON, `timestamp`, `ip_address`, `request_id`.
- `log_compliance_event(ctx, event_type, ...)` — async function. Wrapped in `try/except` that logs warning but never raises (must not break main request).
- Instrument: GAS snapshot display, AI narration generation, backtest result display, scenario output display.
- `GET /compliance/audit-log` — paginated, filterable by `client_id`, `from`, `to`. CSV export.

### B2B-BILLING-01 — Per-Seat Billing ⬜
**Implementation Tasks**
- Stripe products: Starter (≤10 seats, €X/mo), Growth (≤50 seats, €Y/mo), Enterprise (custom).
- Seat count tracked: count of active `tenant_memberships` rows per tenant.
- On invitation: check seat count vs tier limit. Block if at limit. Show upgrade prompt.
- Stripe metered billing: report seat count via `stripe.SubscriptionItem.create_usage_record()` monthly.
- Monthly billing summary email: seat count, tier, invoice amount.

**Definition of Done (all B2B)**
- [ ] Tenant registered, client invited, invitation accepted
- [ ] Branded subdomain shows tenant logo and colour
- [ ] Cross-tenant data isolation test passes
- [ ] AI narration uses tenant config
- [ ] Custom GAS weights applied and logged in compliance audit
- [ ] Compliance audit log populated for all instrumented events
- [ ] Seat limit enforced on invitation

---

## 37. Product Polish & Gap Closure

### POLISH-01 — Watchlist Overview Page ⬜
**Implementation Tasks**
- `GET /api/v1/gas/bulk` — new endpoint. Accept list of symbols. Batch-fetch GAS snapshots. Return array of compact snapshots.
- `app/watchlist-overview/page.tsx` — new page. Fetch all watchlist symbols via `GET /api/v1/watchlist`, then batch-fetch GAS via `/gas/bulk`.
- `WatchlistCard` component: ticker, company name (from Finnhub search), GAS score, colour ring, weather label, conflict flag (bool), regime label.
- Sort controls: GAS desc (default), GAS asc, ticker A–Z.
- "Last updated" timestamp at top of page.
- Add "Watchlist Overview" link to Nav.

### POLISH-02 — Symbol Search Autocomplete ⬜
**Implementation Tasks**
- `GET /api/v1/symbols/search?q={query}` — wraps Finnhub `/search` endpoint. Returns top 8 results: `{symbol, description, type, displaySymbol}`. Cache in Redis for 1 hour per query.
- `SymbolSearchInput` component: replace all free-form ticker inputs. Debounced fetch at min 2 chars, 300ms delay. Dropdown with 8 results. Keyboard navigation (arrow keys + enter). Falls back to free-form entry if Finnhub unavailable.
- Apply to: dashboard ticker input, watchlist add, portfolio holding add, backtesting symbol selector.

### POLISH-03 — Auto Default Alert Rules on Watchlist Add ⬜
**Implementation Tasks**
- `watchlist_service.add_symbol()` — after inserting watchlist row, call `alert_service.create_default_rules(user_id, symbol)` which creates: GAS < 35 alert and GAS > 65 alert.
- De-duplication Redis key: `alert:dedup:{alert_id}:{4h_bucket}` — prevents repeat emails within 4 hours.
- Alert email template: include symbol, GAS at trigger, previous GAS, trigger condition, "View Dashboard" CTA button.

### POLISH-04 — Export to CSV & PDF ⬜
**Implementation Tasks**
- Install `weasyprint` (PDF) and ensure `openpyxl` available (XLSX).
- `GET /api/v1/backtest/{id}/export?format=csv|pdf` — generates export of equity curve + stats.
- `GET /api/v1/portfolios/{id}/export?format=csv|pdf` — portfolio holdings + GAS + metrics.
- PDF template: Jinja2 HTML rendered by weasyprint. Includes Fin-Eye logo, symbol/portfolio name, generated timestamp, standard disclaimer.
- Frontend: "Export CSV" and "Export PDF" buttons on backtesting results and portfolio pages.

### POLISH-05 — Dark / Light Mode Toggle ⬜
**Implementation Tasks**
- `app/layout.tsx` — on mount, read `prefers-color-scheme` media query. Apply `dark` or `light` class to `<html>`.
- Toggle button in Nav: sun icon (light) / moon icon (dark). On click, toggle class and persist to `localStorage`.
- CSS custom properties: `--bg-primary`, `--text-primary`, `--border-color` defined for both modes. All Tailwind `bg-slate-*` and `text-slate-*` classes replaced with custom property equivalents where necessary.
- WCAG AA audit: check contrast ratio ≥ 4.5:1 for all text in both modes.
- Note: Given the app is currently fully dark-mode, adding a "light mode" is a design-level task. Minimum viable: the toggle persists user preference even if only one mode is fully designed initially.

### POLISH-06 — Updated Onboarding Tour ⬜
**Implementation Tasks**
- Review all existing tour steps (`GuidedTour.tsx`) against current UI. Update any stale selectors or copy.
- Add new steps: Watchlist Overview page, Macro FOMC countdown, Backtesting templates, Learn Hub categories, Showcase page.
- Move tour completion from `localStorage` to `users.has_completed_tour` DB column (CORE-AUTH migration needed).
- Add "Restart Tour" button to `app/settings/page.tsx`.

**Definition of Done (all POLISH)**
- [ ] Watchlist Overview shows GAS cards for all watchlist symbols
- [ ] Symbol autocomplete works in all 4 input locations
- [ ] Default alert rules created on watchlist symbol add
- [ ] CSV and PDF exports download correctly
- [ ] Mode toggle persists across page reloads
- [ ] Updated tour covers all current pages

---

## 38. UX & Retention

### UX-UI-01 — Skeleton Loaders ⬜
**Implementation Tasks**
- Replace all `animate-pulse` blank divs with component-accurate skeletons:
  - GAS widget skeleton: circle + two lines of text
  - Regime widget skeleton: two badge shapes + label
  - Timeframe grid skeleton: 5 equal-width rectangular tiles
  - Why Moving panel skeleton: 3 lines of text at varying widths
  - News article list skeleton: 3 card-shaped blocks
- Skeleton colours: `bg-slate-800` animated with `animate-pulse`.
- Show skeleton while `isLoading && !data` (not while `isValidating`).

### UX-UI-02 — Global Toast System ⬜
**Implementation Tasks**
- Install `sonner` or `react-hot-toast` (lightweight toast library).
- `app/layout.tsx` — add `<Toaster />` component at the root.
- Fire toasts from: save success (watchlist, alert, strategy), API errors (4xx/5xx from SWR), GAS alert fire events (server-sent or polling), copy-to-clipboard success.
- Toast types: success (green), error (red), info (blue), warning (amber). Auto-dismiss at 4 seconds.

### UX-UI-03 — Designed Empty States ⬜
**Implementation Tasks**
- Create reusable `EmptyState` component: accepts `icon`, `title`, `description`, `ctaLabel`, `ctaHref`.
- Apply to: News feed (no articles), Sentiment chart (no data), Timeframe grid (no models), Backtesting results (run first backtest), Portfolio holdings (add first holding), Watchlist (add first symbol), Strategy library (no saved strategies).
- Each empty state has a relevant icon (from Lucide), a descriptive message, and an action button.

### UX-GROWTH-01 — GAS History Sparkline ⬜
**Implementation Tasks**
- `GET /api/v1/admin/gas/history/{symbol}?days=7` — new endpoint. Returns last 7 days of daily GAS snapshots: `[{date, gas_score, weather_label}]`. Query `gas_snapshots` table ordered by `computed_at` DESC, limit 7.
- `GasSparkline` component: Recharts `LineChart` with no axes, no grid, just the line. Height 40px. Colour matches current GAS band (emerald/amber/rose). Tooltip shows date + score on hover.
- Add to `MarketWeatherWidget.tsx` below the main GAS score number.

### UX-GROWTH-02 — "What Changed Today" Widget ⬜
**Implementation Tasks**
- `GET /api/v1/gas/changes?symbols=[...]` — new endpoint. For each symbol, compare latest snapshot with snapshot from 24h ago. Returns: `{symbol, current_gas, previous_gas, delta, current_regime, previous_regime, regime_changed}`.
- `WhatChangedWidget` component: list of rows, each showing `{AAPL} GAS: 62 → 71 ↑ (+9)` or `{TSLA} Regime: Risk-Off → Risk-On`. Rows coloured: green for improvement, red for deterioration.
- Add to dashboard as an optional collapsible panel. Hidden by default, expandable via "What changed today?" button.

### UX-EDU-01 — Tooltip System for Score Widgets ⬜
**Implementation Tasks**
- Create `InfoTooltip` component: `[i]` icon button (Lucide `Info` 14px). On hover/click, shows a popover with title + description text + optional "Learn more" link.
- Apply to: GAS score label, Technical Score label, Macro Score label, Sentiment Score label, Regime label, Volatility label, each timeframe signal tile header.
- Tooltip content for each (stored in a config object in the component):
  - GAS: "Global Alignment Score (0–100). Combines technical momentum (40%), news sentiment (30%), and macro conditions (30%). Above 60 = broadly bullish environment."
  - Technical: "ML-based signal agreement across timeframes. Computed from trained XGBoost/Logistic models. High score = multiple timeframes agreeing on bullish direction."
  - Macro: "Economic environment score. Derived from FRED indicators: yield curve, VIX, CPI, unemployment, Fed rate. High = supportive macro backdrop."
  - etc.

### UX-MONETISE-01 — Pro Gate Lock Icons ⬜
**Implementation Tasks**
- `ProGate` component: wraps Pro-only UI. For Free users: renders a `🔒` icon overlay with tooltip "Available on Pro — Upgrade for €14.99/mo". Clicking anywhere on the gate navigates to `/billing`. For Pro users: renders children normally.
- Apply `ProGate` to: unlimited watchlist items beyond 10, backtesting history > 30 days, API key generation, Advanced Sentiment page, bulk analysis, PDF reports, B2B advisor registration.

### UX-TRUST-01 — Data Freshness Indicators ⬜
**Implementation Tasks**
- `FreshnessIndicator` component: accepts `updatedAt: string`. Computes age in minutes. Renders: coloured dot (green <30min, amber 30–60min, red >60min) + "Updated X min ago" text.
- Apply to: GAS widget, Macro indicators section, Sentiment score section, Technical signals section, News article list header.
- All API responses that return time-series data must include an `updated_at` or `computed_at` field. Audit all relevant endpoints.

### UX-TRUST-02 — Graceful Degradation Messages ⬜
**Implementation Tasks**
- When GAS is computed without the sentiment layer (sentiment data unavailable), include `"degraded_components": ["sentiment"]` in the GAS snapshot response.
- Frontend: if `degraded_components` is non-empty, show an inline amber banner: "Sentiment data is temporarily unavailable — GAS computed without the sentiment layer."
- Same pattern for macro data unavailability and technical model absence.
- Banner auto-dismisses when next snapshot refresh has no degraded components.

**Definition of Done (all UX)**
- [ ] Skeleton loaders visible on all loading states
- [ ] Toast fires on watchlist save success and API error
- [ ] All 8 sections have designed empty states
- [ ] GAS sparkline renders on dashboard after 7 days of data
- [ ] "What changed" panel shows correct deltas
- [ ] All 7 score widgets have `[i]` tooltips with correct descriptions
- [ ] Pro gate visible on at least 3 Pro-only features
- [ ] Freshness indicator on all 4 data sections
- [ ] Degradation banner shows when sentiment data missing

---

*End of MASTER-USER-STORIES.md v4.0 — Extended Implementation Edition*  
*This file supersedes v3.0. Source files (user-stories.md, user-stories-v2.md, prdv3.md, todos.md) are preserved as historical reference and must NOT be deleted.*  
*Next review: start of Sprint 1 after pre-launch blockers are complete.*
