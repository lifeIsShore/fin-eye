# Yagmur Terminal — Institutional Grade Stock Intelligence

Yagmur Terminal is a full-stack financial intelligence platform combining **machine learning**, **macroeconomic analysis**, **NLP sentiment**, and **technical analysis** into a single unified score — the **Global Alignment Score (GAS)** — for any traded symbol (equities, crypto, FX, commodities).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [The Global Alignment Score (GAS)](#the-global-alignment-score-gas)
3. [Signal Grade System](#signal-grade-system)
4. [ML Decision Engine](#ml-decision-engine)
5. [Feature Reference](#feature-reference)
6. [Macro Intelligence Layer](#macro-intelligence-layer)
7. [Sentiment Intelligence Layer](#sentiment-intelligence-layer)
8. [Paper Trading Bot](#paper-trading-bot)
9. [Monte Carlo Simulation Engine](#monte-carlo-simulation-engine)
10. [Backtesting Engine](#backtesting-engine)
11. [Community Features](#community-features)
12. [Data Sources](#data-sources)
13. [API & Caching Architecture](#api--caching-architecture)
14. [Running Locally](#running-locally)
15. [Stack](#stack)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                     │
│   Dashboard · Macro · Bot · MC Simulator · Backtesting      │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST / SSE
┌─────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                            │
│                                                             │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │ ML Pipeline │ │ Macro Engine │ │  Sentiment Engine  │   │
│  │ XGBoost /   │ │ FRED + VIX + │ │  FinBERT + Reddit  │   │
│  │ LightGBM /  │ │ Yield Curve  │ │  StockTwits +      │   │
│  │ LogReg +    │ │              │ │  Google Trends +   │   │
│  │ Optuna tune │ │              │ │  Wikipedia Views   │   │
│  └──────┬──────┘ └──────┬───────┘ └─────────┬──────────┘   │
│         │               │                    │              │
│  ┌──────▼───────────────▼────────────────────▼──────────┐   │
│  │              GAS Pre-Compute Service                  │   │
│  │    Technical (40%) + Sentiment (30%) + Macro (30%)   │   │
│  │    → GAS score 0–100 + Signal Grade A+→F             │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                          │                                   │
│           ┌──────────────▼────────────┐                     │
│           │  Redis Cache (15 min TTL) │                     │
│           │  PostgreSQL  (durable)    │                     │
│           │  APScheduler (15+ jobs)   │                     │
│           └───────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## The Global Alignment Score (GAS)

The GAS is a **0–100 composite score** answering: *"How aligned is the macro, technical, and sentiment environment for this symbol right now?"*

### Score Composition

| Component | Weight | Source |
|-----------|--------|--------|
| Technical (ML) | **40%** | ML model inference on OHLCV + indicators |
| Sentiment | **30%** | FinBERT 30-day rolling average on news |
| Macro | **30%** | FRED macroeconomic indicators + VIX |

```
GAS = (technical × 0.40) + (sentiment × 0.30) + (macro × 0.30)
```

### GAS Weather Labels

| Score | Label |
|-------|-------|
| 75–100 | Strong Tailwind |
| 60–74 | Mild Support |
| 45–59 | Mixed Signals |
| 30–44 | Headwind |
| 0–29 | High Instability |

### Market Regime

| Technical Score | Regime |
|-----------------|--------|
| ≥ 60 | Risk-On |
| ≤ 40 | Risk-Off |
| 41–59 | Transitional |

---

## Signal Grade System

Every GAS snapshot is assigned a letter grade (**A+ → F**) that summarises investment decision quality. The grade is the primary filter for the trading bot, portfolio construction, and AI allocation.

### Grade Scoring (0–100 points)

| Component | Max Points | Description |
|-----------|-----------|-------------|
| GAS score | 40 | Maps GAS 30–100 → 0–40 pts |
| Component alignment | 30 | Do technical/sentiment/macro agree? |
| ML model confidence | 20 | Best timeframe Sharpe ratio |
| Signal conviction | 10 | Distance of GAS from neutral (50) |

### Grade Scale

| Grade | Score | Tradeable | Description |
|-------|-------|-----------|-------------|
| A+ | ≥ 88 | ✅ | Exceptional — all signals strongly aligned |
| A | ≥ 78 | ✅ | Strong — reliable for trade decisions |
| B | ≥ 65 | ✅ | Good — minor disagreements, normal sizing |
| C | ≥ 50 | ❌ | Mixed — monitor only |
| D | ≥ 35 | ❌ | Weak — avoid new positions |
| F | < 35 | ❌ | Disqualified — conflicting signals |

**Hard disqualifiers → F:** GAS < 30, or all components at 50 (no real data).

---

## ML Decision Engine

### Step 1 — Data Ingestion
OHLCV data fetched via Yahoo Finance. Supported timeframes: `1h`, `4h` (resampled from 1h), `1d`, `1wk`. Minimum 200 rows required per timeframe.

### Step 2 — Feature Engineering
See [Feature Reference](#feature-reference) for the full list.

### Step 3 — Target Variable
Binary classification: direction of 5-period forward return.
```python
target = 1 if close.shift(-5) / close - 1 > 0 else 0
```

### Step 4 — Model Competition (Walk-Forward)

| Model | Description |
|-------|-------------|
| **XGBoost** | Gradient-boosted trees. Primary workhorse. |
| **LightGBM** | Fast gradient boosting, handles large feature sets. |
| **Logistic Regression** | Linear baseline with StandardScaler + balanced class weights. |

**Split:** 80% train / 20% validation (time-series, no look-ahead).  
**Winner:** Highest annualised Sharpe Ratio on validation set.  
**Optuna:** Nightly hyperparameter tuning (when `ENABLE_HYPERTUNING=True`).

### Step 5 — Signal Generation
```json
{
  "timeframe": "1d",
  "direction": "Bullish",
  "signal_raw": 0.75,
  "confidence": 75.0,
  "validation_sharpe": 1.42,
  "model_used": "xgboost"
}
```

### Step 6 — Technical Consensus Score
Sharpe-weighted average across active timeframes, mapped to 0–100.

### Step 7 — Drift Detection
Hourly check: if live accuracy drops > `DRIFT_THRESHOLD_PP` (default 10pp) below validation accuracy, a `ModelDriftAlert` is created. Auto-retrain triggers when `AUTO_RETRAIN_ON_DRIFT=True`.

---

## Feature Reference

### Core ML Features (active model inputs)

| Feature | Description |
|---------|-------------|
| `ret_1` | 1-period return |
| `sma_cross_10_20` | (SMA10 / SMA20) − 1 |
| `sma_cross_20_50` | (SMA20 / SMA50) − 1 |
| `rsi_14` | RSI-14 (Wilder) |
| `macd`, `macd_hist` | MACD line + histogram |
| `bb_width`, `bb_pb` | Bollinger Band width + %B |
| `mom_10`, `mom_20` | 10/20-period momentum |

### Extended Features (daily DbFeatureBuilder)

| Feature | Source |
|---------|--------|
| `return_1d`, `return_5d`, `volatility_20d` | OHLCV |
| `news_sentiment_1d/7d/30d` | FinBERT sentiment DB |
| `news_source_diversity_30d` | NewsArticle DB |
| `macro_score`, `vix_level`, `yield_spread_10y_2y` | FRED |
| `earnings_days_until_norm`, `earnings_surprise_score_norm` | Earnings DB |
| `google_trends_norm`, `wikipedia_pageviews_zscore` | External signals |
| `reddit_mention_score`, `stocktwits_bull_ratio` | Social signals |
| `day_of_week`, `month`, `hour_of_day` | Calendar features |

---

## Macro Intelligence Layer

### Macro Environment Score (0–100)

Starts at 50 (neutral), adjusted by FRED indicators. Higher = better environment for equities.

Key adjustments: yield curve inversion (−20 pts deeply inverted), CPI > 6% (−15 pts), VIX > 40 (−15 pts), unemployment > 7% (−12 pts), NFP > 300k (+4 pts).

**Labels:** Supportive (≥70) · Neutral (40–69) · Stressed (<40)

### Macro Stress Index (0–100)
Inverse framing decomposed into: Yield Curve (0–25), VIX (0–20), Inflation (0–20), Labour (0–20), Fed Policy (0–15).

### Recession Risk Gauge (0–99%)
Rule-based Estrella/Mishkin-style model. Deeply inverted yield curve (+45 pp), NBER recession indicator → 95% directly.

### FRED Series Fetched
`FEDFUNDS`, `UNRATE`, `T10Y2Y`, `CPIAUCSL`, `DGS1MO`, `DGS2`, `DGS5`, `DGS10`, `DGS30`, `USREC`, `PAYEMS`, `INDPRO` + VIX via Yahoo Finance.

---

## Sentiment Intelligence Layer

### FinBERT
`ProsusAI/finbert` scores each news headline (POSITIVE/NEGATIVE/NEUTRAL → ±confidence). 30-day mention-weighted rolling average mapped to 0–100.

### Crypto Sentiment
Crypto Fear & Greed index (free public API) substituted for FinBERT on `-USD` symbols.

### Additional Signals
- **Google Trends** — weekly interest via pytrends, geo=DE, 90-day window
- **StockTwits** — bullish/bearish message ratio (public API, 15-min cache)
- **Reddit** — mention volume + sentiment via PRAW (every 6h)
- **Wikipedia pageviews** — 252-day z-score (daily)
- **Finanzen.net** — German-language news for `.DE` symbols

---

## Paper Trading Bot

A fully automated paper trading system (`/bot/paper`) that makes BUY/SELL/HOLD decisions every 15 minutes during market hours.

### Decision Matrix

| Condition | Action |
|-----------|--------|
| `halt_flag = True` | SKIP |
| Daily PnL < −`daily_loss_limit` | HALT (auto) |
| Grade D/F + open position | SELL (grade_drop) |
| Price < entry − 2×ATR | SELL (stop_loss) |
| Grade A+/A, no position, GAS ≥ 60 | BUY (Kelly-sized) |
| Open position, grade acceptable | HOLD |
| Grade below `min_grade` | SKIP |

### MC-CVaR Gate (Sprint 56)
Before every BUY, runs a 5,000-path GBM Monte Carlo simulation (30 days ahead) on last 126 days of OHLCV. If predicted portfolio-level CVaR-95 exceeds `daily_loss_limit`, the trade is skipped.

### Position Sizing
Half-Kelly based on GAS score:
```
edge = (gas_score − 50) / 50
half_kelly = edge × 0.5
size = min(half_kelly, max_position_pct) × portfolio_value
```

### Kill Switch
`POST /api/v1/bot/halt` — immediately sets `halt_flag=True`. Optional `close_all=true` closes all open positions at current price.

---

## Monte Carlo Simulation Engine

Located at `/portfolio/montecarlo`. Supports:

- **Single asset** — GBM or Merton Jump Diffusion
- **Portfolio** — Cholesky-correlated multi-asset, monthly contributions/withdrawals, retirement success rate
- **Scenario comparison** — overlay up to 3 runs on one chart
- **Vol auto-fill** — `GET /api/v1/montecarlo/vol-estimate?symbol=AAPL` reads historical OHLCV to populate σ and μ

**OOM guard:** max 50,000 paths per asset request, max 50 assets per portfolio request.

---

## Backtesting Engine

Validate strategies on up to 5 years of historical OHLCV data.

**Supported strategy:** Momentum (SMA crossover + RSI filter).

**Metrics:** Total return, annualised return, max drawdown, Sharpe, Sortino, win rate, profit factor, recovery factor.

**Overfitting warning:** surfaced if in-sample Sharpe > 1.2.

**Forward projection:** After any backtest run, "Simulate 3 Years" button launches MC fan chart from the final equity point.

---

## Community Features

### Discussion Threads
Per-ticker comment threads at the bottom of the dashboard. Rate-limited to 10 comments/hour. Usernames anonymised (`joh***`). Up/down reactions with toggle. Soft delete (author or admin).

### Weekly Bull vs Bear Poll
Every Monday, a new SPY poll opens (`bullish / bearish / neutral`). Results visible as live percentage breakdown after voting. Auto-created by scheduler at 00:01 UTC Monday.

---

## Data Sources

| Source | Data | Method |
|--------|------|--------|
| Yahoo Finance (`yfinance`) | OHLCV, VIX | Python library |
| FRED | Macro indicators | REST API (key required) |
| Finnhub | News per ticker | REST API (key required) |
| Resend | Transactional email | REST API (key required) |
| Stripe | Billing / subscriptions | REST API (key required) |
| Cloudflare R2 | ML model artifact storage | S3-compatible (boto3) |
| StockTwits | Social sentiment | Public REST API |
| pytrends | Google Trends | Unofficial Google API |
| CNN Fear & Greed | Market sentiment | Public scraper |
| Crypto Fear & Greed | Crypto sentiment | Public API |
| PRAW (Reddit) | r/stocks, r/investing | OAuth API |
| Wikipedia | Pageview statistics | Public REST API |
| OpenInsider | US insider transactions | Public scraper |
| Finanzen.net | German-language news | Public scraper |
| ProsusAI/finbert | Sentiment model | HuggingFace Hub |
| Sentry | Error monitoring | SDK (optional) |
| PostHog | Product analytics | SDK (optional) |

---

## API & Caching Architecture

### Three-Tier Read Path for GAS

1. **Redis (< 1ms):** 15-minute TTL, key `gas:snapshot:{SYMBOL}`
2. **PostgreSQL (< 5ms):** Durable snapshot table; re-warms Redis on hit
3. **Live compute (2–3s):** Full ML + sentiment + macro on cold cache miss

### Scheduled Jobs (APScheduler, PostgreSQL-backed)

| Job | Schedule |
|-----|----------|
| GAS pre-compute | Every 15 min, Mon–Fri 13–21 UTC |
| Paper trading bot | Every 15 min (offset +2 min after GAS) |
| OHLCV daily fetch | Mon–Fri 18:05 UTC |
| OHLCV intraday fetch | Mon–Fri 13–21 UTC, hourly |
| Macro refresh | Daily 08:00 UTC |
| News fetch | Mon–Fri every 4h |
| Fear & Greed fetch | Every hour |
| Google Trends | Daily 08:15 UTC |
| Wikipedia pageviews | Daily 08:30 UTC |
| Reddit signals | Every 6h |
| StockTwits signals | Every 6h |
| Earnings ML signals | Daily 07:00 UTC |
| Model drift detection | Every hour at :50 |
| Outcome resolution | Every hour at :45 |
| Optuna tuning | Nightly 01:00 UTC (when enabled) |
| Churn early warning | Daily 09:00 UTC |
| Weekly poll create | Monday 00:01 UTC |
| DB backup | Daily 02:00 UTC |

### Model Persistence
`.joblib` files in `backend/data/models/` (gitignored). JSONL registry at `model_registry.jsonl`. Artifacts synced to Cloudflare R2 after every training run and restored on startup.

---

## Running Locally

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+

### Backend

```bash
cd backend
cp .env.example .env        # fill in required keys (see .env.example)
pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/api/v1/health`

### Frontend

```bash
cd frontend
cp .env.local.example .env.local    # set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

### Required `.env` Keys

| Key | Required | Description |
|-----|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL sync URL |
| `ASYNC_DATABASE_URL` | ✅ | PostgreSQL async URL (asyncpg) |
| `REDIS_URL` | ✅ | Redis connection string |
| `REDIS_PASSWORD` | ✅ | Redis auth password |
| `JWT_SECRET` | ✅ | Random 32-byte hex string |
| `FINNHUB_API_KEY` | ✅ | News data |
| `FRED_API_KEY` | ✅ | Macro indicators |
| `RESEND_API_KEY` | ✅ | Transactional email |
| `STRIPE_SECRET_KEY` | ✅ | Billing |
| `ANTHROPIC_API_KEY` | recommended | AI explanations (LLM insights) |
| `R2_ACCOUNT_ID` etc. | recommended | ML artifact cloud storage |
| `SENTRY_DSN` | optional | Error monitoring |
| `NEXT_PUBLIC_POSTHOG_KEY` | optional | Product analytics |

### Training ML Models

Models must be trained per symbol before GAS can be computed:

```
POST /api/v1/technical/train?symbol=AAPL&timeframe=1d
POST /api/v1/technical/train?symbol=AAPL&timeframe=1h
```

Or train all symbols in the configured universe via the Admin panel.

### Running Tests

```bash
cd backend
pytest tests/ -v

# Run specific suites (Sprint 57)
pytest tests/api/test_bot_api.py tests/api/test_comments_api.py \
       tests/api/test_polls_api.py tests/api/test_montecarlo_api.py -v
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend framework | FastAPI (Python 3.10+) |
| ASGI server | Uvicorn |
| Database | PostgreSQL 14+ + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache | Redis 7 |
| ML models | XGBoost, LightGBM, scikit-learn |
| Hypertuning | Optuna |
| Explainability | SHAP |
| NLP / Sentiment | HuggingFace Transformers (FinBERT) |
| OHLCV data | yfinance |
| Macro data | fredapi |
| Email | Resend |
| Billing | Stripe |
| Storage | Cloudflare R2 (boto3 S3-compatible) |
| Error monitoring | Sentry |
| Analytics | PostHog |
| Background jobs | APScheduler (PostgreSQL jobstore) |
| Containerisation | Docker + Docker Compose |
| Frontend | Next.js 14 + Tailwind CSS |
| Testing | pytest + pytest-asyncio + httpx |
| CI | GitHub Actions (Lighthouse CI) |

---

## Security

- JWT access tokens (30 min) + refresh tokens (7 days) with JTI blacklisting on logout
- Email verification enforced on all sensitive endpoints (`get_current_active_verified_user`)
- TOTP two-factor authentication support
- Account lockout after 10 failed login attempts
- Rate limiting via slowapi (30 req/min anonymous, 120 auth, 300 API key)
- Security headers middleware (CSP, X-Frame-Options, HSTS)
- Production config assertions on startup (DEBUG=False, no wildcard CORS, real JWT_SECRET)
- Multi-stage Docker build, non-root container user

---

*Last updated: April 2026 — Fin-Eye v1.0*
