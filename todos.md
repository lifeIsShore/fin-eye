# Fin-Eye UX & Feature Improvements
> **Authored by:** Senior Developer + Product Owner perspective  
> **Goal:** Maximize user retention, activation, conversion, and long-term loyalty  
> **Legend:** 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Nice-to-have · ⚡ Quick-win

---

## TODO #2 — AI Portfolio Allocation & Autonomous Trading Bot
> **Status:** Planned · **Depends on:** Signal Grade system (implemented in `gas_precompute.py`) + stable model quality  
> **Vision:** Use the A+→F signal grade as the decision layer for AI-driven portfolio weighting and, ultimately, a fully autonomous trading execution bot.

### Phase 2A — Grade-Based Portfolio Construction (UI + API)
- [ ] 🔴 **Grade filter on watchlist**: Let users filter their watchlist by signal grade. "Show me only A+ and A signals right now." This is the core portfolio construction UI.
- [ ] 🔴 **Portfolio builder page** (`/portfolio/build`): A page where users select a universe of symbols, set a minimum grade threshold (e.g., "only A/B"), and fin-eye proposes an equal-weighted or GAS-weighted allocation.
- [ ] 🟠 **Grade badge on every ticker card**: Everywhere a symbol appears in the UI (watchlist, dashboard, cross-asset view), show the grade badge with color coding:
  - A+ / A → emerald
  - B       → sky
  - C       → amber
  - D / F   → rose
- [ ] 🟠 **Grade history sparkline**: Show how the grade has changed over the last 7 days for each symbol. A ticker that was F last week and is now A is more interesting than one that has been A all along.
- [ ] 🟠 **Grade explanation panel**: When a user clicks a grade, show the exact breakdown — which factors contributed, what the reasons were, and what would need to change to improve the grade.
- [ ] 🟡 **Grade leaderboard**: A ranked list of all tracked symbols sorted by grade descending, updated every 15 minutes. "Today's top signals" — extremely high engagement feature.

### Phase 2B — AI Allocation Engine
> The AI reads the current signal grades across a portfolio and proposes allocation weights.
- [ ] 🔴 **Allocation API endpoint** (`POST /api/v1/portfolio/allocate`): Takes a list of symbols + total capital, returns suggested position sizes based on grade and GAS score. Initial algorithm: grade-weighted with risk caps.
  - A+ → up to 20% position
  - A  → up to 15%
  - B  → up to 10%
  - C  → up to 5% (monitoring only)
  - D/F → 0% (no allocation)
- [ ] 🔴 **AI allocation explainer**: After generating weights, call Claude/DeepSeek R1 (via local Ollama or Claude API) to write a 3-5 sentence plain-English explanation of why the portfolio is weighted this way. "AAPL gets 18% because its A+ grade reflects strong technical alignment with macro support. BTC-USD gets 8% as a B-grade diversifier..."
- [ ] 🟠 **Rebalancing trigger**: When any symbol's grade changes by 2+ steps (e.g., A → C), fire an alert: "Rebalancing recommended — AAPL dropped from A to C. Suggested action: reduce position by 50%."
- [ ] 🟠 **Max drawdown guard**: The allocation engine must respect a portfolio-level max drawdown setting. If estimated portfolio drawdown (sum of individual MaxDD × weight) exceeds the user's threshold, reduce all positions proportionally.
- [ ] 🟡 **Backtesting the grade strategy**: Add a backtest mode where the system simulates grade-based allocation over historical GAS snapshots. Shows what equity curve would look like if you always held A/B signals and exited D/F signals.
- [ ] 🟡 **Multi-asset class support**: Extend the grade system beyond equities to cover crypto (BTC-USD, ETH-USD), ETFs (SPY, QQQ, GLD, TLT), and eventually forex pairs. Each asset class may need different grade thresholds.

### Phase 2C — Autonomous Trading Bot
> **⚠️ IMPORTANT PREREQUISITES before building this:**
> - At least 90 days of live grade tracking data to validate grade → return correlation
> - A+ grade precision rate ≥ 65% on out-of-sample data (not backtested)
> - Full audit log of every decision (regulatory requirement in EU)
> - User must explicitly opt in with risk acknowledgement
> - Paper trading mode must be validated for at least 30 days before live execution

- [ ] 🔴 **Paper trading mode** (`/bot/paper`): Execute simulated trades based on grade signals. Track hypothetical P&L, drawdown, win rate. This is the gate before live trading.
- [ ] 🔴 **Broker integration layer**: Connect to a broker API (Interactive Brokers, Alpaca, or eToro for EU users) via OAuth. Store credentials encrypted, never in plaintext.
  - Alpaca: US equities + crypto, REST API, free paper trading
  - Interactive Brokers: EU-compliant, full asset class coverage
  - eToro: EU retail focus, good for fin-eye's target demographic
