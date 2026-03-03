# Fin-Eye – Application Blueprint

> **Version:** 2.0 (PRD-Audited) | **Date:** 2026-03-03  
> Cross-referenced against `user-stories.md` and `prdv3.md`.  
> Defines every **tab, page, panel, and dashboard** in the Fin-Eye platform.

---

## 1. Navigation Structure

Top-level tab bar (defined in `frontend/app/layout.tsx`):

```
[Dashboard]  [Macro]  [News & Sentiment]  [Backtest]  [Hedge]  [Learn]  [Showcase]
```

> **Note:** There is no separate "Explore" tab. MVP-EXPL-01/02 are **panels within the Dashboard**, not separate pages. Auth/Settings are deferred to CORE-AUTH-01.

---

## 2. Pages, Tabs & Panels

### 2.1 Dashboard (`/`)
**Stories:** `MVP-DASH-01`, `MVP-DASH-02`, `MVP-DASH-03`, `MVP-EXPL-01`, `MVP-EXPL-02`  
**Status:** ✅ DASH-01/02/03 DONE | 🔄 EXPL-01/02 IN PROGRESS  
**Purpose:** The primary screen of the platform. Single-page market intelligence hub for a selected ticker.

| Panel / Widget | Story | Description |
|---|---|---|
| **Ticker Input** | DASH-01 | Symbol selector input. Defaults to AAPL. Drives all panels on the page. |
| **Market Weather Widget** | DASH-01 | Global Alignment Score (0–100) + weather label: Strong Tailwind (80–100), Mild Support (60–79), Mixed Signals (40–59), Headwind (20–39), High Instability (0–19). Refreshes every 15 min. |
| **Regime Widget** | DASH-02 | Technical regime: `Risk-On` / `Risk-Off` / `Range-Bound` + confidence %. Volatility regime from VIX: Low (<15), Medium (15–25), High (>25). Highlights regime changes. |
| **Timeframe Grid** | DASH-03 | Five tiles: 1h, 4h, 1d, 1w, 1m. Each shows `Bullish/Neutral/Bearish` label + confidence score (0–100). "Insufficient data" state for sparse timeframes. |
| **Macro Score Summary** | MACRO-02 | Single-line macro score + label. Links to Macro tab. |
| **"Why Is This Moving?" Panel** | **EXPL-01** | Plain-English bullet-point explanation of current drivers: technical momentum contribution, news sentiment contribution, macro backdrop contribution. References actual values (e.g., "4 of 5 timeframes bullish"). Includes non-advisory disclaimer. |
| **Conflict Detector Block** | **EXPL-02** | Visible warning when layers disagree (e.g., technicals bullish vs macro bearish) OR timeframe agreement < 40%. Shows: conflicting layers, magnitude of disagreement. Shows "No major conflicts detected" when aligned. |

---

### 2.2 Macro View (`/macro`)
**Stories:** `MVP-MACRO-01`, `MVP-MACRO-02`, `P2-MACRO-ADV-01`  
**Status:** ✅ MACRO-01/02 DONE | ⏳ P2-MACRO-ADV-01 NOT STARTED  
**Purpose:** Wide-angle view of the macroeconomic environment.

| Panel / Widget | Story | Description |
|---|---|---|
| **Macro Score Card** | MACRO-02 | Composite 0–100 score + label (Supportive / Neutral / Stressed) |
| **Indicators Grid** | MACRO-01 | 5 cards: Fed Funds Rate, Unemployment Rate, CPI YoY, Yield Spread (10y–2y), VIX. Each with plain-English interpretation. |
| **Manual Refresh Button** | MACRO-01 | Triggers `POST /api/v1/macro/refresh` to pull fresh FRED data |
| **[P2] Full Yield Curve Chart** | MACRO-ADV-01 | 2y, 5y, 10y, 30y yield curve over time |
| **[P2] Recession Probability** | MACRO-ADV-01 | Historical and current recession probability |
| **[P2] Macro Stress Index** | MACRO-ADV-01 | Enhanced 0–100 index from advanced indicators |

---

### 2.3 News & Sentiment (`/news-sentiment`)
**Stories:** `MVP-SENT-01`, `MVP-SENT-02`, `P2-RET-01`, `P3-SENT-ADV-01`  
**Status:** ✅ SENT-01/02 DONE | ⏳ P2-RET-01 NOT STARTED | ⏳ P3-SENT-ADV-01 NOT STARTED  
**Purpose:** FinBERT-powered news & sentiment analysis for a selected ticker.

