# Fin-Eye UI/UX Redesign Spec
**Status:** Post-MVP  
**Priority:** High  
**Reference:** Yahoo Finance · Bloomberg Terminal · Koyfin · TradingView

---

## 0. What's Already Built (Audit)

This spec is grounded in the actual codebase. Before listing what to do, here is what **already exists**.

### Components (`/frontend/components/`)

| Component | What it does | UX spec coverage |
|-----------|-------------|-----------------|
| `Nav.tsx` | Full navbar with 19 nav items, user menu (avatar, pro badge, billing, logout, admin links), active state | ✅ Exists — needs layout/height fix |
| `MarketWeatherWidget.tsx` | GAS score (64px font), weather label (Tailwind + Headwind etc.), description text, Info button | ✅ Exists — is the primary signal panel |
| `RegimeWidget.tsx` | Technical Regime + Volatility Regime side-by-side, VIX display, color-coded, Info buttons | ✅ Exists — maps to supporting indicator cards |
| `TimeframeGrid.tsx` | Technical Consensus — multi-timeframe signal grid | ✅ Exists — currently inside a wrapper div |
| `WhyMovingPanel.tsx` | "Why is X moving?" bullet explanation panel | ✅ Exists — correctly placed below signals |
| `ConflictDetector.tsx` | Cross-layer conflict detection (Tech vs Sentiment vs Macro divergence) | ✅ Exists — **not covered in original spec at all** |
| `ScoreExplainPanel.tsx` | Slide-over panel with sub-component breakdown (GAS, Technical, Macro, Volatility) | ✅ Exists — **not covered in original spec at all** |
| `WatchlistWidget.tsx` | Watchlist sidebar with add/remove, active ticker highlight, auth-gated | ✅ Exists — sidebar shown on xl screens, collapses to top on mobile |
| `SentimentChart.tsx` | News sentiment chart (used on `/news-sentiment` page) | ⚠️ Not on dashboard — sentiment shown only as a score in GAS |
| `SourceBreakdownTable.tsx` | Sentiment source breakdown table | ⚠️ Not on dashboard |
| `MarketWeatherWidget.tsx` | Macro score fed via `gasSnapshot.component_scores.macro` | ⚠️ Macro score has no dedicated visible card on dashboard |
| `ArticleList.tsx` | Article list (used in `/learn`) | 🔵 Out of scope for dashboard |
| `ConsentGate.tsx` | GDPR consent gate | 🔵 Separate concern |
| `GuidedTour.tsx` | Onboarding guided tour | ✅ Exists — already wired to dashboard |

### Pages (`/frontend/app/`)

The app has a **rich page ecosystem** that the UX spec didn't account for at all:

| Route | Purpose |
|-------|---------|
| `/` | Main dashboard (GAS + Regime + Timeframes + Why Moving + Conflicts) |
| `/macro` | Full macro intelligence page |
| `/news-sentiment` | Full news sentiment page |
| `/sentiment` | Retail sentiment |
| `/sentiment-adv` | Advanced sentiment |
| `/options` | Options data |
| `/sectors` | Sector performance |
| `/insiders` | Insider transactions |
| `/earnings` | Earnings calendar |
| `/shorts` | Short interest |
| `/fed-policy` | Fed policy tracker |
| `/indicators` | Technical indicators |
| `/hedge` | Hedging tools |
| `/backtesting` | Strategy backtesting |
| `/portfolios` | Portfolio management |
| `/alerts` | Price/signal alerts |
| `/risk` | Risk analysis |
| `/learn` | Educational content |
| `/showcase` | Pro tools |
| `/community` | Community |
| `/billing` | Billing & plans |
| `/settings` | User settings |

### Dashboard Layout (Current)

```
┌──────────────────────────────────────────────────────┐
│  Nav (19 items + UserMenu with Pro/Free badge)        │
├──────────┬───────────────────────────────────────────┤
│          │  Header: "[TICKER] Intelligence"           │
│ Watchlist│  Ticker input + Analyze button + Tour btn  │
│ (xl only)├───────────────────────────────────────────┤
│          │  ROW 1: MarketWeatherWidget | RegimeWidget │
│          │          (GAS score)        + TimeframeGrid│
│          ├───────────────────────────────────────────┤
│          │  ROW 2: WhyMovingPanel | ConflictDetector  │
│          ├───────────────────────────────────────────┤
│          │  Quick links → /macro, /news-sentiment     │
└──────────┴───────────────────────────────────────────┘
```