- [ ] 🔴 **Bot decision engine** (`/api/v1/bot/evaluate`): Runs every 15 minutes (aligned with GAS precompute). For each symbol in the bot's universe:
  1. Fetch current grade from GAS snapshot
  2. Check current position in broker
  3. Apply decision rules:
     - Grade A+ / A + not yet in position → BUY (size per allocation engine)
     - Grade D / F + in position → SELL (close position)
     - Grade C → hold existing, no new entry
  4. Log decision with full reasoning
  5. Execute via broker API if in live mode
- [ ] 🔴 **Full audit log** (`/admin/bot/log`): Every decision — evaluate, entry, exit, hold, skip — must be logged with: timestamp, symbol, grade, GAS score, component scores, action taken, size, price. Required for EU regulatory compliance and for debugging.
- [ ] 🟠 **Kill switch**: A single button in the UI and a `POST /api/v1/bot/halt` endpoint that immediately stops all bot activity and optionally closes all open positions. Must work even if the scheduler is down (direct DB flag).
- [ ] 🟠 **Position sizing rules**: 
  - Never more than 20% in any single symbol
  - Never more than 40% in any single sector
  - Maximum total deployed capital configurable (e.g., "deploy max 60% of portfolio")
  - Remaining cash never deployed below grade B
- [ ] 🟠 **Risk management circuit breakers**:
  - Daily loss limit: if portfolio drops > X% in one day, bot pauses for 24h
  - Drawdown limit: if portfolio drops > max_drawdown setting from peak, close all positions
  - Grade flip speed: if A+ → F happens in < 2 cycles, wait for confirmation before acting
- [ ] 🟡 **Notification system for bot actions**: Every trade the bot executes triggers an email + in-app notification: "BOT: Bought 5 AAPL @ $178.40 — Grade A+, GAS 82, Reason: Strong Tailwind with full component alignment."
- [ ] 🟢 **Strategy variants**: Allow users to configure bot personality:
  - Aggressive: trade C and above, higher position sizes
  - Balanced: trade B and above (default)
  - Conservative: trade A and above only, smaller sizes
  - Custom: user-defined grade threshold and position rules

### Phase 2D — Infrastructure for Autonomous Trading
- [ ] 🟠 **Grade persistence in DB**: Add `signal_grade`, `signal_grade_score`, `signal_tradeable` columns to the `gas_snapshots` table. Currently these fields are computed and cached in Redis but not persisted to DB. Needed for grade history tracking.
  - Migration: `alembic revision --autogenerate -m "add signal grade to gas snapshots"`
- [ ] 🟠 **Grade history table** (`signal_grade_history`): A separate table logging every grade change per symbol (symbol, timestamp, old_grade, new_grade, gas_score). Powers the grade sparkline and the backtest engine.
- [ ] 🟠 **Bot state table** (`bot_positions`): Tracks what the bot currently holds (symbol, entry_price, entry_grade, entry_gas, size, opened_at). Independent from the broker — the broker is the source of truth for execution, but this is the bot's internal view.
- [ ] 🟡 **WebSocket for live bot updates**: Push grade changes and bot actions to the frontend in real time via WebSocket. Users can watch the bot "think" live.

### Grade System Design Reference (already implemented)
The `compute_signal_grade()` function in `gas_precompute.py` is the authoritative grade source.

| Component | Max Points | Description |
|-----------|-----------|-------------|
| GAS score | 40 | Primary composite signal (GAS 30→100 mapped to 0→40) |
| Component alignment | 30 | Do technical + sentiment + macro all agree? |
| Technical model Sharpe | 20 | Best timeframe model quality |
| Signal conviction | 10 | How far from neutral (50)? |

| Grade | Score | Tradeable | Description |
|-------|-------|-----------|-------------|
| A+ | 88-100 | ✅ Yes | Exceptional — all factors strongly aligned |
| A  | 78-87  | ✅ Yes | Strong — reliable signal |
| B  | 65-77  | ✅ Yes | Good — minor disagreements |
| C  | 50-64  | ❌ Monitor only | Mixed — use with caution |
| D  | 35-49  | ❌ No | Weak — avoid new positions |
| F  | 0-34   | ❌ No | Do not use |

---

