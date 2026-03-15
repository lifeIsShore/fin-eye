**Fin-Eye**

Experimental Features — User Story Series v2.0

*15 New Feature Stories  |  External APIs & Data Sources  |  Brainstorm Edition*

# **Overview**
This document defines 15 new experimental user stories for Fin-Eye, organized after a full codebase audit. It also resolves the Reddit question (replace with StockTwits), documents all new free and low-cost data sources, and introduces features spanning geopolitical intelligence, options flow, AI narration, insider tracking, and global macro.

All stories follow the same format as user-stories.md v1.5 and are intended to be appended as Series 2.0.

## **Immediate Action: Replace Reddit with StockTwits**
The existing reddit\_service.py already has mock fallback, so nothing is broken. However StockTwits is a direct upgrade: it requires no API key, no OAuth, targets the financial community specifically, and crucially — users self-tag their posts as Bullish or Bearish, giving you labelled sentiment data for free without needing VADER inference.

## **New Data Sources Summary**

|**Source**|**Data**|**Cost**|**Key Required?**|
| :- | :- | :- | :- |
|**StockTwits API**|Retail sentiment, bullish/bearish labels|Free|No — zero auth|
|**GDELT Event DB**|Global news events, geopolitical risk|Free|No — open API|
|**SEC EDGAR**|13F institutional holdings, Form 4 insiders|Free|No — open API|
|**World Bank API**|GDP, inflation, debt/GDP for G20+|Free|No — open API|
|**ECB Data Portal**|Eurozone rates, inflation, M3|Free|No — open API|
|**BLS Release Calendar**|CPI, PPI, NFP release dates|Free|No for calendar|
|**yfinance (options)**|Put/call ratio, max pain, OI by strike|Free|No — library|
|**pytrends**|Google Trends search interest|Free|No — library|
|**Fed RSS Feed**|FOMC statements and press releases|Free|No — public RSS|
|**Claude API (Anthropic)**|AI daily market narrator|**Pay-per-use**|Yes — Anthropic API|


# **User Stories**

|**EXP-SENT-01  StockTwits Retail Sentiment (Reddit Replacement)**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see what retail traders are saying about a stock on StockTwits with real bullish/bearish labels, so that I can gauge crowd sentiment without needing Reddit access.*|
|**Acceptance Criteria**|<p>- Replace reddit\_service.py with stocktwits\_service.py using the free public API (no auth needed).</p><p>- Endpoint: GET https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json</p><p>- Each message has a built-in sentiment label: 'Bullish' or 'Bearish' — use these directly instead of running VADER.</p><p>- Show: total messages in last 24h, % bullish, % bearish, top 5 bullish and top 5 bearish messages.</p><p>- Retail Sentiment Score (0–100) derived from ratio of bullish vs bearish labels.</p><p>- No API key or OAuth required — works immediately out of the box.</p><p>- Existing mock fallback remains for tickers with no StockTwits coverage.</p><p>- UI unchanged — sentiment tab continues to work as before.</p>|
|**Data Source**|StockTwits Public API — free, no key, no auth. https://api.stocktwits.com/api/2/streams/symbol/AAPL.json|
|**Phase / Effort**|P2 Growth  |  ~4 hours (drop-in replacement)|


|**EXP-GEO-01  Geopolitical Risk Score via GDELT**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to see a real-time geopolitical risk score that reflects global events — wars, elections, sanctions, trade disputes — so that I understand non-financial tail risks affecting markets.*|
|**Acceptance Criteria**|<p>- Ingest top news events from the GDELT Event Database API (free, no key required).</p><p>- Filter events by CAMEO event codes relevant to market risk: military conflict (19), political instability (17), sanctions (163), and diplomatic disputes (16).</p><p>- Compute a Geopolitical Risk Score (0–100) based on weighted event count and Goldstein Scale severity in the last 7 days.</p><p>- Display the score on the macro dashboard with a traffic light: Green (<30), Amber (30–60), Red (>60).</p><p>- Show top 5 highest-risk events with country, event type, and date.</p><p>- Optionally link geopolitical score into the overall Global Alignment Score as a macro sub-layer.</p><p>- Score updates once daily (not real-time — GDELT data is 15-min delayed and daily batch is sufficient).</p><p>- Include a plain-English explanation: 'Elevated geopolitical risk due to [top event].'</p>|
|**Data Source**|GDELT Event Database — free, no key. http://api.gdeltproject.org/api/v2/doc/doc|
|**Phase / Effort**|P2 Growth  |  ~1.5 days|


