# Fin-Eye UI Roadmap — Navigation, Sidebar & Showcase
> **Created:** 2026-03-16  
> **Type:** Design + Frontend TODO  
> **Status:** 📋 Ready to implement when you are  
> **Research basis:** Fintech UX best practices 2025/2026 + current Fin-Eye page inventory

---

## 🧠 Brainstorm Summary

### The Core Problem Right Now
Fin-Eye has **19 pages** but the nav treats them all as equal flat items. There's no visual hierarchy, no sense of "where am I in this tool", and no discovery path for new users. The top bar is already overloaded and the showcase barely surfaces value.

### The Direction (No Dramatic Changes)
The goal is **not** a full redesign. It's:
1. Add a **collapsible left sidebar** that categorises the 19 pages into logical groups — this is the industry-standard pattern for SaaS dashboards with many modules (Linear, Notion, Vercel, TradingView all do this)
2. Keep the **top bar** for logo + search + user menu only (it becomes clean and minimal)
3. **Populate the Showcase** with real, high-value tool ideas grouped properly
4. Add a **page banner/hero** on key pages showing what the page does and surfacing quick actions — right now pages just dump data with no context

### Why Left Sidebar Works for Fin-Eye Specifically
- 19 nav items is too many for a top bar — sidebar is the correct pattern at this scale
- Financial tools (Bloomberg, TradingView, Koyfin, Robinhood web) all use left sidebars
- Sidebar allows **category grouping** with section headers — users immediately understand the information architecture
- Sidebar can show **active page with accent colour** — strong wayfinding
- Collapsible to icon-only mode for power users who want more screen space
- On mobile: already have the drawer, sidebar is the natural upgrade of that

---

## 📐 Part 1 — Left Sidebar Navigation

### Proposed Category Structure

```
CORE ANALYSIS
  ├── Dashboard          (/)
  ├── Macro              (/macro)
  └── Sentiment          (/news-sentiment)

DEEP SIGNALS
  ├── Retail Mood        (/sentiment)
  ├── Adv. Sentiment     (/sentiment-adv)
  ├── Options Flow       (/options)
  ├── Insider Activity   (/insiders)
  ├── Short Interest     (/shorts)
  └── Earnings           (/earnings)

MARKET CONTEXT
  ├── Sectors            (/sectors)
  ├── Fed Policy         (/fed-policy)
  ├── Indicators         (/indicators)
  └── Hedge              (/hedge)

TOOLS
  ├── Backtesting        (/backtesting)
  ├── Portfolio          (/portfolios)
  ├── Alerts             (/alerts)
  └── Pro Tools          (/showcase)

LEARN
  ├── Learn Hub          (/learn)
  └── Community          (/community)
```

### Sidebar Behaviour Spec

| State | Behaviour |
|-------|-----------|
| Default (desktop ≥ lg) | Expanded: 220px wide, shows icon + label + section headers |
| Collapsed (user toggles) | Icon-only: 56px wide, tooltips on hover show label |
| Tablet (md) | Hidden, triggered by hamburger in top bar (existing drawer) |
| Mobile (< md) | Hidden, hamburger drawer (existing) |
| Persistence | Collapse state saved to localStorage |
| Active item | Sky-400 text + slate-800 background + left border accent |
| Section headers | ALL CAPS, slate-600, text-[10px], non-clickable |

### Layout Change

```
Before:
┌─────────────────────────────────────────────┐
│ Header: Logo + [flat nav 19 items] + User   │
├─────────────────────────────────────────────┤
│ Main content                                 │
└─────────────────────────────────────────────┘

After:
┌────────────┬────────────────────────────────┐
│            │ Header: Logo + Search + User   │
│  Sidebar   ├────────────────────────────────┤
│  220px     │ Main content                   │
│            │                                │
└────────────┴────────────────────────────────┘
```

### Files to Touch
- `frontend/components/Nav.tsx` — add `Sidebar` component, keep `MobileNav` drawer
- `frontend/app/layout.tsx` — switch from top-bar-nav layout to sidebar + content layout
- `frontend/components/ui/` — add `SidebarCollapseToggle` button