## 1. News Feed Enhancements
- [ ] 🟠 **External Links**: Add clickable URL links to news articles so users can read the full story on the original source.
- [ ] 🟠 **Pagination/Infinite Scroll**: Implement pagination (e.g., 10 items per page with a selector) or infinite scrolling to prevent performance issues when loading large numbers of articles.
- [ ] 🟡 **Filtering & Sorting**:
  - Filter by sentiment (Bullish, Bearish, Neutral).
  - Filter by news source/publisher.
  - Sort by date or by highest/lowest sentiment score.
- [ ] 🟡 **Sentiment Trend Arrow**: Next to the aggregate score, show a directional arrow (↑ improving vs ↓ deteriorating) comparing current 7d average to the prior 7d to signal momentum, not just the level.
- [ ] 🟢 **"Why this score?" mini-tooltip on articles**: Each article card should show a 1-line reason why FinBERT scored it the way it did (e.g., "Keyword: 'beat expectations' drove positive score").

---

## 2. Educational & Documentation UX (The "Fin-Eye" Mission)
- [ ] 🟠 **Tooltips & Hover States**: Add `[i]` icons next to GAS, Technical Score, Macro Score, Sentiment Score, Regime, VIX, and each timeframe signal. Hovering pops a concise, plain-English explanation. This is the #1 activation driver for new users.
- [ ] 🟠 **Dedicated Documentation / "Learn" Hub**: Build a knowledge base explaining GAS methodology, FinBERT, Technical Consensus, and how to read the Conflict Detector.
- [ ] 🟠 **Interactive Onboarding/Tour**: The GuidedTour component exists — ensure it fires automatically for first-time users (check `has_completed_tour` flag). Add a "What does this mean?" CTA on the GAS widget for cold users.
- [ ] 🟡 **Score Change Explainer**: When GAS changes by more than 5 points between two refreshes, surface a brief "What changed?" banner explaining the shift (e.g., "Macro score dropped 8 pts — VIX spiked to 22").
- [ ] 🟡 **Glossary Page** (`/learn/glossary`): Searchable A–Z glossary. Link every technical term on the dashboard to its glossary entry. Reduces support tickets and keeps users on-site.

---

## 3. General UI/UX Polish
- [ ] 🔴 **Skeleton Loaders**: Replace the `animate-pulse` blank divs with layout-accurate skeleton screens that mirror the real UI shape. Perceived load time is a key retention lever — Bloomberg-grade tools feel instant.
- [ ] 🔴 **Toast Notification System**: Implement a global toast/snackbar system (top-right). Use it for: save success, API errors, GAS alerts firing, strategy saved, copy-to-clipboard. Currently failures are silent or show raw error strings.
- [ ] 🟠 **Empty States**: Every data section (Sentiment, Macro, Backtesting, News) needs a designed empty state with an icon, message, and a clear next-action CTA. "No data" text alone causes abandonment.
- [ ] 🟠 **Responsive Design & Mobile Optimization**: The NAV_ITEMS list has 19 items — on mobile this overflows catastrophically. Implement a hamburger/drawer nav for screens below `md`. The dashboard grid also needs a single-column reflow tested on 375px width.
- [ ] 🟠 **Color Coding & Badges**: Standardize semantic colors globally. Bullish = emerald-400, Bearish = rose-400, Neutral = amber-400, Loading = sky-400. Ensure badges on StrategyCard, TimeframeGrid, RegimeWidget all follow the same palette. Currently mixed.
- [ ] 🟡 **Dark Mode Contrast Audit**: Run a WCAG AA contrast check. Several elements (text-slate-500 on bg-slate-900, small labels) fail 4.5:1 contrast ratio.
- [ ] 🟡 **Page Transition Animations**: Add subtle fade/slide transitions between pages using Framer Motion.
- [ ] 🟢 **Keyboard Navigation**: All interactive elements accessible via keyboard Tab + Enter.

---

## 4. Performance & Technical Debt
- [ ] 🔴 **SWR Error Boundary**: Wrap data-dependent UI sections in error boundaries.
- [ ] 🔴 **API Response Caching Headers**: Ensure FastAPI responses for `/gas/snapshot`, `/macro/latest`, and `/sentiment` include proper `Cache-Control` headers.
- [ ] 🟠 **Bundle Size Audit**: Run `next build --profile` and analyze the bundle. Target < 200kB initial JS.
- [ ] 🟠 **Redis Cache Warming**: On startup/deploy, pre-warm Redis cache for the top 20 most-watched symbols.
- [ ] 🟠 **Background Data Refresh Indicator**: Add subtle spinning indicator on GAS widget when SWR is revalidating.
- [ ] 🟡 **Debounce Ticker Input**: Validate `activeSymbol !== tickerInput` before setting state.
- [ ] 🟡 **API Rate Limit Feedback**: Return structured `429` with `retry_after` field when FRED/Finnhub rate limits are hit.
- [ ] 🟡 **Service Worker / PWA**: Add basic Service Worker for offline caching of last-seen dashboard state.
- [ ] 🟡 **Image Optimization**: Use Next.js `<Image>` with `priority` on above-the-fold images.
- [ ] 🟢 **TypeScript Strict Mode**: Enable `"strict": true` in `tsconfig.json`.
- [ ] 🟢 **Automated Lighthouse CI**: Gate merges on Performance ≥ 85, Accessibility ≥ 90.