|**EXP-EARN-01  Earnings Surprise Predictor**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want the system to show me whether a stock is likely to beat, meet, or miss its upcoming earnings estimate, so that I can position around earnings events with more context.*|
|**Acceptance Criteria**|<p>- Pull upcoming earnings dates and analyst consensus EPS estimates from Finnhub (already have the key).</p><p>- Pull last 8 quarters of EPS actuals vs estimates to compute a 'beat rate' per company.</p><p>- Compute an Earnings Surprise Score: beat\_rate \* recency\_weight \* sentiment\_boost.</p><p>- sentiment\_boost comes from the news sentiment score in the 14 days before earnings.</p><p>- Display: upcoming earnings date, consensus EPS estimate, historical beat rate (e.g. 'Beat 6 of last 8'), and Surprise Score (0–100).</p><p>- Show a mini chart of past EPS actuals vs estimates over 8 quarters.</p><p>- Clearly label all output as 'historical pattern only — not a prediction' with educational disclaimer.</p><p>- Integrate the Earnings Surprise Score into the 7-day event risk panel on the dashboard.</p>|
|**Data Source**|Finnhub /earnings and /calendar/earnings — already have key. No extra API needed.|
|**Phase / Effort**|P2 Growth  |  ~1 day|


|**EXP-INSID-01  Insider Trading Tracker (SEC EDGAR Form 4)**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see when executives and directors are buying or selling their own company stock, so that I can factor insider conviction into my analysis.*|
|**Acceptance Criteria**|<p>- Pull Form 4 filings from the SEC EDGAR full-text search API (free, no key required).</p><p>- For a selected ticker, display a table of insider transactions in the last 90 days: name, role, transaction type (buy/sell), shares, value, and date.</p><p>- Compute an Insider Conviction Score: net buy volume / (buy + sell volume) \* 100, where 100 = all buying.</p><p>- Classify: Strongly Bullish (>70), Mildly Bullish (50–70), Neutral (40–50), Mildly Bearish (30–40), Strongly Bearish (<30).</p><p>- Show a 6-month trend chart of net insider buying/selling.</p><p>- Highlight cluster buys (3+ insiders buying within the same 2-week window) with a special badge.</p><p>- Include a clear caveat: 'Insider sales are often pre-planned and may not be bearish.'</p><p>- Cache results for 24 hours to respect EDGAR rate limits.</p>|
|**Data Source**|SEC EDGAR EFTS API — free, no key. https://efts.sec.gov/LATEST/search-index?q=%22AAPL%22&dateRange=custom&startdt=2025-01-01&forms=4|
|**Phase / Effort**|P2 Growth  |  ~1.5 days|


|**EXP-OPT-01  Options Put/Call Fear & Greed Indicator**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see the put/call ratio for a stock and the overall market, so that I can gauge whether options traders are fearful or greedy.*|
|**Acceptance Criteria**|<p>- Pull options chain data via yfinance (already installed) — no extra API key needed.</p><p>- Compute Put/Call Ratio (PCR) = total put open interest / total call open interest.</p><p>- Compute a Fear & Greed score from PCR: PCR > 1.5 = extreme fear (0–20), 1.0–1.5 = fear (20–40), 0.7–1.0 = neutral (40–60), 0.5–0.7 = greed (60–80), < 0.5 = extreme greed (80–100).</p><p>- Show: current PCR value, Fear & Greed score with colour band and label, and a 30-day chart of PCR.</p><p>- Show top strikes with highest open interest (calls and puts separately) — these act as key levels.</p><p>- Also show max pain price (the strike where option sellers lose least).</p><p>- Make Fear & Greed score available as an input to the Global Alignment Score sentiment layer.</p><p>- Update on every page load for the selected ticker.</p>|
|**Data Source**|yfinance Python library — already installed. Ticker.options and Ticker.option\_chain(). No extra cost.|
|**Phase / Effort**|P2 Growth  |  ~1 day|