---

## 1. Goal

Transform Fin-Eye from a functional dashboard into an **institutional-grade fintech analytics platform**. The redesigned UI should answer one question in under 3 seconds:

> **"Is this asset bullish or bearish — and why?"**

---

## 2. Gap Analysis: What's Missing vs. What Exists

### ✅ Already Implemented (No Action Needed)
- Primary GAS signal panel (`MarketWeatherWidget`) — score at 64px, color-coded, info button
- Technical Regime + Volatility Regime cards (`RegimeWidget`) — side-by-side, VIX shown
- Technical Consensus grid (`TimeframeGrid`)
- "Why moving?" explanation panel (`WhyMovingPanel`)
- Conflict detection (`ConflictDetector`) — a feature *better* than the spec
- Score explainer slide-over (`ScoreExplainPanel`) — a feature *better* than the spec
- Watchlist sidebar (`WatchlistWidget`) — full add/remove/auth-gated
- Navbar with 19 items, user menu, pro/free badge, admin panel access
- Guided onboarding tour

### ⚠️ Partially Implemented / Needs Improvement
These exist but don't fully match the spec's UX quality targets:

| Item | Current State | What's Needed |
|------|--------------|---------------|
| **Asset Header** | Shows "[TICKER] Intelligence" title + snapshot age, but no price/% change, no market status, no timeframe selector | Add real-time price + % change display; add timeframe selector (1D/5D/1M etc.) |
| **Signal Overview Row** | No dedicated 5-card overview row — signals are embedded inside larger panels | Create a compact horizontal row: GAS · Technical · Volatility · Macro · Sentiment (each 140px card) |
| **Macro Score Card** | Macro score feeds GAS composite but has no standalone visible card on the dashboard | Add a dedicated Macro card (score + label, e.g. "54 · Neutral") |
| **Sentiment Score Card** | Same issue — sentiment feeds GAS but isn't surfaced as its own card on the dashboard | Add a dedicated Sentiment card (30d score + label) |
| **Nav layout** | Nav is a flat horizontal wrap of 19 items — no height control, no logo area, no sticky positioning | Set height to 56px, add Fin-Eye logo left, move UserMenu right, consider collapsing low-priority nav items into a dropdown |
| **Watchlist width** | Currently `w-48` (192px) on xl screens only | Widen to 260px, show from lg breakpoint, consider persistent left rail rather than inline aside |
| **Card visual consistency** | Panels use a mix of `rounded-2xl`, `rounded-xl`, varying border opacities | Standardize to one card base class: `rounded-xl border border-slate-800 bg-slate-900/50 p-4` |
| **Section spacing** | `space-y-6` used throughout — roughly 24px | Upgrade to `space-y-8` (32px) between major sections for cleaner breathing room |
| **GAS panel layout** | GAS is in a 50/50 grid with RegimeWidget+TimeframeGrid — the primary signal doesn't dominate | Give GAS panel a slightly larger allocation (e.g. 55/45 or 6/6 with GAS taking more vertical space) |

### ❌ Not Implemented (New Work Required)
These are spec items that don't exist anywhere in the codebase yet:

| Item | Priority | Notes |
|------|----------|-------|
| **Real-time price + % change in Asset Header** | High | Requires a price API call (e.g. Yahoo Finance API or similar) |
| **Timeframe selector on Asset Header** | Medium | Selector exists conceptually (TimeframeGrid) but not as a global date range control on the header |
| **Sentiment card on dashboard** | High | Data is available (`sentData.sentiment_30d`) — just needs a visible card |
| **Macro card on dashboard** | High | Data is available (`macroScore`, `macroLabel`) — just needs a visible card |
| **Signal Overview Row (5 cards)** | High | Compact summary row above the main panels — quick scannable snapshot |
| **Chart Panel** | Low (post-MVP) | Price chart below explanation panel — validates signals visually |
| **"Recently Viewed" section in sidebar** | Low | Nice-to-have for power users |
| **Mobile nav collapse** | Medium | 19 nav items wraps badly on small screens — needs a hamburger/drawer |

