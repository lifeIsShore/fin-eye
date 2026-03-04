## Fin-Eye User Stories

This file translates the PRDV3 requirements into user stories grouped by **persona** and **phase** (MVP, Growth, Premium).  
Format:  
- **Story ID**: `PHASE-AREA-XX`  
- **As a \<persona\>, I want … so that …**  
- **Acceptance Criteria**: concrete, testable conditions.

---

## Phase 1 – MVP (Weeks 1–12)

### 1. Dashboard & Market Intelligence

**Story ID: MVP-DASH-01**  
**As Emma (finance student), I want** a single dashboard that shows a clear Global Alignment Score and market weather label for a selected stock **so that** I can quickly understand whether conditions are broadly supportive, mixed, or hostile without reading raw data.

**Acceptance Criteria**
- User can select a stock (e.g. AAPL, TSLA) from a ticker input.
- Dashboard shows a **Global Alignment Score (0–100)** for the selected stock.
- Dashboard shows one of the defined **Market Weather states** based on GAS:
  - Strong Tailwind (80–100)
  - Mild Support (60–79)
  - Mixed Signals (40–59)
  - Headwind (20–39)
  - High Instability (0–19)
- Weather state is derived from underlying layer outputs (technical, sentiment, macro, volatility) using the rules in PRDV3.
- When underlying data changes (at most every 15 minutes during market hours), GAS and weather state update accordingly.

---

**Story ID: MVP-DASH-02**  
**As Marco (retail trader), I want** to see technical regime classification (Risk-On / Risk-Off / Range-Bound) and volatility regime on the dashboard **so that** I can align my trading aggressiveness with the current environment.

**Acceptance Criteria**
- For each selected stock, dashboard shows:
  - Regime classification: one of `Risk-On`, `Risk-Off`, `Range-Bound`.
  - Confidence percentage for regime (0–100%).
  - Volatility regime label derived from VIX:
    - Low (< 15), Medium (15–25), High (> 25).
- Regime is derived from the combination of technical, macro and volatility signals as defined in PRDV3.
- If regime or volatility regime changes between refreshes, the dashboard highlights the change (e.g. subtle badge or “Regime changed X minutes ago” text).

---

**Story ID: MVP-DASH-03**  
**As Emma, I want** to see multi-timeframe technical signals for the selected stock (1h, 4h, 1d, 1w, 1m) **so that** I can understand if short-term and long-term signals agree or conflict.

**Acceptance Criteria**
- For the selected stock, the UI displays five timeframe tiles: 1h, 4h, 1d, 1w, 1m.
- Each tile shows:
  - Directional label: `Bullish`, `Neutral`, or `Bearish`.
  - Confidence score (0–100).
- Signals are computed from the winning technical model per timeframe as specified in PRDV3.
- If fewer than a minimum amount of data is available for a timeframe, that tile shows a disabled or “insufficient data” state.

---

### 2. Conflict Detector & “Why Is The Market Moving?”

**Story ID: MVP-EXPL-01**  
**As Emma, I want** a plain-English explanation of why the market (or stock) is in its current state **so that** I can connect technical, sentiment and macro drivers without needing quant expertise.

**Acceptance Criteria**
- Dashboard contains a “Why is this stock moving?” explanation panel.
- Panel summarises drivers as bullet points, including:
  - Contribution from technical momentum / trend.
  - Contribution from news sentiment.
  - Contribution from macro background.
- Explanation references actual current layer values (e.g. “4 of 5 timeframes bullish”, “3‑day news sentiment strongly positive”).
- Text explicitly emphasises uncertainty and non-advisory nature (e.g. “This is educational analysis, not investment advice”).

---

**Story ID: MVP-EXPL-02**  
**As Marco, I want** conflict alerts when technical, sentiment, and macro layers disagree **so that** I am warned about unstable environments and avoid overconfidence.

**Acceptance Criteria**
- System computes conflicts whenever:
  - At least one layer is strongly bullish and another is strongly bearish; or
  - Agreement across timeframes is below a configured threshold (e.g. < 40%).
- When a conflict is detected, the dashboard shows a visible but non-intrusive warning block that:
  - Names the conflicting layers (e.g. “Technicals bullish vs Macro bearish”).
  - States the magnitude of disagreement (e.g. percentage points difference).
  - Encourages caution rather than prescriptive trades.
- If no conflict is detected, the section indicates “No major conflicts detected.”

---

### 3. Technical ML Layer & Ensemble

**Story ID: MVP-TECH-01**  
**As a backend/ML engineer, I want** to train four competing models per timeframe and select the winner by Sharpe ratio **so that** the technical consensus is based on risk-adjusted performance rather than accuracy alone.

**Acceptance Criteria**
- For each supported timeframe (1h, 4h, 1d, 1w, 1m), the system can train:
  - LSTM with attention,
  - XGBoost,
  - Logistic/linear baseline,
  - Prophet.
- Training uses the 25-feature set described in PRDV3 (technical, sentiment, macro, temporal).
- A validation protocol using walk-forward testing is implemented (train on ~3 years, validate on ~6 months).
- For each timeframe, the system computes the Sharpe ratio of each model on validation data.
- The model with highest Sharpe is marked as the “winner” and stored for inference.
- Metadata about training and performance (Sharpe, accuracy) is persisted for inspection.

---

**Story ID: MVP-TECH-02**  
**As Marco, I want** the system to aggregate the 5 timeframe predictions into a single technical confidence score **so that** I can see how aligned the technical picture is overall.

**Acceptance Criteria**
- For each timeframe, the winning model outputs:
  - Direction (`Buy`/`Neutral`/`Sell`) mapped to −1 / 0 / +1.
  - Probability or confidence.
- System weights each timeframe by its validation Sharpe ratio and computes a consensus value between −1 and +1.
- Consensus is transformed into a 0–100 **Technical Confidence Score** using the mapping defined in PRDV3.
- The UI displays:
  - Technical Confidence Score (0–100).
  - Simple summary (“Mostly bullish”, “Mixed”, etc.) based on score bands.

---

### 4. Backtesting Engine (MVP)

**Story ID: MVP-BACK-01**  
**As Marco, I want** to run a backtest of a simple momentum strategy on a chosen stock **so that** I can see historical performance with realistic statistics.

**Acceptance Criteria**
- Backtesting tab allows user to:
  - Select a stock.
  - Choose “Momentum” pre-defined template.
  - Adjust key parameters (e.g. SMA length, RSI threshold).
