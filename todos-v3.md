# Fin-Eye — Todos v3
> **Version:** 3.0  
> **Created:** 2026-03-20  
> **Author:** Product + Dev review  
> **Status:** Active working backlog  
>
> ⚠️ This file does NOT replace `todos.md` (v2). Both files are preserved.  
> `todos.md` = the original UX/product backlog (unimplemented, still valid).  
> `todos-v3.md` = this file — the prioritised, actionable dev backlog for the current sprint cycle, informed by the full codebase state, MASTER-USER-STORIES.md, and prdv3.md.
>
> **Legend:** 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Nice-to-have · ⚡ Quick-win · ✅ Done

---

## How This File Is Organised

Items are grouped by **area** and ordered by **priority within each area**.  
Each item has:
- A priority emoji
- A one-line description of the task
- The user story ID it maps to (from MASTER-USER-STORIES.md)
- A brief "why it matters" note where non-obvious

---

## 1. 🔴 Pre-Launch Blockers — Must ship before any public traffic

These items are non-negotiable. The app must not receive real users until all of them are done.

- [ ] 🔴 **Rotate all API keys and secrets** (SEC-01) — FINNHUB, FRED, JWT_SECRET, TOTP Fernet key. Confirm `backend/.env` is in `.gitignore`. Audit git history for committed secrets.
- [ ] 🔴 **Lock down production config** (SEC-02) — Set `REQUIRE_AUTH=True`, `DEBUG=False`, and `ALLOWED_ORIGINS` to the production domain in all non-dev environments. Add a pre-deploy checklist item.
- [ ] 🔴 **Rate limit auth endpoints** (SEC-03) — Install `slowapi`. Apply Redis-backed limits: login 10/min, register 5/min, 2FA verify 5/min. Return 429. Write tests.
- [ ] 🔴 **Refresh token rotation + logout blacklist** (SEC-04) — Add JTI to refresh tokens. Store in Redis. On `/auth/refresh` rotate JTI. On `/auth/logout` add to blocklist. Middleware rejects blocklisted JTIs.
- [ ] 🔴 **Account lockout after failed logins** (SEC-05) — 10 failed attempts in 15 min → 30-min lock stored in Redis. Clear error message. Admin unlock endpoint.
- [ ] 🔴 **Security headers middleware** (SEC-06) — `SecurityHeadersMiddleware` on FastAPI: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS. Integration test asserting headers.
- [ ] 🔴 **Email verification enforcement** (SEC-07) — `get_current_active_verified_user` dependency. Apply to all sensitive endpoints (watchlist, backtesting, GAS, portfolio). Resend verification button in Settings. Tokens expire 24h.
- [ ] 🔴 **Move ML model artifacts to cloud storage** (SEC-08) — Migrate `model_store/` to Cloudflare R2 (or S3). Remove from repo. On fresh deploy, models downloaded from R2 on first startup.
- [ ] 🔴 **Run Alembic migration for volume BigInt** (BUG-011) — `alembic revision --autogenerate -m "volume_bigint" && alembic upgrade head`. Without this, OHLCV inserts fail silently for high-volume stocks (AAPL, SPY, QQQ).
- [ ] 🔴 **Seed the database** — Hit `POST /api/v1/data/fetch/ohlcv`, `POST /api/v1/data/fetch/macro`, `POST /api/v1/data/fetch/news?lookback_days=7` to populate all empty tables. Dashboard shows only fallback 50.0 values until this is done.
- [ ] 🔴 **Train ML models for all 18 symbols** — Run `POST /api/v1/technical/train/{symbol}` for all 18 default symbols. GAS technical component is flat 50.0 until models exist.
- [ ] 🔴 **Warm GAS cache after training** — `POST /api/v1/admin/gas/precompute` after all models are trained.

---

## 2. 🟠 Navigation — The flat 19-item nav is currently unusable on any screen below ~1400px

The nav exists (`Nav.tsx`) but has 19 flat items with no grouping, no mobile support, and no overflow handling. This is the first thing every user sees.