---

## 3. Core Design Principles

| Principle | Description |
|-----------|-------------|
| Signal First | Primary signal visible above the fold, no scrolling required |
| Evidence Second | Supporting indicators grouped near the primary signal |
| Explanation Third | Short bullet reasoning appears after signals |
| Exploration Last | Charts and deep analysis at the bottom |
| Density Over Decoration | No large empty cards; prefer compact, information-rich panels |
| Color For Signals Only | Background/UI stays neutral; color reserved for bullish/bearish/neutral states |

---

## 4. Target Layout Architecture

### 4.1 Global Grid

```
Page width:       1440px
Content max:      1280px
Grid columns:     12
Column gap:       24px
Sidebar width:    260px
Main content:     ~980px
```

### 4.2 Target Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR (56px) — Logo | Nav items | Search | UserMenu    │
├──────────┬──────────────────────────────────────────────┤
│          │  Asset Header (80px)                          │
│          │  TICKER · Price · % Change · Market Status    │
│          │  Timeframe: 1D 5D 1M 3M YTD 1Y 5Y            │
│          ├──────────────────────────────────────────────┤
│          │  Signal Overview Row (140px)                  │
│ SIDEBAR  │  GAS | Technical | Volatility | Macro | Sent  │
│ (260px)  ├──────────────────────────────────────────────┤
│          │  GAS Panel (6col) │ Tech (3col) │ Vol (3col)  │
│          ├──────────────────────────────────────────────┤
│          │  TimeframeGrid (full width or 6col)           │
│          ├──────────────────────────────────────────────┤
│          │  WhyMoving (6col) │ ConflictDetector (6col)   │
│          ├──────────────────────────────────────────────┤
│          │  Chart Panel (optional, post-MVP)             │
└──────────┴──────────────────────────────────────────────┘
```

### 4.3 Alternative: Z-Grid + Signal Spine (Post-MVP Power Mode)

A more advanced layout — all decision logic lives in one vertical column:

```
┌──────────┬──────────────────┬───────────────────────────┐
│ SIDEBAR  │  SIGNAL SPINE    │  CONTEXT ZONE              │
│ (2 col)  │  (4 col)         │  (6 col)                   │
│          │                  │                            │
│Watchlist │  GAS Score       │  Price Chart               │
│          │  Technical       │  Market Data               │
│          │  Volatility      │  Sector Performance        │
│          │  Macro           │  Options Data              │
│          │  Sentiment       │  Recent News               │
│          │                  │                            │
│          │  Why moving?     │                            │
│          │  Conflicts       │                            │
└──────────┴──────────────────┴───────────────────────────┘
```

> **Recommendation:** Implement standard layout (4.2) first. Signal Spine can be a power-user toggle post-launch.

---

## 5. Component Specifications

### 5.1 Navbar (update existing `Nav.tsx`)
- **Height:** 56px fixed, sticky
- **Left:** Fin-Eye logo + primary nav items (collapse low-priority items to a "More" dropdown)
- **Right:** Ticker search input · Notifications bell · `UserMenu` (already built)
- **Active state:** already implemented — keep as-is

### 5.2 Sidebar (update existing `WatchlistWidget.tsx`)
- **Width:** 260px (currently 192px — increase)
- **Show from:** `lg` breakpoint (currently `xl` only)
- **Sections:** Watchlist (already built) · Recently Viewed (new, optional)
- **Ticker row:** symbol · (optionally add price + % change post-MVP)

### 5.3 Asset Header (new — currently just a title + input)
- **Height:** 80px
- **Left:** `[TICKER] — Full Company Name` · Current price · % change (color coded) · Market status (Open/Closed)
- **Right:** Timeframe selector: `1D · 5D · 1M · 3M · YTD · 1Y · 5Y`
- **Below:** Keep existing "Analyze" ticker input (but move to right side or make it a search bar in the header)
- **Data needed:** Real-time price endpoint

### 5.4 Signal Overview Row (new component)
- **Height:** 140px
- **Layout:** 5 equal cards across full width
- **Data:** All data already exists in `page.tsx` — just needs a new presentational row

| Card | Data source | Display |
|------|------------|---------|
| GAS Score | `gasScore` | `36 · Headwind` |
| Technical | `techScore`, `derivedRegime` | `72 · Risk-On` |
| Volatility | `vixLevel`, `volatilityRegime` | `High · VIX 27` |
| Macro | `macroScore`, `macroLabel` | `54 · Neutral` |
| Sentiment | `sent30d` | `+0.12 · Mild Positive` |

### 5.5 GAS Panel (`MarketWeatherWidget.tsx` — already good)
- **Width:** 6 columns
- **Height:** 220px
- Score at 64px ✅, color-coded ✅, info button ✅
- Minor: add score label "/ 100" next to score for new users

### 5.6 Regime Cards (`RegimeWidget.tsx` — already good)
- **Width:** 3 columns each (currently 50/50 flex — fine)
- Add confidence % to Technical card when available

### 5.7 Explanation Panel (`WhyMovingPanel.tsx` — already good)
- Keep at full width, below signal panels ✅
- Add a subtle section header: "Signal Narrative" or "Why is {TICKER} moving?"

### 5.8 Conflict Detector (`ConflictDetector.tsx` — already good, not in original spec)
- Keep as-is — this is a **better** feature than the original spec envisioned
- Consider adding a visual severity indicator (low/medium/high conflict)

### 5.9 Chart Panel (new — post-MVP)
- **Height:** 420–500px
- Embed TradingView widget or lightweight chart library
- Position: below WhyMoving + ConflictDetector

---

## 6. Design Tokens

### 6.1 Colors

```css
/* Backgrounds */
--bg-primary:     #0B0F1A;
--bg-card:        #121826;
--bg-hover:       #1A2235;