- Running the backtest produces:
  - Total return %, Sharpe ratio, Sortino ratio, max drawdown, win rate, recovery factor.
  - Equity curve over time.
- Slippage and commission assumptions are applied (0.1% per trade + spread as defined).
- Backtest period uses at least the last 5 years of data where available.

---

**Story ID: MVP-BACK-02**  
**As Emma, I want** clear warnings about overfitting and the gap between backtests and live performance **so that** I don’t over-trust impressive historical results.

**Acceptance Criteria**
- Backtest results view includes an explicit, non-dismissable text block describing:
  - The difference between backtest and live trading.
  - Typical degradation (e.g. “expect ~50% of backtest Sharpe in live trading”).
- If Sharpe exceeds a configurable threshold (e.g. > 1.2), an additional warning is shown about possible overfitting.
- Warnings include non-advisory language and direct users back to educational content (“Backtesting pitfalls”).

---

### 5. News Sentiment Layer (MVP)

**Story ID: MVP-SENT-01**  
**As Emma, I want** to see a time-series chart of news sentiment for a stock **so that** I can visually understand whether the news flow has been improving or worsening.

**Acceptance Criteria**
- For the selected stock, the system:
  - Pulls recent articles (up to the last 50 per day) from Finnhub.
  - Scores each article with FinBERT sentiment.
  - Aggregates daily sentiment into 1-day, 7-day, and 30-day averages.
- News & Sentiment tab displays:
  - A 30-day line chart of sentiment.
  - Current 1d / 7d / 30d aggregated sentiment values.
- Articles list shows title, source, publication time, and sentiment score.

---

**Story ID: MVP-SENT-02**  
**As Marco, I want** to see which news sources are driving bullish or bearish sentiment **so that** I can assess whether the narrative is broad-based or coming from a few outlets.

**Acceptance Criteria**
- For aggregated sentiment, the system computes a breakdown by source (e.g. Reuters, Bloomberg).
- UI shows a simple distribution (e.g. table or bar chart) of positive vs negative sentiment per source over the last 30 days.
- User can quickly see which sources are most positive/negative for the selected stock.

---

### 6. Macro/Economic Layer (MVP)

**Story ID: MVP-MACRO-01**  
**As Marco, I want** a macro dashboard showing key indicators (Fed rate, CPI, unemployment, 2–10 spread, VIX) **so that** I can frame stock signals within the broader macro environment.

**Acceptance Criteria**
- Macro Dashboard tab shows:
  - Latest Fed Funds Rate, CPI YoY, unemployment rate, 2–10 year yield spread, VIX level.
- Data is pulled from FRED, Yahoo Finance (VIX), and US Treasury according to PRDV3 frequencies.
- Values are updated daily (or more frequently where data allows).
- Each indicator includes a short textual interpretation (e.g. “Yield curve inverted, historically associated with recession risk.”).

---

**Story ID: MVP-MACRO-02**  
**As Emma, I want** a simple macro score (0–100) and a short human-readable label **so that** I don’t need to understand every indicator individually to get a sense of the macro backdrop.

**Acceptance Criteria**
- System combines macro indicators into a single **Macro Score (0–100)** based on the rules defined in PRDV3.
- Score is mapped to a short label (e.g. “Supportive”, “Neutral”, “Stressed”).
- Macro score appears both on the main dashboard (summary) and in more detail on the Macro tab.

---

### 7. Educational Content & Onboarding

**Story ID: MVP-LEARN-01**  
**As Emma, I want** a Learn/Blog section with curated educational posts **so that** I can build structured knowledge about macro, regimes, and backtesting.

**Acceptance Criteria**
- Learn/Blog tab lists published blog posts with:
  - Title, short summary, read-time estimate, and publish date.
- At least six initial posts are available at MVP, covering topics listed in PRDV3 (Macro 101, GAS explained, Backtesting pitfalls, etc.).
- Each article page includes the global disclaimer (educational, not investment advice).
- Posts are navigable via simple categories (e.g. Macro 101, Backtesting, Sentiment).

---

**Story ID: MVP-ONBOARD-01**  
**As a new user (Emma or Marco), I want** a short in-app tour that explains the key dashboard concepts **so that** I don’t feel lost on first login.

**Acceptance Criteria**
- After first login, the app offers a guided tour with 4–6 contextual tooltips covering:
  - Global Alignment Score.
  - Market Weather.
  - Timeframe signals.
  - “Why is this stock moving?” panel.
  - Links to Learn/Blog.
- Tour can be skipped and re-opened later from Settings.
- Tour steps differ slightly by persona goal selection (“Learn fundamentals” vs “Improve trade timing”) but cover the same core concepts.

---

### 8. Basic Hedging Simulator

**Story ID: MVP-HEDGE-01**  
**As Marco, I want** to simulate a simple hedge (stock + protective put or stock + short ETF) **so that** I can see how hedging would have changed drawdowns in past crashes.

**Acceptance Criteria**
- Hedging Simulator tab allows user to:
  - Select a stock.
  - Choose one hedge type:
    - Protective put on the stock.
    - Short an inverse or correlated ETF.
- System estimates:
  - Beta of the stock vs S&P 500.
  - Correlation between stock and hedge instrument.
  - Max drawdown reduction if the stock falls by a specified percentage (e.g. −20%).
  - Approximate cost of hedge (premium or ETF carry).
- UI shows:
  - Before/after equity curve.
  - Simple payoff diagram for the scenario.

---

### 9. Data Infrastructure & APIs (MVP)

**Story ID: MVP-DATA-01**  
**As a backend engineer, I want** robust pipelines for OHLCV, news, macro, and sentiment data **so that** ML models and dashboards always have fresh, consistent inputs.

**Acceptance Criteria**
- Scheduled fetchers are implemented for:
  - OHLCV data (Yahoo Finance).
  - FRED macro indicators.
  - Finnhub news articles.
- Data is stored in PostgreSQL/TimescaleDB with schemas close to the PRDV3 spec.
- Basic validation checks run on ingest (missing values, duplicates, obvious out-of-range values).
- Redis cache is used for:
  - Recent GAS scores (15-minute TTL).
  - Recent sentiment aggregates (daily TTL).

---

## Phase 2 – Growth (Months 3–6)

### 10. Portfolio View & Aggregated Insights

**Story ID: P2-PORT-01**  
**As Marco, I want** to create and manage a portfolio of up to 10 stocks **so that** I can see GAS and risk information at the portfolio level, not just per stock.

**Acceptance Criteria**
- Users can:
  - Add/remove stocks from a named portfolio.
  - Define position sizes (either notional or percentage weights).
