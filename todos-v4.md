# Fin-Eye — Todos v4
> **Version:** 4.1 (updated with confirmed answers)
> **Created:** 2026-03-20
> **Author:** Product + Dev (AI-assisted deep codebase review)
> **Status:** Active implementation backlog — NEW features only
>
> ⚠️ This file covers NEW functionality NOT in todos-v3.md.
> todos-v3.md = existing app polish, bug fixes, security hardening.
> todos-v4.md = bulk data pipeline, ML automation, news storage strategy, external scraping.
>
> **Legend:** 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Nice-to-have · ✅ Done
> **Prefixes:** BE = Backend · FE = Frontend · DB = Database/Migration · SCRAPE = Web Scraping

---

## CONTEXT — Why This File Exists

The dashboard shows "Technical models are not trained for this symbol" for AAPL and every
other ticker. The ML pipeline (ml_pipeline.py, technical_service.py, technical_training.py)
is fully implemented and correct. The root problems are:

1. No OHLCV data has been seeded into the DB for most symbols
2. No models have been trained (model_registry.jsonl is empty / missing symbols)
3. There is no UI trigger to run seeding or training at scale

This file defines the full plan to fix all of that, plus the news storage strategy
and the prioritised external data source list (scraping NOT yet implemented).

---

## ARCHITECTURE DECISIONS (Final — Confirmed)

### Ticker Universe
- **Scope:** Top 1000 by trading volume on Trade Republic DE — stocks + ETFs + crypto
- **Source file:** `backend/data/tickers_predefined.json`
- **Note:** No split by class — pure popularity ranking from TR DE
- **Fallback:** Any ticker yfinance cannot resolve → skip + log as 'yf_invalid'

### Bulk Job Failure Handling
- **Insufficient data (< 200 bars):** Skip silently, mark `status = 'skipped'`, `reason = 'insufficient_data'`
- **yfinance error / network fail:** Mark `status = 'failed'`, `reason = <error message>`
- **Visibility:** Both shown in Settings page failed/skipped list with reason

### News Sentiment Storage
- **Retention:** 1 year of headlines + sentiment scores + URLs
- **Fields stored:** symbol, date, headline, URL, source, sentiment_score, sentiment_label
- **URL is required:** enables 1-click article inspection + DB audit trail
- **NOT stored:** full article body
- **TTL job:** Weekly cron — delete records older than 365 days
- **Re-fetch logic:** Only call Finnhub if ticker+date window missing OR last_fetched > 24h

### External Scraping
- **Phase 6 below = PLANNING ONLY — do not implement yet**
- Full prioritised list with rationale is documented for future sprints

---

## PHASE 1 — Fix "No ML Prediction" Display + Single-Ticker Train Button
> Goal: AAPL dashboard shows real ML predictions within 1 session of work.
> Minimum changes to make the existing ML pipeline actually usable from the UI.

### 1.1 BE — Registry status endpoint
- [ ] 🔴 `BE` Add `GET /api/v1/technical/registry-status`
  - Returns: `{ total_symbols: N, symbols: [{symbol, timeframes_trained, last_trained_at, quality_gate}] }`
  - Reads directly from `model_registry.jsonl` via `JsonlFileModelRegistry`
  - **File:** `backend/app/api/v1/endpoints/technical.py`

### 1.2 BE — Per-symbol training status endpoint
- [ ] 🔴 `BE` Add `GET /api/v1/technical/train-status/{symbol}`
  - Returns: `{ symbol, status: "trained"|"training"|"not_started"|"failed", timeframes, last_trained_at, model_metrics }`
  - Checks `model_registry.jsonl` + `.joblib` file existence in `data/models/`
  - **File:** `backend/app/api/v1/endpoints/technical.py`

### 1.3 FE — Designed "Not Trained" empty state + Train Now button
- [ ] 🔴 `FE` Replace raw error text with a proper empty state on the ticker dashboard:
  ```
  [🧠 icon]
  No ML prediction yet for AAPL
  Technical consensus requires a trained model.
  [▶ Train Now]  →  POST /api/v1/technical/train/{symbol}
  ```
  - Poll `GET /api/v1/technical/train-status/{symbol}` every 5s while status = "training"
  - Show animated progress indicator during training
  - Auto-refresh technical consensus when training completes
  - **File:** wherever "Technical models are not trained" currently appears (dashboard page or TimeframeGrid)

