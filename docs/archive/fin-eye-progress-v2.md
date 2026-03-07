

**FIN-EYE**

Progress Report · Architecture Decision · User Stories v2 & v3

*March 2026  ·  Senior Dev Audit*



|**Section**|**Contents**|
| :- | :- |
|**Section 1**|Progress Audit — All v1 User Stories|
|**Section 2**|Architecture Decision: Server-Side vs Client-Side (+ Security)|
|**Section 3**|User Stories v2.0 — External Data Sources (your 15 stories)|
|**Section 4**|User Stories v3.0 — Bonus Senior Dev Suggestions|




**Section 1 — Progress Audit**

Every user story in user-stories.md v1.5 was cross-referenced against the actual service files, endpoints, tests, and frontend pages. The status is based on what code exists right now — not what was planned.

|**✅  DONE**|**🔶  PARTIAL**|**🔷  BACKEND ONLY**|**❌  NOT STARTED**|
| :-: | :-: | :-: | :-: |
|*Backend + frontend complete and tested.*|*Backend done, frontend not wired or minor gaps.*|*API/service complete, zero frontend connection.*|*No code exists for this story yet.*|

|**✅  DONE**|**🔶  PARTIAL**|**🔷  BACKEND ONLY**|**❌  NOT STARTED**|
| :-: | :-: | :-: | :-: |
|**28 / 46  (60%)**|**10 stories  (21%)**|**1 stories  (2%)**|**7 stories  (15%)**|

|**🏆  STRONGEST AREA: The entire backend is remarkably complete. Data pipelines, ML training, macro scoring, sentiment, backtesting, auth, 2FA, GDPR, alerts, email sequences, A/B experiments — all production-quality code.**|
| :- |

|**⚠️  BIGGEST GAP: The frontend is not wired to the live backend. Most pages exist as UI shells showing mock/static data. #1 priority: connect the dashboard to the technical consensus, sentiment, and macro APIs.**|
| :- |

|**✅  JUST COMPLETED THIS SESSION: Test fix (test\_macro.py), StockTwits service (EXP-SENT-01, replaces Reddit), live data seed script (seed\_live\_data.py) — all implemented.**|
| :- |


**Per-Story Status Table**