### Design Details
- Background: `bg-slate-950` with `border-r border-slate-800`
- Section headers: `text-[10px] font-semibold tracking-widest text-slate-600 uppercase px-3 pt-4 pb-1`
- Nav item (expanded): `flex items-center gap-3 px-3 py-2 rounded-lg text-sm`
- Nav item (active): `bg-slate-800 text-sky-400 border-l-2 border-sky-500`
- Nav item (inactive): `text-slate-400 hover:bg-slate-900 hover:text-slate-100`
- Icons: use `lucide-react` — each section/item gets a relevant icon (see below)

### Icon Mapping

```
Dashboard      → LayoutDashboard
Macro          → Globe
Sentiment      → Newspaper
Retail Mood    → Users
Adv. Sentiment → Zap
Options Flow   → Activity
Insider        → Eye
Shorts         → TrendingDown
Earnings       → Calendar
Sectors        → PieChart
Fed Policy     → Landmark
Indicators     → BarChart2
Hedge          → Shield
Backtesting    → FlaskConical
Portfolio      → Briefcase
Alerts         → Bell
Pro Tools      → ShoppingBag
Learn          → BookOpen
Community      → MessageCircle
Settings       → Settings
```

---

## 📋 Part 2 — Page Banners / Hero Headers

### The Problem
Right now every page just starts dumping data. There's no page-level "what is this and why should I care" moment. New users feel lost.

### The Pattern (Non-Dramatic)
Each major page gets a **slim hero banner** at the top:
- Icon + Page title + 1 line description
- Optional: 1-2 quick action buttons (e.g. "Train Model", "Add to Watchlist")
- Optional: Data freshness indicator ("Last updated 4 min ago")
- Optional: Pro badge if the page is Pro-only

### Banner Design Spec

```tsx
// Compact — fits in ~60px height
<PageBanner
  icon={<Globe />}
  title="Macro Intelligence"
  description="Real-time FRED indicators, yield curve, VIX, and recession risk."
  badge="Live"                    // optional
  actions={[...]}                 // optional
/>
```

### Pages That Most Need It

| Page | Title | 1-liner | Quick Action |
|------|-------|---------|--------------|
| `/` | Dashboard | GAS score, regime, and multi-timeframe consensus | Train model |
| `/macro` | Macro Intelligence | FRED indicators, yield curve, recession risk | — |
| `/news-sentiment` | News Sentiment | FinBERT-scored articles, 30d trend | — |
| `/backtesting` | Strategy Backtester | Simulate momentum strategies on historical data | New backtest |
| `/portfolios` | Portfolio Builder | Grade-based allocation across your watchlist | Build portfolio |
| `/alerts` | Price & GAS Alerts | Get notified when signals cross your thresholds | New alert |
| `/options` | Options Flow | Put/call ratios and unusual activity | — |
| `/insiders` | Insider Activity | SEC Form 4 filings, buy/sell by insiders | — |
| `/showcase` | Pro Tools | Curated tools and templates for your workflow | — |

---

## 🛒 Part 3 — Showcase Redesign + Product Population

### The Problem
Showcase currently pulls from backend DB (dynamic). If the DB is empty or has 2-3 products it looks dead. It also has no category depth or discovery experience.

### Brainstormed Product Categories + Ideas

#### 📊 Analysis Templates
- **GAS Interpretation Cheat Sheet** — PDF/Notion template explaining how to read every Fin-Eye score, what each range means, and how to combine signals. Free/low price.
- **Multi-Timeframe Checklist** — Trading decision checklist that maps 1h/4h/1d/1wk signals to entry/exit criteria. Google Sheets + PDF.
- **Sector Rotation Playbook** — Guide on how to use Fin-Eye's sector data to rotate between XLK/XLF/XLV/XLE at the right time.
- **Macro Regime Playbook** — How to position differently in Risk-On vs Risk-Off vs Transitional regimes.

#### 🧮 Portfolio & Risk Tools
- **Position Sizing Calculator** — Excel/Sheets tool: inputs GAS grade, account size, risk %, outputs exact position size per trade.
- **Grade-Based Allocation Spreadsheet** — Auto-weights a portfolio based on signal grades. Green/amber/red cells.
- **Portfolio Drawdown Tracker** — Tracks max drawdown per position and portfolio-level, flags when you approach your limit.
- **Kelly Criterion Calculator** — Inputs win rate + avg win/loss, outputs optimal position fraction.
- **Risk/Reward Journal Template** — Google Sheets trade journal: entry, exit, grade at entry, GAS at entry, outcome. Builds your edge over time.