|**EXP-CB-01  Central Bank Language Analyzer (Fed, ECB, BOE)**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want the system to analyze the language of the latest Fed, ECB, and BOE statements to tell me whether central bank tone is hawkish, neutral, or dovish, so that I can understand the policy backdrop without reading every press release.*|
|**Acceptance Criteria**|<p>- Pull latest Fed statements from the Fed's public RSS feed (free, no key).</p><p>- Pull ECB press releases from the ECB RSS/API (free, no key).</p><p>- Run a keyword-based hawkish/dovish scoring model: count hawkish words (tighten, restrictive, inflation, concerned) vs dovish words (support, ease, gradual, data-dependent) with pre-defined weights.</p><p>- Produce a Tone Score (0–100): 0 = extremely dovish, 50 = neutral, 100 = extremely hawkish.</p><p>- Show the score as a spectrum slider for each central bank with a plain-English label.</p><p>- Display the 3 most hawkish and 3 most dovish sentences extracted from the latest statement.</p><p>- Show a 12-month trend of tone scores to see if policy is becoming more or less hawkish over time.</p><p>- Integrate CB Tone Score into the macro layer of the Global Alignment Score.</p><p>- Refresh weekly or on new statement publication.</p>|
|**Data Source**|Fed RSS: https://www.federalreserve.gov/feeds/press\_monetary.xml (free, no key). ECB: https://www.ecb.europa.eu/press/pr/activities/mopo/html/index.en.html|
|**Phase / Effort**|P3 Premium  |  ~2 days|


|**EXP-SECT-01  Sector Rotation Heatmap**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see which S&P 500 sectors are gaining and losing momentum on a weekly basis, so that I can understand which parts of the market are leading and which are lagging.*|
|**Acceptance Criteria**|<p>- Track the 11 SPDR Sector ETFs (XLK, XLV, XLF, XLE, XLI, XLB, XLRE, XLY, XLP, XLU, XLC) using yfinance.</p><p>- Compute 1-week, 1-month, and 3-month performance for each sector.</p><p>- Compute relative strength vs SPY for each sector (sector return / SPY return).</p><p>- Display a colour-coded heatmap grid: deep green (top performers) to deep red (worst performers).</p><p>- Show an animated sector rotation wheel (inspired by RRG — Relative Rotation Graph) showing momentum vs relative strength.</p><p>- Categorise sectors by economic cycle phase: Early Cycle (Financials, Consumer Discretionary), Mid Cycle (Tech, Industrials), Late Cycle (Energy, Materials), Recession (Utilities, Healthcare, Consumer Staples).</p><p>- Show which cycle phase is currently 'in favour' based on which sectors are leading.</p><p>- Update weekly on Monday open.</p>|
|**Data Source**|yfinance — sector ETFs are standard tickers. No extra API needed. OpenFIGI for sector classification if needed (free).|
|**Phase / Effort**|P2 Growth  |  ~1.5 days|


|**EXP-AI-01  AI Market Narrator — Daily Briefing in Plain English**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to receive a daily plain-English market briefing that synthesizes macro conditions, top movers, and sentiment into 3–5 short paragraphs, so that I can understand the market story without reading multiple sources.*|
|**Acceptance Criteria**|<p>- Each morning (or on demand), system gathers: GAS for top 10 watchlist tickers, macro snapshot (rates, VIX, yield curve slope), top sector movers, and overnight global events from GDELT.</p><p>- Pass the structured data to the Claude API (claude-sonnet-4-20250514) with a strict prompt template.</p><p>- Prompt instructs the model to produce a 300–400 word briefing in plain English with: 1 paragraph on macro backdrop, 1 on market sentiment, 1 on standout stocks/sectors, 1 on risks to watch.</p><p>- Prominently display: 'This briefing is AI-generated from structured data and is for educational purposes only. It is not investment advice.'</p><p>- Allow the user to ask follow-up questions about the briefing in a small chat panel below it.</p><p>- Save the briefing to the database with a timestamp so users can read past daily briefings.</p><p>- Include a 'Explain this term' tooltip on any finance jargon in the briefing.</p><p>- Tone should be educational and explanatory — never prescriptive (no 'you should buy X').</p>|
|**Data Source**|Claude API (Anthropic) — uses the existing API infrastructure. GDELT for event context. All other data from existing Fin-Eye pipelines.|
|**Phase / Effort**|P3 Premium  |  ~2 days|