- Portfolio-level view shows:
  - Weighted average GAS for the portfolio.
  - Sector breakdown based on holdings.
  - Diversification score using correlation matrix.

---

### 11. Retail Sentiment (Reddit)

**Story ID: P2-RET-01**  
**As Marco, I want** to see how much Reddit is talking about my stock and whether the sentiment is bullish or bearish **so that** I can spot “overheated” retail narratives.

**Acceptance Criteria**
- System ingests posts/comments from target subreddits (e.g. r/stocks, r/wallstreetbets, r/investing, r/SecurityAnalysis) via PRAW.
- For a selected stock, UI shows:
  - Daily mention volume over the last 30 days.
  - Sentiment breakdown: % positive, neutral, negative.
  - Top 5 bullish and top 5 bearish comments (with timestamps and subreddit names).
- A **Retail Sentiment Score (0–100)** is computed and shown on the dashboard and sentiment tab.

---

### 12. Political/Event Tracking (GDELT)

**Story ID: P2-EVENT-01**  
**As Emma, I want** an event calendar highlighting upcoming macro and political events relevant to markets **so that** I can understand when volatility is likely to increase.

**Acceptance Criteria**
- Events are ingested from GDELT/other sources for:
  - Central bank decisions.
  - Major elections.
  - Earnings announcements (for covered stocks).
  - Geopolitical incidents of interest.
- Macro Dashboard or Events tab displays:
  - Upcoming events for the next 30 days.
  - Basic impact tags (e.g. “high volatility risk”, “sector-specific”).
- Past events can be selected to show approximate post-event price movement for a chosen stock or index.

---

### 13. Advanced Hedging & Strategy Library

**Story ID: P2-HEDGE-ADV-01**  
**As Marco, I want** to test multi-leg hedging strategies (e.g. collars, stock + put + short ETF) **so that** I can find cost-effective ways to reduce risk.

**Acceptance Criteria**
- Hedging Simulator supports:
  - At least:
    - Stock + put + short ETF.
    - Collar (long stock, long put, short call).
  - Inputs for strike distances, expiries, and hedge sizes.
- Backtest shows:
  - Equity curves for unhedged vs each hedged strategy.
  - Max drawdown difference and hedge cost over the backtest period.

---

**Story ID: P2-STRAT-01**  
**As Emma and Marco, I want** a strategy library where I can browse, save, and optionally share backtested strategies **so that** I don’t have to start from scratch every time.

**Acceptance Criteria**
- Users can:
  - Save a configured strategy under a custom name.
  - Load previously saved strategies.
- Strategy library view shows:
  - List of templates (platform-provided and user-provided).
  - Key metrics for each strategy (Sharpe, max drawdown, win rate).
- (Optional for later in Phase 2) Users can mark strategies as public and see a simple leaderboard.

---

## Phase 3 – Premium (Months 6+)

### 14. Advanced Sentiment & Custom Analytics

**Story ID: P3-SENT-ADV-01**  
**As Alex (institutional analyst), I want** integrated sentiment from Twitter/X, earnings call transcripts, and Google Trends **so that** I get a more complete picture of crowd and management tone.

**Acceptance Criteria**
- System can ingest:
  - Tweets or posts about relevant tickers and macro topics (via snscrape or similar).
  - Earnings call transcripts for major companies.
  - Google Trends data for ticker/company/sector keywords.
- For a selected stock, premium sentiment view shows:
  - Combined sentiment score by source type (news, Twitter/X, transcripts, Reddit).
  - At least one visualisation comparing source categories over time.

---

**Story ID: P3-ANALYTICS-01**  
**As Alex, I want** a no-code indicator builder and feature engineering playground **so that** I can design and test custom signals without writing code in the core codebase.

**Acceptance Criteria**
- Users can:
  - Select from existing feature primitives (prices, indicators, macro variables).
  - Combine them using basic mathematical operations (add, subtract, multiply, divide, ratios).
- System:
  - Validates custom indicators (no invalid expressions that crash the system).
  - Allows backtesting of strategies that use these custom indicators.

---

### 15. API & Institutional / White-Label

**Story ID: P3-API-01**  
**As Alex, I want** an authenticated API to fetch GAS, macro scores, and sentiment scores for a list of tickers **so that** I can integrate Fin-Eye into my existing portfolio tools.

**Acceptance Criteria**
- REST API exposes endpoints to:
  - Retrieve current GAS and layer scores for one or more tickers.
  - Retrieve historical regime data for a ticker over a specified period.
- API is protected with keys or OAuth and rate-limited.
- Documentation clearly describes parameters, response formats, and constraints.

---

**Story ID: P3-WHITELABEL-01**  
**As Alex, I want** a white-label dashboard I can brand with my firm’s logo and colours **so that** I can share macro/sentiment views directly with clients.

**Acceptance Criteria**
- Whitelabel configuration supports:
  - Custom logo.
  - Colour theme.
  - Custom domain configuration.
- Client-facing view hides Fin-Eye-specific branding except where legally required.
- Same core visualisations (GAS, macro dashboard, sentiment views) are available.

---

### 16. Risk Management & Scenario Analysis

**Story ID: P3-RISK-01**  
**As Alex, I want** scenario and stress-test tools based on historical crises and hypothetical shocks **so that** I can explain portfolio risks to stakeholders.

**Acceptance Criteria**
- Risk tools allow user to:
  - Select a scenario (e.g. 2008 crisis, 2020 COVID crash, or custom shock).
  - Apply scenario to a portfolio and estimate losses.
- Outputs include:
  - Estimated portfolio return under each scenario.
  - Simple VaR/CVaR-style summaries (where data permits).

---

## Cross‑Cutting & Supporting Features

These stories support the core product but cut across phases.

---

### 17. Authentication & Subscription Management

**Story ID: CORE-AUTH-01**  
**As any user, I want** to sign up, log in, and log out securely **so that** my data and settings are protected.

**Acceptance Criteria**
- Users can create an account with email + password (or via chosen auth provider when implemented).
- Passwords are stored securely (hashed, never in plaintext).
- Login, logout, and password reset flows behave as expected.
- After successful login, users are redirected to the main dashboard.

---

**Story ID: CORE-SUB-01**  
**As a Free user, I want** to upgrade to Pro using a simple payment flow **so that** I can unlock real-time features and limits described in PRDV3.

**Acceptance Criteria**
- Pricing/Upgrade UI explains Free vs Pro features clearly.
- Upgrade flow integrates with Stripe:
  - Creates a subscription.
  - Handles payment errors gracefully.