/* Borders */
--border-default: #1F2A44;
--border-soft:    #2A3556;

/* Text */
--text-primary:   #E6EAF2;
--text-secondary: #9AA4B2;
--text-muted:     #6B7280;

/* Signals — currently mapped to Tailwind classes, consider CSS vars */
--signal-bullish: #22C55E;   /* emerald-400 */
--signal-bearish: #EF4444;   /* rose-500 */
--signal-neutral: #F59E0B;   /* amber-400 */

/* Accent */
--accent:         #3B82F6;   /* blue-500 — already used in buttons */
```

> **Note:** The codebase already uses Tailwind color classes consistently (emerald/teal/amber/orange/rose). The above tokens are for a future design-token migration; don't refactor Tailwind colors now.

### 6.2 Typography

```css
/* Font — already Inter via Next.js/Tailwind defaults */
font-family: 'Inter', sans-serif;

/* Current usage (already in codebase) */
GAS Score:      text-6xl font-black    (64px / 900) ✅
Asset Title:    text-3xl font-black    (30px / 900) ✅  → bump to 32px / 600 per spec
Section H2:     text-sm font-semibold  (13px / 600) — slightly small, consider text-base
Card Label:     text-xs                (12px)
Body:           text-sm                (14px) ✅
```

### 6.3 Spacing (8pt System)

```css
/* Current: space-y-6 (24px) throughout */
/* Target: */
--space-card-padding:  16px;   /* p-4 — standardize all cards */
--space-card-gap:      16px;   /* gap-4 between cards in a row */
--space-section-gap:   32px;   /* space-y-8 between major sections */
--space-page-margin:   24px;   /* px-6 on page container */
```

### 6.4 Card Base Style (standardize)

```tsx
// All cards should use this base — some currently use rounded-2xl, some rounded-xl
className="rounded-xl border border-slate-800 bg-slate-900/50 p-4"
```

---

## 7. Known UX Problems (Code-Level)

| # | Problem | Location | Fix |
|---|---------|----------|-----|
| 1 | **No Macro card on dashboard** | `page.tsx` | Add a `MacroCard` component or include macro in Signal Overview Row |
| 2 | **No Sentiment card on dashboard** | `page.tsx` | Same — data is available, just needs a visible card |
| 3 | **GAS + Regime in 50/50 grid** | `page.tsx` line 551 | GAS should be more dominant; try `lg:grid-cols-5` with GAS taking 3 cols |
| 4 | **Asset header has no price/change** | `page.tsx` line 496 | Needs a price API integration |
| 5 | **Nav wraps on medium screens** | `Nav.tsx` | 19 items overflow on tablet — collapse to "More ▾" dropdown |
| 6 | **Watchlist hidden until xl** | `page.tsx` line 486 | Change `hidden xl:block` to `hidden lg:block` |
| 7 | **No Signal Overview Row** | `page.tsx` | Build new compact 5-card row between asset header and main panels |
| 8 | **`space-y-6` everywhere** | `page.tsx` | Change major section gaps to `space-y-8` for better section breathing room |
| 9 | **Mixed border-radius** | Multiple components | Standardize: `rounded-xl` for cards, `rounded-2xl` only for GAS hero panel |
| 10 | **No sticky nav** | `layout.tsx` | Add `sticky top-0 z-40` to nav wrapper |

---

## 8. Scanning Flow to Enforce

```
Ticker + Price (Asset Header)
        ↓