- [ ] 🟠 **Grouped dropdown navigation** (UX-NAV-01) — Replace the flat nav with categorised dropdowns:
  - **Intelligence**: Dashboard, Macro, Sentiment, Retail, Fed Policy
  - **Markets**: Options, Sectors, Earnings, Insiders, Shorts, Adv. Sentiment
  - **Tools**: Backtest, Portfolio, Hedge, Indicators, Alerts
  - **Learn**: Learn, Community
  - **Pro Tools**: Showcase
- [ ] 🟠 **Mobile hamburger / drawer nav** (UX-UI-04) — For screens below `md` breakpoint: collapse nav into a hamburger icon that opens a full-height drawer. Currently the nav wraps and overflows on any small screen.
- [ ] ⚡ **"NEW" / "BETA" badges on nav items** (UX-NAV) — Add a tiny badge to Adv. Sentiment, Fed Policy, and Indicators in the nav to drive exploration of newer features.
- [ ] 🟡 **CMD+K command palette** (UX-NAV-02) — Global keyboard shortcut to jump to any ticker or page. Particularly useful for power users who cycle through many symbols quickly.

---

## 3. 🟠 Dashboard — Core UI quality gaps

The dashboard `page.tsx` is wired correctly but has several gaps that affect first impressions and daily usability.

- [ ] 🟠 **Skeleton loaders** (UX-UI-01) — Replace `animate-pulse` blank divs with layout-accurate skeleton screens that mirror the real component shapes (GAS circle, timeframe grid, why-moving bullets). This is the #1 perceived-performance fix.
- [ ] 🟠 **Global toast / snackbar system** (UX-UI-02) — No feedback currently on: save success, API errors, alert fire, copy-to-clipboard. Implement a top-right toast system. All silent failures become visible.
- [ ] 🟠 **Designed empty states** (UX-UI-03) — Every section (Sentiment, Macro, Backtesting, News, Timeframe Grid) needs an icon + message + CTA empty state. Currently shows raw error text or nothing.
- [ ] 🟠 **GAS History sparkline (7-day)** (UX-GROWTH-01) — Add a mini line chart directly below the GAS score showing the past 7 days of scores. A single static number tells users nothing about trend. This is the single biggest "Aha Moment" driver.
- [ ] 🟠 **Symbol autocomplete search** (POLISH-02) — The current ticker input is a free-form text box. Wire it to `POST /api/v1/symbols/search` (wrapping Finnhub `/search`). Show ticker, company name, exchange, type in dropdown. 8 max results.
- [ ] 🟠 **SWR error boundaries** (UX-PERF-01) — Wrap each dashboard widget in an ErrorBoundary. Currently if `fetchGasSnapshot` throws, the entire page crashes. Each section should fail independently with its own fallback UI.
- [ ] 🟠 **Standardised semantic colours** (UX-UI-05) — Audit all components. Enforce: Bullish = `emerald-400`, Bearish = `rose-400`, Neutral = `amber-400`. Currently mixed across `TimeframeGrid`, `RegimeWidget`, `MarketWeatherWidget`, `StrategyCard`.
- [ ] 🟡 **"What Changed Today" widget** (UX-GROWTH-02) — A panel below the main dashboard showing `AAPL GAS: 62→71 ↑` and `TSLA Regime: Risk-Off→Risk-On` for all watchlist symbols. Gives power users a reason to return daily.
- [x] ✅ **Score Change Explainer banner (UX-EDU-03)** — Implemented Sprint 22: dismissable GAS change banner in `page.tsx`.
- [ ] 🟡 **Responsive dashboard grid** (UX-UI-04) — Test and fix the `lg:grid-cols-2` layout at 375px (iPhone SE). Ensure single-column reflow is clean on mobile.
- [ ] ⚡ **Background refresh indicator** (UX-PERF) — Show a subtle spinner on the GAS widget when SWR is revalidating in the background (`isValidating === true`). Currently users don't know a silent refresh is happening.

---

## 4. 🟠 Watchlist — Currently works but misses key features

`WatchlistWidget.tsx` exists and is wired to the backend, but the experience is minimal.

