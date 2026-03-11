# Fin-Eye UX & Feature Improvements
> **Authored by:** Senior Developer + Product Owner perspective  
> **Goal:** Maximize user retention, activation, conversion, and long-term loyalty  
> **Legend:** 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Nice-to-have · ⚡ Quick-win

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
- [ ] 🟡 **Dark Mode Contrast Audit**: Run a WCAG AA contrast check. Several elements (text-slate-500 on bg-slate-900, small labels) fail 4.5:1 contrast ratio. This affects readability for users with visual impairments and is an SEO/legal risk.
- [ ] 🟡 **Page Transition Animations**: Add subtle fade/slide transitions between pages using Framer Motion. Creates a polished, app-like feel that increases perceived quality and trust — critical for a paid finance tool.
- [ ] 🟢 **Keyboard Navigation**: All interactive elements (score cards, tooltips, dropdowns) should be accessible via keyboard Tab + Enter. Required for accessibility compliance.

---

## 4. Performance & Technical Debt
- [ ] 🔴 **SWR Error Boundary**: Wrap data-dependent UI sections in error boundaries. Currently if `fetchGasSnapshot` throws, the entire Dashboard page crashes. Use `ErrorBoundary` + fallback UI per section.
- [ ] 🔴 **API Response Caching Headers**: Ensure FastAPI responses for `/gas/snapshot`, `/macro/latest`, and `/sentiment` include proper `Cache-Control` headers so the browser/CDN layer caches aggressively. Reduces backend load and improves LCP.
- [ ] 🟠 **Bundle Size Audit**: Run `next build --profile` and analyze the bundle. Recharts, Lucide, and large component files likely inflate the initial JS bundle past 500kB. Code-split each route page using Next.js dynamic imports. Target < 200kB initial JS.
- [ ] 🟠 **Redis Cache Warming**: On startup/deploy, pre-warm Redis cache for the top 20 most-watched symbols (AAPL, MSFT, TSLA, etc.) so first users see sub-200ms responses, not cold cache misses.
- [ ] 🟠 **Background Data Refresh Indicator**: The `SnapshotMeta` component shows staleness — but users don't know if a silent refresh is happening. Add a subtle spinning indicator on the GAS widget when SWR is revalidating in the background (`isValidating`).
- [ ] 🟡 **Debounce Ticker Input**: The ticker input currently triggers a symbol change on form submit, which is correct. But ensure no accidental extra API calls are fired on re-render. Validate `activeSymbol !== tickerInput` before setting state.
- [ ] 🟡 **API Rate Limit Feedback**: When Finnhub or FRED hits rate limits, the backend should return a structured `429` with a `retry_after` field. The frontend should display "Data refreshing — check back in 2 minutes" rather than a generic error.
- [ ] 🟡 **Service Worker / PWA**: Add a basic Service Worker for offline caching of the last-seen dashboard state. Fin-Eye users are traders — they check at odd hours with spotty connections. A cached "last known state" is better than a blank screen.
- [ ] 🟡 **Image Optimization**: Ensure all images (blog thumbnails, showcase product images) use Next.js `<Image>` with `priority` on above-the-fold images and `lazy` on the rest. Add proper `width`/`height` to avoid layout shift (CLS).
- [ ] 🟢 **TypeScript Strict Mode**: Several API response types use `any` (e.g., `macroData: any` in `page.tsx`). Enable `"strict": true` in `tsconfig.json` and replace `any` with proper typed DTOs. Prevents production regressions.
- [ ] 🟢 **Automated Lighthouse CI**: Add a GitHub Action that runs Lighthouse on every PR. Gate merges on Performance ≥ 85, Accessibility ≥ 90. Prevents regression as the product grows.

---

