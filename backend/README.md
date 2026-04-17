# Yagmur Terminal Backend — Complete Technical Reference

> **Stack:** Python 3.10+ · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Redis · APScheduler
> **ASGI server:** Uvicorn

---

## Table of Contents

1. [What Fin-Eye Does](#1-what-fin-eye-does)
2. [Architecture Overview](#2-architecture-overview)
3. [The GAS Score — Global Alignment Score](#3-the-gas-score--global-alignment-score)
4. [ML Pipeline — How the Model Decides Movement](#4-ml-pipeline--how-the-model-decides-movement)
5. [Feature Set — What Is On and What Is Off](#5-feature-set--what-is-on-and-what-is-off)
6. [Macro Scoring Engine](#6-macro-scoring-engine)
7. [Sentiment Pipeline](#7-sentiment-pipeline)
8. [Technical Consensus](#8-technical-consensus)
9. [Data Feeds & External Sources](#9-data-feeds--external-sources)
10. [Caching & Persistence](#10-caching--persistence)
11. [Scheduler & Pre-Computation](#11-scheduler--pre-computation)
12. [Running Locally](#12-running-locally)
13. [Project Structure](#13-project-structure)

---

## 1. What Yagmur Terminal Does

Yagmur Terminal is a stock analysis platform that combines **machine learning-based technical analysis**, **macro-economic scoring**, and **NLP-driven sentiment analysis** into a single composite score (GAS) for any given stock ticker. The goal is to answer one question for the user: *"Is the macro + technical + sentiment environment aligned for this stock right now?"*

---

## 2. Architecture Overview

```
External Data Sources
 ├── Yahoo Finance     (OHLCV price data)
 ├── FRED API          (macro indicators: VIX, CPI, Fed rate, yield curve, etc.)
 ├── Finnhub / News    (news articles for NLP sentiment)
 ├── Reddit / StockTwits (social sentiment)
 └── SEC / Insider data, Options flow, Short interest

FastAPI Backend
 ├── Ingest & Store    (PostgreSQL via SQLAlchemy async)
 ├── Feature Builder   (assembles ML-ready feature matrix per ticker + timeframe)
 ├── ML Pipeline       (trains XGBoost / Logistic Regression / Prophet — picks winner by Sharpe)
 ├── Technical Service (runs inference on trained models → 0–100 technical score)
 ├── Macro Scoring     (rule-based scoring of FRED indicators → 0–100 macro score)
 ├── Sentiment Service (FinBERT 30-day rolling score → 0–100 sentiment score)
 └── GAS Pre-Compute   (combines three scores with weights → final GAS snapshot)

Redis Cache          (15-min TTL per ticker, fast-path reads)
PostgreSQL DB        (durable snapshot storage, fallback reads)
APScheduler          (refreshes GAS every 15 min during market hours)
```

---

## 3. The GAS Score — Global Alignment Score

The **GAS (Global Alignment Score)** is a single 0–100 composite score combining three independently computed sub-scores.

### Weights

| Component | Weight | Source |
|-----------|--------|--------|
| Technical Score | **40%** | ML model inference (XGBoost / Logistic / Prophet) |
| Sentiment Score | **30%** | FinBERT 30-day rolling average on news articles |
| Macro Score | **30%** | Rule-based FRED indicator scoring |

**Formula:**
```
GAS = (technical × 0.40) + (sentiment × 0.30) + (macro × 0.30)
GAS is clamped to [0, 100]
```

### GAS Weather Labels

| Score Range | Label |
|-------------|-------|
| 80 – 100 | Strong Tailwind |
| 60 – 79 | Mild Support |
| 40 – 59 | Mixed Signals |
| 20 – 39 | Headwind |
| 0 – 19 | High Instability |

### Regime Label (from Technical Score only)

| Technical Score | Regime |
|----------------|--------|
| ≥ 60 | Risk-On |
| ≤ 40 | Risk-Off |
| 41 – 59 | Transitional |

### Read Path (Three-Tier Cache)

1. **Redis** — checked first (< 1ms). Key format: `gas:snapshot:<SYMBOL>`. TTL: 15 minutes.
2. **DB snapshot** — if Redis is cold, the latest persisted snapshot is loaded and Redis is re-warmed.
3. **Live compute** — if no snapshot exists at all (cold start), the full pipeline runs on demand.

---

## 4. ML Pipeline — How the Model Decides Movement

The ML pipeline is responsible for predicting the **5-period forward return direction** (up = 1, down = 0) for a given ticker and timeframe.

### Training Flow

```
OHLCV data (≥200 rows required)
    ↓
engineer_features()          ← computes all technical indicators
    ↓
80/20 time-series split      ← training on first 80%, validation on last 20%
    ↓
Train 3 competing models:
  ├── XGBoostClassifier       (n_estimators=100, max_depth=3, lr=0.05)
  ├── LogisticRegression      (class_weight=balanced, StandardScaler)
  └── Prophet                 (price trend slope → binary signal)
    ↓
Walk-forward evaluation on validation set
  → Sharpe Ratio computed per model
  → Accuracy computed per model
    ↓
Winner = model with highest Sharpe Ratio
    ↓
Saved to disk as <SYMBOL>_<TIMEFRAME>_winner.joblib
Metadata logged to model_registry.jsonl
```

### Why Sharpe Ratio, Not Accuracy?

Accuracy measures how often the model is directionally correct. Sharpe Ratio measures the **risk-adjusted return** of actually trading the model's signals. A model that is 60% accurate but wins big and loses small beats a 70% accurate model that wins small and loses big. Sharpe is the correct optimisation target for a trading signal.

### Sharpe Calculation

```python
strategy_returns = where(prediction == 1, actual_5period_return, 0)
sharpe = (mean(strategy_returns) / std(strategy_returns)) × sqrt(252)
```

### Model Inference (Prediction)

At inference time:
1. Fetch recent OHLCV data (up to 730 days for intraday).
2. Run `engineer_features()` on this data.
3. Load the saved winner model from disk.
4. Call `model.predict_proba(latest_row)` → get probability of upward move (`prob_up`).
5. Direction = Bullish if `prob_up > 0.5`, else Bearish.
6. Confidence = `max(prob_up, 1 - prob_up) × 100`.
7. Raw signal = `±1 × (confidence / 100)` in range [-1, +1].

### Multi-Timeframe Consensus

Currently active timeframes: **1h and 4h** (1d/1wk/1mo models are prepared in the codebase but not yet trained — see `technical_service.py: TIMEFRAMES`).

Each timeframe produces an independent signal. These are aggregated into a single consensus:

```
weighted_signal = Σ (signal_raw × max(validation_sharpe, 0.1)) / Σ weights
consensus_score_0_100 = (weighted_signal + 1) / 2 × 100
```

Higher Sharpe timeframe models carry more weight. Models with negative Sharpe are floored at 0.1 weight to prevent inversion.

---

## 5. Feature Set — What Is On and What Is Off

### Features Used in ML Training & Inference (ACTIVE)

These 10 features are fed directly into the XGBoost and Logistic Regression models:

| Feature | Description | Status |
|---------|-------------|--------|
| `ret_1` | 1-period return (price pct change) | ✅ Active |
| `sma_cross_10_20` | SMA(10)/SMA(20) - 1 (crossover ratio) | ✅ Active |
| `sma_cross_20_50` | SMA(20)/SMA(50) - 1 (trend bias) | ✅ Active |
| `rsi_14` | RSI with 14-period window | ✅ Active |
| `macd` | MACD line (EMA12 - EMA26) | ✅ Active |
| `macd_hist` | MACD histogram (MACD - signal) | ✅ Active |
| `bb_width` | Bollinger Band width (volatility proxy) | ✅ Active |
| `bb_pb` | Bollinger Band %B (price position in band) | ✅ Active |
| `mom_10` | 10-period momentum (pct change) | ✅ Active |
| `mom_20` | 20-period momentum (pct change) | ✅ Active |

### Features Computed but NOT Used in ML Models (INTERMEDIATE)

These are computed by `engineer_features()` or `DbFeatureBuilder` but serve as intermediate calculations or are only used by the scoring engines, not passed directly to the classifiers:

| Feature | Description | Status |
|---------|-------------|--------|
| `sma_10`, `sma_20`, `sma_50` | Raw SMA values (used to compute crossover ratios above) | ⚙️ Intermediate |
| `target_ret_5` | 5-period forward return (used to compute the training label only) | ⚙️ Label-only |
| `target` | Binary label (1 = positive 5-period return ahead) | ⚙️ Label-only |
| `close_raw` | Raw close price (required for Prophet wrapper only) | ⚙️ Prophet-only |
| `macd_signal` | MACD signal line (intermediate; `macd_hist` is what the model sees) | ⚙️ Intermediate |
| `std_20` | 20-period standard deviation (used to compute Bollinger bands) | ⚙️ Intermediate |
| `bb_upper`, `bb_lower` | Raw Bollinger band levels | ⚙️ Intermediate |

### Features in the Full Feature Matrix (DbFeatureBuilder — Daily Timeframe)

The `DbFeatureBuilder` assembles an extended feature matrix that includes macro and sentiment context. These are available for future model versions but the current ML classifier only trains on the 10 core technical features above:

| Feature | Description | Active in ML? |
|---------|-------------|---------------|
| `return_1d` | 1-day return | ❌ Not in current classifier |
| `return_5d` | 5-day return | ❌ Not in current classifier |
| `volatility_20d` | 20-day rolling return std | ❌ Not in current classifier |
| `rsi_14` | RSI-14 | ✅ Included |
| `macd`, `macd_signal`, `macd_hist` | MACD indicators | ✅ (hist + macd included) |
| `bb_upper`, `bb_middle`, `bb_lower` | Bollinger bands | ⚙️ Intermediate |
| `news_sentiment_1d` | 1-day news sentiment rolling average | ❌ Not in current classifier |
| `news_sentiment_7d` | 7-day news sentiment rolling average | ❌ Not in current classifier |
| `news_sentiment_30d` | 30-day news sentiment rolling average | ❌ Not in current classifier |
| `news_source_diversity_30d` | Distinct news sources in last 30 days | ❌ Not in current classifier |
| `macro_score` | Computed macro score (0–100) | ❌ Not in current classifier |
| `vix_level` | VIX from FRED | ❌ Not in current classifier |
| `yield_spread_10y_2y` | 10Y–2Y Treasury spread | ❌ Not in current classifier |
| `day_of_week` | Calendar day (0=Mon) | ❌ Not in current classifier |
| `month` | Calendar month | ❌ Not in current classifier |
| `hour_of_day` | Hour of day (intraday) | ❌ Not in current classifier |

> **Note:** The macro and sentiment features are computed and stored alongside price features in preparation for a future multi-input model version. They currently feed the GAS score as independent components rather than as ML input features.

---

## 6. Macro Scoring Engine

**File:** `app/services/macro_scoring.py`

The macro scoring engine produces four outputs:

### 6.1 Macro Score (0–100)

Starts at **50 (neutral)** and adjusts based on each indicator. Missing indicators are skipped gracefully.

| Indicator | Signal | Adjustment |
|-----------|--------|-----------|
| Yield spread 10Y–2Y | Deeply inverted (< -0.5%) | **-20** |
| Yield spread 10Y–2Y | Inverted (< 0%) | **-12** |
| Yield spread 10Y–2Y | Flat (< 0.25%) | **-5** |
| Yield spread 10Y–2Y | Steep (> 1.5%) | **+7** |
| Yield spread 10Y–2Y | Normal (> 0.5%) | **+3** |
| Unemployment | > 7.0% | **-12** |
| Unemployment | > 6.0% | **-8** |
| Unemployment | > 5.0% | **-4** |
| Unemployment | < 3.5% | **+8** |
| Unemployment | < 4.5% | **+5** |
| CPI YoY | > 6.0% | **-15** |
| CPI YoY | > 4.0% | **-10** |
| CPI YoY | > 3.0% | **-5** |
| CPI YoY | 1.5–2.5% (target) | **+5** |
| CPI YoY | < 0% (deflation) | **-8** |
| Fed funds rate | > 5.5% | **-8** |
| Fed funds rate | > 4.5% | **-4** |
| Fed funds rate | < 1.0% | **+3** |
| Fed funds rate | < 2.5% | **+2** |
| VIX | > 40 | **-15** |
| VIX | > 30 | **-10** |
| VIX | > 20 | **-4** |
| VIX | < 12 | **+6** |
| VIX | < 15 | **+4** |
| NFP MoM | > 300K | **+4** |
| NFP MoM | > 150K | **+2** |
| NFP MoM | < -100K | **-8** |
| NFP MoM | < 50K | **-3** |
| Industrial production YoY | < -3% | **-5** |
| Industrial production YoY | < 0% | **-2** |
| Industrial production YoY | > 3% | **+3** |

**Macro Score Labels:** ≥ 70 = Supportive · 40–69 = Neutral · < 40 = Stressed

### 6.2 Macro Stress Index (0–100, inverse framing)

A complementary stress score broken down into named components shown in the UI. 100 = maximum stress. Inputs: yield curve (0–25 pts), VIX (0–20 pts), inflation (0–20 pts), labour market (0–20 pts), Fed policy (0–15 pts).

**Stress Labels:** ≥ 60 = High Stress · 35–59 = Elevated · 15–34 = Moderate · < 15 = Low Stress

### 6.3 Recession Risk Gauge (0–99%)

Rule-based model inspired by the Estrella/Mishkin yield curve approach. Inputs: NBER USREC indicator (if = 1, immediately returns 95%), yield curve inversion, unemployment, industrial production, VIX.

**Recession Labels:** ≥ 60% = High · 30–59% = Elevated · < 30% = Low

### 6.4 Yield Curve Shape

Computed from individual tenor yields (2Y, 5Y, 10Y, 30Y). Classifies the curve as Inverted / Flat / Normal / Steep based on the 10Y–2Y spread.

---

## 7. Sentiment Pipeline

**Files:** `app/services/sentiment_service.py`, `app/services/adv_sentiment_service.py`, `app/services/news_data.py`, `app/services/reddit_service.py`, `app/services/stocktwits_service.py`

Sentiment is scored using **FinBERT**, a finance-domain BERT model. The pipeline:

1. News articles are ingested and stored in the `NewsArticle` table.
2. FinBERT scores each article in the `[-1, +1]` range.
3. Scores are aggregated into `SentimentAggregate` rows (daily, by symbol, by source type).
4. The GAS pre-compute service pulls the **30-day weighted rolling average** for each symbol.
5. The raw FinBERT score is mapped to 0–100: `score_100 = (raw + 1) / 2 × 100`

**Source types tracked:** news, Reddit, StockTwits (social sentiment is stored separately but currently the primary GAS input is news sentiment).

---

## 8. Technical Consensus

**File:** `app/services/technical_service.py`

The technical consensus aggregates multi-timeframe ML signals into a single 0–100 score.

### Active Timeframes

| Timeframe | Status | Notes |
|-----------|--------|-------|
| 1h | ✅ Active | Fetched from Yahoo Finance (max 730 days) |
| 4h | ✅ Active | Resampled from 1h bars (yfinance has no native 4h) |
| 1d | ⏳ Ready (code exists, not trained) | Needs training run |
| 1wk | ⏳ Ready (code exists, not trained) | Needs training run |
| 1mo | ⏳ Ready (code exists, not trained) | Needs training run |

### Consensus Aggregation

Each active timeframe's model runs independently and produces a raw signal in [-1, +1]. The consensus is the Sharpe-weighted average of these signals:

```
For each timeframe:
  weight = max(validation_sharpe, 0.1)   ← floor at 0.1, never negative
  weighted_signal += raw_signal × weight

consensus_raw = weighted_signal / total_weight
consensus_score = (consensus_raw + 1) / 2 × 100
```

**Consensus Labels:**
- ≥ 80: Strong Bullish
- 60–79: Bullish Focus
- 40–59: Mixed / Neutral
- 20–39: Bearish Focus
- < 20: Strong Bearish

---

## 9. Data Feeds & External Sources

| Service | Data Provided | File |
|---------|--------------|------|
| Yahoo Finance | OHLCV price bars (1h, 4h, 1d, 1wk) | `ohlcv_fetcher.py` |
| FRED | VIX, CPI, Fed rate, unemployment, NFP, yield spread, industrial production, NBER recession indicator | `macro_data.py` |
| Finnhub / News APIs | News articles for FinBERT sentiment | `news_data.py` |
| Reddit | Social sentiment mentions | `reddit_service.py` |
| StockTwits | Social sentiment feed | `stocktwits_service.py` |
| SEC / Insider data | Insider buying/selling signals | `insider_service.py` |
| Options flow | Put/call ratios, unusual options activity | `options_service.py` |
| Short interest data | Short float, days-to-cover | `short_service.py` |
| Earnings data | EPS surprises, guidance | `earnings_service.py` |
| Fed policy | FOMC decisions, forward guidance | `fed_policy_service.py` |
| Sector data | Sector rotation, relative strength | `sector_service.py` |

---

## 10. Caching & Persistence

### Redis

- Cache key: `gas:snapshot:<SYMBOL>` (e.g. `gas:snapshot:AAPL`)
- TTL: **900 seconds (15 minutes)**
- Content: full GAS snapshot dict (gas_score, weather_label, regime, component_scores, technical_signals, computed_at)
- Writes: on every pre-compute run and every live compute
- Reads: checked before DB on every API call

### PostgreSQL

- `gas_snapshots` table: durable GAS snapshots, one row per symbol (upserted on each run)
- `stock_ohlcv` table: historical OHLCV bars per symbol
- `macro_indicators` table: FRED indicator values by date
- `sentiment_aggregates` table: daily FinBERT sentiment scores by symbol
- `news_articles` table: raw news articles with source and published_at
- `users`, `watchlists`, `alerts`, `portfolios`, `strategies`: user data

### Model Storage

Trained model artifacts are saved as `.joblib` files in `backend/data/models/`. The registry is a JSONL file (`model_registry.jsonl`) append-logged with metadata per training run (symbol, timeframe, winning model name, Sharpe, accuracy, timestamp).

---

## 11. Scheduler & Pre-Computation

**File:** `app/services/gas_precompute.py`, `app/services/scheduler.py`

The APScheduler runs the GAS pre-computation batch every **15 minutes** during market hours (Mon–Fri, 13:00–21:00 UTC).

### Batch Strategy

1. Compute macro score **once** (it's market-wide, not per-symbol) — shared across all symbols.
2. For each symbol in the default watch list: run technical inference + sentiment lookup **concurrently**, then combine with the shared macro score.
3. Persist each snapshot to DB and Redis.
4. All DB writes are committed in a single transaction after the full batch.

The batch can also be triggered manually via `POST /api/v1/admin/gas/precompute`.

---

## 12. Running Locally

### Prerequisites

- Python 3.10+
- PostgreSQL running
- Redis running
- `.env` file configured (see `.env.example`)

### Start the server

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### DB migrations

```bash
cd backend
alembic upgrade head
```

### Train ML models (required before GAS will work)

The GAS technical score component requires trained models. To train for a symbol:

```bash
# Via the admin API endpoint (once the server is running):
POST /api/v1/admin/ml/train?symbol=AAPL&timeframe=1h
POST /api/v1/admin/ml/train?symbol=AAPL&timeframe=4h
```

Training requires at least 200 rows of OHLCV data for the symbol. Trained models are saved to `backend/data/models/`.

### Health check

```
GET http://localhost:8000/health   →  {"status": "ok"}
```

---

## 13. Project Structure

```
fin-eye/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # Settings, startup, lifecycle
│   │   ├── crud/             # DB query layer
│   │   ├── db/               # DB engine, session
│   │   ├── middleware/        # Auth, CORS, logging
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic DTOs
│   │   └── services/
│   │       ├── ml_pipeline.py          # Model training, feature engineering, walk-forward eval
│   │       ├── technical_service.py    # Multi-timeframe inference + consensus
│   │       ├── feature_builder.py      # DB-backed + stub feature matrix builders
│   │       ├── gas_precompute.py       # GAS composition (technical+sentiment+macro), cache write
│   │       ├── macro_scoring.py        # Macro score, stress index, recession risk, yield curve
│   │       ├── macro_data.py           # FRED data ingestion
│   │       ├── sentiment_service.py    # FinBERT sentiment scoring
│   │       ├── news_data.py            # News article ingestion
│   │       ├── ohlcv_fetcher.py        # Yahoo Finance OHLCV fetch
│   │       ├── market_data.py          # Market data orchestration
│   │       ├── backtesting_service.py  # Strategy backtesting engine
│   │       ├── portfolio_service.py    # Portfolio tracking
│   │       ├── risk_service.py         # Risk metrics
│   │       ├── hedging_service.py      # Hedge simulator
│   │       ├── indicator_service.py    # Custom indicator management
│   │       ├── options_service.py      # Options flow data
│   │       ├── insider_service.py      # Insider trading signals
│   │       ├── short_service.py        # Short interest data
│   │       ├── earnings_service.py     # Earnings data
│   │       ├── sector_service.py       # Sector rotation
│   │       ├── scheduler.py            # APScheduler job definitions
│   │       ├── cache_service.py        # Redis abstraction
│   │       └── analytics_service.py    # User analytics + activation funnel
│   ├── alembic/              # DB migrations
│   ├── data/models/          # Saved ML model artifacts (.joblib + model_registry.jsonl)
│   ├── tests/                # Test suite
│   └── requirements.txt
├── frontend/                 # Next.js frontend
├── model_store/              # Alternative model artifact storage
├── scripts/                  # Utility scripts
├── docs/                     # Product docs
└── docker-compose.yml
```

---

*Last updated: March 2026 — reflects the codebase as implemented.*