---

## 5. Activation & User Retention (Product Growth)
- [ ] 🔴 **"Aha Moment" Optimization**: Add GAS History sparkline (last 7 days) directly on the dashboard.
- [ ] 🔴 **Email Alert Engine**: Threshold-based alerts (e.g., "Notify me when TSLA GAS crosses above 65").
- [ ] 🟠 **Daily/Weekly Digest Email**: Auto-generate weekly email summarizing top 5 movers.
- [ ] 🟠 **Watchlist Improvements**: Drag-and-drop reorder, mini GAS badge, DB persistence, grouping.
- [ ] 🟠 **"What Changed Today" Dashboard Widget**: Feed showing GAS movements for watchlist items.
- [ ] 🟡 **Social Proof & Trust Signals**: User count, testimonials on landing/billing page.
- [ ] 🟡 **Streak & Engagement Gamification**: Learning streak, badges for tour completion.
- [ ] 🟡 **NPS Survey (In-App)**: After 7th session or 30 days.
- [ ] 🟢 **Referral Program**: "Invite a friend, get 1 month free."

---

## 6. Monetization & Conversion Optimization
- [ ] 🔴 **Upgrade Gate UX**: Lock icon on Pro-only features with tooltip and direct billing modal.
- [ ] 🔴 **Billing Page Redesign** (`/billing`): Feature comparison table, monthly/annual toggle, Stripe Checkout.
- [ ] 🟠 **Free Trial for Pro**: 7-day free trial, no credit card on sign-up.
- [ ] 🟠 **Annual Plan Incentive**: "Save €48/year" banner.
- [ ] 🟡 **Cancellation Flow**: Survey + 1-month pause offer.
- [ ] 🟡 **Invoice & Receipt Download**: PDF invoices for Pro users.

---

## 7. Dashboard Intelligence Upgrades
- [ ] 🟠 **GAS History Chart (7-day)**: Mini line chart of GAS score over past 7 days.
- [ ] 🟠 **Regime Change Notification**: Highlighted banner when Regime flips.
- [ ] 🟠 **Cross-Asset Dashboard**: Summary row showing GAS for SPY, QQQ, GLD, TLT, BTC.
- [ ] 🟡 **Price Chart Integration**: Lightweight TradingView chart embedded on dashboard.
- [ ] 🟡 **Technical Consensus Explanation Expansion**: "Top Drivers" sub-section per timeframe signal.
- [ ] 🟢 **Printable/Shareable Report**: "Share Analysis" button generating PNG/PDF card.

---

## 8. Backtesting UX Improvements
- [ ] 🟠 **More Strategy Templates**: Mean Reversion, Macro-Responsive, Trend Following.
- [ ] 🟠 **Monthly Returns Heatmap**: Calendar-style heatmap (green/red by month).
- [ ] 🟠 **Drawdown Chart**: Peak-to-trough losses over time below equity curve.
- [ ] 🟡 **Benchmark Comparison Toggle**: Compare against SPY, QQQ, or BTC.
- [ ] 🟡 **Trade Log Table**: Paginated table of all individual trades.
- [ ] 🟡 **Walk-Forward Validation Panel**: Rolling 6-month performance windows tab.
- [ ] 🟢 **Parameter Optimization Grid**: Heatmap of Sharpe ratios across parameter range.

---

## 9. Macro Dashboard Improvements
- [ ] 🟠 **Fed Meeting Countdown**: Countdown timer to next FOMC decision.
- [ ] 🟠 **Economic Calendar Integration**: Full 2-week macro events calendar with expected vs prior values.
- [ ] 🟡 **Macro Regime Label with History**: "Regime since: Jan 2025 (72 days)".
- [ ] 🟡 **Central Bank Comparison Panel**: Fed, ECB, BoE rates side-by-side.
- [ ] 🟢 **Yield Curve Inversion Alert Banner**: Auto-display when 2Y–10Y spread goes negative.

---