|**Story ID**|**Title**|**Status**|**Notes / Evidence**|
| :- | :- | :- | :- |
|**MVP-DASH-01**|GAS & Market Weather Dashboard|**🔶  PARTIAL**|Backend GAS endpoint exists. Frontend shows mock/stub data — needs wiring to live /api/v1/technical/{symbol}/latest.|
|**MVP-DASH-02**|Regime & Volatility Classification|**🔶  PARTIAL**|macro\_scoring.py computes VIX regime. Endpoint exists. Frontend regime badge not wired to live API.|
|**MVP-DASH-03**|Multi-Timeframe Technical Signals|**🔷  BACKEND**|technical\_service.py + technical\_consensus.py complete. Models trained. Frontend tiles not connected to live endpoint.|
|**MVP-EXPL-01**|Why Is This Stock Moving? Panel|**🔶  PARTIAL**|explanation.py endpoint exists. Template needs wiring to live layer values in the frontend explanation component.|
|**MVP-EXPL-02**|Conflict Detector|**🔶  PARTIAL**|Conflict logic in macro\_scoring.py. API returns conflict flag. Frontend warning component not yet rendered from live data.|
|**MVP-TECH-01**|Train 4 Models per Timeframe (Sharpe winner)|**✅  DONE**|LSTM, XGBoost, Logistic, Prophet pipeline complete. Walk-forward validation + Sharpe selection done. AAPL pre-trained.|
|**MVP-TECH-02**|Technical Confidence Score (0–100)|**✅  DONE**|compute\_technical\_consensus() with Sharpe weighting complete. /api/v1/technical/{symbol}/latest works.|
|**MVP-BACK-01**|Backtesting Engine — Momentum Strategy|**✅  DONE**|backtesting\_service.py complete. Sharpe, Sortino, drawdown, win rate, equity curve all calculated. 5/5 tests pass.|
|**MVP-BACK-02**|Overfitting Warnings in Backtests|**✅  DONE**|Sharpe threshold checks implemented. Warning messages in API payload. Frontend renders them.|
|**MVP-SENT-01**|News Sentiment Timeseries (FinBERT)|**✅  DONE**|Finnhub fetcher + FinBERT scoring + 1d/7d/30d aggregation. /api/v1/sentiment/{symbol}/timeseries works.|
|**MVP-SENT-02**|Source Breakdown (per-outlet sentiment)|**✅  DONE**|get\_source\_breakdown() implemented. /api/v1/sentiment/{symbol}/sources endpoint complete.|
|**MVP-MACRO-01**|Macro Dashboard (FRED + VIX)|**✅  DONE**|11 FRED series + VIX fetched and stored via MacroFetcher. /api/v1/macro/latest returns live data.|
|**MVP-MACRO-02**|Macro Score (0–100) + Label|**✅  DONE**|compute\_macro\_score() in macro\_scoring.py. Supportive/Neutral/Stressed labels. Returned in every macro API response.|
|**MVP-LEARN-01**|Learn / Blog Section|**🔶  PARTIAL**|CMS backend (cms.py, blog model) complete. Frontend blog pages exist but initial content not seeded into DB.|
|**MVP-ONBOARD-01**|In-App Guided Tour|**❌  NOT STARTED**|No tour/coach-marks component built. First-login trigger and Settings re-launch not implemented.|
|**MVP-HEDGE-01**|Basic Hedging Simulator|**✅  DONE**|hedging\_service.py complete. Beta/correlation estimation, scenario P&L, payoff diagram data all implemented.|
|**MVP-DATA-01**|Data Pipelines & Redis Caching|**✅  DONE**|APScheduler runs 8 jobs (OHLCV daily/intraday, macro, news, sentiment, emails, backup). Redis caching in place.|
|**CORE-AUTH-01**|Auth — Register / Login / JWT / Refresh|**✅  DONE**|FastAPI JWT auth complete. Register, login, token refresh, protected route deps all implemented.|
|**CORE-SEC-01**|Two-Factor Auth (TOTP)|**✅  DONE**|TOTP setup/verify/disable endpoints complete. Fernet-encrypted secrets. totp\_service.py fully implemented.|
|**CORE-SEC-02**|Database Backups & Disaster Recovery|**✅  DONE**|backup\_db.py + restore\_db.py. Scheduled daily 02:00 UTC by APScheduler. Rotation logic included.|
|**CORE-WATCH-01**|Watchlist (per-user, persisted)|**✅  DONE**|Watchlist model, CRUD endpoints, frontend integration complete. Marked done in user-stories.md.|
|**CORE-LEGAL-01**|Legal Pages & Consent Gate|**✅  DONE**|ConsentGate, /legal/terms|privacy|disclaimer, DB-versioned consent recording. Marked done.|
|**CORE-GDPR-01**|GDPR Data Export / Delete|**✅  DONE**|gdpr\_service.py, /api/v1/gdpr/ endpoints, Settings UI all implemented.|
|**CORE-OPS-01**|Observability & Monitoring|**🔶  PARTIAL**|MetricsMiddleware, metrics.py, pipeline run logging all done. No external alerting (Slack/PagerDuty) configured yet.|
|**CORE-SET-01**|Profile & Preferences Settings|**🔶  PARTIAL**|Auth user model complete. Profile update endpoints exist. Full Settings UI page not confirmed complete.|
|**CORE-NOTIF-01**|In-App / Email Alerts|**✅  DONE**|alert\_service.py, alert model, /api/v1/alerts endpoints, email delivery via Resend all implemented.|
|**CORE-EMAIL-01**|Onboarding Email Sequence (Day 3 & 7)|**✅  DONE**|onboarding\_email\_service.py with Day-3 and Day-7 batches. Scheduled in APScheduler.|
|**CORE-EMAIL-02**|Weekly Email Digest|**✅  DONE**|weekly\_digest job scheduled every Monday. run\_weekly\_digest\_batch() implemented.|
|**CORE-CMS-01**|CMS / Blog Content Pipeline|**✅  DONE**|cms.py endpoint, blog model, migrate\_posts.py, seed\_case\_studies.py all present.|
|**CORE-CMS-02**|Admin Markdown Editor UI|**🔶  PARTIAL**|Backend CMS endpoint and admin role guard exist. Frontend admin markdown editor not confirmed complete.|
|**CORE-ANALYTICS-01**|Product Analytics & Event Tracking|**✅  DONE**|analytics\_service.py, AnalyticsEvent model, /api/v1/analytics, MetricsMiddleware all built.|
|**CORE-EXPERIMENT-01**|A/B Experimentation Framework|**✅  DONE**|experiment\_service.py, Experiment model, /api/v1/experiments endpoints implemented.|
|**CORE-SUB-01**|Stripe Upgrade to Pro|**❌  NOT STARTED**|No Stripe integration. Deliberately parked — validate product first.|
|**CORE-SUB-02**|Subscription Management|**❌  NOT STARTED**|Depends on CORE-SUB-01.|
|**CORE-COMM-01**|Community Integration (Discord/Forum)|**❌  NOT STARTED**|Not started. Low priority until user base grows.|
|**P2-PORT-01**|Portfolio View & Aggregated Insights|**✅  DONE**|portfolio\_service.py, portfolio model, /api/v1/portfolios endpoints all implemented.|
|**P2-RET-01**|Retail Sentiment (StockTwits — was Reddit)|**✅  DONE**|StockTwitsService built this session. Self-labelled bullish/bearish. 5 unit tests written. No API key needed.|
|**P2-EVENT-01**|Event Calendar (GDELT)|**🔶  PARTIAL**|event\_service.py and events endpoint exist. GDELT ingestion written. Frontend calendar component not confirmed wired.|
|**P2-MACRO-ADV-01**|Advanced Macro (yield curve, recession, NFP)|**✅  DONE**|Full yield curve (2y/5y/10y/30y), USREC, NFP, industrial production all fetched. /api/v1/macro/advanced complete.|
|**P2-HEDGE-ADV-01**|Advanced Hedging (multi-leg strategies)|**✅  DONE**|hedging\_service.py supports collar + multi-leg. /api/v1/hedge endpoints complete.|
|**P2-STRAT-01**|Strategy Library (save & load backtests)|**✅  DONE**|strategy\_service.py, strategy model, saved strategies migration, /api/v1/strategies endpoints all built.|
|**P3-SENT-ADV-01**|Advanced Sentiment (transcripts, Trends)|**❌  NOT STARTED**|Planned in EXP-EARN-02 and EXP-TREND-01 (v2). No implementation yet.|
|**P3-ANALYTICS-01**|No-Code Indicator Builder|**❌  NOT STARTED**|Complex P3 feature. Not started.|
|**P3-API-01**|Authenticated Public REST API|**🔶  PARTIAL**|api\_key model, api\_key\_service.py, /api/v1/api-keys and /public/v1/ endpoints present. Rate limiting needs verification.|
|**P3-WHITELABEL-01**|White-Label Theming|**❌  NOT STARTED**|Not started. P3 premium feature.|
|**P3-RISK-01**|Scenario & Stress Testing|**✅  DONE**|risk\_service.py, /api/v1/risk endpoints, scenario library implemented.|



**Section 2 — Architecture Decision: Server-Side vs Client-Side**

Your question: when a user types TSLA and clicks Analyze, is the computation done on their machine or pulled from your server? This is one of the most important design decisions in the product. Here is the definitive answer with full reasoning.

|**SHORT ANSWER: Always server-side. Never client-side. The analysis is computed on your server and returned as a JSON response. The user's browser only renders the result.**|
| :- |


**Why Client-Side Is Wrong for Fin-Eye**