|**EXP-POL-01  World Leaders & Political Risk Monitor**||
| :- | :- |
|**Persona**|Emma (finance student) / Marco (retail trader)|
|**User Story**|*I want to see a live dashboard of major political events, elections, and government changes worldwide, so that I can understand when country-specific political risks might spill over into markets.*|
|**Acceptance Criteria**|<p>- Maintain a database of G20 + major emerging market countries with: current head of government, party, ideology (left/centre/right), market-friendliness score (derived from policy stance).</p><p>- Pull upcoming elections calendar from a public dataset (Wikipedia via REST API or pre-seeded database).</p><p>- Pull country risk events from GDELT filtered by political instability CAMEO codes.</p><p>- For each country: show a Political Stability Score (0–100) derived from GDELT event tone and recency.</p><p>- Highlight countries with elections in the next 90 days with a badge.</p><p>- Show a world map heatmap coloured by political stability score.</p><p>- Allow user to click a country and see: current leader, upcoming events, recent political events, and which Fin-Eye tickers are most exposed (e.g. companies with majority revenue from that country).</p><p>- Link political risk scores into the Geopolitical Risk Score (EXP-GEO-01).</p><p>- Data refreshes daily.</p>|
|**Data Source**|GDELT (free, no key), Wikipedia REST API for elections data (free, no key), Finnhub company profile for country revenue exposure (existing key).|
|**Phase / Effort**|P3 Premium  |  ~3 days|


|**EXP-MACRO-01  Global Macro Dashboard — World Bank & ECB Layer**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to see macroeconomic data beyond the US — GDP growth, inflation, and debt levels for major economies — so that I can understand the global macro backdrop, not just the US picture.*|
|**Acceptance Criteria**|<p>- Integrate the World Bank Indicators API (free, no key) for: GDP growth rate (NY.GDP.MKTP.KD.ZG), inflation (FP.CPI.TOTL.ZG), debt/GDP (GC.DOD.TOTL.GD.ZS) for G20 countries.</p><p>- Integrate the ECB Data Portal API (free, no key) for Eurozone: policy rate, HICP inflation, M3 money supply.</p><p>- Build a Global Macro Comparison table showing the latest value + 1-year change for each indicator per country.</p><p>- Highlight outliers: countries with inflation > 5% in red, GDP growth < 0 in red.</p><p>- Compute a Global Growth Momentum Score (0–100): weighted average of G20 GDP growth rates.</p><p>- Display a world map choropleth coloured by GDP growth rate.</p><p>- Refresh quarterly (World Bank data is quarterly/annual).</p><p>- Integrate Global Growth Momentum Score into the existing macro layer of the Global Alignment Score.</p>|
|**Data Source**|World Bank API (free, no key): https://api.worldbank.org/v2/. ECB Data Portal (free, no key): https://data-api.ecb.europa.eu/|
|**Phase / Effort**|P2 Growth  |  ~2 days|


|**EXP-TREND-01  Google Trends Retail Interest Tracker**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see whether retail search interest in a stock is rising or falling on Google, so that I can spot surges in retail attention before they show up in price.*|
|**Acceptance Criteria**|<p>- Use pytrends (unofficial Google Trends Python library) to pull relative search interest for a stock ticker over the last 90 days.</p><p>- Compute a Trend Momentum Score: rate of change of 7-day average search interest over the prior 7-day average.</p><p>- Classify: Surging (>50% increase), Rising (10–50%), Stable, Declining (<10% drop), Collapsing (>30% drop).</p><p>- Show a line chart of 90-day search interest trend.</p><p>- Compare search trend with price trend — mark divergences (price up but search interest down, or vice versa).</p><p>- Show related queries from Google Trends — what people are searching alongside the ticker.</p><p>- Fold Google Trends Momentum into the Retail Sentiment Score alongside StockTwits data.</p><p>- Refresh daily. Include note: 'Google Trends data is relative and anonymised — it shows interest, not intent.'</p>|
|**Data Source**|pytrends Python library (pip install pytrends) — unofficial but widely used. No API key needed.|
|**Phase / Effort**|P2 Growth  |  ~1 day|