- After successful payment:
  - User account is marked as Pro.
  - Relevant feature limits are lifted (e.g. unlimited backtests).

---

**Story ID: CORE-SUB-02**  
**As a Pro user, I want** to view, manage, and cancel my subscription **so that** I feel in control and can avoid lock‑in.

**Acceptance Criteria**
- Settings/Subscription area shows:
  - Current plan (Free/Pro/Team/Institutional).
  - Billing period and renewal date.
  - Links to invoices/receipts (via Stripe).
- User can cancel renewal in one or two obvious clicks.
- After cancellation, access downgrades at end of billing period, not immediately.

---

### 18. Settings, Watchlist & Notifications

**Story ID: CORE-SET-01**  
**As Emma, I want** to manage my profile, preferred language (if applicable), and basic preferences **so that** the app feels personal and consistent.

**Acceptance Criteria**
- Settings page allows:
  - Updating name and optional avatar.
  - Changing password (with current password confirmation).
- Profile changes persist and are reflected across the app.

---

**Story ID: CORE-WATCH-01** ✅ DONE (Session 41 — 2026-03-05)
**As Marco, I want** to maintain a watchlist of favourite stocks **so that** I can quickly switch between the instruments I care about most.

**Acceptance Criteria**
- ✅ Users can search and add tickers to a personal watchlist.
- ✅ Users can remove tickers from the watchlist at any time.
- ✅ Dashboard provides quick access to watchlist; selecting a symbol updates the dashboard context.
- ✅ Watchlist is persisted per user and available across sessions/devices.

---

**Story ID: CORE-NOTIF-01**  
**As Marco, I want** to receive alerts when GAS or regimes cross important thresholds **so that** I can react without staring at the screen all day.

**Acceptance Criteria**
- Users can configure notification rules, e.g.:
  - GAS crosses above X or below Y for a given ticker.
  - Regime flips between Risk‑On and Risk‑Off.
- Delivery channels for MVP can be email (push/mobile later).
- Notifications include:
  - Trigger condition.
  - Timestamp.
  - Clear non‑advisory wording.

---

### 19. Content Management & Community

**Story ID: CORE-CMS-01**  
**As a content admin (you), I want** to create, edit, and publish blog and glossary entries via a simple interface or content pipeline **so that** I can keep educational content fresh without code changes.

**Acceptance Criteria**
- There is a clear process (headless CMS or Git‑based content) to:
  - Add new posts.
  - Edit existing posts.
  - Schedule or publish immediately.
- Content changes appear on the Learn/Blog tab without redeploying core backend logic.
- Posts automatically include standard disclaimers and metadata (author, date).

---

**Story ID: CORE-CMS-02**  
**As a content admin (you), I want** a dedicated admin view with a markdown editor **so that** I can manage blog posts directly within the Fin-Eye application.

**Acceptance Criteria**
- Admin dashboard is conditionally shown only to users with the 'admin' role.
- Interface includes a table of all posts with status (Draft, Published).
- Editor includes capability to write markdown, preview it, set titles, slugs, and publish dates.
- Admin can save drafts, publish posts, or unpublish active posts.
- Database or file storage layer handles saving and retrieving of these managed posts.

---

**Story ID: CORE-COMM-01**  
**As Emma, I want** a lightweight community space linked from the app (Discord/Reddit or in‑app forum) **so that** I can discuss ideas and ask questions with others.