### 1.4 FE — Training progress indicator
- [ ] 🟠 `FE` While training is in progress for the active ticker:
  - Show "Training ML models… (30–120 seconds)" with animated progress bar
  - Timeframe checklist: `1h ⟳  4h ⟳  1d ✓  1wk ⟳  1mo ⟳`
  - Disable "Train Now" button while running
  - On completion: toast "Training complete — Sharpe: 1.42, Acc: 57%"

---

## PHASE 2 — Predefined Ticker List Infrastructure
> Define and store the 1000-ticker TR DE universe used by all bulk operations.

### 2.1 DB — tickers_universe table
- [ ] 🟠 `DB` Alembic migration:
  ```sql
  CREATE TABLE tickers_universe (
    id           SERIAL PRIMARY KEY,
    symbol       VARCHAR(20) NOT NULL UNIQUE,
    name         VARCHAR(200),
    asset_class  VARCHAR(20),           -- 'stock', 'etf', 'crypto'
    exchange     VARCHAR(20),
    tr_rank      INTEGER,               -- popularity rank on Trade Republic DE
    is_active    BOOLEAN DEFAULT TRUE,
    yf_valid     BOOLEAN DEFAULT NULL,  -- NULL = not yet validated
    added_at     TIMESTAMP DEFAULT NOW()
  );
  ```
  - **File:** `backend/alembic/versions/xxxx_add_tickers_universe.py`

### 2.2 BE — tickers_predefined.json (top 1000 TR DE)
- [ ] 🟠 `BE` Create `backend/data/tickers_predefined.json`
  - Top 1000 by trading volume on Trade Republic Deutschland
  - Mix of stocks + ETFs + crypto in one flat list, each with metadata
  - Structure:
  ```json
  {
    "meta": {
      "total": 1000,
      "last_updated": "2026-03-20",
      "source": "Trade Republic DE top volume",
      "notes": "Symbols use yfinance format (e.g. BTC-USD, SAP.DE, VWCE.AS)"
    },
    "tickers": [
      { "symbol": "AAPL",    "name": "Apple Inc.",          "class": "stock",  "tr_rank": 1  },
      { "symbol": "TSLA",    "name": "Tesla Inc.",          "class": "stock",  "tr_rank": 2  },
      { "symbol": "NVDA",    "name": "NVIDIA Corp.",        "class": "stock",  "tr_rank": 3  },
      { "symbol": "BTC-USD", "name": "Bitcoin USD",         "class": "crypto", "tr_rank": 4  },
      { "symbol": "ETH-USD", "name": "Ethereum USD",        "class": "crypto", "tr_rank": 5  },
      { "symbol": "VWCE.AS", "name": "Vanguard FTSE All-W", "class": "etf",    "tr_rank": 6  },
      ...
    ]
  }
  ```
  - **This is the single source of truth for all bulk jobs.**

### 2.3 BE — Ticker universe seeder script
- [ ] 🟠 `BE` Create `backend/scripts/seed_ticker_universe.py`
  - Reads `tickers_predefined.json`
  - Upserts all tickers into `tickers_universe`
  - Validates each via `yf.Ticker(sym).fast_info` → sets `yf_valid`
  - Prints summary: N valid / N invalid
  - **Command:** `python scripts/seed_ticker_universe.py`

### 2.4 BE — Admin ticker universe endpoint
- [ ] 🟡 `BE` `GET /api/v1/admin/tickers-universe`
  - Paginated list with filters: `asset_class`, `yf_valid`, `is_active`
  - Used by Settings "View full list" link

---

## PHASE 3 — Bulk Seed Infrastructure (Run Button)
> Settings "Run" button seeds all missing OHLCV for 1000 tickers.
> Slowly-changing windows: append-only, never overwrites existing data.