| Panel / Widget | Story | Description |
|---|---|---|
| **Ticker Input** | SENT-01 | Symbol selector for sentiment analysis |
| **30-Day Sentiment Chart** | SENT-01 | Line chart: daily average FinBERT sentiment (–1 to +1) over 30 days |
| **Aggregated Sentiment Cards** | SENT-01 | 3 cards: current 1d, 7d, 30d rolling average |
| **Article List** | SENT-01 | Latest 10–20 scored headlines: title, source, date, FinBERT label |
| **Source Breakdown Table** | SENT-02 | Per-outlet count of Bullish / Bearish / Neutral headlines (30-day) |
| **[P2] Reddit Sentiment Panel** | RET-01 | Mention volume + sentiment from r/stocks, r/wallstreetbets, etc. Retail Sentiment Score (0–100). Top 5 bullish/bearish comments. |
| **[P3] Advanced Sentiment** | SENT-ADV-01 | Twitter/X, earnings call transcripts, Google Trends combined view |

---

### 2.4 Backtesting Engine (`/backtest`)
**Stories:** `MVP-BACK-01`, `MVP-BACK-02`, `P2-STRAT-01`  
**Status:** ⏳ NOT STARTED  
**Purpose:** Historical strategy simulation with realistic statistics and overfitting warnings.

| Panel / Widget | Story | Description |
|---|---|---|
| **Strategy Configurator** | BACK-01 | Inputs: ticker, date range, strategy template (Momentum), parameters (SMA length, RSI threshold). Min 5 years of data. Slippage + commission applied (0.1% + spread). |
| **Equity Curve Chart** | BACK-01 | Portfolio value over time vs. Buy-and-Hold benchmark |
| **Performance Metrics Table** | BACK-01 | Total return %, Sharpe ratio, Sortino ratio, max drawdown, win rate, recovery factor |
| **Trade Log** | BACK-01 | Chronological list of all simulated trades with P&L |
| **Overfitting Warning Block** | BACK-02 | Non-dismissable disclaimer about backtest vs live gap. Extra warning if Sharpe > 1.2. Links to "Backtesting pitfalls" Learn article. |
| **[P2] Strategy Library** | STRAT-01 | Save/load/browse named strategies. Platform templates + user strategies. Key metrics per strategy. Optional public sharing/leaderboard (P2+). |

---

### 2.5 Hedging Simulator (`/hedge`)
**Stories:** `MVP-HEDGE-01`, `P2-HEDGE-ADV-01`  
**Status:** ⏳ NOT STARTED  
**Purpose:** Simulate hedging strategies and compute hedge ratios vs benchmarks.

| Panel / Widget | Story | Description |
|---|---|---|
| **Hedge Configurator** | HEDGE-01 | Inputs: ticker, hedge type (Protective Put, Short Inverse ETF). |
| **Beta & Correlation Display** | HEDGE-01 | Beta vs S&P 500, correlation with hedge instrument |
| **Payoff Diagram** | HEDGE-01 | Simple payoff diagram for selected scenario (e.g., stock falls –20%) |
| **Before/After Equity Curve** | HEDGE-01 | Unhedged vs hedged portfolio curve |
| **Hedge Cost Estimate** | HEDGE-01 | Approximate cost of hedge (option premium or ETF carry) |
| **[P2] Multi-Leg Strategies** | HEDGE-ADV-01 | Collar (stock + put + short call), Stock + Put + Short ETF. Multi-curve comparison. |

---

### 2.6 Learn / Blog (`/learn`)
**Stories:** `MVP-LEARN-01`, `P2-CONTENT-ADV-01`, `P3-EDU-01`, `CORE-CMS-01`  
**Status:** ⏳ NOT STARTED  
**Purpose:** Educational content hub.

| Panel / Widget | Story | Description |
|---|---|---|
| **Article List** | LEARN-01 | Grid of posts: title, summary, read-time, date, category. Min 6 posts at MVP launch. |
| **Categories** | LEARN-01 | Filter by: Macro 101, GAS Explained, Backtesting, Sentiment, Regime |
| **Article Detail Page** | LEARN-01 | Full article with standard disclaimer footer |
| **[P2] Case Studies** | CONTENT-ADV-01 | "2008 crisis", "2020 COVID crash" with embedded charts and GAS retrospective |
| **[P3] Courses / Webinars** | EDU-01 | Multi-part series with progress tracking, syllabus, scheduling |

---

### 2.7 Pro Tools Showcase / Marketplace (`/showcase`)
**Stories:** `CORE-SHOP-01`, `CORE-SHOP-02`  
**Status:** ⏳ NOT STARTED  
**Purpose:** Revenue module – curated external digital financial tools.