|**EXP-EARN-02  Earnings Call Transcript Sentiment Analyzer**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want the system to analyze the tone of a company's most recent earnings call transcript and tell me whether management is more optimistic or cautious than last quarter, so that I can spot early signals of deteriorating or improving fundamentals.*|
|**Acceptance Criteria**|<p>- Pull earnings call transcripts from the free Motley Fool / SeekingAlpha public pages via web scraping, or use Finnhub's earnings transcript endpoint if available in our tier.</p><p>- Run VADER sentiment analysis on the CEO/CFO prepared remarks and Q&A sections separately.</p><p>- Compute Management Tone Score (0–100) and a QoQ change indicator (e.g. 'More optimistic than last quarter by +12 points').</p><p>- Flag specific language patterns: forward guidance words (expect, anticipate, project), risk words (uncertainty, headwind, challenging), and positive momentum words (record, growth, strong).</p><p>- Show a word cloud of the most frequently used words in the prepared remarks.</p><p>- Compare Management Tone vs News Sentiment for the same stock — divergences are highlighted.</p><p>- Include disclaimer: 'Sentiment analysis of transcripts is automated and may miss nuance or sarcasm.'</p><p>- Refresh quarterly after each earnings release.</p>|
|**Data Source**|Finnhub /stock/transcripts (check tier limits). Fallback: scrape public earnings transcript pages. VADER already installed in requirements.|
|**Phase / Effort**|P3 Premium  |  ~2 days|


|**EXP-INST-01  Smart Money Flow — Institutional 13F Tracker**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see which hedge funds and institutional investors are increasing or decreasing their positions in a stock, so that I can follow smart money and detect conviction changes.*|
|**Acceptance Criteria**|<p>- Pull 13F filings from SEC EDGAR for a selected stock: which institutions hold it and the QoQ change in shares held.</p><p>- Compute an Institutional Conviction Score: net\_new\_buyers / total\_filers over the last 2 quarters.</p><p>- Show a table of top 20 institutional holders with: institution name, shares held, QoQ change (+ or -), and % of portfolio.</p><p>- Highlight notable new positions (institutions that started a new position this quarter).</p><p>- Highlight notable exits (institutions that fully sold their position this quarter).</p><p>- Show a 4-quarter trend chart of total institutional ownership % for the stock.</p><p>- Show concentration risk: if top 3 holders own >50%, flag it as high concentration.</p><p>- Refresh quarterly (13F filings are quarterly with 45-day lag).</p><p>- Add note: 'Institutional data is delayed 45 days by law. Positions may have changed.'</p>|
|**Data Source**|SEC EDGAR full-text search for 13F filings — free, no key. EDGAR company search API.|
|**Phase / Effort**|P3 Premium  |  ~2 days|


|**EXP-CAL-01  Economic Event Calendar — BLS + Fed + ECB**||
| :- | :- |
|**Persona**|Emma (finance student)|
|**User Story**|*I want to see a calendar of upcoming high-impact economic events (CPI release, FOMC meeting, NFP) for the next 90 days with estimated market impact, so that I can prepare for volatility spikes before they happen.*|
|**Acceptance Criteria**|<p>- Pull BLS data release calendar (free JSON API at api.bls.gov — no key for basic use) for: CPI, PPI, NFP, Unemployment Rate.</p><p>- Pull FOMC meeting schedule from the Fed public calendar (free, no key).</p><p>- Pull ECB Governing Council meeting dates from the ECB website.</p><p>- Pull earnings dates from Finnhub for the user's watchlist stocks.</p><p>- Display a unified calendar view (month and list view) with events colour-coded by type: Macro (blue), Central Bank (purple), Earnings (green), Geopolitical (red).</p><p>- For each event, show: estimated market impact (Low / Medium / High based on historical VIX spikes around the event), prior value, and consensus estimate if available.</p><p>- In the 3 days before a high-impact event, show a banner on the relevant stock/macro pages: 'High-impact event in 3 days.'</p><p>- Allow users to subscribe to alerts for specific event types.</p><p>- Refresh weekly.</p>|
|**Data Source**|BLS Release Calendar API (free). Federal Reserve calendar (public HTML, scrape or public JSON). Finnhub earnings calendar (existing key). GDELT for geopolitical events.|
|**Phase / Effort**|P2 Growth  |  ~1.5 days|