### 3.1 DB — bulk_job_runs tracking table
- [ ] 🔴 `DB` Alembic migration:
  ```sql
  CREATE TABLE bulk_job_runs (
    id              SERIAL PRIMARY KEY,
    job_type        VARCHAR(20) NOT NULL,  -- 'seed', 'train', 'news'
    scope           VARCHAR(20) NOT NULL,  -- 'bulk', 'single'
    symbol          VARCHAR(20),
    status          VARCHAR(20) NOT NULL,  -- 'queued', 'running', 'done', 'failed', 'skipped'
    reason          TEXT,                  -- e.g. 'insufficient_data (87 rows)', 'yfinance timeout'
    rows_added      INTEGER DEFAULT 0,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX idx_bulk_job_symbol   ON bulk_job_runs(symbol);
  CREATE INDEX idx_bulk_job_status   ON bulk_job_runs(status);
  CREATE INDEX idx_bulk_job_type     ON bulk_job_runs(job_type, created_at DESC);
  ```

### 3.2 BE — Slowly-changing window seed service
- [ ] 🔴 `BE` Create `backend/app/services/bulk_seed_service.py`
  ```python
  async def seed_symbol_incremental(db, symbol: str) -> SeedResult:
      """
      Append-only, idempotent seed for one symbol.

      Algorithm:
        1. SELECT MAX(trade_date) FROM ohlcv_daily WHERE symbol = symbol
        2. If NULL (no data): fetch full 5y history via yfinance
        3. If exists: fetch only (last_date + 1 day) → today
        4. Upsert — never touches existing rows
        5. Repeat same logic for ohlcv_intraday (1h): check MAX(bar_time)
        6. If total rows < 200: mark as 'skipped', reason = 'insufficient_data (N rows)'
        7. Log result to bulk_job_runs table
      """
  ```
  - Returns `SeedResult(symbol, rows_added_daily, rows_added_intraday, status, reason)`
  - Gracefully handles: network errors, delisted tickers, empty responses

### 3.3 BE — Bulk seed orchestrator endpoint
- [ ] 🔴 `BE` `POST /api/v1/admin/bulk/run-seed`
  Request: `{ "scope": "missing_only" | "all", "asset_classes": [...] optional }`
  - Fetches all `yf_valid=TRUE` tickers from `tickers_universe`
  - Processes in batches of 10 concurrently (asyncio.gather)
  - 1-second sleep between batches (yfinance courtesy rate limit)
  - Returns immediately: `{ job_id, total_tickers, message: "Seed started in background" }`
  - **New file:** `backend/app/api/v1/endpoints/admin_bulk.py`

### 3.4 BE — Bulk seed status endpoint
- [ ] 🔴 `BE` `GET /api/v1/admin/bulk/seed-status`
  Returns:
  ```json
  {
    "total": 891,
    "done": 342,
    "failed": 8,
    "skipped": 14,
    "running": true,
    "pct_complete": 40.9,
    "eta_seconds": 320,
    "recent": [
      { "symbol": "AAPL", "status": "done", "rows_added": 1842 },
      { "symbol": "MSTR", "status": "skipped", "reason": "insufficient_data (87 rows)" }
    ]
  }
  ```

### 3.5 BE — Single-ticker seed endpoint
- [ ] 🟠 `BE` `POST /api/v1/admin/seed/{symbol}`
  - Runs `seed_symbol_incremental` for one symbol in background
  - Status via `GET /api/v1/admin/seed-status/{symbol}`

---

## PHASE 4 — Bulk Train Infrastructure (Train Button)
> After seeding, "Train All Models" trains ML for all seeded tickers.
> Separate Train buttons also on each ticker page.

### 4.1 BE — Bulk train orchestrator endpoint
- [ ] 🔴 `BE` `POST /api/v1/admin/bulk/run-train`
  Request: `{ "scope": "untrained_only" | "retrain_all", "symbols": [...] optional }`
  - Only processes tickers with ≥ 200 OHLCV rows
  - Sequential (ML training is CPU-bound)
  - Calls existing `run_training_pipeline()` per symbol+timeframe
  - Results logged to `bulk_job_runs` (job_type='train')
  - Returns immediately with job metadata

### 4.2 BE — Bulk train status endpoint
- [ ] 🔴 `BE` `GET /api/v1/admin/bulk/train-status`
  Returns:
  ```json
  {
    "total": 847,
    "done": 128,
    "failed": 5,
    "running": true,
    "current_symbol": "MSFT",
    "current_timeframe": "1d",
    "pct_complete": 15.1,
    "recent": [
      { "symbol": "AAPL", "model": "xgboost", "sharpe": 0.91, "accuracy": 0.57, "quality_gate": true }
    ]
  }
  ```