- [x] ✅ **Watchlist Overview page (POLISH-01)** — Implemented Sprint 10: `/watchlist-overview` with GAS cards, sort modes, sparklines, compare mode (Sprint 19), grade filter (Sprint 22).
- [ ] 🟠 **Auto-create default alert rules on watchlist add** (POLISH-03) — When a symbol is added to watchlist, automatically create two alert rules: GAS crosses below 35 and GAS crosses above 65. Max 1 alert per symbol per 4-hour window.
- [x] ✅ **Mini GAS badge on watchlist items** — Implemented Sprint 22: GAS score + `GradeBadge` per item in `WatchlistWidget.tsx`.
- [ ] 🟡 **Drag-to-reorder watchlist** (todos.md §5) — Allow users to reorder their watchlist items by dragging.

---

## 5. 🟠 News & Sentiment — Several wired but incomplete features

`ArticleList.tsx`, `SentimentChart.tsx`, and `SourceBreakdownTable.tsx` exist but the news feed experience has gaps.

- [ ] 🟠 **Clickable external links on articles** (UX-NEWS-01) — Each article in `ArticleList.tsx` must have a clickable link to the original source URL. Currently articles may have no outbound link.
- [ ] 🟠 **Pagination or infinite scroll** (UX-NEWS-02) — Loading 100+ articles into a single list causes performance issues. Implement 10-per-page pagination with a page selector, or infinite scroll.
- [ ] 🟡 **Sentiment trend arrow** (UX-NEWS-04) — Next to the aggregate sentiment score, show ↑ or ↓ comparing the current 7d average to the prior 7d. Signals momentum direction, not just current level.
- [ ] 🟡 **Filter and sort news** (UX-NEWS-03) — Filter by sentiment (Bullish/Bearish/Neutral), by source/publisher, sort by date or sentiment score.
- [ ] 🟡 **"Why this score?" article tooltip** (todos.md §1) — Each article card should show a 1-line reason for the sentiment score (e.g., "Keyword 'beat expectations' drove positive score").

---

## 6. 🟠 Macro Dashboard — Key missing features on an existing page

The macro page (`/macro`) exists and fetches from `/api/v1/macro`. Several high-value features are missing.

- [x] ✅ **Fed Meeting countdown timer (UX-MACRO-01)** — Implemented Sprint 21: `FomcCountdown` on macro page.
- [ ] 🟠 **Full economic calendar (2-week forward)** (UX-MACRO-02) — List of upcoming macro events (NFP, CPI, FOMC, ECB, GDP) with expected vs prior values. The `/events` endpoint and model already exist in the backend.
- [ ] 🟡 **Macro Regime label + history** (todos.md §9) — Show "Current regime: Goldilocks. Active since Jan 2025 (72 days)" and the previous regime name.
- [ ] 🟡 **Central bank comparison panel** (todos.md §9) — Fed, ECB, BoE rates side-by-side. Particularly relevant for EU users tracking EUR/USD macro divergence.
- [x] ✅ **Yield curve inversion alert banner** — Implemented Sprint 23: auto-displays amber banner when spread < 0.

---

## 7. 🟠 Backtesting — Wired but needs more depth

`/backtesting` exists and is wired to `/api/v1/backtest`. The core engine runs but the UX is minimal.

- [ ] 🟠 **More strategy templates** (UX-BACKTEST-01) — Currently only "Momentum" is implemented. Add at minimum: Mean Reversion (Bollinger Band bounce) and Macro-Responsive (buy when macro score > 60). Each needs a parameter schema and backend implementation.
- [ ] 🟠 **Monthly returns heatmap** (UX-BACKTEST-02) — Calendar-style green/red heatmap by month below the equity curve. Standard feature in every serious backtesting tool.
- [ ] 🟠 **Drawdown chart** (UX-BACKTEST-03) — Separate chart below equity curve showing peak-to-trough losses over time. The max drawdown number alone is not visceral enough.
- [ ] 🟡 **Benchmark comparison toggle** (todos.md §8) — Let users switch the buy-and-hold benchmark line between SPY, QQQ, or BTC.
- [ ] 🟡 **Trade log table** (todos.md §8) — Paginated table of all individual trades: entry date, exit, entry price, exit price, P&L, holding period.
- [ ] 🟡 **Walk-forward validation panel** (todos.md §8) — Dedicated "Walk-Forward" tab showing rolling 6-month performance windows. The single most educational anti-overfitting feature.
- [ ] ⚡ **Export to CSV/PDF** (POLISH-04) — "Export" button on backtesting results. CSV with headers and ISO timestamps. PDF with logo, metrics summary, and standard disclaimer.

