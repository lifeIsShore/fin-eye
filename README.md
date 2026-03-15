# Fin-Eye — Intelligent Stock Analysis Platform

Fin-Eye is a full-stack financial intelligence platform that combines **machine learning**, **macroeconomic indicators**, **NLP-based sentiment analysis**, and **technical analysis** into a single unified score — the **Global Alignment Score (GAS)** — for any traded stock symbol.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [The Global Alignment Score (GAS)](#the-global-alignment-score-gas)
3. [ML Decision Engine — How the System Decides on Movement](#ml-decision-engine)
4. [Feature Reference — What Is On, What Is Off, What Feeds the Decision](#feature-reference)
5. [Macro Intelligence Layer](#macro-intelligence-layer)
6. [Sentiment Intelligence Layer](#sentiment-intelligence-layer)
7. [Advanced Sentiment Layer](#advanced-sentiment-layer)
8. [Backtesting Engine](#backtesting-engine)
9. [Data Sources](#data-sources)
10. [API & Caching Architecture](#api--caching-architecture)
11. [Running Locally](#running-locally)
12. [Stack](#stack)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP / REST
┌─────────────────────▼───────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ ML Pipeline│  │ Macro Engine │  │Sentiment Engine │  │
│  │ (XGBoost / │  │ (FRED + VIX) │  │ (FinBERT +      │  │
│  │  LogReg /  │  │              │  │  StockTwits +   │  │
│  │  Prophet)  │  │              │  │  Google Trends) │  │
│  └─────┬──────┘  └──────┬───────┘  └────────┬────────┘  │
│        │                │                   │            │
│  ┌─────▼────────────────▼───────────────────▼────────┐  │
│  │            GAS Pre-Compute Service                  │  │
│  │   Technical (40%) + Sentiment (30%) + Macro (30%)  │  │
│  └─────────────────────┬──────────────────────────────┘  │
│                         │                                 │
│            ┌────────────▼──────────┐                     │
│            │  Redis Cache (15 min) │                     │
│            │  PostgreSQL (durable) │                     │
│            └───────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

---

## The Global Alignment Score (GAS)

The GAS is a **0–100 composite score** that answers the question: *"How aligned is the macro, technical, and sentiment environment for this stock right now?"*

### Score Composition

| Component | Weight | Source |
|-----------|--------|--------|
| Technical (ML) | **40%** | ML model inference on OHLCV + technical indicators |
| Sentiment | **30%** | FinBERT 30-day rolling average on news articles |
| Macro | **30%** | FRED macroeconomic indicators + VIX |

**Formula:**
```
GAS = (technical_score × 0.40) + (sentiment_score × 0.30) + (macro_score × 0.30)
```

All component scores are normalised to 0–100 before weighting.

### GAS Labels (Weather System)

| Score Range | Label |
|-------------|-------|
| 80 – 100 | Strong Tailwind |
| 60 – 79 | Mild Support |
| 40 – 59 | Mixed Signals |
| 20 – 39 | Headwind |
| 0 – 19 | High Instability |

### Market Regime (derived from Technical Score)

| Technical Score | Regime |
|-----------------|--------|
| ≥ 60 | Risk-On |
| ≤ 40 | Risk-Off |
| 41 – 59 | Transitional |

---

## ML Decision Engine

This is the core of how Fin-Eye decides if a stock is likely to move **up or down** over the next 5 periods.

### Step 1 — Data Ingestion

For each symbol and timeframe, the system fetches OHLCV data (Open, High, Low, Close, Volume) via Yahoo Finance. Supported timeframes: `1h`, `4h` (resampled from 1h), `1d`, `1w`, `1m`.

> **Note:** yfinance does not have a native `4h` interval. The pipeline fetches `1h` data and resamples it to 4-hour bars using pandas `.resample("4h")`.

### Step 2 — Feature Engineering

Raw OHLCV data is transformed into a set of technical features. The minimum required history is **200 rows** (the pipeline will reject shorter series).

See [Feature Reference](#feature-reference) for the full list.

### Step 3 — Target Variable

The model predicts the **direction** of the 5-period forward return:

```python
target_ret_5 = close.shift(-5) / close - 1
target = 1 if target_ret_5 > 0 else 0   # Binary: UP or DOWN
```

This is a **binary classification** problem (not regression). The models output a probability of upward movement (`prob_up`).

### Step 4 — Model Competition (Walk-Forward Validation)

Three models are trained in competition for every symbol + timeframe pair:

| Model | Description |
|-------|-------------|
| **XGBoost** | Gradient-boosted trees. `n_estimators=100`, `max_depth=3`, `learning_rate=0.05`. Primary workhorse. |
| **Logistic Regression** | Linear baseline with StandardScaler normalisation and balanced class weights. |
| **Prophet** | Facebook's time-series model. Used for price forecasting; signal is derived from the predicted slope direction. |

**Split:** 80% training, 20% validation (time-series split — no look-ahead).

**Winner selection:** Each model is evaluated on the validation set using the **annualised Sharpe Ratio** of simulated strategy returns. The model with the highest Sharpe Ratio wins and is persisted to disk.

```
Strategy return = actual_ret × predicted_signal (1=long, 0=cash)
Sharpe = (mean(strat_ret) / std(strat_ret)) × sqrt(252)
```

### Step 5 — Per-Timeframe Signal Generation

For each trained timeframe model, the pipeline:
1. Loads the saved winning model from the `model_registry.jsonl`
2. Fetches the most recent OHLCV data
3. Engineers features on the latest row
4. Calls `model.predict_proba()` to get `prob_up`
5. Returns a signal dict:

```json
{
  "timeframe": "1h",
  "direction": "Bullish",
  "signal_raw": 0.75,
  "confidence": 75.0,
  "validation_sharpe": 1.32,
  "model_used": "xgboost"
}
```

### Step 6 — Technical Consensus Score

Active timeframes (`1h`, `4h`) are aggregated into a single **0–100 Technical Consensus Score** using Sharpe-weighted averaging:

```
weight_tf    = max(validation_sharpe_tf, 0.1)   # floor at 0.1 to avoid zero weights
raw_signal   = Σ(signal_raw_tf × weight_tf) / Σ(weight_tf)   # range: -1 to +1
consensus    = (raw_signal + 1) / 2 × 100         # map to 0–100
```

This means **timeframes with a historically stronger Sharpe Ratio have more influence** on the final consensus.

### Step 7 — GAS Assembly

The technical consensus score, along with the 30-day sentiment score and the macro score, is blended with fixed weights (40/30/30) into the final GAS value, persisted to PostgreSQL and cached in Redis.

---

## Feature Reference

### Features Used in ML Decision (ACTIVE — feed directly into model)

These features are computed by `engineer_features()` in `ml_pipeline.py` and are the **inputs to the XGBoost / Logistic / Prophet models**.

| Feature | Description | Status |
|---------|-------------|--------|
| `ret_1` | 1-period price return | ✅ Active |
| `sma_cross_10_20` | (SMA10 / SMA20) − 1. Captures short-term trend alignment | ✅ Active |
| `sma_cross_20_50` | (SMA20 / SMA50) − 1. Captures medium-term trend alignment | ✅ Active |
| `rsi_14` | Relative Strength Index, 14-period Wilder smoothing | ✅ Active |
| `macd` | MACD line (EMA12 − EMA26) | ✅ Active |
| `macd_hist` | MACD Histogram (MACD − Signal line). Captures momentum shifts | ✅ Active |
| `bb_width` | Bollinger Band width ((upper − lower) / middle). Measures volatility expansion/contraction | ✅ Active |
| `bb_pb` | Bollinger Band %B ((close − lower) / (upper − lower)). Measures price position within bands | ✅ Active |
| `mom_10` | 10-period momentum (price change %) | ✅ Active |
| `mom_20` | 20-period momentum (price change %) | ✅ Active |

### Features Computed But NOT Directly in ML Model

These are computed as intermediate values or stored for display purposes, but are not passed as model inputs:

| Feature | Description | Used For |
|---------|-------------|----------|
| `sma_10`, `sma_20`, `sma_50` | Raw SMA values | Used to compute `sma_cross_*` ratios above |
| `std_20` | 20-period rolling standard deviation | Used to compute Bollinger Bands |
| `bb_upper`, `bb_lower` | Bollinger Band upper/lower lines | Used to compute `bb_width` and `bb_pb` |
| `macd_signal` | 9-period EMA of MACD | Used to compute `macd_hist` |
| `target_ret_5` | Raw 5-period forward return | Used only during training to generate the binary `target` label |

### Features in DbFeatureBuilder (Extended Feature Set for Daily Timeframe)

When the system uses the database-backed `DbFeatureBuilder` (daily timeframe), additional features are assembled:

| Feature | Description | Source |
|---------|-------------|--------|
| `return_1d` | 1-day return | OHLCV |
| `return_5d` | 5-day return | OHLCV |
| `volatility_20d` | 20-day rolling volatility | OHLCV |
| `rsi_14` | RSI-14 (Wilder) | OHLCV |
| `macd`, `macd_signal`, `macd_hist` | MACD (12/26/9) | OHLCV |
| `bb_upper`, `bb_middle`, `bb_lower` | Bollinger Bands (20, 2σ) | OHLCV |
| `news_sentiment_1d` | Weighted avg FinBERT score, last 1 day | Sentiment DB |
| `news_sentiment_7d` | Weighted avg FinBERT score, last 7 days | Sentiment DB |
| `news_sentiment_30d` | Weighted avg FinBERT score, last 30 days | Sentiment DB |
| `news_source_diversity_30d` | Count of distinct news sources over last 30 days | NewsArticle DB |
| `macro_score` | Composite macro environment score (0–100) | FRED + Macro Engine |
| `vix_level` | VIX index level | Yahoo Finance via FRED |
| `yield_spread_10y_2y` | 10Y–2Y Treasury yield spread | FRED |
| `day_of_week` | Calendar feature (0=Monday) | Derived |
| `month` | Calendar feature (1–12) | Derived |
| `hour_of_day` | Calendar feature (0–23) | Derived |

> **Note:** The `StubFeatureBuilder` (used for 1h/4h when the DB does not have intraday bars) generates synthetic data with the same schema for development and testing.

### Features NOT Currently Active (Infrastructure Exists, Not Yet Wired Into Model)

| Feature | Status | Location |
|---------|--------|----------|
| Insider trading signals | Service exists, not in ML pipeline | `insider_service.py` |
| Short interest data | Service exists, not in ML pipeline | `short_service.py` |
| Options flow (put/call ratio) | Service exists, not in ML pipeline | `options_service.py` |
| Earnings event proximity | Service exists, not in ML pipeline | `earnings_service.py` |
| Reddit sentiment | Service exists, not in ML pipeline | `reddit_service.py` |
| StockTwits sentiment (raw) | Service exists, display only | `stocktwits_service.py` |
| Sector rotation signals | Service exists, display only | `sector_service.py` |
| Fed policy stance | Service exists, display only | `fed_policy_service.py` |
| Google Trends interest | Wired into Advanced Sentiment composite | `adv_sentiment_service.py` |

These are captured data signals that have not yet been integrated as features into the ML training pipeline. They are available via the API for display purposes.

---

## Macro Intelligence Layer

The macro engine computes **three separate outputs**, all sourced from FRED (Federal Reserve Economic Data) and Yahoo Finance (VIX):

### 1. Macro Environment Score (0–100)

Starts at 50 (neutral) and adjusts based on incoming indicators. **Higher = better environment for equities.**

| Indicator | Condition | Adjustment |
|-----------|-----------|------------|
| Yield Spread (10Y–2Y) | Deeply inverted (< −0.5%) | −20 pts |
| | Inverted (< 0%) | −12 pts |
| | Flat (< 0.25%) | −5 pts |
| | Steep (> 1.5%) | +7 pts |
| Unemployment Rate | > 7% | −12 pts |
| | < 3.5% | +8 pts |
| CPI YoY | > 6% | −15 pts |
| | 1.5–2.5% (target) | +5 pts |
| | < 0% (deflation) | −8 pts |
| Fed Funds Rate | > 5.5% | −8 pts |
| | < 1% | +3 pts |
| VIX | > 40 | −15 pts |
| | < 12 | +6 pts |
| NFP MoM | > 300k | +4 pts |
| | < −100k | −8 pts |
| Industrial Production YoY | < −3% | −5 pts |
| | > 3% | +3 pts |

**Labels:** Supportive (≥70), Neutral (40–69), Stressed (<40)

### 2. Macro Stress Index (0–100)

The inverse framing of the Macro Score. **Higher = more stressed environment.** Decomposed into named components for UI display:

- Yield Curve Inversion: 0–25 pts
- VIX / Volatility: 0–20 pts
- Inflation (CPI): 0–20 pts
- Labour Market: 0–20 pts
- Fed Policy: 0–15 pts

**Labels:** High Stress (≥60), Elevated (35–59), Moderate (15–34), Low Stress (<15)

### 3. Recession Risk Gauge (0–99%)

Rule-based model based on the Estrella/Mishkin yield-curve approach:

- Base rate: 5%
- Deeply inverted yield curve (< −0.75%): +45 pp
- Inverted yield curve (< −0.25%): +30 pp
- Flat yield curve (< 0.25%): +12 pp
- Unemployment > 6.5%: +20 pp
- Industrial production contracting (< −2% YoY): +10 pp
- VIX > 35: +8 pp
- NBER official recession indicator = 1: outputs 95% directly

### FRED Data Series Fetched

| Series | Indicator |
|--------|-----------|
| FEDFUNDS | Fed Funds Rate |
| UNRATE | Unemployment Rate |
| T10Y2Y | 10Y–2Y Treasury Spread |
| CPIAUCSL | CPI YoY |
| DGS2, DGS5, DGS10, DGS30 | Full yield curve tenors |
| USREC | NBER Recession Indicator |
| PAYEMS | Nonfarm Payrolls |
| INDPRO | Industrial Production Index |
| VIX | Fetched from Yahoo Finance (^VIX) |

---

## Sentiment Intelligence Layer

### FinBERT Sentiment Scoring

Each news article headline is scored using **FinBERT** (`ProsusAI/finbert`), a finance-domain BERT model fine-tuned for financial sentiment classification.

- **Output labels:** POSITIVE, NEGATIVE, NEUTRAL
- **Score mapping:** `positive → +confidence`, `negative → −confidence`, `neutral → 0.0`
- **Score range:** approximately −1.0 to +1.0
- **Input truncation:** first 512 tokens of the article title

If `transformers`/`torch` are not installed, the service falls back to a neutral score of 0.0 gracefully.

### Daily Aggregation

Articles are grouped by day and aggregated using **mention-weighted averages**:

```
daily_score = Σ(score_i × mentions_i) / Σ(mentions_i)
```

Three rolling windows are stored: **1-day**, **7-day**, and **30-day**.

### Sentiment Score → 0–100 Scale

The raw FinBERT score (−1 to +1) is mapped to the 0–100 scale for GAS composition:

```
sentiment_score_100 = (raw_avg_30d + 1) / 2 × 100
```

### Source Diversity

A sliding 30-day count of **distinct news sources** is tracked per symbol. This is stored as a feature (`news_source_diversity_30d`) and prevents situations where a single outlet dominates the sentiment signal.

---

## Advanced Sentiment Layer

Beyond the core FinBERT pipeline, the advanced sentiment module (`adv_sentiment_service.py`) adds two additional data sources:

### Google Trends

- **Source:** `pytrends` (no API key required)
- **Query:** `"{TICKER} stock"` keyword, 90-day window, weekly granularity
- **Outputs:**
  - Interest-over-time (0–100 normalised by Google)
  - Rising related queries (top 5)
  - Trend direction: Rising / Falling / Stable
  - Recent 4-week avg vs full-period avg (momentum delta)
- **Cache TTL:** 4 hours (pytrends has aggressive rate-limiting)

### StockTwits

- **Source:** Public StockTwits API (no API key required)
- **Outputs:**
  - Bullish / Bearish / Neutral message counts and percentages
  - Bull/Bear ratio
  - Top 5 bullish and bearish messages ranked by likes
  - Latest 10 messages regardless of sentiment
- **Cache TTL:** 15 minutes

### Advanced Composite Score (0–100)

```
advanced_score = (stocktwits_bullish_ratio × 0.60) + (trends_momentum_mapped × 0.40)
```

| Score | Label |
|-------|-------|
| ≥ 72 | Strong Bullish Momentum |
| 58–71 | Bullish Lean |
| 42–57 | Neutral |
| 28–41 | Bearish Lean |
| < 28 | Strong Bearish Pressure |

---

## Backtesting Engine

The backtesting engine (`backtesting_service.py`) allows users to validate strategies on historical OHLCV data (up to 5 years via Yahoo Finance).

### Currently Supported Strategy: Momentum (SMA Crossover + RSI)

**Parameters (all configurable):**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sma_fast` | 50 | Fast SMA period |
| `sma_slow` | 200 | Slow SMA period |
| `rsi_period` | 14 | RSI period |
| `rsi_threshold` | 40 | Minimum RSI to enter long |
| `initial_capital` | User-defined | Starting portfolio value |
| `slippage_pct` | User-defined | Per-trade slippage cost |

**Entry condition:** `sma_fast > sma_slow AND rsi > rsi_threshold`

**Signal execution:** Position is shifted by 1 bar (executed at next period open).

### Performance Metrics Calculated

| Metric | Description |
|--------|-------------|
| Total Return % | Strategy return vs buy-and-hold benchmark |
| Annualised Return % | Compounded annual return |
| Max Drawdown % | Largest peak-to-trough loss |
| Sharpe Ratio | Annualised (252-day) |
| Sortino Ratio | Downside-only volatility denominator |
| Win Rate % | % of active trading days with positive return |
| Profit Factor | Gross profit / Gross loss |
| Total Trades | Number of position changes |
| Recovery Factor | Total return / abs(Max Drawdown) |

An **overfitting warning** is surfaced if the in-sample Sharpe Ratio exceeds 1.2.

---

## Data Sources

| Source | Data | Method |
|--------|------|--------|
| **Yahoo Finance** (`yfinance`) | OHLCV price data, VIX index | Python library |
| **FRED** (Federal Reserve) | Macro indicators (rates, CPI, NFP, etc.) | REST API |
| **Finnhub** | News articles per ticker | REST API (requires API key) |
| **StockTwits** | Social sentiment messages | Public REST API |
| **pytrends** | Google Trends interest data | Unofficial Google API |
| **ProsusAI/finbert** | Sentiment model weights | HuggingFace Hub |

---

## API & Caching Architecture

### Three-Tier Read Path for GAS

1. **Redis (< 1ms):** 15-minute TTL cache keyed `gas:snapshot:{SYMBOL}`
2. **PostgreSQL (< 5ms):** Durable snapshot table; re-warms Redis on hit
3. **Live compute (2–3s):** Full ML inference + sentiment + macro aggregation on cold cache miss

### Scheduled Pre-Computation

A background APScheduler job runs every **15 minutes** during market hours (Mon–Fri, 13:00–21:00 UTC) to pre-warm the cache for all configured symbols. The macro score is computed **once per batch** (it is market-wide, not per-symbol) and reused for all symbols in that pass.

### Model Persistence

Trained models are saved as `.joblib` files under `backend/data/models/`. A JSONL registry (`model_registry.jsonl`) tracks metadata for each trained model:

```json
{
  "symbol": "AAPL",
  "timeframe": "1h",
  "model_name": "xgboost",
  "trained_at": "2025-03-01T12:00:00",
  "artifact_file": "AAPL_1h_winner.joblib",
  "validation_sharpe": 1.42,
  "metrics": {
    "xgboost": {"accuracy": 0.53, "sharpe_ratio": 1.42},
    "logistic": {"accuracy": 0.51, "sharpe_ratio": 0.87},
    "prophet": {"accuracy": 0.49, "sharpe_ratio": 0.61}
  }
}
```

The inference pipeline always uses the **most recently trained entry** for each symbol + timeframe pair.

---

## Running Locally

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis
- Node.js 18+ (frontend)

### Backend

```bash
cd backend
cp .env.example .env           # fill in DB_URL, REDIS_URL, FINNHUB_API_KEY, FRED_API_KEY
pip install -r requirements.txt

# Run DB migrations
python run_alembic.py

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

### Training ML Models

Before the GAS score can be computed for a symbol, models must be trained. Models need to be trained per symbol, per timeframe:

```
POST /api/v1/technical/train?symbol=AAPL&timeframe=1h
POST /api/v1/technical/train?symbol=AAPL&timeframe=4h
```

The system fetches historical OHLCV data, runs the 3-model competition (XGBoost vs Logistic vs Prophet), selects the winner by Sharpe Ratio, and saves the artifact. Inference is available immediately after training completes.

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend Framework | FastAPI (Python 3.10+) |
| ASGI Server | Uvicorn |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Cache | Redis |
| ML Models | XGBoost, scikit-learn (Logistic Regression), Prophet |
| NLP / Sentiment | HuggingFace Transformers (FinBERT — ProsusAI/finbert) |
| OHLCV Data | yfinance |
| Macro Data | fredapi (FRED) |
| Social Sentiment | pytrends, httpx (StockTwits) |
| Background Jobs | APScheduler |
| Frontend | Next.js + Tailwind CSS |
| Containerisation | Docker + Docker Compose |
| Testing | pytest |

---

*Last updated: March 2026*