### 4.3 BE — Improve existing single-ticker train endpoint
- [ ] 🟠 `BE` Improve `POST /api/v1/technical/train/{symbol}` (existing in `technical.py`)
  - Log progress to `bulk_job_runs` as each timeframe completes
  - Return richer response: `{ symbol, timeframes_queued, estimated_seconds }`
  - Support `?force=true` to retrain even if already trained

### 4.4 FE — Settings page: "Data Pipeline" section (NEW)
- [ ] 🔴 `FE` Add **DataPipelineSection** component to `frontend/app/settings/page.tsx`
  Insert as a new `SectionCard` after "API Keys" section. Admin-only (check `user.is_admin`).

  **Visual design:**
  ```
  ┌─ DATA PIPELINE ─────────────────────────────────────────────────────────┐
  │                                                                           │
  │  TICKER UNIVERSE                                                          │
  │  1,000 tickers (Top TR DE by volume)                                     │
  │  [View full list →]                                                       │
  │                                                                           │
  │  ─────────────────────────────────────────────────────────────────────   │
  │                                                                           │
  │  OHLCV DATA SEEDING               Last run: 2026-03-19 14:32             │
  │  847/1000 tickers seeded · 8 failed · 14 skipped (insufficient data)     │
  │  ████████████████████░░░░ 84.7%                                          │
  │  [▶ Seed Missing]  [▶ Seed All]                                          │
  │  ▼ 8 failed (expandable)                                                 │
  │    XETRA.DE — yfinance returned no data                                  │
  │  ▼ 14 skipped                                                            │
  │    MSTR — insufficient_data (87 rows / 200 required)                     │
  │                                                                           │
  │  ─────────────────────────────────────────────────────────────────────   │
  │                                                                           │
  │  ML MODEL TRAINING                Last run: 2026-03-18 09:15             │
  │  423/847 seeded tickers trained · Avg Sharpe: 0.82 · Gate pass: 71%      │
  │  ██████████░░░░░░░░░░░░░░ 49.9%                                          │
  │  [▶ Train Untrained]  [▶ Retrain All]                                    │
  │                                                                           │
  │  ─────────────────────────────────────────────────────────────────────   │
  │                                                                           │
  │  NEWS SENTIMENT                   Last run: 2026-03-20 06:00             │
  │  2.4M articles · Oldest: 2025-03-20 · ~18GB estimated                   │
  │  [▶ Refresh News — 7 days]  [▶ Backfill — 1 year]                       │
  │                                                                           │
  └─────────────────────────────────────────────────────────────────────────┘
  ```

  Stats come from `GET /api/v1/admin/bulk/pipeline-overview` (Phase 7).
  Live progress polls seed-status / train-status every 3 seconds while active.

### 4.5 FE — Ticker page: Run + Train control row
- [ ] 🔴 `FE` In the Technical Consensus card on each ticker page, add a small status/control row.

  **State A — No data:**
  ```
  ✗ No data for AAPL  [↓ Fetch Data]
  ```

  **State B — Data seeded, no model:**
  ```
  ✓ 1,842 bars ready  [▶ Train Models]
  ```

  **State C — Trained:**
  ```
  ✓ Trained · 5 timeframes · Sharpe 0.91 · 2026-03-19  [↻ Retrain]
  ```

  States from `GET /api/v1/technical/train-status/{symbol}`.

---

## PHASE 5 — News Sentiment Storage (1 Year, Headlines + Scores + URLs)
> Store 1 year of news headlines, sentiment scores, and clickable URLs.
> Cache-first: avoid re-fetching what's already in DB.

### 5.1 DB — Extend news_articles table
- [ ] 🟠 `DB` Alembic migration — extend existing `news_articles` (in `models/sentiment.py`):
  ```sql
  ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS url              TEXT;
  ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS sentiment_label  VARCHAR(10);  -- 'bullish','bearish','neutral'
  ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS finbert_score    FLOAT;        -- raw FinBERT confidence
  ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS last_fetched_at  TIMESTAMP;
  ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS fetch_source     VARCHAR(20);  -- 'finnhub','scraped'
  ```
  - Add unique constraint: `(symbol, title, published_at)` to prevent duplicates
  - Add index: `(symbol, published_at DESC)` for fast per-ticker lookups
  - `url` field is NOT NULL when inserted from Finnhub (Finnhub always provides article URL)