---

## 8. 🟠 Tooltips & Education UX — The #1 activation driver for new users

No tooltips currently exist on any of the score cards or widgets.

- [ ] 🟠 **`[i]` icon tooltips on all score widgets** (UX-EDU-01) — Add hover tooltips to: GAS, Technical Score, Macro Score, Sentiment Score, Regime label, VIX, and each timeframe signal tile. Plain-English explanation. This is the single fastest activation improvement possible.
- [ ] 🟠 **"What does this mean?" CTA on GAS widget** (todos.md §2) — Cold users who see 67/100 for the first time need a path to understanding. The `ScoreExplainPanel` exists — ensure there's a visible "?" or "Explain this" button on the GAS card that opens it.
- [ ] 🟡 **Dedicated Learn Hub** (UX-EDU-02) — The `/learn` page exists. Ensure it has a structured hub with categories: GAS Methodology, FinBERT / Sentiment, Technical Consensus, Conflict Detector, Backtesting Pitfalls, Macro 101.
- [ ] 🟡 **Glossary page** (`/learn/glossary`) (todos.md §2) — Searchable A–Z glossary. Link every technical term on the dashboard to its glossary entry.

---

## 9. 🟠 Onboarding — Exists but incomplete

`GuidedTour` component exists in `/components/onboarding/GuidedTour.tsx` and fires on the dashboard.

- [ ] 🟠 **"Start Here" welcome page** (UX-ONBOARD-01) — After email confirmation, redirect new users to `/welcome`. Ask: "What's your goal?" (Learn basics / Improve trade timing / Research stocks). Route to most relevant feature. Do not drop users directly onto the full dashboard.
- [ ] 🟠 **Update tour to cover all current pages** (POLISH-06) — The tour was written before several pages existed. Extend to include: Watchlist Overview, Macro (Fed countdown), Backtesting, Learn Hub, Showcase.
- [ ] 🟠 **Empty watchlist CTA** (todos.md §11) — If watchlist is empty, show: "Add your first stock to track its GAS score" with a pre-filled search box. An empty watchlist is a strong early churn predictor.
- [ ] 🟡 **Progressive disclosure for new users** (todos.md §11) — Hide advanced nav items (Options, Shorts, Insiders, Adv. Sentiment, Fed Policy, Indicators) for users in their first 3 sessions. Show them after the tour is completed or 3 pages are visited.

---

## 10. 🟠 Monetisation & Billing — Free/Pro distinction is currently invisible

The billing page (`/billing`) exists but the upgrade path has no friction-reducing features.

- [ ] 🔴 **Pro gate with lock icon on Pro-only features** (UX-MONETISE-01) — Every Pro-only feature must have a tasteful 🔒 icon with tooltip "Available on Pro — Upgrade for €14.99/mo". Clicking opens the billing modal directly. Currently free users cannot tell what they're missing.
- [ ] 🟠 **Billing page redesign** (UX-MONETISE-02) — The billing page needs: (1) feature comparison table Free vs Pro, (2) monthly/annual toggle showing annual savings as a concrete "Save €48/year" number, (3) "Most Popular" badge on Pro, (4) 1-click Stripe Checkout.
- [ ] 🟠 **Free 7-day trial** (todos.md §6) — No credit card required to start. Card required to continue. SaaS industry data: free trials increase paid conversion 25–40%.
- [ ] 🟡 **Cancellation flow with pause offer** (todos.md §6) — When a user cancels: 1-question "Why are you leaving?" survey + offer to pause for 1 month free. Pause option reduces churn 15–20%.
- [ ] 🟡 **Invoice download** (todos.md §6) — Pro users must be able to download PDF invoices for expense reporting. Missing this causes support tickets from business users.