Signal Overview Row (5 compact cards — all signals at a glance)
        ↓
Primary Signal: GAS Score
        ↓
Supporting: Technical Regime · Volatility Regime
        ↓
Technical Consensus (TimeframeGrid)
        ↓
Explanation: Why is it moving? + Conflicts
        ↓
Chart (Validation / Deep Analysis) — post-MVP
```

Target: user reads the full investment thesis in **under 5 seconds**.

---

## 9. "Institutional Feel" Checklist

- [ ] Navbar is 56px, sticky, has logo
- [ ] Asset header shows ticker + price + % change
- [ ] Signal Overview Row exists (5 compact cards)
- [ ] GAS score is the visually dominant panel
- [ ] Macro score has a visible card on the dashboard
- [ ] Sentiment score has a visible card on the dashboard
- [ ] Explanation panel (WhyMoving) is below, not above signals ✅
- [ ] ConflictDetector remains visible alongside WhyMoving ✅
- [ ] Color used only for signal states ✅
- [ ] Watchlist sidebar visible from lg breakpoint
- [ ] Cards use consistent border/radius/padding
- [ ] Section spacing is 32px between major blocks
- [ ] Nav collapses gracefully on tablet/mobile
- [ ] At least 8 data points visible above the fold

---

## 10. Implementation Phases

### Phase 1 — Quick Wins (Low effort, high visual impact)
- [ ] Change `space-y-6` → `space-y-8` for major section gaps in `page.tsx`
- [ ] Standardize card border-radius to `rounded-xl` (remove `rounded-2xl` from most cards)
- [ ] Add `sticky top-0 z-40` to nav wrapper in `layout.tsx`
- [ ] Change watchlist breakpoint from `xl` to `lg`
- [ ] Add "/ 100" label next to GAS score number

### Phase 2 — Signal Completeness (Medium effort, fills core gaps)
- [ ] Add **Macro Score card** to dashboard (data already available: `macroScore`, `macroLabel`)
- [ ] Add **Sentiment Score card** to dashboard (data already available: `sent30d`)
- [ ] Build **Signal Overview Row** — 5 compact cards (GAS · Technical · Volatility · Macro · Sentiment)
- [ ] Increase GAS panel visual dominance (adjust grid ratios)

### Phase 3 — Asset Header (Requires new data)
- [ ] Add real-time price + % change API integration
- [ ] Build proper Asset Header component (ticker · company name · price · market status)
- [ ] Add timeframe selector (1D · 5D · 1M · 3M · YTD · 1Y · 5Y)

### Phase 4 — Nav & Mobile
- [ ] Add Fin-Eye logo to left of navbar
- [ ] Collapse low-priority nav items to a "More ▾" dropdown on < 1280px
- [ ] Add hamburger/drawer for mobile nav

### Phase 5 — Polish & Advanced (Post-MVP)
- [ ] Add Chart Panel (TradingView embed or lightweight chart)
- [ ] Add "Recently Viewed" to sidebar
- [ ] Signal Spine layout as a power-user toggle
- [ ] Full responsive audit at 768px / 1024px / 1280px / 1440px

---

## 11. Reference Benchmarks

| Product | What to Study |
|---------|--------------|
| Yahoo Finance | Asset header pattern, signal row, scanning flow |
| Koyfin | Information density, card system, sidebar |
| TradingView | Watchlist UX, chart placement, layout grid |
| Bloomberg Terminal Web | Color discipline, typography hierarchy, institutional tone |