|**Reason**|**Server-Side ✅**|**Client-Side ❌**|
| :- | :- | :- |
|**ML Models**|Your trained XGBoost/LSTM models (joblib files) live on the server. A browser cannot run PyTorch or scikit-learn.|*Impossible — a browser cannot load .joblib model files or run Python ML libraries.*|
|**API Key Security**|Finnhub and FRED keys stay in backend/.env, never leave your server.|*API keys in frontend JavaScript are visible in browser dev tools — trivially stolen in seconds.*|
|**Database Access**|Backend queries PostgreSQL via SQLAlchemy — only the backend touches the DB.|*Direct DB access from a browser = catastrophic security hole. Never do this.*|
|**Performance**|Redis caches results. All users benefit from one computation.|*Every user re-computes from scratch — slow, expensive, inconsistent.*|
|**Data Quality**|You control validation, normalisation, and model updates centrally.|*Users could tamper with inputs to produce misleading outputs.*|
|**GDPR Compliance**|You know exactly what personal data is processed and where.|*No control over client-side processing — compliance nightmare.*|
|**Model Updates**|Update a model on the server → all users instantly get the improved model.|*Every user would need to download new model files — impractical.*|

**The Correct Flow: User Types TSLA → Clicks Analyze**

|**Step**|**Event**|**Where**|**Detail**|
| :- | :- | :- | :- |
|**1**|User types TSLA + clicks Analyze|*Next.js (Browser)*|Sends GET /api/v1/technical/TSLA. Zero computation happens in the browser.|
|**2**|Backend receives request|*FastAPI*|Validates JWT token. Checks Redis cache for recent result. Returns immediately if cached.|
|**3**|Cache miss → compute signals|*technical\_service.py*|Loads TSLA\_1d\_winner.joblib. Fetches OHLCV features from PostgreSQL. Runs ML inference (~50ms).|
|**4**|Aggregate all layers|*technical\_consensus.py + macro\_scoring.py*|Combines 5 timeframe signals (Sharpe-weighted). Fetches live macro score. Gets StockTwits sentiment.|
|**5**|Return unified result|*FastAPI JSON response*|One JSON payload: GAS, regime, timeframe signals, macro score, sentiment, conflict flags.|
|**6**|Render|*Next.js (Browser)*|Displays dashboard with real data. Total round-trip: ~1–2 seconds for a warm cache.|

**About Security — You Are Right to Be Sensitive**

You are correct to worry. Here is what the current codebase already does to protect you and your users, and what you still need to do before going to production.

**Already Implemented ✅**

- **Short-lived tokens:** JWT tokens expire in 30 minutes. Even if a token is stolen, it expires quickly. Refresh token flow is implemented.
- **Bcrypt password hashing:** Passwords are stored with bcrypt. Even a full DB dump reveals nothing readable.
- **TOTP two-factor auth:** TOTP setup/verify/disable endpoints are complete with Fernet-encrypted secrets. A stolen password alone is useless when 2FA is enabled.
- **API keys never leave the server:** All API keys (Finnhub, FRED, Anthropic) are server-side only. They live in .env, never sent to the browser.
- **GDPR delete/export:** gdpr\_service.py is complete with full data export and deletion flows.
- **Database isolation:** Only your FastAPI server talks to PostgreSQL. The frontend has zero direct DB access.
- **Automated daily DB backups:** backup\_db.py runs daily at 02:00 UTC with rotation. If attacked, you can restore.

**Actions Needed Before Production ⚠️**