---

## 11. 🟠 Data Quality & Trust Indicators

Users making time-sensitive decisions need to know they're seeing current data.

- [ ] 🟠 **Data freshness indicators on every section** (UX-TRUST-01) — Every data section (Macro, Sentiment, Technical, GAS) must show "Last updated: 14 min ago" with a coloured dot: green (< 30 min), amber (30–60 min), red (> 60 min). The `SnapshotMeta` component on the dashboard is a good model — extend this pattern everywhere.
- [ ] 🟠 **Graceful degradation messages** (UX-TRUST-02) — When a data source is down (Finnhub, FRED, Yahoo Finance), show a banner: "News sentiment is temporarily unavailable — GAS is computed without the sentiment layer." Currently silent failures show empty UI with no explanation.
- [ ] 🟠 **Data source attribution** (todos.md §13) — Each indicator should link to its source: "VIX from FRED · VIXCLS". Builds trust and protects against accusations of fabricated data.
- [ ] 🟡 **Model confidence intervals** (todos.md §13) — Where the ML model outputs a directional signal, show confidence %: "Bullish — 67% confidence". Low-confidence signals should be visually distinct (lighter colour, "low confidence" badge).

---

## 12. 🟡 Performance & Technical Debt

- [ ] 🟠 **`Cache-Control` headers on GAS, macro, and sentiment endpoints** (UX-PERF-02) — Currently FastAPI returns no `Cache-Control` headers. Adding `max-age=60, stale-while-revalidate=300` on appropriate endpoints reduces backend load and improves LCP.
- [ ] 🟡 **Bundle size audit** (todos.md §4) — Run `next build --profile`. Recharts, Lucide, and large component files likely push the initial JS bundle past 500kB. Code-split each route page with Next.js `dynamic()`. Target < 200kB initial JS.
- [ ] 🟡 **TypeScript strict mode** (todos.md §4) — Enable `"strict": true` in `tsconfig.json`. Replace all `any` types (e.g. `macroData: any` in `page.tsx`) with proper typed DTOs. Prevents production regressions as the codebase grows.
- [ ] 🟡 **Debounce ticker input** (todos.md §4) — Validate `activeSymbol !== tickerInput` before setting state to prevent accidental duplicate API calls on re-render.
- [ ] 🟡 **API rate limit feedback** (todos.md §4) — When Finnhub or FRED hits rate limits, the backend should return a structured `429` with `retry_after`. The frontend should show "Data refreshing — check back in 2 minutes" rather than a generic error.
- [ ] 🟢 **Automated Lighthouse CI** (todos.md §4) — GitHub Action running Lighthouse on every PR. Gate merges on: Performance ≥ 85, Accessibility ≥ 90.

---

## 13. 🟡 Settings & Personalisation

The `/settings` page exists but is minimal.

- [ ] 🟠 **Notification Preferences page** (UX-SETTINGS-01) — Central settings page for: alert thresholds, email frequency, preferred timezone, default ticker, preferred default timeframe. Currently users have no way to configure these.
- [x] ✅ **Default ticker preference** — Implemented Sprint 23: `User.default_symbol` DB column + `PATCH /auth/me` + Settings UI + `seedDefaultOnce()` in SymbolContext.
- [x] ✅ **Risk profile quiz (PLAN-01)** — Implemented Sprint 24: 5-question quiz → 4 profiles, `User.risk_profile` DB column, Settings `RiskProfileSection`.
- [ ] 🟡 **Dark / light mode toggle** (POLISH-05) — Defaults to OS preference. Manual toggle stored in `localStorage`. WCAG AA contrast for both modes.
- [ ] 🟢 **Currency preference (USD/EUR)** (todos.md §14) — Allow users to toggle display currency. EU users seeing "$10,000" initial capital in backtesting creates subtle friction.

---

## 14. 🟡 Legal & Compliance

The `/legal` pages and `ConsentGate` exist. A few compliance gaps remain.