### 5.2 BE — Cache-first news fetcher
- [ ] 🟠 `BE` Rewrite `fetch_recent_news()` in `news_data.py` to be DB-first:
  ```python
  async def fetch_recent_news_smart(db, symbol: str, days_back: int = 7):
      """
      1. SELECT * FROM news_articles WHERE symbol=symbol
            AND published_at >= NOW() - interval
            AND last_fetched_at >= NOW() - 24h
      2. If >= 5 rows found: return from DB (zero Finnhub calls)
      3. If cache miss: call Finnhub, run FinBERT, store with url + last_fetched_at
      4. Return result
      """
  ```
  - **File:** `backend/app/services/news_data.py`
  - URL is stored on every insert — enables 1-click article open from frontend

### 5.3 BE — FinBERT sentiment scorer
- [ ] 🟠 `BE` Create `backend/app/services/sentiment_scorer.py`
  - Model: `ProsusAI/finbert` via `transformers`
  - Input: headline string or list (batch up to 64)
  - Output: `{ label: "positive"|"negative"|"neutral", score: float }`
  - Singleton: load once, reuse across all calls
  - Fallback: keyword scoring if model unavailable
  - Maps to `sentiment_label`: positive→bullish, negative→bearish, neutral→neutral

### 5.4 BE — News bulk seed endpoint
- [ ] 🟡 `BE` `POST /api/v1/admin/bulk/run-news-seed`
  - Fetches + scores news for all active tickers
  - Default lookback: 7 days. Max: 365 days (1 year)
  - Respects Finnhub free tier: ≤ 60 calls/min
  - Progress: `GET /api/v1/admin/bulk/news-status`

### 5.5 BE — Weekly TTL cleanup cron
- [ ] 🟡 `BE` Add to `scheduler.py`:
  ```python
  @scheduler.scheduled_job("cron", day_of_week="sun", hour=2)
  async def cleanup_old_news():
      cutoff = datetime.utcnow() - timedelta(days=365)
      await db.execute(delete(NewsArticle).where(NewsArticle.published_at < cutoff))
  ```

### 5.6 BE — Daily news refresh cron
- [ ] 🟡 `BE` Add to scheduler: runs at 06:00 UTC every weekday
  - Fetches last 2 days for all active tickers
  - Skips tickers where `last_fetched_at >= NOW() - 24h`

### 5.7 FE — Clickable URL on news articles
- [ ] 🟠 `FE` In `ArticleList.tsx` (or wherever articles are rendered):
  - Each article card renders `url` field as a clickable link: `[Read article →]`
  - Opens in new tab (`target="_blank" rel="noopener noreferrer"`)
  - If `url` is null/empty: show plain title only (no broken link)
  - This enables 1-click inspection of any stored article

---

## PHASE 6 — External Data Sources (PLANNING ONLY — DO NOT IMPLEMENT YET)
> Full prioritised list for future sprints. Ordered by signal quality + implementation cost.

---

### TIER 1 — High signal, low cost (implement first when ready)

**1. CNN Fear & Greed Index**
- URL: `https://production.dataviz.cnn.io/index/fearandgreed/graphdata`
- Data: single 0-100 market mood index
- Signal: market-wide greed/fear — powerful regime indicator
- Update: every 1 hour
- Cost: free, no API key, simple JSON endpoint
- ML use: `fear_greed_norm` feature in all tickers

**2. Crypto Fear & Greed Index (alternative.me)**
- URL: `https://api.alternative.me/fng/`
- Data: 0-100 crypto-specific sentiment
- Signal: crypto market mood — especially useful for BTC/ETH
- Update: every 1 hour
- Cost: free, no API key
- ML use: `crypto_fear_greed_norm` feature (crypto tickers only)

**3. Google Trends (pytrends)**
- Library: `pytrends` (pip install pytrends)
- Data: relative search interest 0-100 for any keyword/ticker
- Signal: retail attention spike often precedes price move
- Update: weekly resolution, fetch daily
- Cost: free (unofficial Google API), rate-limited
- ML use: `google_trends_norm` feature
- Variant: `geo='DE'` for Trade Republic DE stocks