## 5. Activation & User Retention (Product Growth)
- [ ] 🔴 **"Aha Moment" Optimization**: The fastest path to the Aha Moment is a user seeing GAS change and understanding why. Add a **"GAS History" sparkline** (last 7 days) directly on the dashboard so users see movement, not just a static score. Movement = engagement.
- [ ] 🔴 **Email Alert Engine**: Users should be able to set threshold-based alerts (e.g., "Notify me when TSLA GAS crosses above 65" or "Alert if Macro Score drops below 40"). This is the #1 retention tool for active traders. Integrate with SendGrid.
- [ ] 🟠 **Daily/Weekly Digest Email**: Auto-generate a weekly email summarizing the top 5 movers in a user's watchlist, macro changes, and a "GAS Leaderboard" (most improved stocks). This passive touchpoint drives re-engagement without requiring users to open the app.
- [ ] 🟠 **Watchlist Improvements**:
  - Add the ability to reorder watchlist items (drag-and-drop).
  - Show mini GAS score badge next to each ticker in the watchlist (not just the name).
  - Persist watchlist in the DB (currently unclear if it's local-only).
  - Allow grouping tickers into custom portfolios/categories.
- [ ] 🟠 **"What Changed Today" Dashboard Widget**: A feed-style panel showing: "AAPL GAS: 62 → 71 ↑" and "TSLA Regime: Risk-Off → Risk-On" for all watchlist items. This gives power users a reason to return every day.
- [ ] 🟡 **Social Proof & Trust Signals**: Add a subtle counter near the signup CTA: "Join 1,200+ investors using Fin-Eye" (update dynamically). Add 2–3 user testimonials on the landing/billing page. Trust signals directly increase free-to-paid conversion.
- [ ] 🟡 **Streak & Engagement Gamification**: Show users a "learning streak" (days in a row they've visited). Small gamification loops (streaks, badges for completing the tour, first backtest, etc.) dramatically improve early-stage retention in EdFintech products.
- [ ] 🟡 **NPS Survey (In-App)**: After a user's 7th session or 30 days, show a 1-question in-app NPS survey: "How likely are you to recommend Fin-Eye?" Collect verbatim feedback. NPS above 40 is the growth threshold for referral loops.
- [ ] 🟢 **Referral Program**: "Invite a friend, get 1 month free." Financial-education tools have high organic referral potential among students and trading communities. Build a simple referral tracking system with unique invite links.

---

## 6. Monetization & Conversion Optimization
- [ ] 🔴 **Upgrade Gate UX**: Currently the free/pro distinction is not visible in the UI. Every Pro-only feature should have a tasteful "lock" icon with a tooltip "Available on Pro — Upgrade for €14.99/mo". Clicking opens the billing modal directly. Friction-free upsell.
- [ ] 🔴 **Billing Page Redesign** (`/billing`): The billing page should show: (1) a feature comparison table (Free vs Pro), (2) monthly vs annual toggle with annual savings prominently displayed, (3) a "Most Popular" badge on Pro, (4) 1-click upgrade via Stripe Checkout. Use loss-aversion copy: "You're missing real-time macro data."
- [ ] 🟠 **Free Trial for Pro**: Offer a 7-day free trial on the Pro plan (no credit card required on sign-up, card required to activate). This removes the biggest conversion barrier. SaaS industry data: free trials increase paid conversion by 25–40%.
- [ ] 🟠 **Annual Plan Incentive**: Add a banner on the billing page: "Lock in €10.99/mo — save 27% with annual billing." Display the savings as a concrete number (e.g., "Save €48/year") rather than a percentage.
- [ ] 🟡 **Cancellation Flow**: When a user cancels, implement a cancellation survey (1 question: "Why are you leaving?") and an offer to pause for 1 month for free. Pause option reduces churn by 15–20% in SaaS benchmarks.
- [ ] 🟡 **Invoice & Receipt Download**: Allow Pro users to download PDF invoices from the `/billing` page for expense reporting. Missing this causes support tickets and churn from business users.

---

## 7. Dashboard Intelligence Upgrades
- [ ] 🟠 **GAS History Chart (7-day)**: Show a mini line chart of the GAS score over the past 7 days on the main dashboard card. A single static number tells users nothing about trend. Trend = insight = stickiness.
- [ ] 🟠 **Regime Change Notification**: When the Regime flips (e.g., Risk-Off → Risk-On), surface a highlighted "Regime Changed" banner with a timestamp and a brief explanation. This is a high-value signal for traders.
- [ ] 🟠 **Cross-Asset Dashboard**: Add a summary row (e.g., "Market Overview") showing GAS scores for SPY, QQQ, GLD, TLT, and BTC without requiring users to switch tickers. Gives macro traders a quick portfolio-level read.
- [ ] 🟡 **Price Chart Integration**: Embed a lightweight TradingView chart (or use Yahoo Finance iframe) directly on the dashboard for the active ticker. Users currently have to leave the app to see price action — this is a major session-killer.
- [ ] 🟡 **Technical Consensus Explanation Expansion**: The `ScoreExplainPanel` for Technical shows timeframe signals but doesn't explain which ML model "won" for each timeframe or what features drove the signal. Add a collapsible "Top Drivers" sub-section (e.g., "RSI oversold bounce + price crossed SMA50").
- [ ] 🟢 **Printable/Shareable Report**: A "Share Analysis" button that generates a clean, shareable PNG or PDF card of the current GAS, regime, and key conflicts for a given ticker. Shareable content = free distribution. Traders love sharing setups.

---

## 8. Backtesting UX Improvements
- [ ] 🟠 **More Strategy Templates**: Currently only "Momentum (SMA Crossover + RSI)" is available. Add at minimum: (1) Mean Reversion (Bollinger Band bounce), (2) Macro-Responsive (buy when macro score > 60), (3) Trend Following (EMA cross). More templates = more "Aha" moments for diverse user types.
- [ ] 🟠 **Monthly Returns Heatmap**: Add a calendar-style heatmap (green/red by month) showing monthly returns. This is a standard feature in every serious backtesting tool and immediately communicates seasonality and risk.
- [ ] 🟠 **Drawdown Chart**: Add a separate drawdown chart below the equity curve showing peak-to-trough losses over time. Currently only max drawdown as a number is shown — visual drawdown is far more visceral and educational.
- [ ] 🟡 **Benchmark Comparison Toggle**: Let users switch the benchmark line (Buy & Hold) to compare against SPY, QQQ, or BTC. "Did my strategy beat the S&P?" is the first question every user has.
- [ ] 🟡 **Trade Log Table**: Show a paginated table of all individual trades (entry date, exit date, entry price, exit price, P&L, holding period). This is critical for users learning from their strategies.
- [ ] 🟡 **Walk-Forward Validation Panel**: Add a dedicated "Walk-Forward" tab in backtesting results showing rolling 6-month performance windows. Visually shows overfitting if Sharpe degrades over time — the single most educational feature a backtesting tool can have.
- [ ] 🟢 **Parameter Optimization Grid**: Allow users to scan a range of parameter values (e.g., SMA Fast: 5–20) and display a heatmap of Sharpe ratios. Teaches users about overfitting risk in a hands-on way.

---

## 9. Macro Dashboard Improvements
- [ ] 🟠 **Fed Meeting Countdown**: Show a prominent countdown timer to the next FOMC decision. "Next Fed Decision in 12 days" — this is a high-value, low-cost feature that traders check constantly.
- [ ] 🟠 **Economic Calendar Integration**: Replace or expand the EventTimeline with a full economic calendar showing the next 2 weeks of macro events (NFP, CPI, FOMC, ECB, etc.) with expected vs prior values. This is the most-checked feature by active traders.
- [ ] 🟡 **Macro Regime Label with History**: The current macro score shows a label (e.g., "Goldilocks") but not how long the current regime has lasted or what the previous regime was. Add "Regime since: Jan 2025 (72 days)" and a brief history.
- [ ] 🟡 **Central Bank Comparison Panel**: Show Fed, ECB, and BoE rates side-by-side. As Fin-Eye targets EU users, EUR/USD macro divergence is a key signal they watch.
- [ ] 🟢 **Yield Curve Inversion Alert Banner**: If the 2Y–10Y spread goes negative (inverted), auto-display a prominent educational banner explaining what yield curve inversion means historically. Educational + high visibility = strong social sharing trigger.

---

## 10. Navigation & Information Architecture
- [ ] 🔴 **Nav Overflow Fix**: 19 nav items in a flat horizontal bar is unusable on any screen below 1400px. Implement a grouped dropdown nav with categories: Intelligence (Dashboard, Macro, Sentiment, Retail), Markets (Options, Sectors, Earnings, Insiders, Shorts), Tools (Backtest, Portfolio, Hedge, Alerts), Learn, Community. Dramatically improves discoverability.
- [ ] 🟠 **Search Bar (Global)**: Add a CMD+K / Ctrl+K command palette that lets users type a ticker and jump to its analysis, or search for a blog post/learn article. Power-user UX staple that improves DAU for engaged users.
- [ ] 🟠 **Breadcrumbs on Inner Pages**: Pages like `/backtesting`, `/macro`, `/hedge` have no visual hierarchy. Add breadcrumbs ("Dashboard > Backtesting") to improve orientation — especially for users who arrive from a deep link.
- [ ] 🟡 **Active Page Highlighting in Nav**: The current nav highlights the active route — but given 19 items, consider adding a subtle left-border accent or background color that's more visually distinct than the current `bg-slate-800`.
- [ ] 🟡 **"New" / "Beta" Badges on Nav Items**: Tag newer features (Adv. Sentiment, Fed Policy, Experiments) with a "NEW" or "BETA" badge in the nav. This drives exploration and signals ongoing product development — a key churn reducer.

---

## 11. Onboarding & First-Time Experience
- [ ] 🔴 **Activation Funnel Tracking**: Instrument key activation events: (1) First ticker searched, (2) GAS explain panel opened, (3) First backtest run, (4) Macro page visited, (5) Watchlist item added. Without this data, you cannot improve onboarding. Use Mixpanel or PostHog.
- [ ] 🔴 **Progressive Disclosure**: New users see all 19 nav items and an information-dense dashboard simultaneously — overwhelming. Implement a "simplified mode" for the first 3 sessions that hides advanced features (Options, Shorts, Insiders) until the user has completed the tour or visited 3+ pages.
- [ ] 🟠 **"Start Here" Flow for New Users**: After email confirmation, redirect new users to a focused `/welcome` page (not the full dashboard). Ask: "What's your goal?" (Learn basics / Improve timing / Research stocks). Route them to the most relevant feature. Personalization at the entry point = 2x activation rates.
- [ ] 🟠 **Empty Watchlist CTA**: If a user's watchlist is empty, the `WatchlistWidget` should show a friendly prompt: "Add your first stock to track its GAS score" with a pre-filled search. An empty watchlist is a strong churn predictor.
- [ ] 🟡 **Feature Discovery Tooltips**: On the 3rd, 7th, and 14th day, surface contextual tooltips introducing unused features (e.g., "Did you know you can set price alerts?" or "Try the Conflict Detector to spot diverging signals").

---

## 12. Community & Social Features
- [ ] 🟡 **Public Strategy Leaderboard**: On the Community/Backtesting page, show a sorted leaderboard of public strategies by Sharpe ratio with a weekly/monthly reset. Competitive elements are powerful retention tools — traders are inherently competitive.
- [ ] 🟡 **Discussion Threads per Ticker**: Allow users to post brief text comments on a ticker's analysis page ("I agree with the bearish macro signal for TSLA — earnings call was weak"). Lightweight social layer increases daily return visits.
- [ ] 🟢 **"Bull vs Bear" Weekly Poll**: Each Monday, post a simple in-app poll: "Are you bullish or bearish on SPY this week?" Show aggregate results. Minimal dev cost, high engagement, creates weekly habit loops.
- [ ] 🟢 **User-Submitted Blog Post Drafts**: Allow Pro users to submit draft blog posts/analyses for review. Community-generated content at zero editorial cost. Publish the best ones to build a contributor identity for power users.

---

## 13. Data Quality & Trust
- [ ] 🔴 **Data Freshness Indicators on Every Data Section**: Every data section (Macro, Sentiment, Technical) should show "Last updated: 14 min ago" with a colored dot (green < 30 min, amber 30–60 min, red > 60 min). Users need to know they are seeing current data — especially traders making time-sensitive decisions.
- [ ] 🟠 **Data Source Attribution**: Each indicator/score should link to its source (e.g., "VIX from FRED · VIXCLS"). This builds trust, meets educational positioning, and protects against accusations of fabricated data.
- [ ] 🟠 **Graceful Degradation Messages**: When a data source is down (Finnhub, FRED, Yahoo Finance), display a banner: "News sentiment is temporarily unavailable. GAS is being computed without the sentiment layer." Currently silent failures confuse users and lead to support tickets.
- [ ] 🟡 **Model Confidence Intervals**: Where the ML model gives a directional signal (Bullish/Bearish), also display a confidence % (e.g., "Bullish — 67% confidence"). Low confidence signals should be visually distinct (lighter color, "low confidence" badge) so users calibrate expectations correctly.

---

## 14. Settings & Personalization
- [ ] 🟠 **Notification Preferences Page**: The Alerts feature exists (`/alerts`) but users need a central Settings page with: alert thresholds, email frequency, preferred timezone, default ticker, and preferred timeframe. Personalization = retention.
- [ ] 🟡 **Default Ticker**: Let users set a default ticker that loads on dashboard open (instead of always AAPL). Power users have a primary stock they track — making it their "home" creates habitual return visits.
- [ ] 🟡 **Currency Preference**: Allow users to toggle between USD/EUR display. Fin-Eye targets EU users — showing "$10,000" initial capital in backtesting for a EUR user creates subtle friction.
- [ ] 🟢 **Compact / Expanded View Toggle**: Power users (traders) want data density. Beginners (students) want spacious layout with more explanations. A toggle between "Compact" and "Guided" view modes serves both without requiring separate products.

---

## 15. Legal & Trust Compliance
- [ ] 🔴 **Cookie Consent Banner**: The `ConsentGate` component exists but verify it blocks analytics cookies until consent is given (GDPR requirement). Analytics must only fire post-consent. Use a CMP (Consent Management Platform) like Cookiebot or a custom solution.
- [ ] 🟠 **Risk Disclaimer on Every Data-Driven Page**: The layout footer has a disclaimer but it's small and at the very bottom. Add a subtle inline disclaimer bar on the Backtesting, Hedge Simulator, and Signals pages specifically — these are highest legal-risk surfaces.
- [ ] 🟡 **Data Deletion Flow**: Under GDPR, users have the right to erasure. Add a "Delete My Account" button in Settings that triggers a confirmed deletion of all user data within 30 days. Show a confirmation email. Missing this is a compliance risk.

---

## 16. Fin-Eye Showcase / Marketplace (Pro Tools)
- [ ] 🟠 **Product Cards with Preview Screenshots**: The `/showcase` page should display product cards with: title, 1-2 line description, price, category badge, and a thumbnail screenshot. Currently unclear if this is implemented beyond a basic list.
- [ ] 🟠 **UTM Tracking on External Product Links**: Every "Buy Now" redirect to the external product site should append `?utm_source=terminal&utm_medium=showcase&utm_campaign=product_id`. Enables proper attribution for revenue from this channel.
- [ ] 🟡 **"Featured" Product Rotation**: Allow admin to flag 2–3 products as "Featured" that display in a highlighted hero row at the top of the Showcase page. Drive attention to highest-margin products.
- [ ] 🟡 **Click Analytics on Showcase**: Track which products are viewed and clicked most. Inform which new products to build next — data-driven product development at zero extra cost.

---

## 17. Admin & Operations
- [ ] 🟠 **User Lifecycle Dashboard** (`/admin/analytics`): The admin analytics page should show: DAU/WAU/MAU trend, free vs Pro user ratio, top tickers searched, feature adoption heatmap (which pages are visited), and funnel conversion (signup → activation → paid). Essential for data-driven growth decisions.
- [ ] 🟠 **Churn Early Warning**: Flag users who have not visited in 7 days in the admin dashboard. Trigger an automated re-engagement email (e.g., "We have new macro data for your watchlist"). Proactive churn prevention.
- [ ] 🟡 **A/B Experiment Framework** (`/admin/experiments` already exists): Ensure the experiment framework supports feature flags and percentage rollouts. First experiments to run: (1) Onboarding flow variants, (2) GAS widget copy variants, (3) Upgrade CTA placement.
- [ ] 🟡 **Error Rate Monitoring**: Integrate Sentry (or equivalent) to capture frontend JS errors in production. Set up alerts for error rate > 1%. Currently silent errors are likely causing invisible user abandonment.

---

## 18. Future / Roadmap Items (Phase 2+)
- [ ] 🟢 **Mobile App (React Native)**: Push notifications for regime changes and GAS threshold crossings are the killer feature. Without push, mobile engagement is limited to browser visits.
- [ ] 🟢 **Portfolio-Level GAS**: Aggregate GAS across a user's portfolio weighted by position size. The ultimate answer to "What is the macro regime for MY portfolio?" — a feature no Bloomberg terminal offers in this format.
- [ ] 🟢 **Earnings Calendar with Sentiment Pre-loading**: Before earnings, pre-compute and display the 30-day sentiment trend for the stock and show the historical pattern of GAS before/after earnings beats vs misses. High-value predictive educational content.
- [ ] 🟢 **API Tier for Developers**: Allow Pro+ users to access GAS scores via a personal API key (rate-limited). Quants and developers building bots will pay for this. Also generates organic word-of-mouth in tech/trading communities.
- [ ] 🟢 **White-Label Inquiry Form**: Add a "For Institutions" CTA on the landing page that routes to a contact form for brokers/fund managers interested in white-labeling. Even 1 institutional deal at €5k/mo changes the business trajectory.

---

*Last updated: March 2026 · Version 2.0*