- [ ] 🟠 **Inline risk disclaimer bars on high-liability pages** (UX-LEGAL-01) — The footer disclaimer is too small and too far down. Add a persistent inline disclaimer bar specifically on: `/backtesting`, `/hedge`, and the Technical Signals section. These are the highest legal-risk surfaces.
- [ ] 🟠 **GDPR data export and deletion flow** (CORE-GDPR-01) — "Request data export" and "Delete my account" buttons in Settings. The `/gdpr` endpoint exists in the backend — wire it to the Settings UI.
- [ ] 🟡 **Cookie consent verification** (todos.md §15) — Verify the `ConsentGate` component actually blocks analytics cookies (PostHog, Mixpanel) until consent is given. Analytics must only fire post-consent.

---

## 15. 🟡 Engagement & Retention Features

These directly drive DAU and reduce early churn.

- [ ] 🟠 **Activation funnel tracking** (CORE-ANALYTICS-01) — Instrument these key events: (1) first ticker searched, (2) GAS explain panel opened, (3) first backtest run, (4) macro page visited, (5) watchlist item added. Without this data you cannot improve onboarding. PostHog is already configured.
- [ ] 🟡 **Regime change notification banner** (todos.md §7) — When the Regime flips (Risk-Off → Risk-On), show a highlighted in-app banner with timestamp and a brief explanation.
- [ ] 🟡 **Weekly email digest opt-in** (CORE-EMAIL-02) — Settings toggle for weekly digest: recent blog posts, high-level macro summary, product updates. Resend is configured as the email provider.
- [ ] 🟡 **Cross-asset overview row** (todos.md §7) — Summary row on the dashboard showing GAS scores for SPY, QQQ, GLD, TLT, BTC without switching symbols. Essential for macro traders.
- [ ] 🟡 **Price chart integration** (todos.md §7) — Embed a lightweight TradingView chart or Yahoo Finance iframe on the dashboard for the active ticker. Users currently leave the app to see price action — a major session-killer.
- [ ] 🟢 **Shareable GAS report card** (todos.md §7) — "Share Analysis" button generating a PNG/PDF card of the current GAS, regime, and key conflicts. Shareable content = free distribution.

---

## 16. 🟡 Portfolio Page — Exists but needs depth

`/portfolios` and `portfolio.py` (backend model) exist.

- [x] ✅ **Portfolio-level weighted GAS (P2-PORT-01)** — Implemented Sprint 13: `PortfolioGasBanner` with weighted GAS + symbol breakdown.
- [ ] 🟠 **Rebalancing calculator** (PLAN-03) — Input current holdings + target allocation %. Output: Buy/Sell/Hold per symbol with approximate trade size. CSV export. Link from portfolio page.
- [x] ✅ **Correlation heatmap (IND-COMPOSITE-02)** — Implemented Sprint 19: `CorrelationMatrix` in portfolio page with Pearson heatmap + period picker.
- [ ] 🟡 **DCA simulator** (PLAN-04) — Side-by-side comparison of DCA vs lump-sum for a chosen symbol and date range. CAGR, max drawdown, total invested for both.
- [x] ✅ **Sector breakdown pie (P2-PORT-01)** — Implemented Sprint 24: `SectorPieChart` donut chart in portfolio analytics.

---

## 17. 🟡 Multi-Asset Expansion — Additional symbols

The ML pipeline already supports any yfinance symbol. These are configuration and feature-set additions.

- [ ] 🟠 **Crypto symbols** (ASSET-CRYPTO-01) — Add BTC-USD, ETH-USD to the default symbol list. Add Crypto Fear & Greed Index as a supplementary indicator on crypto pages.
- [ ] 🟡 **Commodity symbols** (ASSET-COMMODITY-01) — Add GC=F (Gold), CL=F (Oil), NG=F (Natural Gas), SI=F (Silver), HG=F (Copper). Add seasonal sin/cos features to commodity ML pipeline.
- [ ] 🟡 **FX pairs** (ASSET-FOREX-01) — Add EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X. Add interest rate differential feature.
- [ ] 🟡 **Expanded ETF coverage** (ASSET-ETF-01) — Add international (EWJ, EWZ, FXI, EEM), factor (VTV, VUG, MTUM, QUAL, USMV), and thematic (ICLN, AIQ, SOXX, XBI) ETFs.
- [ ] 🟡 **Symbol selector grouping** — In the symbol autocomplete dropdown, visually group results by asset class: Equities, ETFs, Crypto, Commodities, Forex.