**4. Reddit Sentiment (PRAW)**
- Subreddits: r/wallstreetbets, r/investing, r/stocks, r/de (German), r/aktien
- Data: mention count + post sentiment per ticker per 24h
- Signal: retail FOMO/panic — WSB particularly predictive for momentum
- Update: every 6 hours
- Cost: free, PRAW library, Reddit API key needed
- ML use: `reddit_mentions_norm`, `reddit_sentiment_norm`
- Already have: `reddit_service.py` exists — extend it

**5. Wikipedia Pageviews**
- URL: `https://wikistats.wmcloud.org/api/rest_v1/metrics/pageviews/per-article/...`
- Data: daily article view count for any company's Wikipedia page
- Signal: unusual traffic (z-score > 2) often precedes price moves
- Update: daily
- Cost: free, no API key
- ML use: `wikipedia_attention_zscore` feature

---

### TIER 2 — Medium signal, medium cost (2nd wave)

**6. German Financial News (finanzen.net)**
- URL: `https://www.finanzen.net/nachrichten/aktien/{symbol}`
- Data: German-language headlines for TR DE stocks
- Signal: German retail sentiment — directly relevant to TR DE user base
- Update: every 4 hours
- Cost: free (web scraping with BeautifulSoup), respect robots.txt
- Dependency: `beautifulsoup4`
- ML use: feed into FinBERT scorer, store in `news_articles` with `fetch_source='finanzen_net'`

**7. Handelsblatt**
- URL: `https://www.handelsblatt.com/suche?q={symbol}`
- Data: professional German financial journalism
- Signal: higher quality than retail news — institutional sentiment
- Update: every 6 hours
- Cost: free headlines (partial scraping), full article behind paywall
- Dependency: `beautifulsoup4`

**8. Seeking Alpha Headlines**
- URL: RSS feeds or unofficial API
- Data: analyst headlines, earnings previews, ratings changes
- Signal: professional sentiment, earnings expectations
- Update: daily
- Cost: free for headlines (scraping)
- Note: more US-focused, less relevant for TR DE stocks

**9. Finviz (US stocks)**
- URL: `https://finviz.com/quote.ashx?t={symbol}`
- Data: analyst ratings, target prices, recent news aggregated
- Signal: consensus analyst target vs current price = upside/downside
- Update: daily
- Cost: free (scraping), rate-limited
- ML use: `analyst_upside_pct` feature

**10. StockTwits (already have stocktwits_service.py)**
- Data: real-time trader messages, bull/bear sentiment
- Signal: retail momentum sentiment
- Update: every 2 hours
- Cost: free API (limited), already partially implemented
- Action: extend existing `stocktwits_service.py`

---

### TIER 3 — High signal, higher cost (3rd wave)

**11. SEC EDGAR (US stocks)**
- URL: `https://www.sec.gov/cgi-bin/browse-edgar`
- Data: 10-K, 10-Q filings, Form 4 insider transactions
- Signal: insider buying = bullish, large selling = bearish
- Update: daily check for new filings
- Cost: free, official API, no key needed
- Library: `edgar` or raw REST
- ML use: `insider_net_sentiment` feature

**12. OpenInsider.com**
- URL: `https://openinsider.com/screener?s={symbol}`
- Data: aggregated insider buy/sell transactions
- Signal: cluster buying by insiders = strong bullish signal
- Update: daily
- Cost: free (web scraping)
- ML use: `insider_cluster_buy_score` feature

**13. Earnings Call Transcripts**
- Source: Seeking Alpha, Motley Fool, or direct SEC filings
- Data: CEO/CFO tone, forward guidance language
- Signal: linguistic analysis of guidance (positive/negative tone)
- Update: quarterly (per earnings cycle)
- Cost: free partial (scraping), paid for full transcripts
- ML use: `earnings_tone_score` feature — powerful but complex to build

**14. ECB / Fed Press Releases**
- URL: `https://www.ecb.europa.eu/press/pr/` + `https://www.federalreserve.gov/newsevents/`
- Data: official monetary policy statements
- Signal: hawkish/dovish tone → rate expectations → market impact
- Update: per-meeting (8x/year for ECB, 8x/year for Fed)
- Cost: free, official sources
- ML use: `central_bank_tone_score` macro feature

