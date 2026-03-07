# Fin-Eye — Comprehensive Pre-Launch Audit & Strategy Document
**Date:** 2026-03-07  
**Author:** Product Owner / Senior Dev Review  
**Status:** Living document — update before each sprint

---

## Table of Contents
1. [Security Audit](#1-security-audit)
2. [Product Objectives Gap Analysis](#2-product-objectives-gap-analysis)
3. [Advanced Indicators Roadmap](#3-advanced-indicators-roadmap)
4. [ML Expansion — New Asset Classes](#4-ml-expansion--new-asset-classes)
5. [Digital Nomad & Lifestyle Finance Content Module](#5-digital-nomad--lifestyle-finance-content-module)
6. [Tax Structures & Legal Frameworks](#6-tax-structures--legal-frameworks)
7. [Digital Product Showroom Strategy](#7-digital-product-showroom-strategy)
8. [Investment Strategy Planning Module](#8-investment-strategy-planning-module)
9. [Pre-Launch Checklist](#9-pre-launch-checklist)
10. [Architecture Recommendations](#10-architecture-recommendations)

---

## 1. Security Audit

### 1.1 CRITICAL Issues (fix before launch)

| # | Issue | Location | Risk | Fix |
|---|-------|----------|------|-----|
| C1 | **Real API keys in .env committed to git** | `.env` in repo root | CRITICAL | Rotate FINNHUB_API_KEY and FRED_API_KEY immediately. Add `.env` to `.gitignore`. Use `.env.example` with placeholder values only. |
| C2 | **JWT_SECRET is a real value in committed .env** | `backend/.env` | CRITICAL | Rotate key. Never store real secrets in version control. |
| C3 | **TOTP encryption key committed** | `backend/.env` | CRITICAL | Rotate Fernet key. All existing TOTP secrets are now compromised. |
| C4 | **`REQUIRE_AUTH=False` by default** | `config.py` | HIGH | Set `REQUIRE_AUTH=True` in staging/production. Unauthenticated access to all data endpoints currently possible. |
| C5 | **`ALLOWED_ORIGINS=["*"]` as default** | `config.py` | HIGH | Lock to specific origins in production: `["https://app.fin-eye.com"]` |
| C6 | **`DEBUG=True` in .env** | `backend/.env` | HIGH | Set `DEBUG=False` in production. Exposes stack traces via `/docs` error responses. |
| C7 | **No rate limiting on auth endpoints** | `auth.py` | HIGH | Add slowapi or similar rate limiter to `/auth/login` (max 10/min/IP), `/auth/register` (max 5/min/IP), `/auth/2fa/verify` (max 5/min/IP). Prevents brute force. |
| C8 | **No email verification enforcement** | `auth_service.py` | HIGH | `is_verified` column exists but is never checked. Enable `get_current_active_verified_user` dependency on sensitive endpoints. |
| C9 | **Admin endpoints lack IP allowlist** | `ops.py`, `admin_gas.py` | MEDIUM | `require_admin` exists but no network-level protection. Add optional `ADMIN_ALLOWLIST_IPS` env var. |
| C10 | **No password complexity validation** | `auth_service.py`, schemas | MEDIUM | Enforce min 8 chars, at least 1 uppercase, 1 digit, 1 special char at registration. |

### 1.2 HIGH Issues

| # | Issue | Location | Risk | Fix |
|---|-------|----------|------|-----|
| H1 | **No refresh token rotation** | `security.py` | HIGH | On each `/auth/refresh` call, invalidate old refresh token and issue new one. Store issued tokens in Redis with TTL. Prevents refresh token theft. |
| H2 | **No refresh token revocation** | `auth.py` | HIGH | Logout endpoint doesn't blacklist the refresh token. Add `POST /auth/logout` that adds token JTI to Redis blocklist. |
| H3 | **SQL injection surface in raw OHLCV queries** | `ohlcv_fetcher.py` | HIGH | Audit any raw `text()` SQL calls. Use parameterised queries only. SQLAlchemy ORM handles this but verify any `text()` calls. |
| H4 | **No CSRF protection on state-changing endpoints** | All POST/DELETE | MEDIUM | JWT-based auth is inherently CSRF-resistant for API clients, but verify no cookie-based auth paths exist that could be exploited. |
| H5 | **Indicator formula input not size-limited** | `indicator_service.py` | MEDIUM | Add JSON depth limit (currently 10) and total byte limit (max 4KB) on formula input to prevent DoS via deeply nested trees. |
| H6 | **No account lockout after failed logins** | `auth_service.py` | MEDIUM | After 10 failed attempts in 15 minutes, lock account for 30 min. Store attempt counts in Redis. |
| H7 | **Sensitive data in logs** | Multiple services | MEDIUM | Audit log statements for email addresses, IP addresses, partial API keys. Mask PII in logs before production. |
| H8 | **No request size limit** | `main.py` | MEDIUM | Add `app.add_middleware(TrustedHostMiddleware)` and set `fastapi` body size limits to prevent large payload attacks. |

### 1.3 MEDIUM Issues

| # | Issue | Location | Risk | Fix |
|---|-------|----------|------|-----|
| M1 | **Admin check uses `is_admin` but model also has `is_superuser` reference** | `user.py`, `deps.py` | MEDIUM | Consolidate to single field. `deps.py` references `is_superuser` but model only has `is_admin`. Fix the inconsistency. |
| M2 | **Webhook endpoints not implemented** | `main.py` | MEDIUM | Stripe/LemonSqueezy webhooks needed for billing (payment events, subscription changes). Must verify signatures before processing. |
| M3 | **No Content Security Policy headers** | `main.py` | MEDIUM | Add `SecurityHeadersMiddleware` setting CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. |
| M4 | **Scheduler jobs don't have exclusive locks** | `scheduler.py` | LOW | In multi-instance deployment, multiple pods would run duplicate jobs. Add Redis-based distributed lock (e.g., `redis-py-lock`) before each job. |
| M5 | **ML model artifacts stored on local filesystem** | `ml_pipeline.py` | MEDIUM | Move to S3/R2 for production. Local `model_store/` won't survive pod restarts on cloud deployments. |
| M6 | **No API versioning enforcement on public routes** | `public_v1_router` | LOW | Ensure breaking changes require a new `/v2/` prefix. Document deprecation policy. |
| M7 | **Unsubscribe token not rate-limited** | `email.py` | LOW | Unsubscribe endpoint should work without auth but should be rate-limited to prevent scraping/enumeration. |

### 1.4 Immediate Action Plan

```
Priority 1 (Before any public exposure):
  1. Rotate all committed secrets (FINNHUB_API_KEY, FRED_API_KEY, JWT_SECRET, TOTP key)
  2. Add .env to .gitignore — verify with: git check-ignore -v .env
  3. Create .env.example with placeholder values
  4. Set REQUIRE_AUTH=True, DEBUG=False, ALLOWED_ORIGINS locked

Priority 2 (Before beta):
  5. Implement rate limiting on /auth/* endpoints (slowapi)
  6. Add refresh token rotation + logout blacklist
  7. Enforce email verification
  8. Add password complexity rules
  9. Add security headers middleware

Priority 3 (Before public launch):
  10. Account lockout after failed logins
  11. Distribute ML artifacts to S3/R2
  12. Add Redis distributed lock for scheduler jobs
  13. Penetration test with OWASP ZAP
```

---

## 2. Product Objectives Gap Analysis

### 2.1 Vision Alignment Check

The PRD vision: *"Understand the forces behind price movements"* — a layered intelligence engine for retail investors who want market context, not price predictions.

**Current state vs vision:**

| Feature | PRD Status | Built | Gap |
|---------|-----------|-------|-----|
| Multi-timeframe ML consensus (5TF) | Required | ✅ 4 TF | 4h timeframe missing |
| GAS (0-100 score) | Core | ✅ Done | - |
| Market Weather System | Core | ✅ Done | - |
| Conflict Detector | Core | ✅ Done | - |
| Macro layer (FRED) | Core | ✅ Done | - |
| Sentiment (FinBERT + Reddit) | Core | ✅ Done | - |
| Google Trends + StockTwits | P3 | ✅ Done | - |
| Fed Policy visualiser | EXP | ✅ Done | - |
| Backtesting engine | MVP | ✅ Done | Missing walk-forward validation UI |
| Options Fear & Greed | EXP | ✅ Done | - |
| Sector Rotation | EXP | ✅ Done | - |
| Insider Trading | EXP | ✅ Done | - |
| Earnings Calendar | EXP | ✅ Done | - |
| Short Interest | EXP | ✅ Done | - |
| Custom Indicators | P3 | ✅ Done | - |
| Crypto assets | Not in PRD | ❌ No | BTC/ETH in symbol list but no crypto-specific data layer |
| Commodities | Not in PRD | ❌ No | No commodity-specific charts/news |
| Forex | Not in PRD | ❌ No | No FX pair analysis |
| Digital Nomad content | Not in PRD | ❌ No | Opportunity — see Section 5 |
| Digital product showroom | Not in PRD | ❌ No | Revenue stream — see Section 7 |
| Payment/billing | CORE-SUB-01/02 | ❌ Not started | Required for launch |
| Mobile responsiveness | P3-MOBILE | ❌ Not started | Critical for mobile users |
| Rate limiting | Security | ❌ Missing | Required before public launch |
| Email verification flow | CORE | ❌ Partial | `is_verified` unused |

### 2.2 Missing High-Value Features (Pre-Launch)

These are not in the original PRD but would materially improve the product:

1. **4h timeframe ML model** — The ML consensus uses 1h/1d/1wk/1mo but PRD specifies 5 timeframes including 4h. Add it.
2. **Regime-change notifications** — Already planned (CORE-NOTIF-ADV-01 extended). When GAS crosses 35 or 65, email the user.
3. **Watchlist dashboard** — Show mini GAS cards for all watchlist symbols on a single page. Currently they see one symbol at a time.
4. **Symbol search autocomplete** — Frontend has no ticker search. Users type free-form. Add Polygon.io or Finnhub symbol search.
5. **Export to CSV/PDF** — For backtests, portfolio analysis, GAS history. Required for institutional users.
6. **Dark/light mode toggle** — Currently dark only. Good accessibility win.
7. **Onboarding tour improvements** — react-joyride exists but tour content needs updating to cover all new pages.

---

## 3. Advanced Indicators Roadmap

### 3.1 Currently implemented (12 functions)
SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, OBV, ROC, CCI, VWAP, CLOSE/VOLUME

### 3.2 Tier 1 — Add next (high signal value, pure pandas, no new deps)

| Indicator | Formula | Use Case |
|-----------|---------|----------|
| **Williams %R** | `(Highest High - Close) / (Highest High - Lowest Low) * -100` | Overbought/oversold, similar to Stoch but faster |
| **Keltner Channels** | EMA ± (ATR × multiplier) | Trend + volatility filter, pairs with BB |
| **Parabolic SAR** | Trailing stop acceleration factor | Trend reversal signals |
| **Ichimoku Cloud** | Tenkan/Kijun/Senkou A&B/Chikou | Complete trend system, highly popular in crypto |
| **ADX (Average Directional Index)** | Wilder smoothed +DI/-DI | Trend strength (not direction) |
| **Chaikin Money Flow (CMF)** | Volume-weighted close position in range | Accumulation/distribution pressure |
| **DEMA / TEMA** | Double/Triple EMA (less lag) | Trend following with reduced lag |
| **Donchian Channels** | 20-period high/low bands | Breakout detection (Turtle Trading) |
| **Ultimate Oscillator** | Weighted average of 3 timeframe buying pressure | Multi-timeframe momentum |
| **Money Flow Index (MFI)** | RSI with volume weighting | Volume-confirmed overbought/oversold |
| **TRIX** | Triple-smoothed EMA rate of change | Filter out market noise |
| **Elder Ray (Bull/Bear Power)** | EMA ± Low/High | Elder Impulse System component |

### 3.3 Tier 2 — Advanced (require additional data or computation)

| Indicator | Data Needed | Notes |
|-----------|------------|-------|
| **Volume Profile (POC/VAH/VAL)** | Intraday tick data | Point of Control — where most volume traded. Powerful S/R levels. Needs Polygon.io |
| **Market Profile (TPO)** | Tick data | Time-at-price letters. Institutional-grade. |
| **Anchored VWAP** | User-specified start date | AVWAP from earnings/gaps — very popular with semi-pros |
| **Fibonacci Auto-Draw** | Price extremes | Auto-detect swing highs/lows, draw Fib levels |
| **Elliott Wave Counter** | Price history | Complex pattern detection — ML-assisted |
| **Harmonic Patterns** | Price history | Gartley, Bat, Butterfly, Crab detection |
| **Hurst Exponent** | Returns series | Mean-reversion vs trending tendency (0.5 = random walk) |
| **Kalman Filter** | Returns | Adaptive smoothing — better than EMA for noisy data |
| **Z-Score of Price** | Rolling statistics | Statistical deviation from rolling mean |
| **Beta-adjusted RSI** | Requires SPY correlation | Normalize RSI for high-beta stocks |

### 3.4 Composite / Cross-Asset Indicators (unique to Fin-Eye)

These don't exist elsewhere and would be genuine differentiators:

| Indicator | Description |
|-----------|-------------|
| **GAS-Weighted RSI** | RSI dampened/amplified by the current GAS score. High GAS = RSI signals more reliable. |
| **Macro-Sentiment Divergence Index** | Measures gap between macro score and sentiment score. Large divergence = unstable regime. |
| **Cross-Asset Correlation Heatmap** | Rolling 30-day correlation of user's watchlist. Dynamic portfolio risk visualization. |
| **Regime-Conditioned Bollinger** | BB width dynamically adjusted for current VIX regime. Tighter in low-vol, wider in stress. |
| **Smart Money Index (SMI) Approximation** | First 30 min vs last 30 min of session performance. Smart money trades the close. |

---

## 4. ML Expansion — New Asset Classes

### 4.1 Current state
ML pipeline trained on equity OHLCV data (XGBoost + Logistic + Prophet). Predicts next-5-bar direction.

### 4.2 Expansion opportunities

#### Cryptocurrencies
- **Data source**: Binance WebSocket (free, real-time), CoinGecko (free REST)
- **Adaptations needed**: 
  - 24/7 market — remove market-hours logic from scheduler
  - Add on-chain metrics as features: active addresses, exchange inflows, funding rates
  - Crypto-specific sentiment: CryptoPanic API, Santiment (paid), LunarCrush
  - Fear & Greed index for crypto (Alternative.me — free)
- **New ML features**: funding_rate, open_interest_change, whale_transaction_count, exchange_netflow

#### Commodities
- **Data sources**: yfinance (GC=F gold, CL=F oil, SI=F silver, NG=F natgas), Quandl futures
- **Adaptations**:
  - Seasonal patterns are stronger — add sin/cos seasonal features
  - COT (Commitment of Traders) report data — positioning by commercial hedgers vs speculators
  - Geopolitical event weighting (oil responds heavily to news)
  - Supply/demand indicators: EIA weekly inventory (oil), WASDE reports (grains)
- **USDA WASDE API**: Free — crop supply/demand estimates for grains (corn, wheat, soybeans)

#### Forex
- **Data sources**: Oanda API (free demo), FX rates (openexchangerates.org), yfinance `EURUSD=X`
- **Adaptations**:
  - Interest rate differential as primary feature (carry trade)
  - Economic calendar sensitivity (NFP, CPI, central bank decisions)
  - Correlation matrix with equities (risk-on/risk-off flows)
  - Overnight swap rates
- **Unique signals**: Real Interest Rate Differential, Purchasing Power Parity deviation

#### Fixed Income / Bonds
- **Data sources**: FRED (Treasury yields), yfinance (TLT, IEF, HYG ETFs as proxies)
- **Adaptations**:
  - Duration risk features
  - Credit spread (HY - IG) as risk indicator
  - MOVE index (bond market VIX equivalent)
  - Fed policy path expectation from futures curve

#### ETFs / Sector Rotation
- **Already partially built** (sector rotation page exists)
- **Expansion**: International ETFs (EWJ Japan, EWZ Brazil, FXI China, EEM EM)
- **Factor ETFs**: Value (VTV), Growth (VUG), Momentum (MTUM), Quality (QUAL), MinVol (USMV)
- **Thematic**: Clean energy (ICLN), AI (AIQ), Semiconductor (SOXX), Biotech (XBI)

### 4.3 Implementation roadmap for multi-asset

```
Phase A — Crypto (1 sprint):
  - Add BTC-USD, ETH-USD, BNB-USD to default symbols
  - Crypto fear & greed index endpoint
  - Funding rates + open interest from Binance
  - CryptoCompare news sentiment

Phase B — Commodities (1 sprint):
  - Gold, Oil, Natural Gas, Silver, Copper
  - COT report data ingestion (CFTC free)
  - Seasonal decomposition feature
  - Commodity-specific stress scenarios in risk engine

Phase C — Forex (1 sprint):
  - Major pairs: EUR/USD, GBP/USD, USD/JPY, USD/CHF
  - Interest rate differential feature
  - Currency strength index (basket-weighted)
  - Central bank calendar integration

Phase D — ML improvements (1 sprint):
  - Add 4h timeframe model
  - Walk-forward validation with Bayesian optimization
  - Feature importance API endpoint (what's driving the signal)
  - Model drift detection — alert when live accuracy drops below training
```

---

## 5. Digital Nomad & Lifestyle Finance Content Module

### 5.1 Rationale
Your target audience (finance/econ students, curious retail investors, semi-pro traders) has significant overlap with the digital nomad and financial independence community. Adding high-quality, genuinely useful content in this space:
- Increases SEO authority on high-value keywords
- Differentiates from pure fintech tools
- Creates organic social sharing
- Supports the digital product showroom (Section 7)

### 5.2 Content pillars

#### Pillar 1: Tax Residency & Tax Havens (Educational)
*Disclaimer: all content is informational only. Consult a tax professional.*

**Top Destinations with Key Details:**

| Country | Personal Tax Rate | Capital Gains Tax | Key Requirements | Suitability |
|---------|------------------|-------------------|-----------------|-------------|
| **UAE (Dubai)** | 0% | 0% | Residency visa ($2-15k/yr), no min stay | Best overall for high earners |
| **Portugal (NHR)** | 20% flat (NHR scheme) | 0-28% | 183 days presence, EU citizen easier | Great EU option, expires 2024 (replaced by IFICI) |
| **Cyprus** | 0% capital gains (non-property) | 0% stocks | EU member, 60-day rule for tax residency | Excellent for investment income |
| **Malta** | 0-15% (remittance basis) | 0% on remitted | EU member, 90 days, global income foreign | Strong financial sector |
| **Georgia** | 1% on foreign-source income | 0% | Virtual Zone, easy residency | Very low cost, underrated |
| **Paraguay** | 0% foreign income | 0% | Rentista visa $1,200/mo bank account | Cheapest + easiest |
| **Panama** | 0% foreign income | 0% | Friendly Nations visa | Strong banking |
| **Estonia (e-Residency)** | EU company, 0% retained profit | 20% on distribution | Digital nomad visa, e-Residency | Best for EU business without living there |
| **Thailand (LTR Visa)** | 17% flat (LTR visa) | 0% on offshore | $80k/yr income or $500k investment | Southeast Asia hub |
| **Cayman Islands** | 0% all taxes | 0% | Residency $1.2M investment | Offshore only, expensive |

**Important caveats to always include:**
- US citizens are taxed on worldwide income regardless of residency (FATCA/FBAR obligations)
- "Tax residency" ≠ "permanent residency" ≠ "citizenship"
- Most countries require surrendering previous tax residency
- Substance requirements are increasing globally (OECD BEPS)

#### Pillar 2: Legal Investment Structures

**Best legal structures by investor profile:**

| Structure | Jurisdiction | Best For | Setup Cost | Annual Cost |
|-----------|-------------|----------|-----------|------------|
| **Cyprus Holding Co + IP Box** | Cyprus | EU investors, IP income | €3-5k | €2-4k |
| **US LLC (Wyoming/Delaware)** | USA | Non-US residents, online business | $100-500 | $50-300/yr |
| **UAE Freezone LLC** | UAE | Middle East/Asia base, 0% corporate | $3-8k | $3-5k/yr |
| **Cayman Islands Fund** | Cayman | Investment fund structure | $15-30k | $10-20k/yr |
| **UK LLP** | UK | Transparent taxation, EU access post-Brexit limited | £500 | £200/yr |
| **BVI Company** | BVI | Offshore holding, privacy | $2-3k | $1-2k/yr |
| **Irish Holding Co** | Ireland | EU access, 12.5% corporate, participation exemption | €3-5k | €2-5k/yr |
| **Singapore Pte Ltd** | Singapore | Asia-Pacific base, 17% corporate | SGD 1-3k | SGD 1-3k/yr |
| **Estonian OU** | Estonia | EU, 0% on retained earnings | €200 | €150/yr |

**Key concepts to cover in articles:**
- Substance requirements (you must actually operate from there)
- Controlled Foreign Corporation (CFC) rules in your home country
- Transfer pricing documentation
- Economic substance — the OECD's crackdown on shell companies
- Double Taxation Treaties (how to use them legally)
- Beneficial Ownership registers (increasing transparency globally)

#### Pillar 3: Digital Nomad Practical Finance

- **Banking**: Wise (multi-currency), Revolut Business, Mercury (US LLC), Starling
- **Investment accounts**: Interactive Brokers (accepts most countries), DEGIRO (EU)
- **Crypto custody**: Hardware wallet vs exchange, tax reporting tools (Koinly, CoinTracker)
- **Health insurance**: SafetyWing, Cigna Global, Allianz Care
- **Pension/retirement**: SIPP (UK), QROPS (for expats), Roth IRA conversion strategy
- **Estate planning**: which country's laws govern your assets

### 5.3 Implementation

**New frontend pages needed:**
- `/lifestyle/digital-nomad` — hub page
- `/lifestyle/tax-residency` — interactive country comparison table
- `/lifestyle/legal-structures` — structure comparison by profile
- `/lifestyle/investment-abroad` — practical guide

**New backend content:**
- Seed these as blog posts (CMS already built)
- Add "Lifestyle" and "Tax & Legal" categories
- SEO-optimize with long-tail keywords

---

## 6. Tax Structures & Legal Frameworks

### 6.1 Investment Strategy Planning

**For the platform itself:**

The right structure for a SaaS fintech depends on your residency and target market:

| Scenario | Recommended Structure |
|----------|----------------------|
| Founder in EU, customers worldwide | Cyprus or Ireland holding co + Estonia operating entity (best EU tax + substance) |
| Founder wanting UAE base | Dubai Mainland LLC + UAE tax residency. 0% corporate, 0% personal, easy banking |
| US customers focus | Delaware C-Corp (for VC), or Wyoming LLC (bootstrapped). File 83(b) if giving equity |
| Founder non-US, selling to US | US LLC (Wyoming) wholly owned by foreign entity — no US tax on foreign-source income |
| Already in Turkey (your location) | Turkey has high taxes. UAE or Cyprus relocation is commonly used by Turkish entrepreneurs |

**Recommended sequence:**
1. Establish operating entity (Estonia or Cyprus for EU, UAE for global)
2. Get tax residency in chosen country
3. Surrender Turkish tax residency (or use DTT to manage)
4. Open business banking (Mercury for US LLC, Emirates NBD for UAE)
5. IP ownership: hold IP in low-tax jurisdiction
6. Revenue: flows to holding company, distribute only what's needed

### 6.2 Platform Revenue Legal Considerations

- **VAT/GST on digital services**: EU requires charging VAT in customer's country (OSS scheme). Use LemonSqueezy or Paddle — they handle VAT/GST globally (Merchant of Record model).
- **GDPR compliance**: Already implemented in the app. Add DPA (Data Processing Agreement) for B2B.
- **Financial services regulations**: Since Fin-Eye is "educational only", you avoid MiFID II licensing in EU. But ensure all disclaimers are prominent and consistent.
- **Terms of Service**: Must explicitly state not financial advice. Limitation of liability. Class action waiver (for US users).

---

## 7. Digital Product Showroom Strategy

### 7.1 Concept
A curated "marketplace" within Fin-Eye where users can browse and purchase downloadable financial tools. Low customer acquisition cost (users already trust the platform), high margin (digital products), no inventory.

### 7.2 Product lineup (already seeded in database)

| Product | Price | Target Audience | Differentiation |
|---------|-------|-----------------|----------------|
| Investment Portfolio Tracker (Excel) | €12.99 | Active investors | Live data connections, heat map |
| Retirement Planning Calculator (Excel) | €14.99 | 30-50 yr olds | Monte Carlo simulation, FIRE calculator |
| Household Budget Tracker (Excel) | €7.99 | Families | Beautiful design, bill reminders |
| **Teen Financial Planner (Google Sheets)** | €4.99 | Parents buying for teens | Fun, emoji-rich, educational |
| Dividend Income Tracker (Excel) | €9.99 | Income investors | Ex-date calendar, DRIP calculator |
| Options P&L Tracker (Excel) | €19.99 | Options traders | Greeks tracking, covered calls workflow |

### 7.3 Future products (roadmap)

- **FI/FIRE Calculator (Excel)** — when can you retire? Monte Carlo + SWR analysis
- **Tax-Loss Harvesting Tracker** — track unrealized losses for year-end optimization
- **Business Valuation Tool (Excel)** — DCF model, comparable company analysis
- **Crypto Tax Report Generator** — import from exchange CSV, calculate gains/losses
- **Real Estate Investment Analyzer** — cap rate, cash-on-cash, IRR calculation
- **DCA Bot Tracker** — track dollar-cost averaging across multiple assets

### 7.4 Monetization
Use LemonSqueezy (Merchant of Record — handles EU VAT/GST automatically):
- **Commission model**: 0% if you own the products
- **Affiliate model**: 30-50% commission if partnering with creators
- Add `LEMON_SQUEEZY_VARIANT_*` IDs to `.env` (already added in new .env)

### 7.5 Showcase page enhancements needed
- Add "Preview" button opening a read-only Google Sheets link
- Add star ratings / review count display
- Add "Gift this" flow (email delivery to recipient)
- Add bundle pricing (e.g., "Investor Bundle: 3 for €29.99")

---

## 8. Investment Strategy Planning Module

### 8.1 New feature: "Strategy Planner"

A guided investment planning tool — not advice, but a structured framework:

**Sub-features:**

1. **Risk Profile Quiz** — 5 questions → assigns Aggressive/Moderate/Conservative/Income profile
2. **Asset Allocation Suggester** — Based on profile + age + time horizon → suggested % allocation by asset class
3. **Rebalancing Calculator** — Given current holdings, calculate trades needed to reach target allocation
4. **Dollar-Cost Averaging Simulator** — Model DCA over 1-10 years with historical data
5. **Sequence of Returns Risk Visualizer** — Show how retiring into a bear market affects portfolios
6. **Bond Ladder Builder** — Plan fixed-income ladder for income investors

**Important disclaimers required on all:**
- "This is a planning tool for educational purposes. It is not personalized financial advice."
- "Past performance does not predict future results."
- "Consult a qualified financial advisor before making investment decisions."

### 8.2 Integration with existing features
- Risk profile → auto-configure GAS alert thresholds
- Asset allocation → tie to portfolio tracker
- Rebalancing → show in portfolio page as "Suggested Trades" (not executed)

---

## 9. Pre-Launch Checklist

### 9.1 Technical (must-have)
- [ ] Rotate all committed secrets (JWT_SECRET, API keys, TOTP key)
- [ ] Add `.env` to `.gitignore`, create `.env.example`
- [ ] Set `REQUIRE_AUTH=True`, `DEBUG=False`, `ALLOWED_ORIGINS` locked in production
- [ ] Implement rate limiting on `/auth/*` endpoints
- [ ] Add refresh token rotation + blacklist
- [ ] Enforce email verification for account access
- [ ] Add security headers middleware (CSP, HSTS, X-Frame-Options)
- [ ] Move ML model artifacts to S3/R2
- [ ] Add Redis distributed lock for scheduler jobs
- [ ] Implement `POST /webhooks/stripe` with signature verification
- [ ] Mobile responsive layout audit — test all pages on 375px viewport
- [ ] Add symbol search autocomplete (Finnhub `/search` endpoint)
- [ ] Sentry error monitoring wired up
- [ ] Database backups tested + verified restorable

### 9.2 Payment & Billing (CORE-SUB-01/02)
- [ ] Stripe integration (subscription creation, upgrade, cancellation)
- [ ] Webhook handling (payment_intent.succeeded, customer.subscription.deleted)
- [ ] Billing portal (Stripe Customer Portal)
- [ ] Feature gating by `subscription_tier` (free vs pro vs institutional)
- [ ] Grace period for failed payments (3-day retry)
- [ ] Cancel flow with win-back offer

### 9.3 Legal & Compliance
- [ ] Privacy Policy reviewed by lawyer (or use Iubenda auto-generation)
- [ ] Terms of Service finalized — include "not financial advice" prominently
- [ ] Cookie consent (Cookiebot or Iubenda) — GDPR + ePrivacy
- [ ] Risk Disclaimer page prominently linked
- [ ] GDPR: data export and deletion confirmed working
- [ ] Age verification (18+ for financial tools) — add to consent gate

### 9.4 Product Polish
- [ ] All pages tested with `--skip-ml` (fallback to 50.0 scores)
- [ ] Empty states on all pages (no blank/broken UI when data is absent)
- [ ] 404 and 500 error pages designed
- [ ] Loading skeletons on all data-fetching components
- [ ] Onboarding tour updated to cover all new pages
- [ ] Dark mode consistency audit
- [ ] Favicon, OG image, meta tags for social sharing
- [ ] First Contentful Paint < 2s on production

### 9.5 Go-Live Sequence
1. Staging deployment (Render/Railway + Supabase + Upstash Redis)
2. Run `seed_all_data.py --fast` on staging
3. Security scan with OWASP ZAP
4. Smoke test all pages
5. Load test with k6 (target: 100 concurrent users, < 2s P95)
6. DNS + SSL cert (Cloudflare)
7. Stripe live keys activated
8. Production deployment with rolling restart
9. Monitor Sentry + ops dashboard for 24h
10. Soft launch (invite-only beta, 50 users)
11. Fix issues from beta feedback
12. Public launch

---

## 10. Architecture Recommendations

### 10.1 Deployment (recommended stack)
```
Frontend:  Vercel (auto-deploys from GitHub, edge network)
Backend:   Render.com or Railway.app (Docker, managed scaling)
Database:  Supabase PostgreSQL (managed, daily backups, connection pooling)
Redis:     Upstash (serverless Redis, pay per request, global replicas)
Storage:   Cloudflare R2 (S3-compatible, no egress fees)
Email:     Resend (already integrated)
Payments:  Stripe + LemonSqueezy
CDN:       Cloudflare (DDoS, WAF, analytics)
Monitoring: Sentry + Uptime Robot (free tier)
```

### 10.2 Estimated monthly costs (at launch, ~500 users)
| Service | Cost |
|---------|------|
| Vercel (Pro) | $20/mo |
| Render (Starter) | $25/mo |
| Supabase (Pro) | $25/mo |
| Upstash Redis | ~$5/mo |
| Cloudflare R2 | ~$1/mo |
| Resend | Free (3k/mo) |
| Sentry | Free (5k errors) |
| **Total** | **~$76/mo** |

Break-even: 6 Pro subscribers at €14.99 = €89.94/mo > $76/mo costs.

### 10.3 Scaling path
- At 1,000 users: upgrade DB to Supabase Pro, add read replica
- At 5,000 users: horizontal backend scaling, Redis cluster, CDN for static assets
- At 10,000 users: consider microservices split (ML inference as separate service)
- ML inference: move to dedicated GPU instance or AWS SageMaker for production quality

### 10.4 Future technical investments
1. **WebSocket real-time quotes** — Polygon.io WebSocket for live ticks on dashboard
2. **Vector database** — Pinecone/pgvector for semantic news search and RAG
3. **LLM explanations** — GPT-4o-mini to narrate GAS score changes in plain English
4. **Mobile app** — React Native sharing component logic with Next.js web
5. **GraphQL API** — For more flexible querying in the public API tier