---

## 18. 🟡 ML Improvements — Post-data-seeding work

These are blocked until the DB is seeded and models are trained (see section 1).

- [x] ✅ **SHAP feature importance panel (ASSET-ML-03)** — Implemented Sprint 24: `ShapPanel` collapsible below `TimeframeGrid` on dashboard. Top-5 SHAP features with bars + plain-English descriptions.
- [x] ✅ **Model drift detection (ASSET-ML-02)** — Implemented Sprint 6: `ModelDriftAlert` model + `drift_service.py` + Drift tab on model-info page + `/admin/ml/drift-alerts`.
- [ ] 🟡 **Bayesian hyperparameter optimisation** (ASSET-ML-02) — Add `optuna` to requirements. Run during training to select optimal hyperparameters per model per timeframe instead of hard-coded defaults.
- [ ] 🟡 **LSTM model implementation** (BUG-006) — The PRD specifies 4 competing models; only 3 are implemented. Add LSTM with attention using PyTorch (already in requirements). Treat as the 4th competitor in the ensemble.

---

## 19. 🟡 Showcase (Digital Products) — `/showcase` exists but is bare

`showcase.py` (backend), `showcase.py` (model), and `/showcase` (frontend) all exist.

- [ ] 🟠 **Product preview modal** (SHOP-V2-01) — Each product card needs a "Preview" button opening an embedded Google Sheets or PDF in a modal. Clearly watermarked "Sample Only".
- [ ] 🟠 **Bundle configuration** (SHOP-V2-03) — Configure at least one bundle (e.g., "Investor Bundle" — Portfolio Tracker + Retirement Calculator). "Save X%" badge. "What's included" expandable section.
- [ ] 🟡 **Star ratings on product cards** (SHOP-V2-04) — Add `rating` and `review_count` fields to the product model. Build star rating display. Seed from beta tester feedback.
- [ ] 🟡 **Coming Soon + "Notify me"** (SHOP-ROADMAP-01) — A "Coming Soon" section for roadmap products (FIRE Calculator, Tax-Loss Harvesting Tracker, Crypto Tax Report, Real Estate Analyzer). "Notify me" button stores user preference.
- [ ] 🟡 **UTM tracking on outbound product links** (todos.md §16) — Append `?utm_source=terminal&utm_medium=showcase&utm_campaign={product_id}` to all "Buy now" redirects.

---

## 20. 🟡 Investment Strategy Planner — Not yet built

A new section of the app. No existing pages or backend routes.

- [ ] 🟠 **Risk profile quiz** (PLAN-01) — 5 questions → Aggressive / Moderate / Conservative / Income profile. Stored on user record. GAS alert thresholds auto-adjust per profile.
- [ ] 🟡 **Asset allocation suggester** (PLAN-02) — Inputs: profile, age, horizon, currency. Output: pie chart + table. Always shows disclaimer.
- [ ] 🟡 **DCA simulator** (PLAN-04) — See Portfolio section above.
- [ ] 🟡 **Sequence of Returns Risk Visualiser** (PLAN-05) — Retirement planning tool. Three scenarios (retiring before 2000/2008/2020 crash). Portfolio survival rate shown.
- [ ] 🟢 **Bond Ladder Builder** (PLAN-06) — Uses FRED Treasury yield data. Table + bar chart per rung. Links to Macro Dashboard yield curve.

---

## 21. 🟢 Lifestyle Finance Content — Not yet built

- [ ] 🟡 **`/lifestyle` hub page** (NOMAD-01) — Four content pillars: Tax Residency, Legal Structures, International Banking, Estate & Pension. "Lifestyle" added to nav under Learn.
- [ ] 🟡 **Interactive tax residency comparison table** (NOMAD-02) — 10 countries with filter/sort. FATCA callout for US citizens.
- [ ] 🟡 **Legal entity type comparison** (NOMAD-03) — 9 structures with interactive "Which fits me?" filter.
- [ ] 🟢 **International banking & investing guide** (NOMAD-04) — Practical checklist format with expandable detail sections.

