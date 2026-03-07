# Fin-Eye User Stories — v2.0

**Based on:** PRE-LAUNCH-STRATEGY.md brainstorming session (2026-03-07)  
**Extends:** user-stories.md v1.5  
**Status:** Living document — review at start of each sprint

> This document adds net-new user stories and implementation tasks derived from the pre-launch audit, multi-asset expansion plan, digital nomad content module, digital product showroom, investment strategy planner, advanced indicators roadmap, and the B2B2C "Landlord" architecture pivot. All existing v1.5 story IDs remain valid and unchanged.

---

## Table of Contents

1. [Security Hardening (SEC)](#1-security-hardening)
2. [Multi-Asset ML Expansion (ASSET)](#2-multi-asset-ml-expansion)
3. [Advanced Indicators (IND)](#3-advanced-indicators)
4. [Digital Nomad & Lifestyle Finance Content (NOMAD)](#4-digital-nomad--lifestyle-finance-content)
5. [Digital Product Showroom v2 (SHOP)](#5-digital-product-showroom-v2)
6. [Investment Strategy Planner (PLAN)](#6-investment-strategy-planner)
7. [B2B2C Landlord Architecture (B2B)](#7-b2b2c-landlord-architecture)
8. [Product Polish & Gap Closure (POLISH)](#8-product-polish--gap-closure)
9. [Implementation Task Checklists](#9-implementation-task-checklists)

---

## 1. Security Hardening

> Priority: ALL stories in this section are **pre-launch blockers**. None of the following stories are optional.

---

**Story ID: SEC-01**  
**As the platform operator, I want** all production secrets rotated and removed from version control **so that** no committed credentials can be exploited after the repository is ever made public or accessed by an unauthorised party.

**Acceptance Criteria**
- `FINNHUB_API_KEY`, `FRED_API_KEY`, `JWT_SECRET`, and the TOTP Fernet key are all rotated to fresh values.
- `.env` is listed in `.gitignore` and confirmed via `git check-ignore -v .env`.
- `.env.example` exists with clearly labelled placeholder values only (e.g. `FINNHUB_API_KEY=your_key_here`).
- `git log` and `git grep` confirm no real secret values remain anywhere in repository history.
- All deployment environments pull secrets from a secret manager or environment variable injection — never from committed files.

---

**Story ID: SEC-02**  
**As the platform operator, I want** production configuration locked down before any public traffic reaches the app **so that** debug output, open CORS, and unauthenticated access cannot be exploited.

**Acceptance Criteria**
- `REQUIRE_AUTH=True` is the default in all non-development environments.
- `DEBUG=False` in staging and production; stack traces never exposed via `/docs` error responses.
- `ALLOWED_ORIGINS` is set to the specific production domain (e.g. `["https://app.fin-eye.com"]`), not `["*"]`.
- A deployment checklist item confirms these three values are verified before each production deploy.

---

**Story ID: SEC-03**  
**As the platform operator, I want** rate limiting on all authentication endpoints **so that** brute-force and credential-stuffing attacks are prevented.

**Acceptance Criteria**
- `slowapi` (or equivalent) middleware is applied to:
  - `POST /auth/login` — max 10 requests/minute per IP.
  - `POST /auth/register` — max 5 requests/minute per IP.
  - `POST /auth/2fa/verify` — max 5 requests/minute per IP.
- Requests exceeding the limit receive a `429 Too Many Requests` response.
- Rate limit counters are stored in Redis so they survive app restarts and work in multi-instance deploys.
- Tests exist covering both the happy path and the rate-limited path.

---

**Story ID: SEC-04**  
**As the platform operator, I want** refresh token rotation and a logout blacklist **so that** stolen tokens cannot be replayed after a user logs out.

**Acceptance Criteria**
- Every call to `POST /auth/refresh` invalidates the presented refresh token and issues a new one.
- Issued refresh token JTIs are stored in Redis with the token's TTL.
- `POST /auth/logout` adds the refresh token's JTI to a Redis blocklist.
- Auth middleware rejects any access token whose associated refresh token JTI is on the blocklist.
- Existing sessions on other devices are not invalidated unless a "log out everywhere" action is taken.

---

**Story ID: SEC-05**  
**As any user, I want** my account locked temporarily after repeated failed login attempts **so that** automated credential stuffing attacks cannot succeed over time.

**Acceptance Criteria**
- After 10 failed login attempts within a 15-minute sliding window, the account is locked for 30 minutes.
- Attempt counts and lock state are stored in Redis keyed by (email + IP).
- Locked accounts receive a clear error message indicating when the lock expires.
- A successful login resets the failed-attempt counter.
- Admin users can manually unlock any account from the ops dashboard.

---

**Story ID: SEC-06**  
**As the platform operator, I want** security headers applied to all HTTP responses **so that** common browser-based attacks (XSS, clickjacking, MIME sniffing) are mitigated without any frontend changes.

**Acceptance Criteria**
- A `SecurityHeadersMiddleware` is registered on the FastAPI app that sets at minimum:
  - `Content-Security-Policy`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Strict-Transport-Security` (HTTPS only)
- Headers are verified in integration tests via response inspection.
- No existing frontend functionality is broken by the CSP policy.

---

**Story ID: SEC-07**  
**As any user, I want** email verification enforced before I can access protected features **so that** unverified accounts cannot consume premium resources or create misleading signals in usage analytics.

**Acceptance Criteria**
- The `is_verified` column in the users table is checked by a `get_current_active_verified_user` dependency.
- All sensitive endpoints (watchlist, backtesting, GAS fetch, portfolio) use this dependency.
- Unverified users who attempt to access these endpoints receive a `403 Forbidden` response with a clear message prompting email verification.
- The verification email is re-sendable from the Settings page.
- Verification link tokens expire after 24 hours.

---

**Story ID: SEC-08**  
**As the platform operator, I want** ML model artifacts stored in cloud object storage rather than the local filesystem **so that** pod restarts or redeployments on cloud platforms do not result in lost models.

**Acceptance Criteria**
- All model files previously in `model_store/` are migrated to Cloudflare R2 (or S3-compatible).
- The ML pipeline reads and writes model artifacts from R2 using a configured `MODEL_STORE_BUCKET` env variable.
- Local `model_store/` is removed from the repository and added to `.gitignore`.
- On a fresh deployment with an empty local filesystem, the ML inference service correctly downloads and uses models from R2 on first startup.

---

## 2. Multi-Asset ML Expansion

---

**Story ID: ASSET-CRYPTO-01**  
**As Marco (retail trader), I want** to analyse BTC, ETH, and other major cryptocurrencies using the same GAS/ML intelligence framework as equities **so that** I can apply a consistent analysis methodology to the crypto assets already in my portfolio.

**Acceptance Criteria**
- BTC-USD, ETH-USD, and BNB-USD are available as selectable symbols on the dashboard.
- OHLCV data for these symbols is ingested from the Binance REST API or CoinGecko on a 24/7 schedule (not restricted to market hours).
- The ML pipeline removes market-hours filtering when processing crypto symbols.
- The GAS score is computed for crypto symbols using the existing layer framework.
- A **Crypto Fear & Greed Index** (sourced from Alternative.me) is displayed as a supplementary indicator on crypto symbol pages.

---

**Story ID: ASSET-CRYPTO-02**  
**As Marco, I want** on-chain and derivatives data included in the crypto analysis **so that** I can see signals that are unique to the crypto asset class and not available for equities.

**Acceptance Criteria**
- For supported crypto symbols, the following additional data points are fetched and displayed:
  - Funding rate (from Binance perpetual futures).
  - Open interest (from Binance or Coinglass).
  - Exchange netflow (from CryptoCompare or Glassnode free tier).
- These fields are added as supplementary features in the crypto ML training pipeline.
- The Crypto-specific data panel is visually distinct from the standard equity indicators panel.
- Data unavailability degrades gracefully to a "Data unavailable" state without breaking the rest of the page.

---

**Story ID: ASSET-COMMODITY-01**  
**As Emma (finance student), I want** to analyse major commodities (Gold, Oil, Natural Gas, Silver, Copper) in Fin-Eye **so that** I can understand cross-asset relationships and how commodity trends affect equity regimes.

**Acceptance Criteria**
- GC=F (Gold), CL=F (Crude Oil), NG=F (Natural Gas), SI=F (Silver), HG=F (Copper) are available as selectable symbols.
- OHLCV data is fetched via `yfinance` on the existing equity schedule.
- Seasonal decomposition features (sin/cos of week-of-year and month) are added to the commodity ML feature set.
- A **COT (Commitment of Traders) Report** widget is displayed for commodity symbols showing commercial vs speculative positioning, sourced from the CFTC free API.
- Commodity symbols are grouped under a "Commodities" category in the symbol selector.

---

**Story ID: ASSET-FOREX-01**  
**As Marco, I want** to analyse major FX pairs (EUR/USD, GBP/USD, USD/JPY, USD/CHF) using the Fin-Eye framework **so that** I can track macro-driven currency flows and their relationship to equity risk-on/risk-off regimes.

**Acceptance Criteria**
- EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X are available as selectable symbols via `yfinance`.
- An **Interest Rate Differential** feature (sourced from FRED, computed as the spread between the two relevant central bank policy rates) is added to the Forex ML feature set.
- A **Currency Strength Index** widget (basket-weighted vs USD) is shown for each FX pair.
- Forex symbols are grouped under a "Forex" category in the symbol selector.
- The Macro Dashboard shows a "Central Bank Calendar" section listing upcoming rate decisions for G10 currencies.

---

**Story ID: ASSET-ETF-01**  
**As Alex (institutional analyst), I want** expanded ETF coverage including international, factor, and thematic ETFs **so that** I can use Fin-Eye to analyse a broader investable universe across geographies and investment styles.

**Acceptance Criteria**
- The following ETFs are added to the symbol list and fully supported:
  - International: EWJ, EWZ, FXI, EEM.
  - Factor: VTV, VUG, MTUM, QUAL, USMV.
  - Thematic: ICLN, AIQ, SOXX, XBI.
- All ETFs are processed through the existing ML and GAS pipeline without modification.
- ETFs are grouped in the symbol selector under "ETFs → International", "ETFs → Factor", and "ETFs → Thematic" subcategories.

---

**Story ID: ASSET-ML-01**  
**As the ML engineer, I want** a 4-hour timeframe model added to the ML consensus **so that** the multi-timeframe ensemble covers all 5 timeframes specified in the PRD (1h, 4h, 1d, 1w, 1m).

**Acceptance Criteria**
- A 4h OHLCV data ingestion job exists and populates a `ohlcv_4h` table.
- Training scripts support `timeframe="4h"` with appropriate data windowing.
- The model competition (LSTM, XGBoost, Logistic, Prophet) runs for 4h and a winner is selected by Sharpe ratio.
- The 4h signal is included in the ensemble consensus computation and in the multi-timeframe tile on the dashboard.
- All existing 4-timeframe tests pass with 5 timeframes present.

---

**Story ID: ASSET-ML-02**  
**As the ML engineer, I want** model drift detection and walk-forward validation with Bayesian optimisation **so that** live model performance is monitored and hyperparameters are tuned systematically rather than by hand.

**Acceptance Criteria**
- Walk-forward validation splits the training data into rolling windows and re-evaluates each model.
- Bayesian optimisation (via `optuna` or equivalent) is run during training to select optimal hyperparameters per model per timeframe.
- A `model_performance_log` table records live inference accuracy daily by comparing predictions to subsequent realised outcomes.
- If a model's rolling 30-day live Sharpe drops more than 20% below its training-time Sharpe, a drift alert is sent to the ops notification channel.
- A `/admin/ml/drift-report` endpoint returns per-model drift metrics for inspection.

---

**Story ID: ASSET-ML-03**  
**As Marco, I want** to see a "Feature Importance" panel for the current GAS signal **so that** I can understand which underlying drivers are most responsible for today's score.

**Acceptance Criteria**
- For the currently selected symbol and timeframe, the backend computes SHAP feature importance values for the winning XGBoost model.
- The top 5 most important features are returned in the GAS API payload.
- A "What's driving this?" expandable panel on the dashboard shows each feature with its name (human-readable), its current value, and its contribution (positive/negative) to the signal.
- If SHAP computation is unavailable (e.g. non-tree model is the winner), the panel shows "Explanation not available for this model type" rather than an error.

---

## 3. Advanced Indicators

---

**Story ID: IND-TIER1-01**  
**As Marco, I want** access to Williams %R, Keltner Channels, Parabolic SAR, ADX, CMF, Donchian Channels, MFI, TRIX, Ichimoku Cloud, DEMA/TEMA, Ultimate Oscillator, and Elder Ray in the custom indicator builder **so that** I have a richer palette of proven technical tools to design and backtest strategies.

**Acceptance Criteria**
- All 12 new indicators are implemented in `indicator_service.py` using pure pandas (no new pip dependencies).
- Each indicator is accessible via the custom indicator builder UI and the backtesting engine.
- Each indicator has a unit test covering at least one known output value against a reference dataset.
- Indicator definitions are documented in the Learn/Glossary section with a plain-language explanation of each one's use case.

---

**Story ID: IND-COMPOSITE-01**  
**As Marco, I want** access to Fin-Eye's unique composite indicators (GAS-Weighted RSI, Macro-Sentiment Divergence Index, Regime-Conditioned Bollinger Bands, Smart Money Index) **so that** I can use signals that combine the platform's proprietary layers into something not available on any other tool.

**Acceptance Criteria**
- The following composite indicators are implemented in `composite_indicator_service.py` and available as optional overlay panels on the dashboard:
  - **GAS-Weighted RSI**: RSI amplitude scaled by the current GAS score.
  - **Macro-Sentiment Divergence Index**: Absolute difference between macro score and sentiment score, with a rolling z-score.
  - **Regime-Conditioned Bollinger Bands**: BB width multiplied by a VIX regime factor.
  - **Smart Money Index (SMI) Approximation**: First 30-minute vs last 30-minute session performance ratio.
- These composites are labelled "Fin-Eye Proprietary" in the UI with a tooltip explaining what makes them unique.
- They can be used as inputs in the custom indicator builder and as signals in backtesting strategies.

---

**Story ID: IND-COMPOSITE-02**  
**As Alex, I want** a Cross-Asset Correlation Heatmap for my watchlist **so that** I can visualise dynamic portfolio risk and understand which holdings are moving together.

**Acceptance Criteria**
- The Correlation Heatmap page (accessible from the Portfolio section) renders a square heatmap of 30-day rolling pairwise correlations for all symbols in the user's watchlist.
- Colours range from deep red (perfect negative correlation) through white (zero) to deep green (perfect positive correlation).
- A "Diversification Score" (average absolute off-diagonal correlation, inverted) is displayed above the heatmap with a colour-coded label (Highly Diversified / Moderate / Concentrated).
- Hovering a cell shows the exact correlation value and a sparkline of both assets over the 30-day window.
- The heatmap updates when the user modifies their watchlist.

---

## 4. Digital Nomad & Lifestyle Finance Content

---

**Story ID: NOMAD-01**  
**As Emma or a financially independent reader, I want** a dedicated Lifestyle Finance section in Fin-Eye's content area **so that** I can find high-quality, structured information about tax residency, legal structures, and international investing in one place.

**Acceptance Criteria**
- A "Lifestyle" section is added to the navigation alongside "Learn".
- A hub page at `/lifestyle` shows four content pillars with cards: Tax Residency & Tax Havens, Legal Investment Structures, Digital Nomad Banking & Investing, International Estate & Pension Planning.
- All pages include a prominent, non-dismissable disclaimer: "All content is for educational and informational purposes only. This is not legal or tax advice. Consult a qualified professional before making decisions."
- Content is tagged with relevant keywords for SEO.

---

**Story ID: NOMAD-02**  
**As an investor considering international residency, I want** an interactive tax residency comparison table **so that** I can filter and compare countries by the criteria most relevant to my situation.

**Acceptance Criteria**
- The page at `/lifestyle/tax-residency` features an interactive table covering at minimum 10 countries: UAE, Portugal (IFICI), Cyprus, Malta, Georgia, Paraguay, Panama, Estonia (e-Residency), Thailand (LTR Visa), Cayman Islands.
- Each row displays: personal income tax rate, capital gains tax rate, minimum stay requirement, approximate setup cost, and a "Suitability" tag.
- Users can filter by columns (e.g. "show only 0% capital gains countries") and sort by any column.
- A fixed callout at the top warns US citizens about worldwide taxation obligations (FATCA/FBAR).
- A "Key Concepts" accordion below the table explains: tax residency vs permanent residency vs citizenship, OECD BEPS substance requirements, double taxation treaties.

---

**Story ID: NOMAD-03**  
**As an entrepreneur or investor, I want** a structured comparison of international legal entity types **so that** I can understand which structure fits my profile without spending hours on preliminary research.

**Acceptance Criteria**
- The page at `/lifestyle/legal-structures` shows a comparison table covering 9 structures: Cyprus Holding + IP Box, US LLC (Wyoming/Delaware), UAE Freezone LLC, Cayman Islands Fund, UK LLP, BVI Company, Irish Holding Co, Singapore Pte Ltd, Estonian OÜ.
- Each row shows: jurisdiction, best-use profile, approximate setup cost, approximate annual maintenance cost.
- An interactive "Which structure fits me?" filter lets users select founder residency region and primary income type and filters the table accordingly.
- A dedicated subsection covers: substance requirements, CFC rules, transfer pricing, beneficial ownership registers.
- A "Turkish founder" callout explains the commonly used UAE/Cyprus path with a practical step-by-step sequence.

---

**Story ID: NOMAD-04**  
**As a digital nomad or expat investor, I want** a practical guide to banking, investing, and financial services available to non-residents **so that** I know which providers and accounts I can actually open given my residency situation.

**Acceptance Criteria**
- The page at `/lifestyle/investment-abroad` covers: multi-currency banking (Wise, Revolut Business, Mercury, Starling), investment accounts accessible to non-residents (IBKR, DEGIRO), crypto custody and tax reporting tools, international health insurance options, and expat pension/retirement vehicles (SIPP, QROPS, Roth IRA conversion).
- Content is structured as a practical checklist with expandable detail sections.
- All product/service links are informational (not affiliate links unless explicitly disclosed).

---

**Story ID: NOMAD-CMS-01**  
**As the content admin, I want** the Lifestyle Finance content managed through the same CMS workflow as the existing Learn/Blog content **so that** I do not need separate infrastructure to publish and update lifestyle articles.

**Acceptance Criteria**
- The existing CMS supports a "Lifestyle" category alongside existing categories.
- Lifestyle articles appear both in the `/lifestyle` section and optionally in the main `/learn` feed if tagged accordingly.
- SEO metadata (title, meta description, OG image) is configurable per lifestyle article.
- New lifestyle article templates automatically include the financial information disclaimer.

---

## 5. Digital Product Showroom v2

> Extends existing `CORE-SHOP-01` and `CORE-SHOP-02` stories.

---

**Story ID: SHOP-V2-01**  
**As a user browsing the Product Showroom, I want** to preview a product before buying it **so that** I can verify it meets my needs without committing to a purchase.

**Acceptance Criteria**
- Each product card includes a "Preview" button.
- Clicking "Preview" opens a read-only embedded Google Sheets link (or PDF preview) in a modal or new tab.
- The preview is clearly watermarked or labelled "Sample / Preview Only".
- Products without a preview file configured show the "Preview" button in a disabled state.

---

**Story ID: SHOP-V2-02**  
**As a user purchasing a digital product, I want** to gift it to someone else by entering their email address **so that** I can send financial tools as a gift without requiring the recipient to be a Fin-Eye user first.

**Acceptance Criteria**
- On the product detail view, an optional "Gift this" toggle reveals a "Recipient email" input field.
- When gifted, the LemonSqueezy checkout is configured to deliver the download link to the recipient's email.
- The gifter receives a confirmation email confirming the gift was sent.
- If the delivery fails, the gifter is notified within 24 hours.

---

**Story ID: SHOP-V2-03**  
**As a user interested in multiple products, I want** to purchase a discounted bundle **so that** I can get more tools at a lower total cost.

**Acceptance Criteria**
- At least one bundle is configured (e.g. "Investor Bundle": Portfolio Tracker + Retirement Calculator + Dividend Tracker for €29.99 vs €37.97 separately).
- Bundle cards are displayed at the top of the Showroom page with a "Save X%" badge.
- Bundles are processed as a single LemonSqueezy variant that delivers all included product files.
- A "What's included" expandable section lists each product in the bundle with its individual description.

---

**Story ID: SHOP-V2-04**  
**As the product owner, I want** to see star ratings and review counts on product cards **so that** social proof increases conversion and I can identify which products are most valued.

**Acceptance Criteria**
- Each product has a star rating (1–5) and a review count displayed on both the card and detail view.
- For launch, ratings are manually seeded from beta tester feedback; a formal review submission flow can be added post-launch.
- Products with no ratings yet display "No reviews yet" rather than a 0-star display.
- The admin product management view allows editing of seed ratings.

---

**Story ID: SHOP-ROADMAP-01**  
**As a power user, I want** to be notified when upcoming products (FIRE Calculator, Tax-Loss Harvesting Tracker, Crypto Tax Report Generator, Real Estate Analyzer, DCA Bot Tracker) become available **so that** I don't miss tools I'm interested in.

**Acceptance Criteria**
- A "Coming Soon" section at the bottom of the Showroom page lists roadmap products with brief descriptions.
- Each coming-soon item has a "Notify me" button that stores the user's email preference against that product.
- When a coming-soon product is published, all opted-in users receive an email notification.
- The admin panel allows promoting a product from "Coming Soon" to "Live" status, which triggers the notification batch.

---

## 6. Investment Strategy Planner

---

**Story ID: PLAN-01**  
**As Emma, I want** to complete a risk profile quiz that classifies me as Aggressive, Moderate, Conservative, or Income-focused **so that** the app can personalise its suggestions and alert thresholds to match my actual risk tolerance.

**Acceptance Criteria**
- A 5-question risk profile quiz is accessible from the Dashboard or Settings.
- Questions cover: investment time horizon, reaction to a 20% portfolio drop, income stability, existing emergency fund, and primary investment goal.
- The quiz outputs one of four profiles: Aggressive, Moderate, Conservative, Income.
- The assigned profile is stored on the user record and is visible in Settings.
- GAS alert default thresholds are automatically adjusted based on profile (e.g. Conservative → alert at GAS < 45; Aggressive → alert only at GAS < 25).
- Users can retake the quiz at any time and the profile updates accordingly.

---

**Story ID: PLAN-02**  
**As Emma, I want** a suggested asset allocation based on my risk profile, age, and investment time horizon **so that** I have a structured starting point for building a portfolio.

**Acceptance Criteria**
- Inputs: risk profile (auto-filled from quiz), age, investment time horizon (years), and primary currency.
- Output: a suggested percentage allocation across asset classes: Global Equities, Bonds/Fixed Income, Cash, Commodities, Real Estate/REITs, Alternative/Crypto (optional).
- Allocation is displayed as both a pie chart and a table.
- A prominent disclaimer reads: "This is a planning tool for educational purposes only. It is not personalised financial advice. Consult a qualified financial adviser before making investment decisions."

---

**Story ID: PLAN-03**  
**As Marco, I want** a rebalancing calculator that shows me the trades required to bring my actual holdings back to my target allocation **so that** I can maintain my intended risk profile as markets move.

**Acceptance Criteria**
- The user can enter their current holdings (symbol + value) alongside their target allocation percentages.
- The calculator outputs a "Suggested Trades" table showing: symbol, current %, target %, difference, and indicative trade direction (Buy/Sell/Hold) and approximate trade size.
- Trades are labelled "Suggested — Not Instructions" and are not connected to any execution engine.
- The tool is linked from the Portfolio page as "Rebalance this portfolio".
- Output can be exported as CSV.

---

**Story ID: PLAN-04**  
**As Emma, I want** a Dollar-Cost Averaging (DCA) Simulator that models how a recurring investment into a symbol would have grown historically **so that** I can visualise the smoothing effect of DCA compared to lump-sum investing.

**Acceptance Criteria**
- Inputs: symbol, recurring investment amount, investment frequency (weekly/monthly), start date, end date.
- Output: side-by-side equity curve comparing DCA vs lump-sum (same total capital deployed on start date).
- Statistics shown: total invested, final portfolio value, CAGR, max drawdown for both strategies.
- At least 5 years of historical OHLCV data is used.
- The standard backtesting disclaimer is displayed alongside results.

---

**Story ID: PLAN-05**  
**As Emma, I want** a Sequence of Returns Risk Visualiser **so that** I understand how retiring into a bear market affects long-term portfolio survival — one of the most important and under-discussed risks in retirement planning.

**Acceptance Criteria**
- Inputs: starting portfolio value, annual withdrawal amount, expected annual return, retirement duration (years), withdrawal start year.
- The visualiser runs three scenarios: retiring just before a historical bear market (2000, 2008, 2020), at market peak, and in a neutral year.
- Output: three equity curves showing portfolio value over the retirement duration for each scenario.
- A "Portfolio Survival Rate" percentage is shown (how many historical sequences resulted in non-zero balance at end of period).
- A plain-English explanation of sequence risk is always shown below the tool.

---

**Story ID: PLAN-06**  
**As Alex, I want** a Bond Ladder Builder that helps me plan a fixed-income ladder across defined maturities **so that** I can structure predictable income from bonds without needing specialist software.

**Acceptance Criteria**
- Inputs: total capital to allocate, number of rungs (years), starting year, currency.
- Output: a table showing each rung (year 1 through N), capital allocated per rung, current yield for that maturity (from FRED Treasury data), and estimated annual income.
- A visual bar chart shows the ladder structure across years.
- Disclaimer: "This tool uses current yield data for illustration. Actual bond pricing varies. This is not financial advice."
- The tool links to the Macro Dashboard yield curve widget for context.

---

## 7. B2B2C Landlord Architecture

> These stories implement multi-tenancy so financial advisors can subscribe as tenants and provide branded Fin-Eye access to their clients. All stories are backwards-compatible with existing B2C users.

---

**Story ID: B2B-TENANT-01**  
**As a financial advisor, I want** to register my firm as a Tenant and invite my clients to access a branded portal **so that** I can offer market intelligence as part of my advisory service without building my own data platform.

**Acceptance Criteria**
- A `/advisors/register` flow allows an advisor to create a Tenant account with: firm name, logo upload, primary colour, custom subdomain (e.g. `smithfa.fin-eye.com`), and billing details.
- A `tenants` table is created with columns: `id`, `slug`, `name`, `logo_url`, `brand_colour`, `subdomain`, `ai_narrator_config` (JSON), `subscription_tier`, `created_at`.
- The advisor can invite clients via email from their admin panel; an invitation token is generated and a `tenant_memberships` row is created linking the user to the tenant on acceptance.
- Existing B2C users are unaffected (their `tenant_id` remains `null`).
- A Pydantic model validates that the subdomain slug is URL-safe, unique, and does not conflict with reserved platform paths.

---

**Story ID: B2B-TENANT-02**  
**As a financial advisor, I want** my clients to see Fin-Eye's intelligence presented under my firm's branding **so that** the experience feels like part of my service.

**Acceptance Criteria**
- When a client accesses via the advisor's subdomain, the frontend renders: the advisor's logo in place of the Fin-Eye logo, the advisor's primary brand colour as the accent colour, and the firm name in page titles and email subjects.
- The white-label rendering is driven entirely by the `tenants` record — no code changes needed to onboard a new advisor.
- Fin-Eye branding is hidden from the client-facing UI except in the footer legal text where required.
- The footer reads: "Powered by Fin-Eye" in a subtle, non-prominent style.

---

**Story ID: B2B-ISOLATION-01**  
**As the platform operator, I want** tenant data strictly isolated at the application layer **so that** advisor A cannot see advisor B's clients and a client cannot see another client's data.

**Acceptance Criteria**
- A `TenantContext` dataclass is injected via FastAPI dependency injection into all endpoints that handle portfolio, watchlist, alert, or user data.
- `TenantContext` exposes: `user_id`, `tenant_id` (nullable), `role` (`client` | `advisor` | `admin`).
- All database queries for client-specific resources include `.where(resource.tenant_id == ctx.tenant_id)` as a mandatory filter.
- Composite indexes are added on `(tenant_id, user_id)` for Portfolio, Watchlist, and Alert tables.
- An integration test verifies that an advisor from tenant A cannot retrieve data belonging to tenant B even with a valid JWT.

---

**Story ID: B2B-NARRATOR-01**  
**As a financial advisor, I want** to configure the tone, persona, and brand name used in AI narrations my clients receive **so that** GAS explanations and daily briefings sound like they come from my firm.

**Acceptance Criteria**
- The advisor admin panel includes an "AI Narrator" configuration section with fields: tone (Professional / Friendly / Concise), AI persona label, brand name used in narration, advisor firm name, list of forbidden topics, and max response word count.
- These values are stored in the `ai_narrator_config` JSON column on the `tenants` table.
- The narration service renders a system prompt from a Jinja2 template that injects these values per request.
- A mandatory disclaimer is hard-coded into the prompt template and cannot be removed: "This briefing is market intelligence provided by {brand_name}. Speak with {advisor_name} for advice specific to your situation."
- The default config (used for B2C users with `tenant_id = null`) produces the existing Fin-Eye narration behaviour unchanged.

---

**Story ID: B2B-GAS-WEIGHTS-01**  
**As a financial advisor, I want** to adjust the weighting of the Technical, Macro, and Sentiment layers in the GAS score for my clients **so that** the intelligence score reflects my firm's analysis methodology.

**Acceptance Criteria**
- The advisor admin panel includes a "GAS Weight Profile" section with three sliders: Technical weight, Macro weight, Sentiment weight.
- Three preset profiles are offered as starting points: "Macro-Focused" (20/55/25), "Momentum Trader" (60/20/20), "Balanced" (40/30/30 — default).
- Pydantic validation enforces that the three weights must sum to exactly 1.0; a 422 error is returned otherwise.
- The GAS computation function accepts an optional `weights` parameter; if `None`, the default weights are used (backwards compatible with existing B2C behaviour).
- Per-client GAS scores computed with non-default weights are annotated in the compliance audit log with the weights that were used.

---

**Story ID: B2B-COMPLIANCE-01**  
**As a financial advisor operating under regulatory requirements, I want** a complete compliance audit log of what intelligence was shown to each client **so that** I can produce evidence for regulators demonstrating that Fin-Eye outputs are educational data, not personalised investment advice.

**Acceptance Criteria**
- A `compliance_audit_logs` table is created as append-only (no UPDATE or DELETE operations via the application).
- A log row is written for every: GAS score display, AI narration generation, backtest result display, and scenario/stress-test output.
- Each row records: `client_user_id`, `advisor_tenant_id`, `event_type`, `symbol` (if applicable), `score_value`, `gas_weights_used` (JSON), `timestamp`, `ip_address`, `request_id`.
- The log writer never raises an exception to the main request handler — a logging failure must never break the user-facing request.
- Advisors can access `GET /compliance/audit-log?client_id=&from=&to=` to retrieve their tenant's audit trail with pagination and CSV export.

---

**Story ID: B2B-BILLING-01**  
**As a financial advisor, I want** a per-tenant billing model based on the number of active client seats **so that** my subscription cost scales with actual usage.

**Acceptance Criteria**
- Advisor billing tiers are defined: Starter (up to 10 clients), Growth (up to 50 clients), Enterprise (unlimited, custom pricing).
- Stripe metered billing is used for seat count so the monthly invoice reflects the peak active client count for the billing period.
- When an advisor exceeds their tier's seat limit, they are prompted to upgrade; new client invitations are blocked until they do.
- Advisors receive a monthly billing summary email showing seat count, tier, and invoice amount.
- Upgrading or downgrading tiers takes effect at the next billing cycle.

---

## 8. Product Polish & Gap Closure

---

**Story ID: POLISH-01**  
**As any user, I want** a single Watchlist Dashboard view showing a GAS mini-card for every symbol in my watchlist **so that** I can do a rapid portfolio health check at a glance instead of clicking through each symbol one at a time.

**Acceptance Criteria**
- A "Watchlist Overview" page is accessible from the primary navigation.
- For each symbol in the user's watchlist, a compact card is displayed showing: ticker, company name, current GAS score (0–100), GAS colour indicator (green/amber/red), Market Weather label, and whether any conflicts are active.
- Cards are sorted by GAS score descending by default; users can sort by ticker or change direction.
- Clicking a card navigates to the full single-symbol dashboard for that ticker.
- The page shows a "Last updated" timestamp.

---

**Story ID: POLISH-02**  
**As any user, I want** a symbol search autocomplete that helps me find tickers by company name or ticker symbol **so that** I don't have to know exact ticker strings from memory.

**Acceptance Criteria**
- The ticker input has an autocomplete dropdown powered by the Finnhub `/search` endpoint.
- As the user types 2 or more characters, results appear within 300ms showing: ticker, company name, exchange, and instrument type.
- Results are limited to 8 suggestions.
- Selecting a result populates the ticker field and triggers the data load.
- If the Finnhub search API is unavailable, the input falls back to free-form entry without breaking the page.

---

**Story ID: POLISH-03**  
**As Marco, I want** to receive a GAS threshold notification when the score crosses 35 or 65 for any symbol in my watchlist **so that** I am alerted to significant regime changes without having to monitor the dashboard continuously.

**Acceptance Criteria**
- Two default notification rules are automatically created for every watchlist symbol a user adds:
  - GAS crosses below 35 (entering "Headwind" territory) → email alert.
  - GAS crosses above 65 (entering "Mild Support" territory) → email alert.
- Users can modify or delete these rules from the Notifications settings page.
- Email alerts include: symbol, GAS score at trigger time, previous GAS score, trigger condition, and a link back to the dashboard.
- Alerts are not re-sent more than once per 4-hour window per symbol to prevent notification flooding.

---

**Story ID: POLISH-04**  
**As any user, I want** to export backtesting results, GAS score history, and portfolio analysis to CSV or PDF **so that** I can work with Fin-Eye data in external tools or share it with others.

**Acceptance Criteria**
- An "Export" button is available on: the Backtesting results page, the GAS history chart (per symbol), and the Portfolio overview.
- CSV export produces a well-structured file with headers, ISO timestamps, and numeric values without currency symbols.
- PDF export produces a formatted summary including the Fin-Eye logo, timestamp, symbol/portfolio name, key metrics, and a footer with the standard educational disclaimer.
- PDF generation uses server-side rendering (not browser print) to ensure consistent output.
- Export requests for large date ranges (> 1 year of daily data) are handled asynchronously with an email delivery option.

---

**Story ID: POLISH-05**  
**As any user, I want** a dark/light mode toggle **so that** I can use the app comfortably in different lighting conditions and in line with my OS preference.

**Acceptance Criteria**
- A mode toggle (sun/moon icon) is accessible from the top navigation bar on all pages.
- On first load, the app defaults to the user's OS preference (`prefers-color-scheme`).
- The user's manual toggle choice is persisted in `localStorage` and restored on next visit.
- Both modes pass WCAG AA contrast ratio requirements for all text elements.
- No feature is hidden or visually broken in light mode compared to dark mode.

---

**Story ID: POLISH-06**  
**As a new user, I want** the onboarding tour updated to cover all current pages (Watchlist Overview, Lifestyle, Product Showroom, Strategy Planner) **so that** the tour does not skip pages added after the original tour was written.

**Acceptance Criteria**
- The onboarding tour is extended with new steps covering: Watchlist Overview, the Lifestyle Finance section, the Product Showroom, and the Strategy Planner.
- Tour step content matches the current UI (labels, button text, navigation structure).
- Existing tour steps are reviewed and any stale copy is corrected.
- The tour can be re-triggered from Settings → "Restart tour".
- Tour completion state is stored per-user in the database so it persists across devices.

---

## 9. Implementation Task Checklists

### 9.1 Security Hardening

- **SEC-01** — Rotate FINNHUB_API_KEY, FRED_API_KEY, JWT_SECRET, TOTP Fernet key. Add `.env` to `.gitignore`. Create `.env.example`. Audit git history for committed secrets.
- **SEC-02** — Set `REQUIRE_AUTH=True`, `DEBUG=False`, lock `ALLOWED_ORIGINS` in non-dev environments. Add CI pre-deploy check.
- **SEC-03** — Install `slowapi`, configure Redis-backed limiter, apply limits to `/auth/login`, `/auth/register`, `/auth/2fa/verify`. Write 429 tests.
- **SEC-04** — Add `jti` (UUID) to refresh token payload. Store in Redis with TTL. On `/auth/refresh` delete old JTI, issue new one. On `/auth/logout` add JTI to blocklist. Middleware rejects blocklisted JTIs.
- **SEC-05** — Implement Redis key `lockout:{email}:{ip}` with 15-minute sliding window. Lock account for 30 minutes after 10 failures. Add `/admin/users/unlock` endpoint.
- **SEC-06** — Implement `SecurityHeadersMiddleware` with CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS. Add header assertion integration tests.
- **SEC-07** — Create `get_current_active_verified_user` dependency. Apply to sensitive endpoints. Add "Resend verification email" button to Settings. Set token expiry to 24 hours.
- **SEC-08** — Configure R2/S3 client with `MODEL_STORE_BUCKET` env var. Replace all local `model_store/` file I/O with R2 helpers. Add R2 download on startup. Remove `model_store/` from repo.

---

### 9.2 Multi-Asset ML Expansion

- **ASSET-CRYPTO-01/02** — Add Binance REST OHLCV fetcher with 24/7 schedule. Add crypto symbol list. Implement `GET /crypto/fear-greed`. Add funding rate + open interest fetcher. Add crypto features to ML pipeline.
- **ASSET-COMMODITY-01** — Add yfinance fetchers for GC=F, CL=F, NG=F, SI=F, HG=F. Add seasonal sin/cos features. Implement CFTC COT report ingester. Build COT widget.
- **ASSET-FOREX-01** — Add yfinance fetchers for major FX pairs. Implement interest rate differential feature. Implement Currency Strength Index. Add G10 central bank calendar to Macro Dashboard.
- **ASSET-ML-01** — Add `fetch_ohlcv_4h` job and `ohlcv_4h` table. Add `"4h"` case to training scripts. Update consensus computation and dashboard tile layout to 5 timeframes.
- **ASSET-ML-02** — Add `optuna` to requirements. Implement walk-forward validation utility. Add `model_performance_log` table and daily comparison job. Implement drift alert at 20% Sharpe degradation. Add `/admin/ml/drift-report` endpoint.
- **ASSET-ML-03** — Add `shap` to requirements. Compute SHAP values post-inference for XGBoost models. Return top-5 features in GAS API payload. Build "What's driving this?" collapsible UI component.

---

### 9.3 Advanced Indicators

- **IND-TIER1-01** — Add 12 new indicator functions to `indicator_service.py` (Williams %R, Keltner, SAR, ADX, CMF, Donchian, MFI, TRIX, Ichimoku, DEMA/TEMA, Ultimate Oscillator, Elder Ray). Register in builder. Write unit tests. Add Glossary entries.
- **IND-COMPOSITE-01** — Implement GAS-Weighted RSI, Macro-Sentiment Divergence Index, Regime-Conditioned BB, and SMI in `composite_indicator_service.py`. Add "Fin-Eye Proprietary" UI panel.
- **IND-COMPOSITE-02** — Implement 30-day rolling pairwise correlation job. Build heatmap UI with colour scale and hover tooltips. Implement Diversification Score. Wire to watchlist changes.

---

### 9.4 Digital Nomad Content

- **NOMAD-01** — Design and implement `/lifestyle` hub page with four pillar cards. Add "Lifestyle" to navigation. Create reusable disclaimer component.
- **NOMAD-02** — Seed 10-country comparison dataset as JSON config. Implement interactive filter/sort table. Add FATCA callout. Add "Key Concepts" accordion.
- **NOMAD-03** — Seed 9-structure comparison dataset as JSON config. Implement "Which structure fits me?" filter. Add Turkish founder callout section.
- **NOMAD-04** — Write practical guide content. Structure as accordions/checklist. Add relevant external links.
- **NOMAD-CMS-01** — Add "Lifestyle" category to CMS. Ensure lifestyle articles appear in correct sections. Make SEO metadata configurable per article. Auto-inject disclaimer in lifestyle templates.

---

### 9.5 Product Showroom v2

- **SHOP-V2-01** — Add `preview_url` field to product model. Build Preview modal with embedded viewer. Disabled state for products without preview URL.
- **SHOP-V2-02** — Add "Gift this" toggle to product detail. Implement gift recipient email input. Configure LemonSqueezy checkout for recipient delivery. Implement gifter confirmation email.
- **SHOP-V2-03** — Configure at least one bundle as a LemonSqueezy variant. Create bundle card component with "Save X%" badge and expandable "What's included" section. Display bundles featured at top of Showroom grid.
- **SHOP-V2-04** — Add `rating` and `review_count` fields to product model. Build star rating display component. Implement "No reviews yet" fallback. Allow manual seeding via admin.
- **SHOP-ROADMAP-01** — Add `status` field to product model (`live | coming_soon`). Implement "Notify me" button storing `(user_id, product_id)` in `product_notifications`. Implement admin "Publish" action that triggers notification batch.

---

### 9.6 Investment Strategy Planner

- **PLAN-01** — Design 5-question quiz schema and scoring logic in config. Build quiz UI with progress bar. Implement profile assignment and storage. Integrate profile with GAS alert default thresholds.
- **PLAN-02** — Define allocation matrices per profile/age/horizon as config. Implement allocation calculator. Build pie chart + table UI. Ensure disclaimer is always rendered.
- **PLAN-03** — Implement rebalancing computation function. Build holdings input table. Build suggested trades output table. Implement CSV export.
- **PLAN-04** — Implement DCA vs lump-sum simulation using historical OHLCV. Build side-by-side equity curve chart. Display CAGR, max drawdown, total invested for both strategies.
- **PLAN-05** — Implement portfolio withdrawal simulation for three historical scenarios. Implement portfolio survival rate. Build overlapping line chart.
- **PLAN-06** — Pull Treasury yield data from FRED by maturity. Implement ladder computation. Build bar chart visualisation. Link to Macro Dashboard yield curve widget.

---

### 9.7 B2B2C Landlord Architecture

- **B2B-TENANT-01** — Write Alembic migration: `tenants`, `tenant_memberships`, add nullable `tenant_id` to Portfolio/Watchlist/Alert. Implement `/advisors/register` endpoint and form. Implement invitation token and acceptance flow.
- **B2B-TENANT-02** — Implement tenant config loader (fetch by subdomain on request init). Pass tenant config to frontend on boot. Implement dynamic logo and accent colour theming via CSS custom properties.
- **B2B-ISOLATION-01** — Implement `TenantContext` dataclass and FastAPI dependency. Refactor all resource queries to use `TenantContext`. Add composite indexes `(tenant_id, user_id)` on affected tables. Write cross-tenant access denial integration test.
- **B2B-NARRATOR-01** — Add `ai_narrator_config` JSON column to `tenants`. Implement Jinja2 prompt template with tenant config injection. Hard-code mandatory disclaimer as a non-removable template block. Test that B2C requests use default narration unchanged.
- **B2B-GAS-WEIGHTS-01** — Add `gas_weight_profile` JSON column to `tenants`. Add optional `weights` parameter to `compute_gas_score()`. Build advisor weight configuration UI with three sliders and preset buttons. Add Pydantic validator enforcing weights sum to 1.0.
- **B2B-COMPLIANCE-01** — Create `compliance_audit_logs` table (append-only). Implement `log_compliance_event()` with silent failure handling. Instrument GAS display, AI narration, backtests, and scenarios. Implement paginated `/compliance/audit-log` endpoint with CSV export.
- **B2B-BILLING-01** — Define Stripe products for Starter/Growth/Enterprise tiers. Implement seat count metering via Stripe usage records. Implement seat limit enforcement on invitation endpoint. Build tier upgrade prompt UI.

---

### 9.8 Product Polish

- **POLISH-01** — Implement batch GAS fetch endpoint for a list of symbols. Build `WatchlistCard` component. Build `WatchlistOverview` page with sort controls.
- **POLISH-02** — Implement `/symbols/search?q=` backend endpoint wrapping Finnhub `/search`. Build `SymbolSearchInput` combobox with debounced fetch (min 2 chars, 300ms delay). Replace all free-form ticker inputs.
- **POLISH-03** — Implement auto-creation of two default alert rules on watchlist symbol add. Add 4-hour deduplication Redis key. Build Notifications settings page to view/edit/delete alert rules.
- **POLISH-04** — Implement server-side PDF generation (`weasyprint` or `reportlab`) with styled template. Implement CSV export for backtesting results and GAS history. Add Export button to Backtesting, GAS History, and Portfolio pages. Implement async export for large ranges with email delivery.
- **POLISH-05** — Implement `prefers-color-scheme` detection. Implement CSS custom properties for light/dark theming. Build mode toggle button with `localStorage` persistence. Audit all pages for WCAG AA contrast in light mode.
- **POLISH-06** — Review all existing tour steps against current UI and update stale copy. Add new tour steps for Watchlist Overview, Lifestyle, Showroom, and Strategy Planner. Move tour completion state to user record in database. Add "Restart tour" to Settings.

---

_End of user-stories-v2.md — extends v1.5 with the full pre-launch brainstorming implementation. Both files are maintained together; v1.5 story IDs remain valid and unchanged._