|**EXP-CORR-01  Cross-Asset Correlation & Contagion Monitor**||
| :- | :- |
|**Persona**|Marco (retail trader)|
|**User Story**|*I want to see a real-time correlation matrix across stocks, sectors, bonds, and commodities, so that I can detect when correlations are rising (indicating contagion risk or a risk-off event).*|
|**Acceptance Criteria**|<p>- Compute rolling 30-day and 90-day Pearson correlations between: user's watchlist stocks, major sector ETFs (XLK, XLV etc.), bond proxies (TLT, IEF), commodities (GLD, OIL), and VIX.</p><p>- Display as an interactive colour-coded heatmap: dark red = strong positive correlation (>0.8), dark blue = strong negative (<-0.6), white = uncorrelated.</p><p>- Compute a Market Stress Indicator: average pairwise correlation of all asset pairs. When this rises above 0.7, it indicates a risk-off event where 'everything falls together'.</p><p>- Show a 1-year chart of the Market Stress Indicator to show periods of contagion.</p><p>- Alert the user when average pairwise correlation exceeds 0.65 (configurable threshold) — labelled 'Correlation spike detected: markets may be entering a risk-off phase.'</p><p>- Allow users to add/remove assets from the correlation matrix.</p><p>- Integrate Market Stress Indicator into the Global Alignment Score volatility layer.</p><p>- Use yfinance for all OHLCV data — no extra API needed.</p>|
|**Data Source**|yfinance for all price data. scipy/numpy for correlation computation (already available in Python). No extra API needed.|
|**Phase / Effort**|P2 Growth  |  ~1.5 days|


# **Implementation Roadmap**

## **Wave 1 — Immediate Wins (This Week, No New API Keys)**
- EXP-SENT-01 — StockTwits (4 hours, no API key, replaces Reddit cleanly)
- EXP-OPT-01 — Options Put/Call (1 day, uses yfinance already installed)
- EXP-SECT-01 — Sector Rotation Heatmap (1.5 days, uses yfinance)
- EXP-EARN-01 — Earnings Surprise (1 day, uses Finnhub already have key)

## **Wave 2 — Short Sprint (2–3 Weeks)**
- EXP-INSID-01 — Insider Trading via SEC EDGAR (1.5 days, free)
- EXP-MACRO-01 — World Bank + ECB macro layer (2 days, free)
- EXP-GEO-01 — Geopolitical Risk via GDELT (1.5 days, free)
- EXP-CAL-01 — Economic Event Calendar (1.5 days, mostly free)
- EXP-TREND-01 — Google Trends (1 day, no key)
- EXP-CORR-01 — Cross-Asset Correlations (1.5 days, yfinance)

## **Wave 3 — Premium / Experimental (4–6 Weeks)**
- EXP-CB-01 — Central Bank Language Analyzer (2 days, free data)
- EXP-POL-01 — World Leaders Political Risk Monitor (3 days, free data)
- EXP-AI-01 — AI Market Narrator via Claude API (2 days, Claude API cost)
- EXP-EARN-02 — Earnings Call Transcript Sentiment (2 days, scraping)
- EXP-INST-01 — Institutional 13F Tracker (2 days, free SEC data)


# **Remaining Blockers Before First Run**
Before any of the above features, these two items in backend/.env must be completed:

|**Setting**|**Generate Command**|**Status**|
| :- | :- | :- |
|**JWT\_SECRET**|python -c "import secrets; print(secrets.token\_hex(32))"|Needs user action|
|**TOTP\_ENCRYPTION\_KEY**|python -c "from cryptography.fernet import Fernet; print(Fernet.generate\_key().decode())"|Needs user action|

*Run both commands in a Python terminal, copy the output, and paste into backend/.env. Then run: alembic upgrade head, then uvicorn app.main:app --reload.*


*End of User Stories Series v2.0 — 15 stories, 10 new free data sources, 3 waves of implementation*