## 10. Navigation & Information Architecture
- [ ] 🔴 **Nav Overflow Fix**: Grouped dropdown nav with categories.
- [ ] 🟠 **Search Bar (Global)**: CMD+K command palette.
- [ ] 🟠 **Breadcrumbs on Inner Pages**: "Dashboard > Backtesting" navigation.
- [ ] 🟡 **Active Page Highlighting in Nav**: More visually distinct than current `bg-slate-800`.
- [ ] 🟡 **"New" / "Beta" Badges on Nav Items**: Tag newer features.

---

## 11. Onboarding & First-Time Experience
- [ ] 🔴 **Activation Funnel Tracking**: Instrument key activation events with Mixpanel or PostHog.
- [ ] 🔴 **Progressive Disclosure**: Simplified mode for first 3 sessions.
- [ ] 🟠 **"Start Here" Flow for New Users**: `/welcome` page with goal selection.
- [ ] 🟠 **Empty Watchlist CTA**: Friendly prompt with pre-filled search.
- [ ] 🟡 **Feature Discovery Tooltips**: Contextual tooltips on days 3, 7, 14.

---

## 12. Community & Social Features
- [ ] 🟡 **Public Strategy Leaderboard**: Sorted by Sharpe ratio with weekly reset.
- [ ] 🟡 **Discussion Threads per Ticker**: Brief text comments on ticker analysis pages.
- [ ] 🟢 **"Bull vs Bear" Weekly Poll**: Monday SPY sentiment poll.
- [ ] 🟢 **User-Submitted Blog Post Drafts**: Pro users submit drafts for review.

---

## 13. Data Quality & Trust
- [ ] 🔴 **Data Freshness Indicators on Every Data Section**: Colored dot with "Last updated: 14 min ago".
- [ ] 🟠 **Data Source Attribution**: Link each indicator to its source (FRED, Finnhub, etc.).
- [ ] 🟠 **Graceful Degradation Messages**: Banner when a data source is down.
- [ ] 🟡 **Model Confidence Intervals**: Show confidence % alongside directional signals.

---

## 14. Settings & Personalization
- [ ] 🟠 **Notification Preferences Page**: Central settings for alerts, email frequency, timezone.
- [ ] 🟡 **Default Ticker**: User-configurable default symbol on dashboard open.
- [ ] 🟡 **Currency Preference**: USD/EUR toggle.
- [ ] 🟢 **Compact / Expanded View Toggle**: Data density setting.

---

## 15. Legal & Trust Compliance
- [ ] 🔴 **Cookie Consent Banner**: Verify ConsentGate blocks analytics until consent.
- [ ] 🟠 **Risk Disclaimer on Every Data-Driven Page**: Inline disclaimer on Backtesting, Hedge, Signals.
- [ ] 🟡 **Data Deletion Flow**: "Delete My Account" with 30-day erasure confirmation email.

---

## 16. Fin-Eye Showcase / Marketplace (Pro Tools)
- [ ] 🟠 **Product Cards with Preview Screenshots**: Title, description, price, category badge, thumbnail.
- [ ] 🟠 **UTM Tracking on External Product Links**: `?utm_source=terminal&utm_medium=showcase`.
- [ ] 🟡 **"Featured" Product Rotation**: Admin flag for highlighted hero row.
- [ ] 🟡 **Click Analytics on Showcase**: Track which products are viewed and clicked most.

---

## 17. Admin & Operations
- [ ] 🟠 **User Lifecycle Dashboard** (`/admin/analytics`): DAU/WAU/MAU, funnel conversion.
- [ ] 🟠 **Churn Early Warning**: Flag users not visited in 7 days, trigger re-engagement email.
- [ ] 🟡 **A/B Experiment Framework**: Feature flags and percentage rollouts.
- [ ] 🟡 **Error Rate Monitoring**: Sentry integration, alert on error rate > 1%.

---

## 18. Future / Roadmap Items (Phase 2+)
- [ ] 🟢 **Mobile App (React Native)**: Push notifications for regime changes and grade changes.
- [ ] 🟢 **Portfolio-Level GAS**: Aggregate GAS across portfolio weighted by position size.
- [ ] 🟢 **Earnings Calendar with Sentiment Pre-loading**: 30-day sentiment trend before earnings.
- [ ] 🟢 **API Tier for Developers**: GAS scores via personal API key (rate-limited).
- [ ] 🟢 **White-Label Inquiry Form**: "For Institutions" CTA on landing page.

---

*Last updated: March 2026 · Version 2.1 — Added TODO #2 (AI Portfolio + Autonomous Trading Bot)*