**15. Bundesanzeiger (German companies)**
- URL: `https://www.bundesanzeiger.de`
- Data: German company filings, annual reports, ad-hoc announcements
- Signal: German regulatory disclosures — relevant for TR DE stocks
- Update: daily
- Cost: free (official German government portal)
- Note: German language, requires NLP in German

---

### TIER 4 — Niche / experimental (implement last)

**16. App Store Ratings (Apple + Google Play)**
- Data: consumer app ratings for tech/consumer companies
- Signal: product quality proxy — useful for Apple, Spotify, Meta etc.
- Cost: scraping required, fragile

**17. Glassdoor / LinkedIn Job Postings**
- Data: employee sentiment, hiring growth
- Signal: rapidly growing headcount = expansion; layoffs = contraction
- Cost: scraping required, anti-bot measures

**18. Satellite Data / Alternative Data Vendors**
- Data: parking lot traffic, shipping container counts, credit card flows
- Signal: real-world economic activity proxy
- Cost: typically paid APIs (e.g. Quandl, Bloomberg)

**19. Patent Filings (USPTO)**
- Data: new patent applications by company
- Signal: R&D activity proxy — relevant for tech/pharma
- Cost: free USPTO API

**20. Google Maps Reviews (retail companies)**
- Data: consumer sentiment for physical locations
- Signal: foot traffic proxy + consumer satisfaction
- Cost: scraping required

---

## PHASE 7 — Pipeline Overview Endpoint
> Powers the Stats section in the Settings Data Pipeline UI.

### 7.1 BE — Pipeline overview endpoint
- [ ] 🔴 `BE` `GET /api/v1/admin/bulk/pipeline-overview`
  ```json
  {
    "ticker_universe": {
      "total": 1000,
      "yf_valid": 891,
      "by_class": { "stock": 650, "etf": 250, "crypto": 100 }
    },
    "seeding": {
      "seeded": 847,
      "failed": 8,
      "skipped": 14,
      "missing": 122,
      "last_run_at": "2026-03-19T14:32:00",
      "failed_tickers": [{ "symbol": "XETRA.DE", "reason": "yfinance returned no data" }],
      "skipped_tickers": [{ "symbol": "MSTR", "reason": "insufficient_data (87 rows)" }]
    },
    "training": {
      "trained": 423,
      "failed": 5,
      "untrained": 419,
      "avg_sharpe": 0.82,
      "quality_gate_pct": 71.0,
      "last_run_at": "2026-03-18T09:15:00"
    },
    "news": {
      "total_articles": 2400000,
      "oldest_article": "2025-03-20",
      "last_fetch_at": "2026-03-20T06:00:00"
    },
    "active_jobs": {
      "seeding": false,
      "training": false,
      "news": false
    }
  }
  ```

---

## PHASE 8 — Per-Ticker Data Panel on Ticker Intelligence Page
> Each ticker page shows its own data / model status + action buttons.

### 8.1 BE — Ticker data status endpoint
- [ ] 🟠 `BE` `GET /api/v1/admin/ticker-status/{symbol}`
  ```json
  {
    "symbol": "AAPL",
    "ohlcv": {
      "daily_bars": 1842,
      "hourly_bars": 17230,
      "last_date": "2026-03-20",
      "first_date": "2021-03-20",
      "is_seeded": true
    },
    "training": {
      "status": "trained",
      "timeframes_trained": 5,
      "best_sharpe": 0.91,
      "best_model": "xgboost",
      "trained_at": "2026-03-18T10:00:00"
    },
    "news": {
      "article_count": 847,
      "oldest": "2025-03-20",
      "newest": "2026-03-20",
      "last_fetched_at": "2026-03-20T06:00:00"
    }
  }
  ```

### 8.2 FE — TickerDataPanel component
- [ ] 🔴 `FE` Create `frontend/components/TickerDataPanel.tsx`
  Collapsible panel below Technical Consensus card:

  ```
  ── DATA & MODELS  [▾ show] ─────────────────────────────────────────────

  OHLCV Data   ✓  1,842 daily · 17,230 hourly · Last: 2026-03-20   [↻ Refresh]
  ML Models    ✓  5 timeframes · Sharpe 0.91 (XGBoost/1d)           [↻ Retrain]
  News         ✓  847 articles · Last: 3h ago                       [↻ Refresh]
  ─────────────────────────────────────────────────────────────────────────
  ```

  Empty state:
  ```
  OHLCV Data   ✗  No data yet                                    [↓ Fetch Data]
  ML Models    —  Requires data first
  News         ✗  No news cached                                 [↓ Fetch News]
  ```