#### 📰 Research & Education
- **Macro Indicator Deep Dive** — Mini-course PDF: what each FRED indicator means, historical behaviour, how Fin-Eye weights it.
- **FinBERT Sentiment Guide** — How NLP sentiment works, how to interpret 30d vs 7d vs 1d, when sentiment leads price.
- **Earnings Season Playbook** — How to use Fin-Eye signals in the 2 weeks before and after earnings.
- **Crypto Signal Guide** — Specific to BTC/ETH/SOL — how to interpret GAS for 24/7 assets, weekend signal behaviour.
- **Backtesting Interpretation Guide** — What Sharpe Ratio, Sortino, max drawdown mean in practice. When to trust a backtest.

#### ⚙️ Workflow Tools
- **Watchlist Builder Template** — Notion/Sheets template: symbol, sector, GAS history, notes, last checked.
- **Weekly Market Review Template** — Sunday ritual: macro score check, regime status, top watchlist grades, plan for the week.
- **Signal Alert Setup Guide** — Step-by-step guide to configuring the best Fin-Eye alerts for different trading styles.
- **Trading Plan Template** — One-page PDF per trade: thesis, entry, stop, target, grade at entry, exit rules.

#### 🔗 Integrations (Future)
- **TradingView Indicator Pack** — Pine Script indicators that mirror Fin-Eye's GAS/regime signals on your charts.
- **Notion Trading Dashboard** — Pre-built Notion workspace synced to Fin-Eye's signal categories.

### Showcase New Category Structure

```
All  |  Templates  |  Portfolio Tools  |  Education  |  Workflow  |  Integrations
```

### Showcase UI Improvements
- **Featured row** at top: 1-2 hero products with larger card, gradient background
- **"New" badge** on products added in last 30 days
- **"Free" vs "Paid" filter** — many users want free resources first
- **Search bar** inside the showcase to filter by keyword
- **Rating/popularity** indicator (download count or star rating)
- Grid: 3-col on desktop, 2-col on tablet, 1-col on mobile

---

## 🏗️ Part 4 — Implementation Order

When you're ready, do these in order — each step is self-contained and non-breaking:

### Step 1 — Page Banners (Quickest win, no layout change)
- [ ] Create reusable `PageBanner` component (`components/ui/PageBanner.tsx`)
- [ ] Add to: Dashboard, Macro, Sentiment, Backtesting, Portfolio, Alerts, Showcase
- [ ] Estimated effort: **2-3 hours**

### Step 2 — Showcase Populated
- [ ] Seed the showcase DB with 12-15 products from the brainstorm above
- [ ] Add Free/Paid filter to showcase page
- [ ] Add featured hero row for top 2 products
- [ ] Estimated effort: **2-3 hours**

### Step 3 — Left Sidebar (The big one)
- [ ] Build `Sidebar` component with expand/collapse, icons, category sections
- [ ] Update `layout.tsx` to sidebar + content layout
- [ ] Remove `Nav` (desktop top nav links) — sidebar replaces it
- [ ] Keep `MobileNav` hamburger drawer as-is (it already works)
- [ ] Test on all breakpoints
- [ ] Estimated effort: **4-6 hours**

### Step 4 — Polish
- [ ] Add `PageBanner` to remaining pages (options, insiders, shorts, etc.)
- [ ] Add sidebar collapse state to localStorage
- [ ] Add "New" badge logic to showcase
- [ ] WCAG contrast audit on sidebar colors
- [ ] Estimated effort: **2 hours**

---

## 📌 Reference — What Top Financial Tools Do

| Tool | Navigation Pattern |
|------|--------------------|
| TradingView | Left sidebar (collapsible) + top bar for search/user |
| Koyfin | Left sidebar with categories, icon+label |
| Bloomberg Terminal | Left sidebar, section grouped |
| Robinhood Web | Left sidebar (minimal), top search |
| Notion | Left sidebar with sections + collapse |
| Linear | Left sidebar with grouped sections + icons |
| Vercel Dashboard | Left sidebar, icon-only collapse mode |

**Conclusion:** Left sidebar with grouped categories is the universal standard for tools with 10+ pages. Fin-Eye is at 19 pages — the top bar was already past its limit.

---

*Last updated: 2026-03-16*