---

## 22. 🟢 B2B2C Landlord Architecture — Phase 3

This is a significant architectural addition. Do not start until the B2C product is stable and generating revenue.

- [ ] 🟢 **Tenant registration + client invitation** (B2B-TENANT-01) — `tenants` table, `/advisors/register` flow, invitation tokens.
- [ ] 🟢 **Tenant branding / white-label** (B2B-TENANT-02) — Subdomain-based logo + accent colour theming.
- [ ] 🟢 **Tenant data isolation** (B2B-ISOLATION-01) — `TenantContext` FastAPI dependency. Cross-tenant access denied integration test.
- [ ] 🟢 **AI Narrator configuration** (B2B-NARRATOR-01) — Jinja2 prompt template with tenant config injection. Hard-coded mandatory disclaimer.
- [ ] 🟢 **Custom GAS weights per advisor** (B2B-GAS-WEIGHTS-01) — Three sliders (Technical/Macro/Sentiment). Preset profiles. Weights must sum to 1.0.
- [ ] 🟢 **Compliance audit log** (B2B-COMPLIANCE-01) — Append-only `compliance_audit_logs` table. Paginated CSV export endpoint.
- [ ] 🟢 **Per-seat billing** (B2B-BILLING-01) — Stripe metered billing for advisor tiers (Starter ≤10, Growth ≤50, Enterprise unlimited).

---

## 23. 🟢 Community & Social

- [ ] 🟡 **Community entry point** (CORE-COMM-01) — The `/community` page exists in the nav. Ensure it links clearly to Discord/Reddit or an in-app channel. Currently unclear what's at this route.
- [ ] 🟢 **Public strategy leaderboard** (todos.md §12) — Sorted leaderboard of public strategies by Sharpe ratio with weekly/monthly reset.
- [ ] 🟢 **"Bull vs Bear" weekly poll** (todos.md §12) — Simple in-app Monday poll: "Are you bullish or bearish on SPY this week?" Creates weekly habit loop.

---

## 24. 🟢 Admin & Operations

- [ ] 🟠 **User Lifecycle Dashboard** (todos.md §17) — `/admin/analytics` should show DAU/WAU/MAU trend, free vs Pro user ratio, top tickers, feature adoption, and funnel conversion. The `/admin/analytics` route exists — needs real metrics wired to it.
- [ ] 🟡 **Churn early warning** (todos.md §17) — Flag users in admin dashboard who have not visited in 7 days. Trigger automated re-engagement email.
- [ ] 🟡 **A/B experiment framework** (CORE-EXPERIMENT-01) — `/admin/experiments` exists. Ensure it supports feature flags and % rollouts. First experiment: Onboarding flow variants.
- [ ] 🟡 **Error rate monitoring** (todos.md §17) — Sentry DSN is configured in `.env` but empty. Set up Sentry to capture frontend JS errors. Alert at error rate > 1%.

---

## Appendix: Quick Reference — Correct API Endpoint URLs

These were confirmed correct during the bug-fix session. Use these, not the URLs in older docs.

| Action | Method | URL |
|---|---|---|
| Fetch OHLCV | POST | `/api/v1/data/fetch/ohlcv` |
| Fetch Macro | POST | `/api/v1/data/fetch/macro` |
| Fetch News | POST | `/api/v1/data/fetch/news?lookback_days=7` |
| Train symbol | POST | `/api/v1/technical/train/{symbol}` |
| Get technical consensus | GET | `/api/v1/technical/{symbol}/latest` |
| Trigger GAS precompute (all) | POST | `/api/v1/admin/gas/precompute` |
| Get GAS snapshot | GET | `/api/v1/admin/gas/snapshots/{symbol}` |
| System health | GET | `/api/v1/health` |

---

*todos-v3.md — Created 2026-03-20. Do NOT delete todos.md (v2) — it remains the full UX backlog and is preserved as historical reference.*