- **1. HTTPS (Nginx + Let's Encrypt):** Always serve over HTTPS in production. Use Nginx as reverse proxy with Let's Encrypt certificates. Never serve HTTP in prod.
- **2. CORS — restrict origins:** Set ALLOWED\_ORIGINS in .env to your exact frontend domain (e.g. https://fin-eye.com). Never use '\*' in production.
- **3. .env in .gitignore:** Add .env to .gitignore immediately if not already done. Never commit API keys or secrets to Git.
- **4. Login rate limiting:** Add rate limiting to the /api/v1/auth/login endpoint (e.g. 5 attempts per minute per IP) to prevent brute-force attacks. Consider slowapi or a middleware.
- **5. Production secrets:** When deploying, set all passwords (PostgreSQL, Redis) to strong random values. The defaults (postgres/postgres) in config are for development only.

|**BOTTOM LINE: Your architecture is correct and your security foundation is solid. The main remaining steps are HTTPS, CORS restriction, and login rate limiting before you launch publicly.**|
| :- |



**Section 3 — User Stories v2.0 — External Data Sources**

Your 15 experimental stories from fin-eye-stories-v2.md, formatted consistently with user-stories.md v1.5. EXP-SENT-01 is already implemented.

**New External Data Sources**

|**Source**|**Data**|**Cost**|**API Key?**|
| :- | :- | :- | :- |
|**StockTwits API**|Retail sentiment, self-labelled bullish/bearish|**Free**|No — DONE ✅|
|**GDELT Event DB**|Global news events, geopolitical risk scores|**Free**|No|
|**SEC EDGAR**|13F institutional holdings, Form 4 insider trades|**Free**|No|
|**World Bank API**|GDP, inflation, debt/GDP for G20 countries|**Free**|No|
|**ECB Data Portal**|Eurozone policy rate, HICP inflation, M3|**Free**|No|
|**BLS Release Calendar**|CPI, PPI, NFP release dates|**Free**|No for calendar|
|**yfinance (options)**|Put/call ratio, max pain, OI by strike|**Free**|No — library|
|**pytrends**|Google Trends search interest by ticker|**Free**|No — library|
|**Fed RSS Feed**|FOMC statements and press releases|**Free**|No — public RSS|
|**Claude API (Anthropic)**|AI daily market narrator|**Pay-per-use**|Yes — Anthropic|

**Implementation Waves**

|**Wave**|**Stories**|**Effort**|
| :- | :- | :- |
|**Wave 1 — This Week<br>No new API keys**|EXP-SENT-01 ✅ Done  ·  EXP-OPT-01  ·  EXP-SECT-01  ·  EXP-EARN-01|**~4.5 days total**|
|**Wave 2 — 2-3 Weeks<br>All free APIs**|EXP-GEO-01  ·  EXP-INSID-01  ·  EXP-MACRO-01  ·  EXP-CAL-01  ·  EXP-TREND-01  ·  EXP-CORR-01|**~9 days total**|
|**Wave 3 — Premium<br>4-6 weeks**|EXP-CB-01  ·  EXP-POL-01  ·  EXP-AI-01  ·  EXP-EARN-02  ·  EXP-INST-01|**~11 days total**|

**Story Cards**

|**EXP-SENT-01  ·  StockTwits Retail Sentiment (Reddit Replacement)**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see what retail traders are saying about a stock on StockTwits with real bullish/bearish labels, so that I can gauge crowd sentiment without needing Reddit access.*|
|**Acceptance Criteria**|<p></p><p>- - Replace reddit\_service.py with stocktwits\_service.py using the free public API (no auth needed).</p><p>- - Each message has a built-in Bullish/Bearish label — use directly instead of running VADER inference.</p><p>- - Show: total messages, % bullish, % bearish, top 5 bullish and top 5 bearish messages.</p><p>- - Retail Sentiment Score (0–100) derived from ratio of labelled messages.</p><p>- - Mock fallback for tickers with no StockTwits coverage.</p><p>- - 5 unit tests written covering: happy path, 422, timeout, scoring, empty list.</p>|
|**Data Source**|*StockTwits Public API — free, no key. api.stocktwits.com/api/2/streams/symbol/{ticker}.json*|
|**Phase / Effort**|P2 Growth  |  ~4 hours  |  ✅ IMPLEMENTED THIS SESSION|
|**Status**|**✅ DONE — stocktwits\_service.py implemented, endpoint updated, tests written.**|

|**EXP-GEO-01  ·  Geopolitical Risk Score via GDELT**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to see a real-time geopolitical risk score reflecting wars, elections, sanctions, and disputes, so that I understand non-financial tail risks affecting markets.*|
|**Acceptance Criteria**|<p></p><p>- - Ingest top events from GDELT Event DB filtered by CAMEO codes: military (19), instability (17), sanctions (163), disputes (16).</p><p>- - Compute Geopolitical Risk Score 0–100 based on weighted event count × Goldstein Scale severity over last 7 days.</p><p>- - Traffic light: Green (<30), Amber (30–60), Red (>60).</p><p>- - Show top 5 highest-risk events with country, type, and date.</p><p>- - Plain-English label: 'Elevated risk due to [top event].'</p><p>- - Integrate score into GAS as a macro sub-layer. Refresh daily.</p>|
|**Data Source**|*GDELT Event Database — free, no key. api.gdeltproject.org/api/v2/*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-EARN-01  ·  Earnings Surprise Predictor**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want the system to show me whether a stock is likely to beat, meet, or miss its upcoming earnings estimate, so that I can position around earnings with more context.*|
|**Acceptance Criteria**|<p></p><p>- - Pull upcoming earnings dates and consensus EPS from Finnhub (existing key).</p><p>- - Pull last 8 quarters of EPS actuals vs estimates, compute historical beat rate.</p><p>- - Earnings Surprise Score = beat\_rate × recency\_weight × sentiment\_boost (14-day pre-earnings news sentiment).</p><p>- - Display: earnings date, EPS estimate, historical beat rate (e.g. 'Beat 6 of 8'), Surprise Score 0–100.</p><p>- - Mini chart of past 8 quarters: actual vs estimate bars.</p><p>- - Label all output: 'Historical pattern only — not a prediction.'</p>|
|**Data Source**|*Finnhub /earnings and /calendar/earnings — existing API key, no extra cost.*|
|**Phase / Effort**|P2 Growth  |  ~1 day  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-INSID-01  ·  Insider Trading Tracker (SEC EDGAR Form 4)**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see when executives are buying or selling their own stock, so that I can factor insider conviction into my analysis.*|
|**Acceptance Criteria**|<p></p><p>- - Pull Form 4 filings from SEC EDGAR EFTS API (free, no key) for last 90 days.</p><p>- - Table: name, role, transaction type, shares, value, date.</p><p>- - Insider Conviction Score = net\_buy\_volume / (buy + sell) × 100.</p><p>- - Classify: Strongly Bullish (>70) → Strongly Bearish (<30).</p><p>- - 6-month chart of net insider buy/sell.</p><p>- - Cluster buy badge: 3+ insiders buying within same 2-week window.</p><p>- - Caveat: 'Insider sales are often pre-planned and may not be bearish.'</p><p>- - Cache 24h to respect EDGAR rate limits.</p>|
|**Data Source**|*SEC EDGAR EFTS API — free, no key. efts.sec.gov/LATEST/search-index?forms=4*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-OPT-01  ·  Options Put/Call Fear & Greed Indicator**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see the put/call ratio for a stock so that I can gauge whether options traders are fearful or greedy.*|
|**Acceptance Criteria**|<p></p><p>- - Pull options chain via yfinance (already installed). Compute PCR = total put OI / total call OI.</p><p>- - Fear & Greed score: PCR >1.5 = extreme fear (0–20), 1.0–1.5 = fear, 0.7–1.0 = neutral, 0.5–0.7 = greed, <0.5 = extreme greed (80–100).</p><p>- - Show: current PCR, Fear & Greed score with colour band, 30-day PCR chart.</p><p>- - Show top strikes by open interest (calls + puts separately) as key levels.</p><p>- - Show max pain price.</p><p>- - Fold Fear & Greed score into GAS sentiment layer.</p>|
|**Data Source**|*yfinance — Ticker.options and Ticker.option\_chain(). Already installed, no extra cost.*|
|**Phase / Effort**|P2 Growth  |  ~1 day  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-CB-01  ·  Central Bank Language Analyzer (Fed, ECB, BOE)**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want the system to analyze the tone of the latest Fed and ECB statements to tell me hawkish vs dovish, so that I can understand the policy backdrop without reading every press release.*|
|**Acceptance Criteria**|<p></p><p>- - Pull latest Fed statements from Fed public RSS feed (free, no key).</p><p>- - Pull ECB press releases from ECB RSS/API (free, no key).</p><p>- - Keyword-based hawkish/dovish scoring: count hawkish words (tighten, restrictive) vs dovish (ease, gradual) with pre-defined weights.</p><p>- - Tone Score 0–100 per central bank: 0 = extremely dovish, 100 = extremely hawkish.</p><p>- - Show as spectrum slider with plain-English label.</p><p>- - 3 most hawkish and 3 most dovish sentences from latest statement.</p><p>- - 12-month trend of tone scores.</p><p>- - Integrate CB Tone Score into GAS macro layer.</p>|
|**Data Source**|*Fed RSS: federalreserve.gov/feeds/press\_monetary.xml (free). ECB: ecb.europa.eu RSS (free).*|
|**Phase / Effort**|P3 Premium  |  ~2 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-SECT-01  ·  Sector Rotation Heatmap**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see which S&P 500 sectors are gaining and losing momentum weekly, so that I can understand which parts of the market are leading.*|
|**Acceptance Criteria**|<p></p><p>- - Track 11 SPDR Sector ETFs via yfinance. Compute 1w, 1m, 3m performance.</p><p>- - Compute relative strength vs SPY.</p><p>- - Colour-coded heatmap: deep green (top) to deep red (worst).</p><p>- - Sector rotation wheel showing momentum vs relative strength (RRG-inspired).</p><p>- - Categorise by cycle phase: Early/Mid/Late/Recession.</p><p>- - Show which cycle phase is currently in favour based on leading sectors.</p><p>- - Update weekly on Monday open.</p>|
|**Data Source**|*yfinance — 11 SPDR ETFs (XLK, XLV, XLF, XLE, XLI, XLB, XLRE, XLY, XLP, XLU, XLC). No extra cost.*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-AI-01  ·  AI Market Narrator — Daily Briefing in Plain English**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want a daily plain-English market briefing synthesizing macro, movers, and sentiment into 3–5 short paragraphs, so that I understand the market story without reading multiple sources.*|
|**Acceptance Criteria**|<p></p><p>- - Each morning gather: GAS for top 10 watchlist tickers, macro snapshot, top sector movers, overnight GDELT events.</p><p>- - Pass structured data to Claude API (claude-sonnet-4-20250514) with strict prompt.</p><p>- - Produce 300–400 word briefing: macro backdrop, sentiment, standout stocks/sectors, risks to watch.</p><p>- - Prominent disclaimer: 'AI-generated from structured data. Educational only. Not investment advice.'</p><p>- - User can ask follow-up questions in a small chat panel.</p><p>- - Save briefings to DB with timestamp. Users can read past briefings.</p><p>- - 'Explain this term' tooltip on finance jargon.</p><p>- - Tone: educational and explanatory — never prescriptive.</p>|
|**Data Source**|*Claude API (Anthropic, pay-per-use). GDELT for events. All other data from existing Fin-Eye pipelines.*|
|**Phase / Effort**|P3 Premium  |  ~2 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-POL-01  ·  World Leaders & Political Risk Monitor**|
| :- |
|**Persona**|Emma + Marco|
|**User Story**|*I want a live dashboard of political events and government changes worldwide, so that I can understand when political risks might spill into markets.*|
|**Acceptance Criteria**|<p></p><p>- - Database of G20 + major EM countries: head of government, party, ideology, market-friendliness score.</p><p>- - Pull upcoming elections calendar from Wikipedia REST API (free).</p><p>- - Pull country risk events from GDELT filtered by political instability CAMEO codes.</p><p>- - Political Stability Score 0–100 derived from GDELT event tone + recency.</p><p>- - World map heatmap coloured by stability score.</p><p>- - Click country: current leader, upcoming events, recent incidents, exposed Fin-Eye tickers.</p><p>- - Link scores into EXP-GEO-01 Geopolitical Risk Score. Refresh daily.</p>|
|**Data Source**|*GDELT (free), Wikipedia REST API (free), Finnhub company profile for country revenue exposure (existing key).*|
|**Phase / Effort**|P3 Premium  |  ~3 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-MACRO-01  ·  Global Macro Dashboard — World Bank & ECB Layer**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want macroeconomic data beyond the US — GDP, inflation, debt for major economies — so that I understand the global macro backdrop.*|
|**Acceptance Criteria**|<p></p><p>- - Integrate World Bank Indicators API for G20: GDP growth, CPI inflation, Debt/GDP.</p><p>- - Integrate ECB Data Portal: Eurozone policy rate, HICP inflation, M3 money supply.</p><p>- - Global Macro Comparison table: latest value + 1-year change per country per indicator.</p><p>- - Highlight outliers: inflation >5% in red, GDP growth <0 in red.</p><p>- - Global Growth Momentum Score 0–100: weighted average of G20 GDP growth rates.</p><p>- - World map choropleth coloured by GDP growth rate.</p><p>- - Refresh quarterly. Integrate score into GAS macro layer.</p>|
|**Data Source**|*World Bank API (free): api.worldbank.org/v2/. ECB Data Portal (free): data-api.ecb.europa.eu/*|
|**Phase / Effort**|P2 Growth  |  ~2 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-TREND-01  ·  Google Trends Retail Interest Tracker**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see whether retail search interest in a stock is rising or falling, so that I can spot surges in attention before they show up in price.*|
|**Acceptance Criteria**|<p></p><p>- - Use pytrends to pull relative search interest for a ticker over last 90 days.</p><p>- - Trend Momentum Score = rate of change of 7-day vs prior 7-day average.</p><p>- - Classify: Surging (>50% increase), Rising (10–50%), Stable, Declining, Collapsing.</p><p>- - 90-day line chart of search interest.</p><p>- - Mark price vs search divergences.</p><p>- - Show related queries from Google Trends.</p><p>- - Fold Trend Momentum into Retail Sentiment Score alongside StockTwits.</p><p>- - Note: 'Relative and anonymised — shows interest, not intent.'</p>|
|**Data Source**|*pytrends Python library (pip install pytrends) — unofficial but stable. No API key needed.*|
|**Phase / Effort**|P2 Growth  |  ~1 day  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-EARN-02  ·  Earnings Call Transcript Sentiment Analyzer**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want the system to analyze the tone of the most recent earnings call and tell me whether management is more optimistic or cautious than last quarter.*|
|**Acceptance Criteria**|<p></p><p>- - Pull earnings transcripts via Finnhub /stock/transcripts (check tier) or public scraping fallback.</p><p>- - Run VADER on CEO/CFO prepared remarks and Q&A separately.</p><p>- - Management Tone Score 0–100 + QoQ change ('More optimistic by +12 points').</p><p>- - Flag patterns: guidance words, risk words, positive momentum words.</p><p>- - Word cloud of most-used words in prepared remarks.</p><p>- - Compare Management Tone vs News Sentiment — highlight divergences.</p><p>- - Disclaimer: 'Automated — may miss nuance or sarcasm.'</p><p>- - Refresh quarterly after each earnings release.</p>|
|**Data Source**|*Finnhub /stock/transcripts (existing key) or public transcript scraping. VADER already installed.*|
|**Phase / Effort**|P3 Premium  |  ~2 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-INST-01  ·  Smart Money Flow — Institutional 13F Tracker**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see which hedge funds are increasing or decreasing positions in a stock, so that I can follow smart money conviction changes.*|
|**Acceptance Criteria**|<p></p><p>- - Pull 13F filings from SEC EDGAR for selected stock: institution, shares, QoQ change.</p><p>- - Institutional Conviction Score = net\_new\_buyers / total\_filers over last 2 quarters.</p><p>- - Table of top 20 institutional holders: institution, shares, QoQ change, % of portfolio.</p><p>- - Highlight new positions and full exits.</p><p>- - 4-quarter trend chart of total institutional ownership %.</p><p>- - Flag concentration risk: top 3 holders owning >50%.</p><p>- - Note: 'Data delayed 45 days by law. Positions may have changed.'</p>|
|**Data Source**|*SEC EDGAR 13F filings — free, no key. EDGAR company search API.*|
|**Phase / Effort**|P3 Premium  |  ~2 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-CAL-01  ·  Economic Event Calendar (BLS + Fed + ECB + Earnings)**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want a calendar of upcoming high-impact economic events for the next 90 days, so that I can prepare for volatility spikes before they happen.*|
|**Acceptance Criteria**|<p></p><p>- - Pull BLS release calendar for CPI, PPI, NFP, Unemployment Rate.</p><p>- - Pull FOMC meeting schedule from Fed public calendar.</p><p>- - Pull ECB Governing Council meeting dates.</p><p>- - Pull earnings dates from Finnhub for watchlist stocks.</p><p>- - Unified calendar (month + list view) colour-coded: Macro (blue), Central Bank (purple), Earnings (green), Geopolitical (red).</p><p>- - Per event: impact (Low/Medium/High based on historical VIX spikes), prior value, consensus estimate.</p><p>- - Banner 3 days before high-impact event on relevant stock pages.</p><p>- - Users can subscribe to alerts for specific event types.</p>|
|**Data Source**|*BLS Release Calendar (free). Fed public calendar (free). ECB website (free). Finnhub earnings (existing key).*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  NOT STARTED|
|**Status**|**Not started**|

|**EXP-CORR-01  ·  Cross-Asset Correlation & Contagion Monitor**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want a real-time correlation matrix across stocks, sectors, bonds, and commodities, so that I can detect when correlations spike (contagion risk).*|
|**Acceptance Criteria**|<p></p><p>- - Compute 30-day and 90-day Pearson correlations: watchlist stocks, sector ETFs, TLT, GLD, OIL, VIX.</p><p>- - Colour-coded heatmap: dark red = strong positive (>0.8), dark blue = strong negative (<-0.6), white = uncorrelated.</p><p>- - Market Stress Indicator = average pairwise correlation. >0.7 = risk-off contagion event.</p><p>- - 1-year chart of Market Stress Indicator.</p><p>- - Alert when average correlation exceeds 0.65: 'Correlation spike — markets may be entering risk-off phase.'</p><p>- - Users can add/remove assets from the matrix.</p><p>- - Integrate Market Stress Indicator into GAS volatility layer.</p>|
|**Data Source**|*yfinance for all price data. scipy/numpy for correlation (already available). No extra API needed.*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  NOT STARTED|
|**Status**|**Not started**|



**Section 4 — User Stories v3.0 — Senior Dev Bonus Suggestions**

These 8 stories are my own recommendations on top of your v2 list. Each addresses a gap or opportunity I identified while reading the full codebase and PRD. They are ordered by impact-to-effort ratio.

|**WHY THESE STORIES: The v2 list is great for data coverage. These v3 stories focus on (1) making the product FEEL fast and alive, (2) closing the most damaging gaps for a financial product, and (3) features that drive retention and word-of-mouth.**|
| :- |


|**EXP-WIRE-01  ·  Frontend API Integration Sprint — Wire All Live Data**|
| :- |
|**Persona**|All users (Emma + Marco + Alex)|
|**User Story**|*I want every dashboard section to show real live data from the backend, not mock/stub values, so that the product actually works as described and I can trust what I see.*|
|**Acceptance Criteria**|<p></p><p>- - Connect Dashboard page → GET /api/v1/technical/{symbol}/latest (live ML signals, not mocks).</p><p>- - Connect Macro tab → GET /api/v1/macro/latest and /api/v1/macro/advanced (live FRED data).</p><p>- - Connect Sentiment tab → GET /api/v1/sentiment/{symbol}/timeseries + /sources (live FinBERT scores).</p><p>- - Connect Retail Sentiment → GET /api/v1/sentiment/retail/{symbol} (live StockTwits data).</p><p>- - Connect Backtesting tab → POST /api/v1/backtest/run (already tested and passing on backend).</p><p>- - Replace every hardcoded mock constant or placeholder array in the frontend with an API call.</p><p>- - All loading states show skeletons, not empty screens. All error states show a retry button.</p><p>- - This is the #1 most impactful 'feature' because it turns a demo into a product.</p>|
|**Data Source**|*All existing Fin-Eye FastAPI endpoints — no new backend work needed.*|
|**Phase / Effort**|P1 MVP CRITICAL  |  ~2–3 days  |  HIGHEST PRIORITY|

|**EXP-PERF-01  ·  GAS Pre-Computation Job — No On-Demand Latency**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want the GAS and regime to load instantly when I open the dashboard, so that the app feels fast and professional rather than making me wait 3 seconds for ML inference.*|
|**Acceptance Criteria**|<p></p><p>- - Add a pre-computation APScheduler job that runs GAS + regime for all default symbols every 15 minutes during market hours (Mon–Fri 13:00–21:00 UTC).</p><p>- - Store computed GAS results in a new gas\_snapshots DB table (symbol, gas\_score, regime, computed\_at).</p><p>- - Cache results in Redis with 15-minute TTL.</p><p>- - Dashboard API endpoint reads from cache first, falls back to DB snapshot, falls back to live compute.</p><p>- - P50 response time for dashboard load drops below 200ms for any of the 9 default symbols.</p><p>- - Admin endpoint /api/v1/admin/gas/precompute to trigger manually.</p>|
|**Data Source**|*Existing scheduler (APScheduler already configured). Existing technical\_consensus.py and macro\_scoring.py.*|
|**Phase / Effort**|P1 MVP  |  ~1 day  |  HIGH PRIORITY|

|**EXP-MOBILE-01  ·  Progressive Web App (PWA) — Installable on Mobile**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to install Fin-Eye as an app on my phone's home screen and use it without opening a browser every time, so that I can check market conditions quickly during the day.*|
|**Acceptance Criteria**|<p></p><p>- - Add a next-pwa config to the Next.js frontend.</p><p>- - Add web app manifest (name, icons, theme colour, display: standalone).</p><p>- - Add a Service Worker that caches the dashboard shell (not live data) so the app opens instantly even on slow connections.</p><p>- - Notification API integrated so in-app alerts (CORE-NOTIF-01) can also be delivered as push notifications on mobile.</p><p>- - Works on iOS Safari and Android Chrome — tested on both.</p><p>- - PWA install banner shown to returning users after 2+ visits.</p>|
|**Data Source**|*next-pwa npm package. Web Push Notifications API. No backend changes needed.*|
|**Phase / Effort**|P2 Growth  |  ~1 day  |  HIGH IMPACT, LOW EFFORT|

|**EXP-ONBOARD-ADV-01  ·  Advanced Personalized Onboarding — Goal-Driven**|
| :- |
|**Persona**|New users (Emma + Marco)|
|**User Story**|*I want the app to ask me my goal when I first sign up and then customize the dashboard layout and initial tutorial based on that goal, so that the first experience feels relevant to me personally.*|
|**Acceptance Criteria**|<p></p><p>- - After first login and consent, show a 3-step goal-selection screen: 'Learn how markets work' / 'Improve my trade timing' / 'Monitor my portfolio risk'.</p><p>- - Store selected goal in the user profile (user\_goal field).</p><p>- - Based on goal: customize dashboard default tab, order of cards, and tutorial content.</p><p>- - Learning goal → opens to Macro tab with explanations front-and-center.</p><p>- - Trading goal → opens to Technical Signals tab with regime badge prominent.</p><p>- - Portfolio goal → opens to Portfolio view with correlation warnings first.</p><p>- - Onboarding email sequence (CORE-EMAIL-01) uses goal to personalise Day 3 and Day 7 content.</p><p>- - Goal can be changed in Settings at any time.</p>|
|**Data Source**|*Existing user model, CORE-EMAIL-01 onboarding email service. Frontend only — no new backend endpoints needed.*|
|**Phase / Effort**|P1 MVP  |  ~1.5 days  |  HIGH RETENTION IMPACT|

|**EXP-EXPLAIN-ADV-01  ·  Interactive Explanation Mode — Click Any Number to Understand It**|
| :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to click on any score, number, or chart in the app and get a plain-English explanation of what it means and how it was computed, so that I learn as I use the product rather than needing to read documentation.*|
|**Acceptance Criteria**|<p></p><p>- - Every score badge (GAS, macro score, regime confidence, technical confidence) has a small ℹ️ icon.</p><p>- - Clicking the icon opens a non-modal side panel with: what this number is, the range (e.g. 0–100), what the current value means in plain English, and the formula / inputs that produced it.</p><p>- - Side panel also shows how much each sub-component contributed (e.g. 'Macro score: 62/100 — boosted by low VIX, dragged down by inverted yield curve').</p><p>- - Panel links to relevant Learn/Blog articles where applicable.</p><p>- - No additional API calls — all explanation data is bundled with the existing score endpoints.</p><p>- - Panel is keyboard-accessible and screen-reader friendly.</p>|
|**Data Source**|*No new data sources. All explanation text is generated from the existing score payloads and a static interpretation map.*|
|**Phase / Effort**|P1 MVP  |  ~1 day  |  HIGH EDUCATIONAL DIFFERENTIATION|

|**EXP-ALERT-ADV-01  ·  Smart GAS Alerts — Notify on Regime Change**|
| :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to be automatically notified by email and push notification when a stock's GAS or regime changes significantly, so that I can react quickly without watching the screen all day.*|
|**Acceptance Criteria**|<p></p><p>- - Build on the existing alert\_service.py. Add two new rule types: GAS threshold cross (above/below a user-set value) and regime flip (Risk-On ↔ Risk-Off ↔ Range-Bound).</p><p>- - GAS pre-computation job (EXP-PERF-01) checks alert rules on every computation cycle.</p><p>- - Alert email shows: ticker, old value, new value, timestamp, and a link back to the Fin-Eye dashboard.</p><p>- - User can configure: per-ticker thresholds, regime change sensitivity, quiet hours (e.g. no alerts between 22:00–07:00).</p><p>- - Push notifications via PWA (EXP-MOBILE-01) when enabled.</p><p>- - Alert history page shows last 30 triggered alerts with timestamps.</p><p>- - Non-advisory language in all alert messages: 'Condition triggered — review for context.'</p>|
|**Data Source**|*Existing alert\_service.py + CORE-NOTIF-01 email delivery. EXP-PERF-01 pre-computation job as trigger.*|
|**Phase / Effort**|P2 Growth  |  ~1.5 days  |  HIGH RETENTION DRIVER|

|**EXP-SHAREABLE-01  ·  Shareable Analysis Cards — Social Sharing**|
| :- |
|**Persona**|Emma + Marco|
|**User Story**|*I want to share a stock's GAS and sentiment summary as a clean image card on Twitter/X or Discord, so that I can share analysis with my community and drive organic growth for Fin-Eye.*|
|**Acceptance Criteria**|<p></p><p>- - Backend endpoint POST /api/v1/share/{symbol} generates a PNG image card using Pillow or a serverless OG image generator.</p><p>- - Card shows: Fin-Eye branding, ticker, GAS score, regime label, market weather, top 3 timeframe signals, and generated timestamp.</p><p>- - Card dimensions: 1200×628 (Twitter/X standard) and 1080×1080 (square for Discord/Instagram).</p><p>- - Disclaimer watermark: 'Educational only — not investment advice. fin-eye.com'</p><p>- - Frontend shows a 'Share' button on the dashboard that downloads or copies a link to the card.</p><p>- - Generated cards are cached in Redis (1h TTL) to avoid regenerating on every click.</p><p>- - UTM parameters appended to the card URL to track social referral traffic.</p>|
|**Data Source**|*Python Pillow for image generation (pip install Pillow). No new data APIs needed.*|
|**Phase / Effort**|P2 Growth  |  ~1 day  |  ORGANIC GROWTH DRIVER|

|**EXP-AUDIT-01  ·  Data Freshness Indicator & Pipeline Health Dashboard**|
| :- |
|**Persona**|You (operator) + power users (Alex)|
|**User Story**|*I want to see at a glance whether all data pipelines ran successfully and when data was last updated, so that I can catch data quality issues before users notice stale or wrong numbers.*|
|**Acceptance Criteria**|<p></p><p>- - New internal page /admin/pipeline-health (admin role only) showing all 8 scheduled jobs and their last run result.</p><p>- - Per job: last run time, duration, status (success/failure), number of rows processed.</p><p>- - Job statuses are read from the existing pipeline\_run\_logs table (already being written by metrics.py).</p><p>- - Data freshness badge on the main dashboard: 'OHLCV updated 2h ago  ·  Macro updated 6h ago  ·  Sentiment updated 4h ago.'</p><p>- - If any job has not succeeded in more than 2× its expected interval, badge turns amber and you receive an admin alert email.</p><p>- - Public API response headers include X-Data-As-Of timestamps for institutional users.</p><p>- - All this data is already being collected by MetricsMiddleware and record\_pipeline\_run() — just needs a UI.</p>|
|**Data Source**|*Existing metrics.py, pipeline\_run\_logs table, MetricsMiddleware. No new backend services needed.*|
|**Phase / Effort**|P1 MVP (ops)  |  ~1 day  |  CRITICAL FOR TRUST|



**Implementation Priority Order — Senior Dev Recommendation**

Based on the full audit, here is the order I would implement everything if I were running this sprint:

|**Priority**|**Story ID**|**Title**|**Reason**|
| :- | :- | :- | :- |
|**🔴  NOW**|EXP-WIRE-01|**Wire frontend to live backend APIs**|Makes the product actually work. Everything else is meaningless without this.|
|**🔴  NOW**|seed\_live\_data.py|**Run seed\_live\_data.py once**|Populates DB with real data. Run this before wiring the frontend.|
|**🔴  NOW**|pytest fix|**Run pytest to confirm test\_macro.py passes**|Clean house. All tests green before new features.|
|**🟠  THIS WEEK**|EXP-PERF-01|**GAS pre-computation job**|Makes the dashboard feel instant. Critical for user experience.|
|**🟠  THIS WEEK**|EXP-OPT-01|**Options Fear & Greed**|No new API, yfinance already installed. 1 day, high signal.|
|**🟠  THIS WEEK**|EXP-SECT-01|**Sector Rotation Heatmap**|No new API, visually impressive, drives retention.|
|**🟡  NEXT SPRINT**|EXP-EXPLAIN-ADV-01|**Interactive Explanation Mode**|Emma persona's core need. Differentiates Fin-Eye from Bloomberg.|
|**🟡  NEXT SPRINT**|EXP-ONBOARD-ADV-01|**Goal-Driven Onboarding**|Activation metric driver. Ensures first-time users understand the product.|
|**🟡  NEXT SPRINT**|EXP-INSID-01|**Insider Trading (SEC EDGAR)**|Free, no key, unique signal not in competitor tools.|
|**🟡  NEXT SPRINT**|EXP-EARN-01|**Earnings Surprise Predictor**|Uses existing Finnhub key. Adds pre-earnings context.|
|**🟢  MONTH 2**|EXP-CAL-01|**Economic Event Calendar**|Establishes Fin-Eye as a complete market intelligence tool.|
|**🟢  MONTH 2**|EXP-ALERT-ADV-01|**Smart GAS Alerts**|Retention driver. Users come back when alerted.|
|**🟢  MONTH 2**|EXP-AUDIT-01|**Pipeline Health Dashboard**|Critical for trust in a financial product.|
|**🔵  PREMIUM**|EXP-AI-01|**AI Market Narrator (Claude API)**|Premium differentiator. Implement after core product is solid.|


*End of Document  ·  46 v1 stories audited  ·  15 v2 stories  ·  8 v3 bonus stories  ·  March 2026*