---

## SUMMARY: All New Files

### Backend — Create
```
backend/app/api/v1/endpoints/admin_bulk.py      # Bulk seed/train/news API + pipeline-overview
backend/app/services/bulk_seed_service.py        # Slowly-changing window seeder logic
backend/app/services/sentiment_scorer.py         # FinBERT singleton scorer
backend/data/tickers_predefined.json             # 1000 top TR DE tickers
backend/scripts/seed_ticker_universe.py          # Populate tickers_universe table
```

### Backend — Modify
```
backend/app/api/v1/endpoints/technical.py        # registry-status + train-status/{symbol}
backend/app/services/news_data.py                # Cache-first fetcher + URL storage
backend/app/services/scheduler.py                # TTL cleanup + daily news refresh
backend/app/main.py                              # Register admin_bulk router
backend/requirements.txt                         # Add: pytrends, beautifulsoup4 (future)
```

### Database — Alembic migrations
```
xxxx_add_tickers_universe.py
xxxx_add_bulk_job_runs.py
xxxx_extend_news_articles.py                     # Add url, sentiment_label, finbert_score, etc.
xxxx_add_external_signals.py                     # For Phase 6 when ready
```

### Frontend — Create
```
frontend/components/TickerDataPanel.tsx           # Per-ticker data/model status panel
```

### Frontend — Modify
```
frontend/app/settings/page.tsx                   # DataPipelineSection component
frontend/components/TimeframeGrid.tsx             # "Not trained" empty state + Train Now
frontend/lib/api.ts                              # All new endpoint calls
```

---

## SPRINT ORDER

```
Sprint 1 — Day 1–2:  Fix the visible gap on AAPL
  Phase 1 (all):   train-status endpoint + "Train Now" button
  Phase 2 (2.1–3): tickers_universe table + JSON file

Sprint 2 — Day 3–4:  Bulk seed pipeline
  Phase 3 (all):   bulk_job_runs + bulk_seed_service + seed endpoints

Sprint 3 — Day 5–6:  Settings Data Pipeline UI
  Phase 4 (4.1–4.3): bulk train endpoints
  Phase 7 (7.1):     pipeline-overview endpoint
  Phase 4 (4.4):     DataPipelineSection in settings page

Sprint 4 — Day 7–8:  Per-ticker controls + news
  Phase 4 (4.5):   ticker page Run/Train buttons
  Phase 8 (all):   ticker-status + TickerDataPanel
  Phase 5 (5.1–3): extend news table + cache-first fetcher + FinBERT

Sprint 5 — Day 9–10: News scheduling + URLs
  Phase 5 (5.4–6): bulk news seed + TTL cron + daily refresh
  Phase 5 (5.7):   clickable URLs on article cards

Sprint 6 — Future:   External scrapers (Phase 6 Tier 1 first)
  Start with: CNN Fear & Greed → Crypto Fear & Greed → Google Trends → Reddit
```

---

## OPEN QUESTIONS — ALL RESOLVED

| # | Question | Final Decision |
|---|---|---|
| 1 | Ticker list format? | Top 1000 TR DE by volume — stocks + ETFs + crypto, flat list |
| 2 | Failure handling? | Skip silently, mark 'insufficient_data' with reason in status |
| 3 | News retention? | 1 year, headlines + scores + URLs (~10-15 GB) |
| 4 | Scraping? | Planning only — Phase 6 list documented, Tier 1 first when ready |
| 5 | Store full bodies? | No — headline + URL + sentiment score only |
| 6 | Slowly-changing window? | Append-only; fetch delta from MAX(date) to today |
| 7 | Train concurrency? | Sequential (CPU-bound) |
| 8 | Seed concurrency? | 10 parallel per batch, 1s sleep between batches |

---

*todos-v4.md — v4.1 updated 2026-03-20.*
*Covers: bulk ML pipeline · news storage (1yr + URLs) · 20-source external data priority list.*
*Companion files: todos-v3.md (app polish + security), todos.md (original UX backlog).*