| Panel / Widget | Story | Description |
|---|---|---|
| **Product Grid** | SHOP-01 | Cards: title, short description, category badge, "View details" button. Admin-manageable. |
| **Product Detail Modal** | SHOP-02 | Longer description, key features list, "Buy now" button |
| **Tracked Redirect** | SHOP-02 | "Buy now" opens external storefront in new tab with `product_id`, `source=terminal` tracking params |

---

### 2.8 Settings (`/settings`) ← Deferred
**Stories:** `CORE-AUTH-01`, `CORE-SET-01`, `CORE-SUB-01`, `CORE-SUB-02`, `CORE-WATCH-01`, `CORE-NOTIF-01`, `CORE-GDPR-01`, `CORE-SEC-01`, `CORE-LEGAL-01`  
**Status:** 🔒 DEFERRED (implement after all functional features)

| Sub-page | Stories | Description |
|---|---|---|
| **/auth/login, /auth/signup** | AUTH-01 | Email + password auth. Password hashing. JWT. |
| **/settings/profile** | SET-01 | Name, avatar, password change |
| **/settings/subscription** | SUB-01/02 | Plan details, Stripe billing, cancel flow |
| **/settings/watchlist** | WATCH-01 | Add/remove tickers; persisted per user |
| **/settings/notifications** | NOTIF-01 | GAS threshold alerts, regime change alerts; email delivery |
| **/settings/privacy** | GDPR-01 | Data export request, account deletion request |
| **/settings/security** | SEC-01 | 2FA (TOTP) enable/disable |

---

### 2.9 Onboarding Tour (Overlay on Dashboard) ← Deferred
**Story:** `MVP-ONBOARD-01`  
**Status:** 🔒 DEFERRED (requires AUTH-01 for "first login" trigger)  
**Description:** 4–6 contextual tooltip steps after first login covering GAS, Market Weather, timeframe signals, "Why is this moving?", Learn/Blog links. Can be skipped and re-opened from Settings.

---

## 3. Shared Components (Global)

| Component | Purpose |
|---|---|
| `layout.tsx` | Global nav bar across all pages |
| `TickerSearch.tsx` | Reusable symbol input with autocomplete |
| `ScoreBadge.tsx` | Renders any 0–100 score with colour coding |
| `TimeframeSelector.tsx` | Reusable 1m/1h/4h/1d/1w pill selector |
| `Skeleton.tsx` | Animated loading placeholder |
| `DisclaimerBanner.tsx` | Non-advisory educational disclaimer (required on all analysis panels) |

---

## 4. URL Route Map

```
/                        → Dashboard (GAS + regime + timeframe grid + EXPL panels)
/macro                   → Macro View
/news-sentiment          → News & Sentiment
/backtest                → Backtesting Engine          [NOT_STARTED]
/hedge                   → Hedging Simulator           [NOT_STARTED]
/learn                   → Learn / Blog                [NOT_STARTED]
/learn/[slug]            → Individual article
/showcase                → Pro Tools Marketplace       [NOT_STARTED]
/auth/login              → Login                       [DEFERRED]
/auth/signup             → Signup                      [DEFERRED]
/settings/*              → Settings sub-pages          [DEFERRED]
```

---

## 5. Implementation Order (Dependency Graph)

```
MVP-DATA-01 ✅
  ├── MVP-MACRO-01 ✅ → MVP-MACRO-02 ✅
  ├── MVP-SENT-01 ✅  → MVP-SENT-02 ✅
  └── MVP-TECH-01 ✅  → MVP-TECH-02 ✅
                           │
                 ┌─────────┴────────┐
            MVP-DASH-01 ✅     MVP-DASH-02/03 ✅
                 │
       ┌─────────┴──────────┐
  MVP-EXPL-01 🔄       MVP-EXPL-02 🔄    ← CURRENT FOCUS
       │
  ┌────┴──────────────────────────┐
  MVP-BACK-01 ⏳     MVP-HEDGE-01 ⏳    MVP-LEARN-01 ⏳
       │
  MVP-BACK-02 ⏳     CORE-SHOP-01 ⏳   CORE-SHOP-02 ⏳

CORE-AUTH-01 🔒 (deferred — implement last, blocks settings/watchlist/notifications)
```

---

## 6. Personas

| Persona | Profile | Primary Use Cases |
|---|---|---|
| **Emma** | Finance student, learning macro & market analysis | Learn tab, GAS explanation, "Why moving?" panel, onboarding tour |
| **Marco** | Retail trader, wants timing & risk signals | Regime widget, conflict detector, backtesting, hedging |
| **Alex** | Institutional analyst | Bulk analysis (P3), API (P3), white-label (P3), advanced reports (P3) |