**Acceptance Criteria**
- App surfaces a clear “Community” entry point (link to Discord/Reddit or embedded forum).
- Access is gated by login to reduce spam.
- Community link can highlight key channels (e.g. #macro‑101, #strategy‑discussion).

---

### 20. Legal, Compliance & Privacy UX

**Story ID: CORE-LEGAL-01**  
**As any user, I want** to clearly see and acknowledge the main disclaimer, Terms of Service, and Privacy Policy **so that** I understand the nature of the service and my rights.

**Acceptance Criteria**
- On first sign‑up/login, users see:
  - A concise disclaimer.
  - Links to full ToS and Privacy Policy.
- Legal pages are accessible from footer or settings on every screen.
- Consent is recorded (timestamp + version) for compliance purposes.

---

**Story ID: CORE-GDPR-01**  
**As an EU user, I want** to export or delete my data on request **so that** my GDPR rights are respected.

**Acceptance Criteria**
- Settings include:
  - “Request data export” action (e.g. sends zip via email or download when ready).
  - “Request account deletion” action with confirmation.
- After deletion:
  - User can no longer log in.
  - Personal data is removed or anonymised according to policy (except where retention is legally required).

---

### 21. Monitoring, Reliability & Ops

**Story ID: CORE-OPS-01**  
**As the Fin‑Eye operator, I want** observability over key services **so that** I can detect outages, slowdowns, or model failures early.

**Acceptance Criteria**
- Basic metrics are collected and visible in monitoring:
  - API latency and error rates.
  - Data pipeline success/failure counts.
  - Model inference times.
- Alerting rules trigger notifications (e.g. email/Slack) when thresholds are breached.

---

### 22. Revenue “Window Showcase” Module

**Story ID: CORE-SHOP-01**  
**As a Pro or power user, I want** a curated “Pro Tools” / marketplace view inside the app **so that** I can discover your external digital financial tools that complement Fin‑Eye.

**Acceptance Criteria**
- Navigation includes an entry for the Window Showcase/Marketplace.
- Page shows a grid of product cards including:
  - Title.
  - Short description.
  - Category badge (e.g. Portfolio Tools, Planning Tools).
  - “View details” button.
- Cards and details are manageable by you via an admin process (config file or simple CRUD UI).

---

**Story ID: CORE-SHOP-02**  
**As the product owner, I want** a product detail modal and tracked external redirect **so that** I can measure interest and conversions for each digital product.

**Acceptance Criteria**
- Clicking a product opens a detail view with:
  - Longer description.
  - Key features bullet list.
  - “Buy now” button.
- “Buy now” opens the external storefront in a new tab and appends tracking parameters (`product_id`, `source=terminal`, optional anonymised user identifier).
- Basic click statistics per product are stored (views, detail opens, outbound clicks).

---

### 23. Mobile Experience (Later Phase)

**Story ID: P3-MOBILE-01**  
**As Marco, I want** a mobile‑friendly version of the main dashboard **so that** I can quickly check GAS, regimes, and alerts on the go.

**Acceptance Criteria**
- On small screens, dashboard:
  - Uses a responsive layout optimised for touch.
  - Prioritises key indicators (GAS, Market Weather, current regime, key alerts).
- Navigation is simplified for mobile while preserving access to core tabs.

---

**Story ID: P3-MOBILE-02**  
**As any Pro user, I want** push notifications on my phone for key alerts (GAS thresholds, regime changes, major events) **so that** I stay informed even when the app is closed.

**Acceptance Criteria**
- Users can opt‑in to mobile push notifications.
- Notification rules map 1:1 with existing alert rules (from CORE-NOTIF-01) where technically feasible.
- Notifications respect user time‑zone and quiet‑hours preferences where configured.

---

### 24. Advanced Macro Intelligence Expansion

**Story ID: P2-MACRO-ADV-01**  
**As Marco, I want** a deeper macro view with yield curves, recession probabilities, and macro stress index **so that** I can judge when regimes are changing beyond the basic indicators.

**Acceptance Criteria**
- Macro Dashboard can switch to an “Advanced” view showing at minimum:
  - Full yield curve (2y, 5y, 10y, 30y) over time.
  - Historical and current recession probability (where data is available).
  - Additional leading indicators (e.g. leading economic index, real yield spreads).
- A **Macro Stress Index (0–100)** is computed from these inputs, following the logic in PRDV3, and displayed alongside the base Macro Score.
- Advanced charts are clearly labeled and include short helper text explaining why each indicator matters.

---

### 25. Institutional Reporting & Bulk Analysis

**Story ID: P3-BULK-01**  
**As Alex, I want** to run bulk analysis for dozens of stocks at once **so that** I can assess macro/sentiment risk across a full portfolio efficiently.

**Acceptance Criteria**
- Institutional users can submit a list of tickers (e.g. 50+) via UI or API.
- System returns, for each ticker:
  - Current GAS and layer scores.
  - Current regime classification.
  - Key conflicts (if any).
- Bulk responses are optimised for performance and can be exported (e.g. CSV/Excel).

---

**Story ID: P3-REPORT-01**  
**As Alex, I want** client‑ready reports (PDF/Excel) with portfolio GAS, risk scenarios, and macro context **so that** I can communicate insights to non‑technical stakeholders.

**Acceptance Criteria**
- From an institutional or portfolio view, user can generate a report that includes:
  - Portfolio‑level GAS and diversification metrics.
  - Selected scenarios/stress‑test summaries.
  - Key macro indicators relevant to the portfolio.
- Reports can be exported as PDF and at least one data format (CSV or Excel).
- Branding follows white‑label settings where configured.

---

### 26. Professional Content & Education

**Story ID: P2-CONTENT-ADV-01**  
**As Emma, I want** advanced case studies and video content (e.g. “2008 crisis”, “regime shifts”) **so that** I can go beyond basics and see how the framework behaved in real history.

**Acceptance Criteria**
- Learn/Blog section adds:
  - A “Case Studies” category (e.g. 2008, 2020) with at least one detailed post per case.
  - Embedded or linked videos where appropriate.
- Each case study references how GAS and macro indicators would have looked, with clear caveats about hindsight.

---

**Story ID: P3-EDU-01**  
**As Marco, I want** access to structured premium educational series (courses/webinars) **so that** I can deepen my understanding in a guided way.

**Acceptance Criteria**
- There is a dedicated “Courses” or “Webinars” section accessible from Learn/Blog or navigation.
- At least one multi‑part series is represented with:
  - Syllabus/outline.
  - Progress tracking (completed vs pending lessons).
- Live or recorded sessions include clear scheduling/availability information.

---

### 27. Security, Backups & Disaster Recovery

**Story ID: CORE-SEC-01**  
**As a security‑conscious user, I want** optional two‑factor authentication (2FA) on my account **so that** I can reduce the risk of unauthorised access.

**Acceptance Criteria**
- Settings page offers enabling/disabling 2FA (e.g. TOTP app or similar standard mechanism).
- Login flow supports second‑factor prompts when 2FA is enabled.
- Recovery options are clearly documented (backup codes or similar) without exposing secrets in plaintext.

---

**Story ID: CORE-SEC-02**  
**As the Fin‑Eye operator, I want** regular encrypted backups and a tested recovery process **so that** we can recover quickly from data loss or incidents.

**Acceptance Criteria**
- Automated backups run on a defined schedule for:
  - Core databases (PostgreSQL/TimescaleDB).
  - Critical configuration (excluding secrets stored in dedicated secret managers).
- Backups are encrypted at rest and stored in a separate location.
- A documented restore procedure exists and is tested at a regular cadence (e.g. quarterly).

---

### 28. Product Analytics & Experimentation

**Story ID: CORE-ANALYTICS-01**  
**As the product owner, I want** instrumentation for key product events and funnels **so that** I can measure activation, engagement, and conversion against the KPIs in PRDV3.

**Acceptance Criteria**
- Analytics events are defined and implemented at minimum for:
  - Sign‑up, first dashboard view, first backtest, first macro dashboard view.
  - Upgrade to Pro, cancellation, key feature use (hedging simulator, sentiment tab).
- Events are captured in an analytics tool (e.g. Mixpanel/Plausible) with privacy‑respecting configuration.
- Dashboards or reports exist to view:
  - Activation rate.
  - Feature adoption.
  - Free‑to‑paid conversion and churn trends.

---

**Story ID: CORE-EXPERIMENT-01**  
**As the product team, I want** the ability to run simple A/B tests on onboarding and messaging **so that** we can iteratively improve activation and understanding.

**Acceptance Criteria**
- System supports assigning users to variants (e.g. Onboarding A vs B) in a controlled way.
- Variant exposure is tracked in analytics.
- At least one initial experiment is set up for:
  - Dashboard‑first vs tutorial‑first onboarding, or
  - Alternative GAS explanation copy.

---

### 29. Email Onboarding & Newsletter

**Story ID: CORE-EMAIL-01**  
**As a new user, I want** a short onboarding email sequence **so that** I learn how to get value from Fin‑Eye over the first days/weeks.

**Acceptance Criteria**
- After sign‑up, user receives a series of emails over ~1–2 weeks that:
  - Introduce the dashboard and GAS.
  - Highlight key features (backtesting, macro dashboard, Learn tab).
  - Remind users about disclaimers and educational focus.
- Users can opt out of non‑transactional emails at any time.

---

**Story ID: CORE-EMAIL-02**  
**As an engaged user, I want** an optional weekly or bi‑weekly market/email digest **so that** I can stay informed about new content and key macro developments.

**Acceptance Criteria**
- Settings include an opt‑in toggle for the newsletter/digest.
- Digest includes:
  - Links to recent blog posts or case studies.
  - High‑level macro summary (not trade recommendations).
  - Product updates when relevant.
- Email sending respects consent and complies with GDPR/email regulations (e.g. unsubscribe link).

---

### 30. Epics & Implementation Tasks (Pre‑Development)

This section groups user stories into higher‑level epics and notes key implementation tasks to plan before and during development. Story IDs in parentheses show the mapping; tasks are implementation‑oriented, not user‑facing.

---

#### 30.1 MVP Core Product Epics

- **Epic E1 – Dashboard, GAS & Explanations**  
  **Stories**: `MVP-DASH-01`, `MVP-DASH-02`, `MVP-DASH-03`, `MVP-EXPL-01`, `MVP-EXPL-02`, `MVP-MACRO-02`, `MVP-SENT-01`, `MVP-SENT-02`.  
  **Key implementation tasks**
  - Define API contracts for: current GAS, layer scores, regimes, conflicts, sentiment aggregates, macro scores.
  - Design initial dashboard UI/UX (wireframes + component hierarchy).
  - Implement server endpoints and integrate with cached data (Redis).
  - Implement “Why is this stock moving?” explanation templating logic.
  - Implement basic error/loading states for all dashboard widgets.

- **Epic E2 – Data & ML Platform (Technical Layer & GAS Engine)**  
  **Stories**: `MVP-TECH-01`, `MVP-TECH-02`, `MVP-DATA-01`, relevant parts of PRD Section 4.  
  **Key implementation tasks**
  - Stand up data store schemas for OHLCV, macro, news, sentiment features.
  - Implement scheduled fetchers/pipelines for OHLCV, FRED, news, sentiment scoring.
  - Implement feature engineering pipeline and model‑training scripts for all four model types.
  - Implement Sharpe‑based model selection and model registry.
  - Implement ensemble consensus + GAS calculation service with unit tests.

- **Epic E3 – Backtesting & Basic Hedging**  
  **Stories**: `MVP-BACK-01`, `MVP-BACK-02`, `MVP-HEDGE-01`.  
  **Key implementation tasks**
  - Decide on backtesting engine (library vs custom) and integrate it.
  - Implement parameterisable strategy templates (momentum, mean reversion, macro‑responsive later).
  - Implement P&L, drawdown, Sharpe and other metric calculations.
  - Implement UI for configuring strategies and displaying results/plots.
  - Implement basic hedging simulator calculations and visualisations.

- **Epic E4 – Auth, Subscriptions & Settings**  
  **Stories**: `CORE-AUTH-01`, `CORE-SUB-01`, `CORE-SUB-02`, `CORE-SET-01`, `CORE-WATCH-01`, later `CORE-SEC-01`.  
  **Key implementation tasks**
  - Choose auth provider (e.g. Auth0) and integrate signup/login/logout/password reset.
  - Integrate Stripe plans and webhooks for subscription lifecycle.
  - Implement settings UI (profile, subscription info, watchlist management).
  - Implement server‑side enforcement of plan entitlements (limits, Pro‑only features).
  - Implement optional 2FA and secure session handling.

- **Epic E5 – Legal, Compliance, Security & Privacy**  
  **Stories**: `CORE-LEGAL-01`, `CORE-GDPR-01`, `CORE-SEC-01`, `CORE-SEC-02`.  
  **Key implementation tasks**
  - Implement ToS, Privacy Policy, and disclaimer pages and link them in the UI.
  - Implement consent recording (legal doc version + timestamp).
  - Implement GDPR export/delete flows and admin tooling to process requests.
  - Configure HTTPS, secure secrets management, database encryption where needed.
  - Implement backup jobs and document/verify the restore procedure.

- **Epic E6 – Learn/Blog & Content Infrastructure**  
  **Stories**: `MVP-LEARN-01`, `CORE-CMS-01`, `P2-CONTENT-ADV-01`, `P3-EDU-01`.  
  **Key implementation tasks**
  - Choose content storage approach (headless CMS vs markdown in repo) and implement it.
  - Implement blog listing and article pages wired to the content source.
  - Implement glossary and case‑studies categories.
  - Implement basic admin/content workflow (how you add/edit/publish).
  - Integrate video/course links and optional progress tracking.

---

#### 30.2 Growth & Premium Epics

- **Epic E7 – Portfolio, Advanced Macro & Retail Sentiment**  
  **Stories**: `P2-PORT-01`, `P2-MACRO-ADV-01`, `P2-RET-01`, `P2-EVENT-01`.  
  **Key implementation tasks**
  - Implement portfolio entity and calculations (portfolio GAS, diversification, correlations).
  - Extend macro ingestion for yield curves, recession probabilities, stress index.
  - Implement Reddit ingestion and sentiment scoring; design “retail buzz” charts.
  - Implement event calendar UI and event–price linkage (simple impact view).

- **Epic E8 – Advanced Hedging, Strategy Library & Community**  
  **Stories**: `P2-HEDGE-ADV-01`, `P2-STRAT-01`, `CORE-COMM-01`.  
  **Key implementation tasks**
  - Extend hedging simulator for multi‑leg strategies and richer payoff/backtest outputs.
  - Implement strategy persistence, loading, and (optionally) sharing/leaderboards.
  - Implement community integration (Discord/Reddit links or embedded forum with SSO).

- **Epic E9 – Institutional, API & White‑Label**  
  **Stories**: `P3-API-01`, `P3-WHITELABEL-01`, `P3-BULK-01`, `P3-REPORT-01`.  
  **Key implementation tasks**
  - Design and implement authenticated API (keys, rate‑limits, monitoring).
  - Implement white‑label theming (branding, logo, domains) and configuration.
  - Implement bulk‑analysis endpoints and efficient batch computation.
  - Implement report generation pipeline (PDF/CSV/Excel) with templating and branding.

- **Epic E10 – Mobile & Notifications**  
  **Stories**: `P3-MOBILE-01`, `P3-MOBILE-02`, `CORE-NOTIF-01`, `CORE-EMAIL-01`, `CORE-EMAIL-02`.  
  **Key implementation tasks**
  - Design responsive layouts or dedicated mobile app shell.
  - Implement notification rules engine (conditions → events → channels).
  - Integrate email service provider and implement onboarding + digest flows.
  - Integrate mobile push notification service and map alerts to mobile channels.

---

#### 30.3 Product Analytics & Experimentation

- **Epic E11 – Analytics, KPIs & Experiments**  
  **Stories**: `CORE-ANALYTICS-01`, `CORE-EXPERIMENT-01`, plus KPIs from PRDV3 Section 6.  
  **Key implementation tasks**
  - Define and document the analytics event taxonomy (names, properties).
  - Implement client‑ and/or server‑side tracking for key events.
  - Build basic analytics dashboards for acquisition, activation, engagement and monetisation KPIs.
  - Implement a simple experimentation framework (assignment, exposure tracking, result reading).

---

### 31. Per‑Story Implementation Tasks

The lists below break each story into concrete implementation to‑dos. Use them as a checklist when creating tickets.

---

#### 31.1 MVP Dashboard, GAS, Explanations & Layers

- **MVP-DASH-01 – Dashboard GAS & Market Weather**
  - Design dashboard layout component that can display GAS and Market Weather state for a selected ticker.
  - Implement backend endpoint to return GAS + layer summaries for a single symbol.
  - Wire ticker selector to query the endpoint and update dashboard state.

- **MVP-DASH-02 – Regime & Volatility**
  - Implement regime classification function and store its output alongside GAS.
  - Implement volatility regime calculation from VIX and expose in the API.
  - Display regime + volatility badges on the dashboard with change/highlight logic.

- **MVP-DASH-03 – Multi‑Timeframe Signals**
  - Implement API response shape for timeframe signals (1h, 4h, 1d, 1w, 1m).
  - Build UI tiles that render direction + confidence per timeframe.
  - Handle “insufficient data” states gracefully in UI and API.

- **MVP-EXPL-01 – Why Is This Stock Moving?**
  - Design explanation schema (e.g. template + variables from layers).
  - Implement explanation generator service that consumes current layer values.
  - Render explanation text block in the dashboard and ensure disclaimer is always present.

- **MVP-EXPL-02 – Conflict Detector**
  - Define numeric thresholds and rules for “conflict” between layers/timeframes.
  - Implement conflict detection logic and add to the main dashboard API payload.
  - Implement a reusable conflict warning UI component and integrate it.

- **MVP-SENT-01 – News Sentiment Timeseries**
  - Implement news ingestion and FinBERT scoring job for selected symbols.
  - Implement aggregation logic for 1d/7d/30d sentiment series.
  - Build sentiment chart component and article list UI.

- **MVP-SENT-02 – Source Breakdown**
  - Extend sentiment aggregation to include per‑source statistics.
  - Add per‑source data to the sentiment API response.
  - Build table or chart showing positive/negative share per source.

- **MVP-MACRO-01 – Macro Dashboard Basics**
  - Implement fetchers for FRED, VIX, and yield‑curve data and persist them.
  - Implement macro API endpoint returning latest values and basic interpretations.
  - Build Macro Dashboard UI section with cards/mini‑charts for each indicator.

- **MVP-MACRO-02 – Macro Score**
  - Define scoring formula that maps macro indicators to a 0–100 macro score.
  - Implement macro score computation and store/cache it.
  - Display macro score + label on dashboard and Macro tab.

---

#### 31.2 MVP ML, Backtesting, Hedging, Data

- **MVP-TECH-01 – Competing Models per Timeframe**
  - Implement training pipeline for LSTM, XGBoost, logistic baseline, and Prophet per timeframe.
  - Implement model evaluation that computes Sharpe and accuracy on validation sets.
  - Implement a model registry that records winner per timeframe and stores artefacts.

- **MVP-TECH-02 – Technical Confidence Score**
  - Implement consensus logic to map per‑timeframe signals to a single −1..+1 score.
  - Map consensus score to 0–100 technical confidence as defined in PRD.
  - Add confidence and agreement metrics to the dashboard API and UI.

- **MVP-BACK-01 – Momentum Backtests**
  - Implement generic backtest runner with pluggable strategy rules.
  - Implement momentum strategy rules and parameter schema (SMA length, RSI thresholds, etc.).
  - Implement results object with equity curve and metrics, and render in the Backtesting tab.

- **MVP-BACK-02 – Overfitting Warnings**
  - Implement threshold checks on Sharpe and other metrics to detect “too good” backtests.
  - Add warning messages to the backtest results payload when thresholds are exceeded.
  - Render warnings prominently in UI with links to relevant educational content.

- **MVP-HEDGE-01 – Basic Hedging Simulator**
  - Implement utility functions to estimate beta and correlations between stock and hedge instruments.
  - Implement scenario simulation (e.g. −20% stock move) for unhedged vs hedged P&L.
  - Build UI for configuring hedges and visualising equity/payoff diagrams.

- **MVP-DATA-01 – Data Pipelines & Caching**
  - Implement scheduled jobs for OHLCV, macro, and news ingestion.
  - Implement validation checks and logging/monitoring around pipeline runs.
  - Implement Redis caching for latest GAS and sentiment aggregates; add cache invalidation rules.

---

#### 31.3 MVP Learn, Onboarding & Settings

- **MVP-LEARN-01 – Learn/Blog**
  - Implement content source (CMS or markdown) and content loading logic.
  - Implement Learn/Blog index and detail pages wired to content data.
  - Ensure all article templates include standard disclaimers and metadata.

- **MVP-ONBOARD-01 – In‑App Tour**
  - Define onboarding steps and copy for each tooltip.
  - Implement a tour/coach‑marks component that can be triggered on first login.
  - Persist completion state and provide a way to re‑launch the tour from Settings.

- **CORE-SET-01 – Profile & Preferences**
  - Implement backend endpoints for reading/updating user profile data.
  - Build Settings UI for profile and password changes.
  - Implement validation and error handling for all profile operations.

- **CORE-WATCH-01 – Watchlist**
  - Implement database model for per‑user watchlist entries.
  - Implement endpoints for adding/removing/listing watchlist tickers.
  - Build watchlist UI and integrate with dashboard symbol selection.

---

#### 31.4 Auth, Billing, Legal, Security & Privacy

- **CORE-AUTH-01 – Auth**
  - Integrate chosen auth provider (e.g. Auth0) and configure callbacks.
  - Implement frontend auth flow hooks/guards to protect app routes.
  - Implement logout and token refresh handling.

- **CORE-SUB-01 – Upgrade to Pro**
  - Define Stripe products/plans matching Free/Pro tiers.
  - Implement upgrade UI, checkout flow, and success/failure handling.
  - Implement webhook handler to update user subscription status.

- **CORE-SUB-02 – Manage Subscription**
  - Implement subscription summary endpoint that reads from Stripe/own DB.
  - Build UI in Settings to show plan, renewal date, and invoices.
  - Implement cancellation and downgrade behaviour in accordance with PRD.

- **CORE-LEGAL-01 – Legal Pages & Consent**
  - Implement static content for ToS, Privacy Policy, and main disclaimer.
  - Add legal links to footer/header and sign‑up/login flows.
  - Implement persistence for “accepted terms” with versioning.

- **CORE-GDPR-01 – Data Export/Delete**
  - Implement backend flows for packaging user data for export.
  - Implement backend flows for anonymising/deleting user data.
  - Implement Settings UI to trigger export/delete and track request status.

- **CORE-SEC-01 – 2FA**
  - Integrate a TOTP or similar 2FA provider with user accounts.
  - Build UI for enabling/disabling 2FA and showing recovery options.
  - Update login flow to require second factor when enabled.

- **CORE-SEC-02 – Backups & DR**
  - Configure and schedule automated database and config backups.
  - Document restore procedure and run at least one dry‑run.
  - Integrate backup/restore status into monitoring/alerts.

---

#### 31.5 Notifications, Email & Community

- **CORE-NOTIF-01 – In‑App/Email Alerts**
  - Design rule model (conditions on GAS/regimes/events) and storage.
  - Implement alert evaluation job that runs on schedule or triggers.
  - Integrate with chosen notification channels (email first, others later).

- **CORE-EMAIL-01 – Onboarding Sequence**
  - Create email templates for the onboarding sequence.
  - Implement event‑based triggers (post sign‑up, first backtest, etc.).
  - Integrate with email service provider and track basic delivery metrics.

- **CORE-EMAIL-02 – Newsletter/Digest**
  - Implement newsletter subscription list management (opt‑in/opt‑out).
  - Create digest email template that links to new content and macro summary.
  - Implement a weekly job that composes and sends the digest to subscribers.

- **CORE-COMM-01 – Community Integration**
  - Decide on primary community platform (Discord/Reddit/in‑app).
  - Add navigation entry and SSO/role‑based access if applicable.
  - Document community guidelines and link to them from the app.

---

#### 31.6 Growth, Retail Sentiment, Events & Advanced Macro

- **P2-PORT-01 – Portfolio View**
  - Implement portfolio domain model linking user, portfolio, and positions.
  - Implement portfolio statistics computation (weighted GAS, sector mix, diversification).
  - Build portfolio summary UI and link positions back to single‑stock views.

- **P2-MACRO-ADV-01 – Advanced Macro**
  - Extend macro data ingestion for full yield curve and extra indicators.
  - Implement Macro Stress Index calculation and persistence.
  - Extend Macro Dashboard with additional charts and helper copy.

- **P2-RET-01 – Reddit Retail Sentiment**
  - Implement Reddit ingestion and mapping of posts to tickers.
  - Implement sentiment classification for Reddit posts/comments.
  - Build “retail buzz” UI visualising volume, sentiment, and top comments.

- **P2-EVENT-01 – Event Calendar**
  - Implement event ingestion from GDELT/other sources with normalised schema.
  - Implement API and UI calendar components to show upcoming events.
  - Implement simple event‑to‑price move lookup for past events.

- **P2-HEDGE-ADV-01 – Advanced Hedging**
  - Extend hedging engine to support multi‑leg combinations and parameterisation.
  - Implement more detailed performance and risk metrics for hedged vs unhedged.
  - Enhance hedging UI with configuration controls and comparison views.

- **P2-STRAT-01 – Strategy Library**
  - Implement storage for saved strategies (user‑scoped and optional public).
  - Implement UI for browsing, searching, and loading strategies.
  - Implement leaderboards or popularity metrics if public sharing is enabled.

---

#### 31.7 Premium, Institutional, API & Reporting

- **P3-SENT-ADV-01 – Advanced Sentiment**
  - Implement data collection for Twitter/X, earnings transcripts, and Google Trends.
  - Implement sentiment/score aggregation per source category.
  - Extend sentiment UI with premium view toggle and comparative charts.

- **P3-ANALYTICS-01 – No‑Code Indicator Builder**
  - Implement expression builder that safely combines existing features.
  - Implement validation and sandboxed evaluation of custom indicators.
  - Integrate with backtesting so users can use custom indicators in strategies.

- **P3-API-01 – Public API**
  - Design REST API specification (paths, responses, error codes).
  - Implement API handlers and authentication (keys/OAuth).
  - Implement usage logging and rate limiting.

- **P3-WHITELABEL-01 – White‑Label**
  - Implement theming engine for logos, colours, and domain mappings.
  - Implement configuration admin for white‑label tenants.
  - Ensure legal text and disclaimers adapt correctly to white‑label context.

- **P3-RISK-01 – Scenario & Stress Tests**
  - Implement scenario library (historical + hypothetical shocks).
  - Implement portfolio‑level stress computation for each scenario.
  - Build UI for selecting scenarios and viewing impact summaries.

- **P3-BULK-01 – Bulk Analysis**
  - Implement batch API endpoint or job to process large ticker sets efficiently.
  - Implement batching/pagination of results for UI and API.
  - Provide CSV/Excel export of bulk analysis results.

- **P3-REPORT-01 – Client‑Ready Reports**
  - Design report templates for PDF and CSV/Excel.
  - Implement report generation service using portfolio + scenario data.
  - Implement UI and API for triggering report generation and downloading files.

- **P2-CONTENT-ADV-01 – Advanced Case Studies & Video**
  - Implement content type or category for case studies and advanced content.
  - Create at least one full case study (e.g. 2008, 2020) referencing GAS/macro.
  - Integrate video embeds or links into relevant articles.

- **P3-EDU-01 – Premium Courses/Webinars**
  - Implement course/lesson data model and storage.
  - Implement UI for course listing, details, and progress tracking.
  - Implement webinar scheduling/integration with video platform.

- **P3-MOBILE-01 – Mobile Dashboard**
  - Implement responsive layouts or mobile app components for dashboard.
  - Optimise navigation and performance on mobile devices.
  - Test on a range of screen sizes and browsers/devices.

- **P3-MOBILE-02 – Mobile Push Notifications**
  - Integrate mobile push provider and device registration flow.
  - Map existing alert rules to push notification events.
  - Implement opt‑in/opt‑out and quiet‑hours controls in mobile contexts.

---

_End of user stories v1.5 – includes per‑story implementation task checklists, epic‑level tasks, and full coverage of PRDV3 requirements. Treat this as a living document and refine tasks as you learn during development._

