# PRDV3 - FIN-EYE PRODUCT REQUIREMENTS DOCUMENT (DETAILED)
## Complete Product Specification with All Missing Sections Expanded

---

## 📋 SECTION 0: EXECUTIVE SUMMARY

**Product Name:** Fin-Eye  
**Tagline:** "Understand the forces behind price movements"  
**Vision:** A market intelligence platform combining machine learning consensus, macro sentiment analysis, and educational content to help retail investors make informed decisions through understanding market environments.  

**Target Users:**
- Finance & Economics students (primary)
- Curious retail investors
- Intermediate learners wanting structure
- Semi-professional traders

**Price Model:** 
- Free Tier: €0 (limited features, 24h delayed data)
- Pro Tier: €14.99/month worldwide
- Estimated LTV if 6-month retention: €89.94

**Core Value Proposition:**
Instead of predicting prices, Fin-Eye answers: "Why is the market moving?" by combining:
1. **Multi-timeframe ML consensus** - What do technical models agree on?
2. **Macro sentiment layer** - What do central banks, governments, and economic indicators signal?
3. **Retail sentiment** - What does social media and retail positioning show?
4. **Conflict detection** - Where do signals disagree? (highest education value)

**Core Differentiator:** 
Global Alignment Score (GAS) + Conflict Detector showing environmental clarity, not false certainty.

**Key Promise:**  
NOT: "AI predicts 125€ target price"  
YES: "Current regime is Risk-On, 73% macro alignment, 4/5 timeframes bullish, but retail sentiment overheating signals exhaustion risk"

**Legal Positioning:** 
Educational analytics platform (not financial advice). All disclaimers emphasize model uncertainty and historical backtesting limitations.

---

## 🎯 SECTION 1: PRODUCT OVERVIEW

### 1.1 What Fin-Eye Does

Fin-Eye is a layered intelligence engine that synthesizes four data streams into actionable insights:

```
LAYER 1: TECHNICAL LAYER
├─ 4 ML models compete per timeframe (1h, 4h, 1d, 1w, 1m)
├─ Winner selected by Sharpe ratio (best risk-adjusted returns)
├─ 5-timeframe consensus averaged
└─ Output: Technical confidence score (0-100)

LAYER 2: SENTIMENT LAYER
├─ FinBERT sentiment from financial news (positive/negative)
├─ Reddit retail sentiment (mention volume + polarity)
├─ Political event tracking (GDELT)
└─ Output: Sentiment alignment score (0-100)

LAYER 3: MACRO LAYER
├─ Fed policy signals (rates, balance sheet)
├─ Treasury yield curves (liquidity stress indicator)
├─ Inflation trends (CPI/PCE)
├─ Recession probability (inverted curves, jobless claims)
└─ Output: Macro environment score (0-100)

LAYER 4: VOLATILITY REGIME
├─ VIX classification (low/medium/high stress)
├─ Historical volatility (20-day, 60-day)
├─ Implied volatility skew
└─ Output: Risk appetite classification

SYNTHESIS ENGINE: GLOBAL ALIGNMENT SCORE (GAS)
├─ Average of all 4 layers weighted by timeframe relevance
├─ Identify conflicts (e.g., bullish technicals + bearish macro)
├─ Output: Single 0-100 score + conflict warnings
└─ Express as: Market Weather System (☀️ to 🌪)
```

### 1.2 Core User Tabs

1. **Dashboard Tab** (Landing page)
   - Global Alignment Score (huge, central)
   - Market Weather System (visual)
   - "Why Is The Market Moving?" explanation
   - Key alerts/conflicts
   - Real-time updates

2. **Backtesting Tab**
   - Strategy templates (Momentum, Mean Reversion, Macro-Responsive)
   - Walk-forward validation results
   - Live vs backtest performance comparison
   - Slippage/commission assumptions
   - Parameter tuning interface

3. **News & Sentiment Tab**
   - Real-time news feed (filtered by ticker)
   - FinBERT sentiment scores per article
   - Sentiment timeseries (last 30 days)
   - Source breakdown (which outlets are bullish/bearish)
   - Topic extraction (what themes drive sentiment?)

4. **Macro Dashboard Tab**
   - FRED economic indicators (Fed rates, inflation, unemployment)
   - Treasury yield curve (2y, 5y, 10y)
   - Historical recessions marked
   - G20 event tracker
   - Central bank speech sentiment
   - Recession probability meter

5. **Hedging Simulator Tab**
   - Select stock + hedge instruments (puts, calls, ETFs)
   - Correlation heatmap (stock vs indices)
   - Beta calculation vs S&P 500
   - Max drawdown reduction estimation
   - Cost/benefit analysis

6. **Learn/Blog Tab**
   - Weekly market insights (2 posts/week)
   - "Macro 101" educational series
   - Case studies (historical regime shifts)
   - Video tutorials (YouTube embeds)
   - Glossary (definitions of GAS, regime, alignment, etc.)

7. **Settings/Portfolio Tab**
   - User profile management
   - Watchlist management (favorite stocks)
   - Notification preferences
   - Data export options
   - Subscription management


---

## 📊 SECTION 2: DETAILED FEATURE SCOPE

### Phase 1: MVP (Weeks 1-12)
**Goal: Single-stock intelligence engine with clear market regime visualization**

#### 2.1.1 Market Intelligence Features
- **Single stock analysis** with multi-timeframe ML consensus (1h, 4h, 1d, 1w, 1mo)
- **Global Alignment Score (GAS)** visualization: 0-100 scale
- **Market Weather System**  representations (no emoji nor images):
  - Strong Tailwind (80-100): All layers aligned bullish
  -  Mild Support (60-79): Mostly bullish, some caution
  -  Mixed Signals (40-59): Disagreement between layers
  -  Headwind (20-39): Mostly bearish, some hope
  -  High Instability (0-19): All layers aligned bearish
- **Conflict Detector**: Highlights when layers disagree (e.g., "Technicals bullish +4% vs. Macro bearish -3%")
- **Regime Classification**: Risk-On / Risk-Off / Range-Bound with confidence %
- **Volatility Regime**: Low (VIX < 15) / Medium (15-25) / High (> 25)
- **Multi-timeframe view**: One chart per timeframe with model consensus

#### 2.1.2 Technical ML Layer
- **Four competing models per timeframe**:
  - LSTM with attention (deep learning, captures long-term patterns)
  - XGBoost (gradient boosting, handles non-linearity)
  - Linear regression (baseline, interpretability)
  - Prophet (Facebook's time-series forecasting for seasonality)
- **Feature set** (v1):
  - Price features: Returns, log-returns, volatility, RSI, MACD, Bollinger Bands
  - Sentiment features: News sentiment score (from FinBERT)
  - Macro features: Fed rates, VIX, yield spreads
  - Time features: Day-of-week, month, seasonality
- **Target variable**: 1-day-ahead directional prediction (Up/Down/Neutral)
- **Evaluation**: Sharpe ratio on validation set (reward risk-adjusted returns)
- **Training data**: 5 years of historical data (initial), expandable to 10 years
- **Retraining**: Monthly (or after market regime shifts detected)
- **Model selection**: Top-performing model per timeframe becomes "Technical Consensus"
- **Output**: Directional signal (Bullish/Neutral/Bearish) + confidence (0-100)

#### 2.1.3 Backtesting & Strategy Engine
- **Strategy templates** (users can modify parameters):
  - Momentum: Buy if price > 50-day SMA, sell if RSI > 70
  - Mean Reversion: Buy if price < 2σ below, sell on bounce
  - Macro-Responsive: Buy if bullish regime + positive momentum, exit on regime shift
- **Walk-forward validation**: 
  - Train on 3 years, test on next 6 months (rolling window)
  - Repeat across full history to get realistic performance
- **Metrics reported**:
  - Total return %
  - Sharpe ratio
  - Sortino ratio
  - Max drawdown
  - Win rate %
  - Recovery factor (total profit / max drawdown)
- **Slippage/Commission**: 0.1% per trade + 5 basis points spread assumption
- **Live tracking**: Compare backtest returns vs actual forward performance (weekly update)
- **Parameter tuning UI**: Adjust lookback windows, thresholds, let user see impact on backtest

#### 2.1.4 Sentiment Layer (News)
- **Data source**: Finnhub News API (free tier: 60/min requests, covers major global news)
- **Processing**: 
  - Pull last 50 articles per stock daily
  - Run through FinBERT sentiment classifier (0-1 score, 0=very negative, 1=very positive)
  - Aggregate: Last 1-day, 7-day, 30-day average sentiment
- **Display**:
  - Sentiment timeseries (line chart, last 30 days)
  - Sentiment breakdown by source (which outlets are most bullish?)
  - Current sentiment score with trend arrow (↑ increasing, ↓ decreasing)
  - Sample headlines grouped by sentiment (most bullish, most bearish)
- **Feature for ML**: Include news sentiment in feature set for model training
- **Output**: Sentiment score (0-100, 50=neutral)

#### 2.1.5 Macro/Economic Layer (MVP: Basics Only)
- **Data sources**:
  - FRED API: Federal Funds Rate, CPI, Unemployment (daily/monthly updates)
  - Yahoo Finance: VIX index (real-time)
  - US Treasury: 2-10yr yield spread (daily)
- **Indicators displayed**:
  - Current Fed Funds Rate (%)
  - Latest CPI (% YoY)
  - Latest unemployment rate (%)
  - 2-10yr yield spread (basis points)
  - VIX (0-100 scale)
- **Interpretation layer**:
  - Recession probability meter: If 2-10yr inverted + weak jobs, show "Recession risk elevated"
  - Liquidity meter: If yields rising fast, show "Tightening environment"
  - Inflation meter: If CPI elevated, show "Stagflation risk"
- **Output**: Macro score (0-100, based on combination of above)

#### 2.1.6 Educational Content
- **"Why Is The Market Moving?" Engine**:
  - Plain English explanation of current regime
  - Example output: "Stock is rising mainly because:
    - 60% Technical momentum (4 of 5 timeframes bullish)
    - 30% Positive news sentiment (3-day average +0.65/1.0)
    - 10% Macro tailwind (Fed rates stable, VIX declining)
    - **Warning:** Retail sentiment overheating - reversal risk if news turns negative"
- **Blog/Learn Tab**:
  - 2 blog posts per week minimum
  - Topics: "Why the Fed matters," "What is regime," "Reading yield curves," "Backtesting pitfalls"
  - Glossary: Define GAS, alignment, timeframe, regime, volatility regime
- **Risk disclaimers on every page**:
  - "This is educational analysis, not investment advice"
  - "Past performance does not guarantee future results"
  - "Backtests can overfit; forward performance often worse"
  - "Always risk what you can afford to lose"
- **User onboarding**:
  - Tour of all tabs (5 min walkthrough)
  - Example of how to interpret GAS
  - Example of how to use hedging simulator

#### 2.1.7 Risk Simulation (Basic)
- **Hedging scenario builder**:
  - User picks stock (e.g., Tesla)
  - Select hedge: Add protective put (OTM) or short ETF (inverse correlation)
  - System calculates:
    - Beta of stock vs S&P 500 (how correlated?)
    - Correlation of stock vs hedge instrument
    - Max drawdown reduction if stock drops 20%
    - Cost: Annual cost of put premium or ETF carry
- **Visualization**:
  - Before/after equity curve (backtest simulation)
  - Payoff diagram (stock up/down, with/without hedge)
  - "If you had hedged 2020 crash, losses would be reduced by X%"

#### 2.1.8 Data Infrastructure (MVP)
- **Market data**: 
  - Provider: Yahoo Finance (free, covers 5min+ OHLCV)
  - Refresh: Every 15 min during market hours, daily close outside
  - Storage: TimescaleDB (PostgreSQL + time-series) for scalability
- **News data**:
  - Finnhub News API (60 req/min free tier)
  - Cached for 1 day to avoid re-querying
  - Redis cache layer for frequent lookups
- **FinBERT sentiment**:
  - Hosted on: HuggingFace free tier (transformers library)
  - Batch processing: Run nightly on accumulated articles
  - Store results in PostgreSQL for 30 days
- **FRED data**:
  - Daily pull via FRED API (free, no rate limits)
  - Store last 30 years
  - Update daily after 8 AM ET release

---

### Phase 2: Growth (Months 3-6)
**Goal: Multi-asset portfolio view + Macro depth + Retail sentiment**

#### 2.2.1 Portfolio Management
- Track up to 10 stocks + aggregate insights
- Portfolio-level GAS (weighted average by position size)
- Sector breakdown (% tech, financials, energy, etc.)
- Correlation heatmap across holdings
- Diversification score (0-100, based on correlation matrix)

#### 2.2.2 Macro Intelligence Expansion
- FRED integrations:
  - Treasury yield curve (2y, 5y, 10y, 30y) with historical context
  - Recession probability (from Federal Reserve's dynamic factor model)
  - Leading economic index
  - Real yield spreads
- World Bank data:
  - Emerging market growth forecasts
  - Debt sustainability analysis
- IMF data:
  - Global Fiscal Monitor (government spending, deficits)
  - World Economic Outlook (growth/inflation forecasts by country)
- **Macro stress index**: Composite score from all above (0-100)

#### 2.2.3 Retail Sentiment (Reddit)
- PRAW integration (Reddit API wrapper):
  - Track r/stocks, r/wallstreetbets, r/investing, r/SecurityAnalysis
  - Count daily mentions of target stock
  - Aggregate sentiment polarity (positive/negative/neutral posts)
  - Detect volume spikes (unusual discussion increase)
- Display:
  - "Retail buzz" chart (mention volume over 30 days)
  - Sentiment breakdown (% positive vs negative)
  - Top 5 most bullish, most bearish comments
- **Output**: Retail sentiment score (0-100)

#### 2.2.4 Political Event Tracking (GDELT)
- GDELT (Global Database of Events, Language, and Tone):
  - Real-time global news event database
  - Track G20 meetings, central bank announcements, elections
  - Score by tone (positive/negative impact on risk assets)
- **Events tracked**:
  - ECB/Fed rate decisions
  - Earnings announcements
  - Geopolitical incidents (war, sanctions, elections)
  - Natural disasters / supply shocks
- Display:
  - Event calendar (upcoming announcements)
  - Past events with impact (stock price move post-event)
  - Risk score (how much volatility expected near event)

#### 2.2.5 Advanced Hedging Strategies
- Multi-leg hedges:
  - Stock + put + short correlated ETF
  - Collar strategies (buy put, sell call for income)
  - Beta-neutral pairs (long stock, short index to isolate alpha)
- Currency hedges (for EUR, GBP, JPY exposure)
- Options chain integration (show implied volatility, Greeks)
- Backtest hedge effectiveness across different market regimes

#### 2.2.6 Strategy Library
- Templates expanding to include:
  - Macro-responsive (buy when recession probability drops, sell on rise)
  - Sentiment-driven (buy on bullish news spikes, sell on bearish)
  - Event-based (trading around earnings/Fed announcements)
- Community sharing:
  - Users can save strategies, share with others
  - Leaderboard (best-performing shared strategies)
  - Fork & modify strategies from other users
- Performance attribution:
  - What % of returns came from timing (alpha) vs market exposure (beta)?

#### 2.2.7 Advanced Blog/Content
- Case studies: "2008 Crisis - What did GAS predict?" 
- Video series (YouTube embeds, 5-10 min each)
- "Macro 201" deeper dive courses
- Analyst commentary on weekly market moves

---

### Phase 3: Premium (Months 6+)
**Goal: Institutional-grade features + Custom analytics**

#### 2.3.1 Advanced Sentiment
- Twitter/X scraping (snscrape):
  - Political figures (Fed chairs, presidents, finance ministers)
  - Real-time event tracking (earnings calls, FOMC speeches)
  - Viral trend detection
- Google Trends integration:
  - Search interest spikes for company/sector
  - Historically correlated with volatility spikes
- Earnings call NLP:
  - Auto-download transcripts, extract sentiment
  - Identify management confidence shifts
- Crowdsourced sentiment:
  - Users submit views (bullish/bearish/neutral)
  - Voting mechanism to weight quality contributors

#### 2.3.2 Custom Analytics Engine
- No-code indicator builder:
  - Users create custom indicators without coding
  - Combine existing indicators with mathematical operators
- ML feature engineering playground:
  - Select custom features, let model train
  - Export winning feature combinations
- API for power users:
  - Webhooks for real-time signals
  - Bulk analysis requests
  - Custom data export (CSV, Parquet, JSON)

#### 2.3.3 Mobile App
- iOS + Android (React Native or Flutter)
- Push notifications:
  - GAS crosses above/below thresholds (e.g., bullish flip)
  - Conflict alerts (big disagreement between layers)
  - Event alerts (Fed announcement, earnings)
- Offline mode: Cached dashboard from last update
- Charting: Mobile-optimized (tap to expand, swipe to navigate)

#### 2.3.4 Institutional Products
- RESTful API:
  - Real-time GAS feeds
  - Historical regime data
  - Custom portfolio analysis
- White-label dashboard:
  - Brokers can rebrand Fin-Eye for their clients
  - Custom branding, logo, domain
- Bulk analysis:
  - Portfolio managers: Analyze 50+ stocks at once
  - Export reports (PDF, Excel)

#### 2.3.5 Risk Management Tools
- Scenario analysis:
  - "What if USD strengthens 5%?"
  - "What if Fed hikes to 6%?"
  - "What if stock falls 30%?"
  - See portfolio impact
- Stress testing vs historical crises:
  - Compare to 2008 crash, 2020 COVID drop, etc.
  - "Your portfolio would lose 15% in 2008 scenario"
- Monte Carlo simulations:
  - Project portfolio returns over 1-10 years
  - Show confidence bands (10th-90th percentile)
- VaR/CVaR calculations:
  - Value-at-Risk: 95% confidence, max daily loss
  - Expected Shortfall: Average loss in worst 5% scenarios

#### 2.3.6 Professional Content
- Research reports:
  - Monthly sector deep dives
  - Quarterly macro outlook
  - Special reports on market regime shifts
- Video webinars:
  - Weekly (Thursdays 5 PM ET): "Markets This Week" analysis
  - Monthly: "Macro Masterclass" (45 min deep dive)
- Expert network:
  - Guest contributors (hedge fund managers, economists)
  - Q&A sessions with users

---

## 🏗️ SECTION 3: DETAILED TECHNICAL ARCHITECTURE

### 3.1 Frontend Stack (Recommended)

```
FRAMEWORK: Next.js 13+ (React-based)
├─ Why: Full-stack capabilities, server-side rendering for SEO, API routes
├─ Alternative: Vue 3 + Nuxt for lighter weight

CHARTING LIBRARY: TradingView Lightweight Charts
├─ Why: Professional quality, multi-timeframe capable, fast rendering
├─ Alternative: Plotly (interactive but slower), Apache ECharts

UI COMPONENTS: Tailwind CSS + HeadlessUI / shadcn/ui
├─ Why: Rapid development, customizable, accessible components
├─ Alternative: Material-UI (heavier), Ant Design (enterprise)

STATE MANAGEMENT: Zustand or TanStack Query (React Query)
├─ Why: Lightweight, simple, great for server state caching
├─ Alternative: Redux Toolkit (overkill for MVP)

REAL-TIME UPDATES: WebSockets (Socket.io or native WS)
├─ Why: Low latency for GAS updates, backtesting progress
├─ Alternative: Server-Sent Events (simpler but unidirectional)

DEPLOYMENT: Vercel (for Next.js) or AWS Amplify
├─ Why: Automatic scaling, edge functions, CDN included
```

### 3.2 Backend Stack (Recommended)

```
LANGUAGE: Python 3.10+
├─ Why: Rich ML/data science ecosystem (NumPy, Pandas, scikit-learn, PyTorch)
├─ Alternative: Node.js (faster but fewer ML libraries), Go (compiled but setup slower)

FRAMEWORK: FastAPI
├─ Why: Modern, async, automatic API docs, 10x faster than Flask
├─ Alternative: Django (batteries included but slower), Flask (simpler but less async)

DATABASE: PostgreSQL (structured data) + TimescaleDB (time-series)
├─ Why: TimescaleDB native time-series optimization for OHLCV, highly available
├─ Alternative: ClickHouse (analytics focus), MongoDB (less suitable for structure)

CACHE: Redis
├─ Why: Sub-millisecond access, supports pub/sub for real-time updates
├─ Use cases:
│   ├─ Cache latest GAS scores (expires every 15 min)
│   ├─ Cache news sentiment (expires daily)
│   ├─ Session management

JOB QUEUE: Celery + Redis/RabbitMQ
├─ Why: Schedule ML retraining (nightly), sentiment batching (daily 8 PM)
├─ Alternative: APScheduler (simpler, single-worker only)

API GATEWAY: Kong or AWS API Gateway
├─ Why: Rate limiting, versioning, API key management
├─ Alternative: Nginx + custom logic

MONITORING: Prometheus + Grafana + ELK Stack
├─ Why: Track request latency, error rates, ML model drift
```

### 3.3 ML/Data Processing Stack

```
MODEL SERVING: FastAPI endpoints (embedded Python)
├─ Why: Simple, low latency, no separate service needed for MVP
├─ Future: TensorFlow Serving, MLflow Models (production at scale)

ML LIBRARIES:
├─ scikit-learn: XGBoost, linear regression (CPU-efficient)
├─ TensorFlow 2.x: LSTM + attention models (GPU-accelerated)
├─ Prophet: Time-series forecasting (Facebook's library)
├─ Hugging Face Transformers: FinBERT (sentiment classification)

DATA PROCESSING:
├─ Pandas: Data wrangling, feature engineering
├─ NumPy: Numerical computations
├─ TA-Lib / Pandas-TA: Technical indicators
├─ yfinance: Historical OHLCV data

NLP: HuggingFace Transformers (FinBERT)
├─ Model: finbert-tone (sentiment), 768-dim embeddings
├─ Batch inference: Process 100 articles in ~5 seconds
├─ GPU optional (CPU fine for <100 articles/day at MVP)

BACKTESTING: Backtrader or Zipline
├─ Why: Event-driven, realistic slippage/commission simulation
├─ Alternative: Vectorbt (ultra-fast for single models, less flexible)
```

### 3.4 Infrastructure & Deployment

```
HOSTING: AWS (or GCP/Azure for multi-region)
├─ Compute: EC2 (backend) or ECS (containerized)
├─ Database: RDS for PostgreSQL, TimescaleDB on EC2
├─ Cache: ElastiCache (Redis)
├─ Storage: S3 (model artifacts, backtest results)
├─ CDN: CloudFront (static assets, API responses)
├─ Load balancer: ALB or NLB

CONTAINERIZATION: Docker
├─ Dockerfile for backend (Python + dependencies)
├─ docker-compose.yml for local dev (backend + PostgreSQL + Redis)
├─ ECR registry for image storage

ORCHESTRATION: 
├─ MVP: Docker Compose (single machine)
├─ Growth: Kubernetes (EKS on AWS) for auto-scaling

CI/CD: GitHub Actions
├─ Test on PR (linting, unit tests, integration tests)
├─ Deploy to staging on merge to dev
├─ Manual promote to production
├─ Rollback capability

MONITORING & LOGGING:
├─ CloudWatch (AWS) for logs, metrics, alarms
├─ Prometheus for app metrics (request latency, error rates)
├─ Grafana for dashboards
├─ Sentry for error tracking & alerting
```

### 3.5 Data Architecture

```
DATA PIPELINE:

    News APIs ──┐
    FRED API ───┼──> Fetchers → Validators → Raw DB → Feature Engineering → Model Training
    Reddit API──┤
    Stock data──┤
    GDELT ──────┘

DETAILS:

1. FETCHERS (Python scripts, Celery tasks):
   └─ Run on schedule (e.g., every 15 min for OHLCV, daily 8 PM for news)
   └─ Connect to APIs, handle rate limits + retries
   └─ Push raw data to message queue (Kafka or Redis streams)

2. VALIDATORS:
   └─ Check data quality (missing values, outliers, duplicates)
   └─ Alert if source is down (Slack notification)
   └─ Handle API failures gracefully (cache older data)

3. RAW STORAGE (PostgreSQL):
   └─ stock_ohlcv: (symbol, timestamp, open, high, low, close, volume)
   └─ news_articles: (symbol, title, sentiment_score, source, date)
   └─ macro_indicators: (indicator_name, value, date)
   └─ social_sentiment: (symbol, mentions, sentiment, source, date)

4. FEATURE ENGINEERING (Pandas DataFrames):
   └─ Calculate technical indicators (RSI, MACD, Bollinger Bands)
   └─ Lag features (yesterday's return, 5-day volatility)
   └─ Temporal features (day-of-week, is-earnings-day)
   └─ Sentiment aggregations (7-day rolling average)
   └─ Store in separate feature_engineered_data table

5. MODEL TRAINING (Scheduled nightly at 10 PM ET):
   └─ Load last 5 years of features
   └─ Train 4 models per stock
   └─ Validate on recent 3 months (walk-forward)
   └─ Save best model to S3
   └─ Update model_registry table (symbol, model_id, performance)

6. INFERENCE (Real-time, on every API request for dashboard):
   └─ Load trained model from S3 cache
   └─ Get latest 100 bars of features
   └─ Run inference (< 100 ms per prediction)
   └─ Cache result in Redis for 15 minutes
   └─ Return to frontend
```

---

## 🤖 SECTION 4: ML MODEL SPECIFICATIONS (DETAILED)

### 4.1 Overview

For each stock, for each timeframe (1h, 4h, 1d, 1w, 1m), we train 4 competing models. Winner is selected by Sharpe ratio on validation set. Consensus across 5 timeframes feeds into GAS.

### 4.2 Model Specifications

#### Model 1: LSTM with Attention
```
Architecture:
- Input: 100 timesteps × 25 features
- Embedding layer (if categorical features)
- LSTM layer 1: 64 units, 30% dropout
- LSTM layer 2: 32 units, 30% dropout
- Attention layer: (Dense(25), Softmax over timesteps)
- Dense layer: 16 units, ReLU
- Output layer: 3 units (Up/Neutral/Down), Softmax

Training:
- Optimizer: Adam (learning rate 0.001)
- Loss: Categorical Crossentropy
- Batch size: 32
- Epochs: 50
- Early stopping: Patience 5 (if validation loss doesn't improve)
- Dropout: 30% (prevent overfitting)

Pros: Captures long-term dependencies, learns attention patterns
Cons: Black box (hard to interpret), requires more data (5+ years)
```

#### Model 2: XGBoost
```
Parameters:
- Learning rate: 0.05
- n_estimators: 300
- max_depth: 6
- min_child_weight: 1
- subsample: 0.8
- colsample_bytree: 0.8
- objective: multi:softprob (multi-class classification)

Feature importance ranking automatically generated.

Training:
- Train/val split: 80/20 time-series aware (no shuffling)
- Watchlist: Monitor validation accuracy
- Early stopping: 20 rounds (if val accuracy doesn't improve)

Pros: Interpretable (feature importance), fast, robust to outliers
Cons: Shallow learning, may miss complex patterns
```

#### Model 3: Linear Regression (Baseline)
```
Simple logistic regression for comparison.
- Baseline: If technical signals agree, default to majority direction
- If logistic regression outperforms LSTM/XGBoost → model is overfit, revert to simple approach
```

#### Model 4: Prophet (Time-Series Decomposition)
```
Facebook's prophet: Decompose series into trend + seasonality + residuals.
- Growth: Linear
- Yearly seasonality: Enabled
- Weekly seasonality: Enabled
- Interval width: 0.80 (80% prediction interval)

Good for: Capturing seasonal patterns (e.g., December holiday buying)
Cons: Assumes repeating patterns, misses regime changes
```

### 4.3 Features (Full List)

#### Technical Features (11 features)
```python
close_returns = (close - open) / open
volatility_20 = std(close_returns, window=20)
rsi_14 = RSI(close, window=14)
macd = MACD(close, fast=12, slow=26, signal=9)
bb_upper, bb_lower = BollingerBands(close, window=20, std=2)
bb_position = (close - bb_lower) / (bb_upper - bb_lower)
sma_20 = SimpleMovingAverage(close, window=20)
sma_50 = SimpleMovingAverage(close, window=50)
price_to_sma20 = close / sma_20
price_to_sma50 = close / sma_50
momentum_10 = close / close[10 periods ago]
```

#### Sentiment Features (3 features)
```python
news_sentiment_1d = mean(sentiment_scores, window=1)
news_sentiment_7d = mean(sentiment_scores, window=7)
news_sentiment_30d = mean(sentiment_scores, window=30)
# Each score from -1 (very bearish) to +1 (very bullish)
```

#### Macro Features (6 features)
```python
fed_rate_level = current Federal Funds rate (%)
fed_rate_trend = (current - 1mo ago) / 1mo ago
treasury_2_10 = yield_10y - yield_2y (basis points)
vix_level = current VIX closing price
vix_20day_ma = 20-day moving average of VIX
inflation_latest = latest CPI YoY (%)
```

#### Temporal Features (5 features)
```python
day_of_week = [0-4] encoded
month = [0-11] encoded
quarter = [0-3] encoded
is_earnings_day = boolean (1 if day of earnings announcement, else 0)
days_to_major_event = days until FOMC, NFP, CPI release (or 999 if none)
```

**Total: 25 features**

### 4.4 Training & Validation

#### Data Splits
```
Historical period: 2019-01-01 to present (5+ years)

Train: 2019-2022 (3 years)
Validation: 2023-06 to 2023-12 (6 months)
Test: 2024-01 to now (forward-looking, live trades)

Walk-forward retraining:
- Retrain every month
- Slide window 1 month forward
- Keep 3 years of training, 6 months validation
```

#### Evaluation Metrics
```
Primary metric: Sharpe Ratio
├─ Why: Rewards risk-adjusted returns
├─ Formula: mean(returns) / std(returns)
├─ Target: > 1.0 (excellent), > 0.5 (good)

Secondary metrics:
├─ Accuracy: % of correct directional predictions (target > 55%)
├─ Precision: Of bullish predictions, % correct (target > 52%)
├─ Recall: Of actual bullish days, % caught (target > 50%)
├─ F1-score: Harmonic mean of precision + recall
├─ Drawdown: Worst peak-to-trough loss (target < 15%)

Forward evaluation (live testing):
├─ Track actual model predictions vs realized moves
├─ Compare backtest Sharpe to forward Sharpe monthly
├─ If forward Sharpe < 50% of backtest Sharpe → retrain or alert
```

### 4.5 Model Drift Detection

```
Monitor for degradation (overfitting in backtests):

1. ACCURACY DRIFT
   ├─ Metric: Actual directional accuracy this month
   ├─ Compare to: Historical backtest accuracy
   ├─ Threshold: If < 50% of backtest, flag for retraining
   └─ Action: Reduce model confidence (GAS weight)

2. VOLATILITY SPIKE DETECTION
   ├─ Metric: Is current volatility regime (VIX) outside training range?
   ├─ Threshold: If VIX > 95th percentile of training data, alert
   └─ Action: Increase model uncertainty band, flag conflict warnings

3. CORRELATION BREAKDOWN
   ├─ Metric: Are feature correlations changing?
   ├─ Check: Are technical indicators still working?
   ├─ Action: Downweight technical features if uncorrelated to returns

4. NEWS SENTIMENT EFFECTIVENESS
   ├─ Metric: Does news sentiment still predict moves?
   ├─ Threshold: If rolling correlation < 0.1, reduce sentiment weight
   └─ Action: Increase macro layer weight instead
```

### 4.6 Ensemble Method (5-Timeframe Consensus)

```
Per stock, we have:
- 1h model: Buy/Neutral/Sell score
- 4h model: Buy/Neutral/Sell score
- 1d model: Buy/Neutral/Sell score
- 1w model: Buy/Neutral/Sell score
- 1m model: Buy/Neutral/Sell score

Consensus calculation:

Step 1: Convert each model to numerical score
├─ Sell = -1
├─ Neutral = 0
├─ Buy = +1

Step 2: Weight by confidence (Sharpe ratio on validation)
├─ If 1h Sharpe = 1.2, weight = 1.2
├─ If 4h Sharpe = 0.8, weight = 0.8
├─ Normalize weights to sum to 1

Step 3: Calculate weighted average
├─ consensus = Σ(score_i × weight_i)
├─ Result ranges from -1 (all bearish) to +1 (all bullish)

Step 4: Map to 0-100 scale
├─ Technical_confidence = 50 + (consensus × 50)
├─ So -1 → 0%, 0 → 50%, +1 → 100%

Step 5: Count agreement
├─ n_agree = # models with same signal
├─ agreement_% = n_agree / 5 × 100
├─ If < 40% agree → "Mixed signals" warning
```

---

## 👥 SECTION 5: USER PERSONAS (DETAILED)

### Persona 1: Emma - Finance Student

**Demographics:**
- Age: 23
- Location: EU (Germany, France, Spain)
- Education: Economics/Finance student
- Technical skill: Medium (comfortable with Excel, Python basics)
- Income: Limited (~€500/month from part-time job)

**Motivations:**
- Wants to understand how markets work before trading real money
- Reads news about Fed, IMF, but doesn't connect to stock prices
- Wants structured learning, not random YouTube videos
- Fears making emotional mistakes (FOMO buying)

**Pain Points:**
- Overwhelmed by data (10 charting apps, which to use?)
- Can't tell signal from noise (is this news bullish or bearish?)
- Doesn't understand macro's impact (Why does Fed matter?)
- Backtesting sounds important but too technical

**Behavior:**
- Visits app weekly (30 mins per session)
- Reads blog posts (60% of app usage)
- Backtests her ideas (20% of usage)
- Checks sentiment for fun stocks (20% of usage)

**Conversion Path:**
- Day 1: Reads blog post "Why the Fed Matters for Apple Stock"
- Day 3: Clicks through to app, explores dashboard
- Week 2: Sets up watchlist, reads 3 blog posts
- Week 4: Subscribes after seeing free tier limitations
- **Willingness to pay:** YES, €14.99/mo for structured learning

**Key Feature Preferences:**
1. Blog/Learn tab (most important)
2. Market Weather System (easy to understand GAS)
3. Conflict Detector (teaches how layers interact)
4. Backtesting (validates her ideas)
5. NOT interested in: Options chains, advanced risk models

**Messaging Angle:** "Master market fundamentals like a portfolio manager"

---

### Persona 2: Marco - Retail Trader

**Demographics:**
- Age: 35
- Location: EU (Italy)
- Job: Software engineer (solid income €3k+/mo)
- Technical skill: High (Python, SQL)
- Trading experience: 3 years (mostly tech stocks)

**Motivations:**
- Wants to beat his buy-and-hold returns
- Trades on emotion, wants discipline
- Reads macroeconomic analysis but doesn't trade it
- Wants a toolkit to test ideas quickly

**Pain Points:**
- Backtest results often disappoint in live trading (overfitting)
- Misses regime shifts (bullish in 2022 into bear market)
- Trades impulsively when news hits
- No systematic approach to hedging

**Behavior:**
- Visits app daily (1-2 hours on weekends)
- Backtests 2-3 strategies per week
- Checks macro dashboard before market open
- Manually trades 10-15 times per month

**Conversion Path:**
- Day 1: Finds app via Reddit r/stocks thread
- Day 3: Backtests his momentum strategy, sees realistic results
- Week 1: Compares his live trades to model predictions
- Week 4: Wants to integrate macro layer (macro API access)
- Week 8: Subscribes for advanced hedging simulator
- **Willingness to pay:** YES, €14.99/mo for backtesting + signals

**Key Feature Preferences:**
1. Backtesting (most important)
2. ML predictions (wants edge)
3. Macro dashboard (wants discipline)
4. Hedging simulator (risk management)
5. API access (future: integrate with trading bot)

**Messaging Angle:** "Trade with macro conviction, test with walk-forward backtests"

---

### Persona 3: Alex - Institutional Analyst

**Demographics:**
- Age: 42
- Role: Portfolio manager (€50M AUM)
- Location: London
- Technical skill: Very high (Bloomberg terminal, proprietary tools)
- Background: 15+ years in finance

**Motivations:**
- Wants retail sentiment layer (not available in Bloomberg)
- Wants to monitor regime shifts across 20+ positions
- Needs to educate team on macro + sentiment integration
- Wants white-label version for client reporting

**Pain Points:**
- Bloomberg is expensive (€25k+/year)
- No retail sentiment integration
- Building sentiment indices requires hiring quants
- No easy way to explain models to clients

**Behavior:**
- Visits app daily (portfolio review, 30 mins)
- Creates custom reports monthly
- Backtests new strategies quarterly
- Wants API access for integration

**Conversion Path:**
- Month 1: Team member finds app, brings to Alex
- Month 2: Evaluates GAS vs proprietary models
- Month 3: Requests white-label version + API SLA
- Month 6: Integrates with portfolio monitoring system
- **Willingness to pay:** YES, €5k+/month for white-label + API

**Key Feature Preferences:**
1. White-label API (most important)
2. Portfolio view (20+ stocks)
3. Macro + retail sentiment (differentiation)
4. Bulk analysis (50+ stocks in one report)
5. Custom reporting (PDF export, client-ready)

**Messaging Angle:** "Institutional macro intelligence + retail sentiment for retail asset managers"

---

### Onboarding Flows Per Persona

#### Emma's Onboarding (5 steps, 10 mins)
```
1. Email signup → email confirmation
2. "What's your goal?" → Select "Learn trading fundamentals"
3. Dashboard tour (GAS explanation, Market Weather System)
4. Blog recommendation: "Macro 101 - Fed Fundamentals"
5. Prompt: "Join community to get weekly market insights" → Email list signup
```

#### Marco's Onboarding (5 steps, 15 mins)
```
1. Email signup → email confirmation
2. "What's your goal?" → Select "Improve trade timing"
3. Dashboard tour (Backtesting tab, GAS confidence)
4. Sample: Run his existing strategy in backtester
5. Prompt: "Upgrade to Pro for macro indicators + simulator" → Payment modal
```

#### Alex's Onboarding (3 steps, 5 mins + Sales call)
```
1. Email signup (LinkedIn import optional)
2. "What's your goal?" → Select "Institutional analysis"
3. Show: White-label demo + API docs
4. Trigger: Sales team contacts Alex within 24h
```

---

## 📈 SECTION 6: KEY PERFORMANCE INDICATORS (KPI TARGETS)

### 6.1 User Acquisition Metrics

| KPI | Target Month 1-3 | Target Month 3-6 | Target Month 6-12 |
|-----|-----------------|-----------------|-----------------|
| Free user signups | 50 | 300 | 1500 |
| Weekly active users (WAU) | 30 | 150 | 800 |
| Monthly active users (MAU) | 40 | 200 | 1000 |
| Paid subscriptions | 5 | 50 | 200+ |

**Rationale:** 
- Free-to-paid conversion: 2-5% (financial SaaS benchmark)
- If 500 free users by month 3, expect 10-25 paying
- Target 1000 paying users (€15k/month revenue) by month 12

### 6.2 Product Quality Metrics

| KPI | Target |
|-----|--------|
| Model accuracy (directional) | > 55% |
| Sharpe ratio (backtest) | > 0.8 |
| Sharpe ratio (forward/live) | > 50% of backtest |
| System uptime | 99.5% |
| API response time (p95) | < 500ms |
| GAS update latency | < 30s after market data |
| Model drift detection accuracy | > 90% (catch overfitting) |
| False positive alerts | < 5% of all conflict warnings |

**Monitoring:** 
- Daily: Backtest vs live model performance
- Weekly: Accuracy tracking, drift detection
- Monthly: Sharpe ratio trend analysis

### 6.3 User Engagement Metrics

| KPI | Target |
|-----|--------|
| Session duration | > 15 mins/session |
| Daily active user % (of MAU) | > 20% |
| Feature adoption (backtesting) | > 60% of free users |
| Feature adoption (macro dashboard) | > 40% of Pro users |
| Blog post readership | 200 readers/post/week |
| Time on blog | > 3 mins/post |
| Newsletter signup | > 30% of free users |

### 6.4 Monetization Metrics

| KPI | Target |
|-----|--------|
| Free-to-paid conversion rate | 2-5% |
| Monthly subscription churn rate | < 5% |
| ARPU (Average Revenue Per User) | €14.99 (base) |
| LTV (Lifetime Value) | €89.94 (6 month retention) |
| CAC (Customer Acquisition Cost) | < €5 (via organic) |
| LTV:CAC ratio | > 15:1 (healthy) |
| Annual plan adoption | > 20% (if offered) |

**Targets:**
- Month 3: 50 paying users × €14.99 = €749/month
- Month 6: 100 paying users × €14.99 = €1,499/month
- Month 12: 200 paying users × €14.99 = €2,998/month

**Note:** At €15k/month goal (1000 users), need to focus on community expansion, content marketing.

### 6.5 Content & Community Metrics

| KPI | Target |
|-----|--------|
| Blog posts published | 2/week |
| Blog traffic | 1000 visitors/week (month 6) |
| Email subscriber growth | +10/week |
| Reddit mentions (organic) | 5-10/month (month 6) |
| Twitter followers | 500 by month 6 |
| YouTube subscribers (if started) | 100 by month 6 |
| NPS (Net Promoter Score) | > 40 (good for SaaS) |
| Customer support response time | < 24h |

### 6.6 Technical Metrics (Infrastructure)

| KPI | Target |
|-----|--------|
| Database query latency (p95) | < 100ms |
| Cache hit rate (Redis) | > 80% |
| ML inference time | < 500ms per prediction |
| Data freshness | < 15 mins for OHLCV |
| Error rate | < 0.1% of requests |
| Cost per user (cloud) | < €1/month |

---

## 🗓️ SECTION 7: DETAILED ROADMAP & TIMELINE

### Phase 1: MVP Development (Weeks 1-12, ~3 months)

#### Sprint 1: Foundation (Weeks 1-4)
```
GOAL: Backend API + single stock technical analysis

TASKS:
Backend Infrastructure:
  □ Set up FastAPI project structure
  □ PostgreSQL + TimescaleDB setup (local + AWS RDS)
  □ Redis setup (caching)
  □ Docker & docker-compose for dev environment
  □ GitHub repo + CI/CD pipeline (GitHub Actions)

Data Pipelines:
  □ Fetch OHLCV data (Yahoo Finance API)
  □ Store in TimescaleDB (1-min, 5-min, 1h, 4h, 1d candles)
  □ Fetch FRED macro data (Fed rates, CPI, unemployment)
  □ Cache macro data in Redis (daily updates)
  □ Data validation & error handling

Technical ML (1 model, 1 timeframe):
  □ Feature engineering pipeline (25 features as defined)
  □ XGBoost model training (start simple)
  □ Model validation (walk-forward backtest)
  □ Model serving API endpoint
  □ Test on 10 stocks (AAPL, MSFT, TSLA, etc.)

Frontend:
  □ Next.js project setup
  □ Basic layout (header, sidebar, main content)
  □ Stock ticker selector dropdown
  □ Dashboard shell (ready for data binding)

Deliverables:
  ✅ FastAPI running with /predict endpoint
  ✅ XGBoost model achieving > 55% accuracy on 1d data
  ✅ TimescaleDB storing 1 year of OHLCV per stock
  ✅ Frontend responsive shell (no data yet)

TEAM: 1 backend engineer (Python) + 1 frontend engineer (React)
RISKS: FRED API rate limits, model accuracy < 55% → pivot to feature engineering
```

#### Sprint 2: Multi-Timeframe Consensus (Weeks 5-8)
```
GOAL: All 5 timeframes + ensemble consensus + basic GAS

TASKS:
ML Expansion:
  □ Train 4 models per timeframe (LSTM, XGBoost, Linear, Prophet)
  □ Model selection by Sharpe ratio
  □ Ensemble: Calculate 5-timeframe consensus
  □ Implement model drift detection
  □ Backtest on 2019-2024 data (walk-forward)

GAS Calculation:
  □ Technical confidence layer (from ensemble)
  □ Sentiment layer (basic: news only, coming)
  □ Macro layer (FRED + VIX)
  □ Volatility regime (VIX-based)
  □ Synthesize into 0-100 GAS score
  □ Market Weather System mapping (☀️ to 🌪)

Frontend:
  □ Connect dashboard to /predict endpoint
  □ Display GAS score (big, center)
  □ Display Market Weather visual
  □ Display timeframe signals (1h, 4h, 1d, 1w, 1m)
  □ Real-time update (WebSocket) every 15 mins
  □ Basic styling (Tailwind)

Backtesting UI:
  □ Backtesting tab structure
  □ Momentum strategy template
  □ Display backtest results (Sharpe, drawdown, win rate)
  □ Parameter input (users adjust thresholds)

Deliverables:
  ✅ GAS score live on dashboard (updating every 15 mins)
  ✅ Market Weather System visual (e.g., "🌤 Mild Support")
  ✅ Backtesting tab functional (basic momentum strategy)
  ✅ Model comparison (LSTM vs XGBoost Sharpe displayed)

TEAM: +1 ML engineer (for all 4 models + ensemble)
RISKS: LSTM training slow, need GPU → use smaller hidden states or AWS SageMaker
```

#### Sprint 3: Sentiment + Educational Content (Weeks 9-12)
```
GOAL: News sentiment + basic macro + blog/learn content

TASKS:
Sentiment Layer:
  □ Finnhub News API integration
  □ FinBERT model setup (HuggingFace)
  □ Batch sentiment scoring (nightly, Celery task)
  □ Aggregate sentiment (1d, 7d, 30d)
  □ Sentiment layer in GAS calculation

Macro Layer Expansion:
  □ FRED API integration (10+ indicators)
  □ Treasury yield curve tracking
  □ Recession probability meter
  □ Macro stress index calculation

Frontend Tabs:
  □ News Sentiment tab (articles + sentiment scores)
  □ Macro Dashboard tab (indicators + interpretation)
  □ Hedging Simulator tab (basic: stock + put)
  □ Learn/Blog tab (CMS integration, static content)

Educational Content:
  □ Write 6 blog posts (Macro 101, GAS explained, Backtesting pitfalls, etc.)
  □ Risk disclaimers on every page
  □ Glossary (define 10 terms)
  □ User onboarding tour

Compliance:
  □ Legal review: financial advice disclaimers
  □ GDPR compliance (privacy policy, cookie consent)
  □ Terms of Service

Deliverables:
  ✅ News Sentiment tab live with FinBERT scores
  ✅ Macro Dashboard with 10+ FRED indicators
  ✅ Blog/Learn tab with 6 posts
  ✅ Hedging Simulator (stock + single put)
  ✅ Legal pages (disclaimer, ToS, privacy policy)
  ✅ MVP ready for beta launch

TEAM: +1 content writer/marketer + 1 legal review (external consultant)
RISKS: FinBERT latency → batch processing only, not real-time
```

---

### Phase 2: Beta Launch & Growth (Weeks 13-24, ~3 months)

```
WEEKS 13-16: BETA LAUNCH

Tasks:
  □ Set up payment processor (Stripe)
  □ User auth & subscription management
  □ Email onboarding sequence (5 emails)
  □ Analytics setup (Mixpanel or Plausible)
  □ Monitoring (Prometheus, Grafana, Sentry)
  □ Invite 50 finance students (via universities, Reddit)
  □ Monitor support tickets (Slack #support channel)

Success Metrics:
  - 50 beta users signed up by week 16
  - < 2 support tickets/day average
  - NPS > 30 from beta feedback

WEEKS 17-20: REDDIT + TWITTER LAUNCH

Tasks:
  □ Post on r/stocks, r/investing, r/wallstreetbets (organic)
  □ Share blog posts (2x/week)
  □ Launch Twitter account, post daily market updates
  □ Respond to comments in real-time
  □ Collect testimonials (user success stories)

WEEKS 21-24: PUBLIC LAUNCH

Tasks:
  □ Fix beta bugs (based on 50 users)
  □ Open registration (freemium model)
  □ Launch landing page (SEO-friendly)
  □ Email announcement to subscribers
  □ Paid marketing test (Google Ads budget = €500)
  □ Target: 500 free users, 50 paid by end of week 24

TEAM: +1 growth marketer + 1 customer support person (part-time)

Deliverables:
  ✅ Payment system live (Stripe integrated)
  ✅ 50 beta users → 10 paying by week 20
  ✅ Public launch with 500+ free signups
  ✅ Blog posts library (12 posts)
  ✅ Customer testimonials/case studies
```

---

### Phase 3: Scaling & Monetization (Months 6-12)

```
MONTHS 6-9: FEATURE EXPANSION

Tasks (Phase 2 features):
  □ Portfolio management (track 10 stocks)
  □ Reddit sentiment integration (PRAW API)
  □ Political event tracking (GDELT)
  □ Advanced hedging (multi-leg strategies)
  □ Strategy library + community sharing
  □ Mobile app (React Native)

Growth:
  □ 500 free users → 1000+ free users
  □ 50 paying → 150 paying
  □ Content marketing (2 posts/week, video series)

MONTHS 9-12: MONETIZATION + COMMUNITY

Tasks:
  □ White-label version (for 1-2 brokers)
  □ API tier (for prop traders)
  □ Community features (Discord, leaderboards)
  □ Email nurturing sequences (reduce churn)
  □ Retention improvements (feature requests from users)

Growth:
  □ 1000+ free users, 200+ paying
  □ €2,998/month revenue target
  □ NPS > 40

TARGET BY END OF MONTH 12:
  ✅ 1000+ free users
  ✅ 200+ paying users (€3k/month)
  ✅ 50 active blog post readers/week
  ✅ 2-3 white-label partnerships
  ✅ 0.5% daily active users (engaged core)
  ✅ < 5% monthly churn
```

---

## 🛡️ SECTION 8: LEGAL & COMPLIANCE (COMPREHENSIVE)

### 8.1 Regulatory Landscape by Region

#### EU (Primary Market)
```
REGULATION: MiFID II (Markets in Financial Instruments Directive)
├─ Applies if: Provide "investment advice" or "investment services"
├─ Fin-Eye positioning: Educational analytics platform (NOT advice)
├─ Key distinction:
│   ├─ BANNED: "Buy Tesla at €250, sell at €300"
│   ├─ ALLOWED: "Macro alignment bullish, model consensus +70%"
├─ Compliance steps:
│   ├─ Clear disclaimer on every page
│   ├─ Explain model limitations (backtesting != reality)
│   ├─ No guaranteed return promises
│   ├─ Advise users to consult licensed advisor for real advice

REGULATION: GDPR (General Data Protection Regulation)
├─ Applies to: Any EU user data
├─ Key requirements:
│   ├─ Privacy Policy (what data collected, how used, retention)
│   ├─ Cookie consent (if using analytics cookies)
│   ├─ Data Subject Rights (user can request deletion)
│   ├─ Data Processing Agreement (if using cloud providers)
│   ├─ Data breach notification (within 72h if compromised)
├─ Fin-Eye data types:
│   ├─ Email, password hash (minimal personal data)
│   ├─ Trading activity logs (if user shares strategies)
│   ├─ IP address (from analytics)
│   ├─ Stripe payment data (handled by Stripe, not stored locally)

REGULATION: PSD2 (Payment Services Directive)
├─ If: Accept payments (which Fin-Eye does)
├─ Use Stripe (handles compliance for you)

ACTION ITEMS:
  □ Consult EU law firm (€2k-5k) for MiFID II review
  □ Draft Privacy Policy (use template, customize)
  □ Draft Terms of Service (use template, customize)
  □ Implement cookie consent banner
  □ Document data processing (for DPA)
```

#### UK (Secondary Market)
```
REGULATION: FCA (Financial Conduct Authority)
├─ Applies if: Provide "regulated activities"
├─ Fin-Eye positioning: Communication/marketing about investments
├─ If avoiding direct advice, likely NOT FCA-regulated
├─ But: Recommend legal review (FCA guidance is evolving)

ACTION ITEMS:
  □ FCA review (£2k-5k, UK solicitor)
  □ If NOT regulated: Add "Not FCA regulated" disclaimer
  □ If regulated: Complex, may require capital, insurance, etc.

GDPR STILL APPLIES (until UK framework changes)
```

#### US (Tertiary Market)
```
REGULATION: SEC (Securities and Exchange Commission)
├─ Applies if: Provide "securities advice" or operate as "investment adviser"
├─ Fin-Eye positioning: Educational analytics (NOT advice)
├─ Safe harbor: If clear disclaimers ("not investment advice")
├─ Rule 206 safe harbor applies if:
│   ├─ Communication not advice (Fin-Eye: ✅)
│   ├─ Educational purpose (Fin-Eye: ✅)
│   ├─ No direct recommendations ("Buy AAPL") (Fin-Eye: ✅)

ACTION ITEMS:
  □ SEC legal review (€5k+) - USA-based attorney
  □ Include "Not investment advice" disclaimer
  □ Avoid specific buy/sell recommendations
```

### 8.2 Risk Disclaimers (Template)

```
DISCLAIMER (Place on every page, homepage & blog):

⚠️ IMPORTANT DISCLAIMER ⚠️

Fin-Eye provides educational analytics and market intelligence tools. 
We are NOT a licensed investment adviser. Nothing on Fin-Eye constitutes 
investment advice, a recommendation, or an offer to buy or sell any security.

RISKS YOU MUST UNDERSTAND:

1. MODEL LIMITATIONS
   └─ Our ML models are trained on historical data. Past performance 
      does NOT guarantee future results. Markets change, and our models 
      may fail in new regimes.

2. BACKTESTING BIAS
   └─ Backtested results often don't match live trading because:
      ├─ No slippage/commission in reality worse than assumed
      ├─ You may not execute perfectly at backtested prices
      ├─ Overfitting: Models "memorized" historical patterns
      ├─ Survivor bias: Backtests assume perfect hindsight

3. PAST PERFORMANCE
   └─ Backtests showing 20% annual returns should be viewed with skepticism.
      Real trading has friction, emotions, and surprises.

4. MARKET RISK
   └─ Trading stocks carries risk of total loss. Only invest money you 
      can afford to lose entirely.

5. SENTIMENT ANALYSIS
   └─ NLP sentiment may misinterpret news. Sarcasm, context, and nuance 
      can be misclassified by AI models.

6. MACRO DATA DELAYS
   └─ Some indicators (unemployment, CPI) are released monthly with lags.
      By the time data is public, markets already reacted.

USER RESPONSIBILITIES:

- Always consult a licensed financial adviser before making trades
- Never risk capital on Fin-Eye signals alone
- Understand the models (read our explanations)
- Test ideas in paper trading first
- Manage your position size and stops
- Don't trade with borrowed money (margin) unless you understand leverage risks

NEITHER FIN-EYE NOR ITS CREATORS ARE LIABLE FOR:
- Trading losses or poor decisions
- Unreliability of third-party data (news, economic data, sentiment)
- Technical issues, downtime, or data errors
- Regulatory changes or market circuit breakers

YOU USE FIN-EYE AT YOUR OWN RISK.

By using Fin-Eye, you agree to these terms and assume all trading risks.
```

### 8.3 Terms of Service (Summary)

```
KEY SECTIONS:

1. USE RIGHTS
   └─ Non-commercial use only (no selling Fin-Eye data/signals)
   └─ Educational use is permitted
   └─ No API scraping or automated access

2. LIABILITY
   └─ Fin-Eye is provided "as-is" without warranty
   └─ Limitation of liability: Fin-Eye not liable for trading losses
   └─ Indemnification: User indemnifies Fin-Eye for lawsuits from users

3. INTELLECTUAL PROPERTY
   └─ Fin-Eye models, content, design are proprietary
   └─ Users get non-exclusive license to use (no copying)

4. PAYMENT TERMS
   └─ Pro tier: €14.99/month, auto-renews
   └─ Cancellation: 1-click in settings, no lock-in
   └─ Stripe handles billing/payments

5. DATA & PRIVACY
   └─ Refer to Privacy Policy
   └─ No selling user data to third parties
   └─ User data deleted 30 days after cancellation (GDPR retention)

6. TERMINATION
   └─ Fin-Eye can terminate account for ToS violations
   └─ User can cancel anytime

7. GOVERNING LAW
   └─ If EU: Governed by Irish law (neutral EU jurisdiction)
   └─ If US: Choose state (Delaware common for SaaS)
   └─ Dispute resolution: Arbitration (faster, cheaper than court)
```

### 8.4 Compliance Checklist

```
BEFORE LAUNCH:

Legal:
  ☐ Privacy Policy (drafted & reviewed by EU lawyer)
  ☐ Terms of Service (drafted & reviewed by lawyer)
  ☐ Risk Disclaimers (on every page)
  ☐ Cookies consent banner (if using analytics)
  ☐ Newsletter consent (double opt-in)
  ☐ DPA with cloud providers (AWS, Stripe)
  ☐ GDPR Data Processing Addendum

Financial Regulatory:
  ☐ MiFID II review (EU lawyer) - ensure not offering advice
  ☐ FCA review (UK lawyer) - if UK users
  ☐ SEC review (US lawyer) - if US users > 1000
  ☐ "Not investment advice" disclaimer
  ☐ Clear model limitations explanation

Data Security:
  ☐ HTTPS only (SSL certificate)
  ☐ Password hashing (bcrypt, not plaintext)
  ☐ 2FA option for accounts
  ☐ Data encryption at rest (AWS KMS)
  ☐ Regular security audits (quarterly)
  ☐ GDPR breach response plan

Payment:
  ☐ Stripe fully PSD2 compliant (handles for you)
  ☐ Refund policy (e.g., 30-day money-back)
  ☐ Invoice generation (for users)
  ☐ Tax compliance (collect VAT for EU users)

Ongoing:
  ☐ Annual legal review (regulations evolve)
  ☐ Monitor user complaints (keep records)
  ☐ Respond to data subject requests (GDPR)
  ☐ Update ToS/Privacy policy as features change
```

---

## ⚠️ SECTION 9: COMPREHENSIVE RISK ASSESSMENT

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **ML Model Degradation** | High | High | Monthly validation, drift detection, downweight poor models |
| **API Rate Limits** | High | Medium | Caching layer, paid data tiers, fallback to cached data |
| **Real-time Latency** | Medium | Medium | Batch processing for sentiment, cache GAS for 15 min |
| **Database Scaling** | Medium | High | TimescaleDB, sharding by stock, compression |
| **Data Quality Issues** | Medium | Medium | Validators, alerts on missing data, manual review |
| **Model Overfitting** | High | High | Walk-forward validation, test on out-of-sample, track live vs backtest |
| **LSTM Training Failures** | Medium | Medium | Use GPU, smaller models, fallback to XGBoost |
| **Redis Cache Failure** | Low | Low | Fallback to database, multi-region Redis |
| **News API Downtime** | Medium | Low | Cache older articles, graceful degradation |

### 9.2 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **User Lawsuit** | High | Critical | Clear disclaimers, educational framing, liability insurance |
| **Regulatory Crackdown** | Medium | Critical | Conservative messaging, legal review pre-launch, compliance team |
| **Competitor Launch** | High | Medium | Brand, content moat, community, early users |
| **Model Underperformance** | High | High | Transparency, education focus (not prediction hype), manage expectations |
| **User Churn (Bear Market)** | High | High | Content education, explain model uncertainty, build community |
| **Poor Onboarding** | High | Medium | A/B test onboarding flows, measure activation, iterate |
| **CAC > LTV** | High | High | Focus on free signups, content marketing, viral loops |
| **Team Turnover** | Medium | High | Document code, knowledge sharing, good compensation |
| **Macro Data Inaccuracy** | Low | Medium | Credit FRED/sources, acknowledge lags, manual review |

### 9.3 Market Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **Market Regime Shift** | Medium | High | Retrain models monthly, detect regime changes |
| **Volatility Spike** | High | High | Model drift detection, conflict warnings, educate users |
| **New Regulations** | Medium | High | Legal monitoring, compliance team, agile response |
| **Data Licensing Changes** | Low | Medium | Diversify data sources, build relationships with providers |

### 9.4 Risk Mitigation Strategy

```
INSURANCE:
  □ Professional liability insurance (€50k-100k coverage)
  □ Cyber liability insurance (data breach, ransomware)

LEGAL:
  □ Solid ToS + disclaimers (main defense)
  □ Annual legal reviews (regulations evolve)
  □ Lawyer on retainer (quick response to issues)

OPERATIONAL:
  □ Bug bounty program (responsible disclosure)
  □ Regular security audits (quarterly)
  □ Data backups (daily, 30-day retention)
  □ Disaster recovery plan (RTO < 4 hours)

PRODUCT:
  □ Model monitoring dashboard (daily checks)
  □ User feedback loop (collect & respond to concerns)
  □ Transparent communication (explain limitations)
  □ Community governance (users help moderate)
```

---

## 🔌 SECTION 10: API INTEGRATION CHECKLIST (DETAILED)

### 10.1 Market Data APIs

| API | Purpose | Tier | Cost | Implementation |
|-----|---------|------|------|-----------------|
| **Yahoo Finance** | OHLCV data | Free | €0 | yfinance Python library |
| **Finnhub** | News + financial data | Free (60/min) | €0-300/mo | REST API + Python wrapper |
| **Twelve Data** | Alternative OHLCV | Free (500/day) | €0-100/mo | REST API |

**Recommendation:** Start with Yahoo Finance (free), add Finnhub for news, scale to Twelve Data if needed.

### 10.2 Economic Data APIs

| API | Purpose | Tier | Cost | Implementation |
|-----|---------|------|------|-----------------|
| **FRED** | Fed data | Free | €0 | REST API, no auth needed |
| **World Bank** | Development data | Free | €0 | REST API |
| **IMF** | Global economics | Free (exports) | €0 | Manual downloads or API |

**Recommendation:** FRED is gold. Pull daily (no rate limits). Cache for 1 day.

### 10.3 Sentiment & NLP APIs

| API | Purpose | Tier | Cost | Implementation |
|-----|---------|------|------|-----------------|
| **HuggingFace** | FinBERT model | Free | €0-50/mo (hosting) | transformers library, local inference |
| **Finnhub News** | News articles | Free (60/min) | Included in Finnhub | REST API |
| **PRAW** | Reddit API | Free | €0 | Python library |

**Recommendation:** Use HuggingFace transformers locally (batch processing). Don't call API per request.

### 10.4 Event/Political Data APIs

| API | Purpose | Tier | Cost | Implementation |
|-----|---------|------|------|-----------------|
| **GDELT** | Global events | Free | €0 | REST API or GCS downloads |
| **EventRegistry** | News events | Free (limited) | €0-1000/mo | REST API |

**Recommendation:** GDELT is free and comprehensive. Set up daily export.

### 10.5 User Management & Payments

| Service | Purpose | Tier | Cost | Implementation |
|---------|---------|------|------|-----------------|
| **Stripe** | Payments | Standard | 2.9% + €0.30/transaction | Stripe SDK (Python + JavaScript) |
| **Auth0** | User authentication | Free | €0-1000/mo | Auth0 library, OAuth 2.0 |
| **SendGrid** | Transactional email | Free | €0-100/mo | Email API (onboarding, alerts) |

**Recommendation:** Stripe for payments (most reliable). Auth0 for auth (built-in 2FA).

### 10.6 Integration Implementation Order

```
PHASE 1 (MVP):
  1. Yahoo Finance (OHLCV)
  2. Finnhub News API
  3. FRED API
  4. HuggingFace FinBERT (local)
  5. Stripe (payments)
  6. Auth0 (auth)

PHASE 2 (Growth):
  7. PRAW (Reddit)
  8. GDELT (political events)
  9. Twelve Data (backup OHLCV)
  10. SendGrid (email)

PHASE 3 (Premium):
  11. snscrape (Twitter)
  12. Google Trends API
  13. Options chain APIs (broker APIs)
  14. Custom integrations (user requests)
```

---

## 🎨 SECTION 11: UI/UX DETAILED FLOW

### 11.1 User Journey Map

```
EMMA (STUDENT) JOURNEY:

Day 1: Discovery
└─ Finds blog post "Why Fed Rate Hikes Matter" (via Google, Reddit)
└─ Reads 4-min article (learns basics)
└─ "Sign Up Free" button
└─ Email signup (no credit card needed)

Day 2: Onboarding
└─ Receives email: "Welcome to Fin-Eye! Start with the dashboard"
└─ Clicks link → Onboarding tour (2 mins)
│   ├─ "This is the Global Alignment Score (GAS)"
│   ├─ "Green means bullish, red means bearish"
│   └─ "Let's look at Apple"
└─ Dashboard shows AAPL with GAS = 68 (🌤 Mild Support)
└─ Explanation: "3 of 5 timeframes bullish + positive news + Fed rates stable"
└─ Prompt: "Want to learn more? Explore the Blog tab"

Week 1: Exploration
└─ Reads 3 blog posts (Macro 101, Backtesting 101, Conflict Detector)
└─ Explores different stocks (MSFT, TSLA, SPY)
└─ Shares blog post with friend (viral growth potential)
└─ Email 3: "You've explored 5 stocks! Here's a tip..." (re-engagement)

Week 2: Aha Moment
└─ Backtests simple momentum strategy
└─ Sees realistic results (Sharpe 0.6, drawdown -15%)
└─ "Oh, my strategy wouldn't have worked in 2022 bear market"
└─ Emails support: "I don't understand the conflict warning"
└─ Support responds < 2h with explanation

Week 3: Upgrade Consideration
└─ Free tier shows "delayed macro dashboard (24h lag)"
└─ Sees "Pro tab (€14.99/month)" button
└─ Modal: "Get real-time macro + more backtests"
└─ Signs up (first paying user from onboarding!)

MARCO (TRADER) JOURNEY:

Day 1: Discovery
└─ Reddit post: "Found a backtesting tool with ML signals + macro"
└─ Clicks link → lands on homepage
└─ "Try backtesting your strategy" CTA
└─ Signs up with email

Day 1-3: Activation
└─ Tries backtesting his momentum strategy
└─ Sees results (Sharpe, drawdown, win rate, live vs backtest)
└─ Realizes: "My live trading has 40% of backtest Sharpe = I'm overfitting!"
└─ "This is useful" → explores other features

Week 1: Engagement
└─ Checks macro dashboard (Fed rates, yield curve)
└─ Hedging simulator: "If I short ES index, I cut max drawdown from 25% to 10%"
└─ Trades 2 ideas (documents in app)

Week 2: Purchase
└─ Free tier limits (can't save > 3 strategies)
└─ Modal: "Unlock unlimited strategies, premium alerts"
└─ Converts to Pro (€14.99/mo)
└─ Sets up alerts (GAS cross above 60 = SMS alert)

ALEX (INSTITUTIONAL) JOURNEY:

Day 1: Introduction
└─ Team member: "Found a retail sentiment + macro dashboard"
└─ Shows Alex the product
└─ Alex: "Interesting, but can we white-label this?"

Day 2: Email
└─ Alex emails sales@fin-eye.com: "Interested in institutional solution"
└─ Sales team: "Perfect, let's set up a call"

Week 2: Sales Call
└─ Alex: "We want real-time GAS for 20 stocks + API access"
└─ Sales: "We can white-label + provide API SLA"
└─ Quote: €5k/month
└─ Contract signed, onboarded to API docs

Month 1: Integration
└─ Alex's team integrates GAS into portfolio monitoring
└─ Sees alerts when regime shifts
└─ Reduces improper trades (macro-aware positioning)
└─ ROI: Saved €50k by avoiding bad macro calls

```

### 11.2 Navigation & Information Architecture

```
HOME / DASHBOARD (Main Entry Point)

┌─────────────────────────────────────────────────────────────┐
│  HEADER: Fin-Eye | Stock Selector | User Menu | Login/Signup │
├─────────────────────────────────────────────────────────────┤
│                     LEFT SIDEBAR (Navigation)                 │
│                                                               │
│  🏠 Dashboard (home)                                         │
│  📊 Backtesting                                              │
│  📰 News & Sentiment                                          │
│  📈 Macro Dashboard                                           │
│  🛡 Hedging Simulator                                         │
│  📚 Learn / Blog                                              │
│  ⚙️  Settings                                                 │
│  👥 Community [Premium feature]                              │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                    MAIN CONTENT AREA                          │
│                                                               │
│  Dashboard Tab:                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         GLOBAL ALIGNMENT SCORE (CENTER, BIG)          │  │
│  │                  68 / 100                              │  │
│  │              🌤 MILD SUPPORT                           │  │
│  │                                                        │  │
│  │  Technical: 72% bullish | Sentiment: 65% bullish      │  │
│  │  Macro: 60% supportive  | Volatility: Low stress      │  │
│  │                                                        │  │
│  │  ⚠️  CONFLICT ALERT:                                    │  │
│  │  "Retail sentiment very high (88%) but macro          │  │
│  │   showing signs of cooling. Exhaustion risk."         │  │
│  │                                                        │  │
│  │  [Why Is This Stock Moving?]                          │  │
│  │  "Apple is up because short-term technicals are      │  │
│  │   bullish (RSI oversold bounce) + positive earnings   │  │
│  │   guidance. However, slowing iPhone sales in China    │  │
│  │   and Fed rate expectations (higher for longer) may   │  │
│  │   limit upside."                                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  TIMEFRAME SIGNALS                                    │  │
│  │  [1h: Buy] [4h: Buy] [1d: Neutral] [1w: Sell]         │  │
│  │  [1m: Sell] → Consensus: Neutral (2 agree bullish)    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  CHART (Lightweight Charts)                            │  │
│  │  [Candlesticks AAPL 1D] [5D MA 20] [RSI Overlay]      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  RIGHT SIDEBAR (Real-time Updates)                           │
│                                                               │
│  🔴 LIVE UPDATES (Last 15 mins)                              │
│                                                               │
│  📰 News:                                                    │
│    "Apple Q4 beat expectations" +0.75                        │
│    "iPhone demand concerns"     -0.60                        │
│                                                               │
│  📊 Macro:                                                   │
│    Fed Rate: 5.25% (no change)                               │
│    2-10yr spread: 15 bps (stable)                            │
│                                                               │
│  👥 Retail Sentiment:                                        │
│    Reddit mentions: ↑↑ (spike today)                         │
│    Sentiment: 78% bullish (overheating?)                     │
│                                                               │
│  🔔 Alerts:                                                  │
│    "GAS crossed above 60" ← Subscribe to alerts              │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Backtesting Tab:

┌─────────────────────────────────────────────────────────────┐
│  [New Strategy] [Load Strategy] [Compare Strategies]         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Strategy: Momentum (BUY if price > SMA20)                   │
│  [Adjust Parameters] [Run Backtest] [Share Scenario]         │
│                                                               │
│  Backtest Results (2019-2024):                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Total Return: 45% | Sharpe: 0.8 | Max DD: 20%        │  │
│  │ Win Rate: 58% | Avg Win/Loss: 1.2x                   │  │
│  │                                                        │  │
│  │ [Performance Chart]                                   │  │
│  │ [Drawdown Chart]                                      │  │
│  │ [Monthly Returns Heatmap]                             │  │
│  │                                                        │  │
│  │ ⚠️ Warning: This Sharpe is better than most. Check    │  │
│  │ if overfitted. Live trading usually gives 50% of      │  │
│  │ backtest Sharpe. Be conservative with position size.  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Live Performance vs Backtest:                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 2024 YTD: Backtest 12%, Live 6% → 50% degradation    │  │
│  │ This is normal but suggests overfitting.              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

News & Sentiment Tab:

┌─────────────────────────────────────────────────────────────┐
│  Last 30 Articles | Sentiment Timeseries                    │
│                                                               │
│  Article 1: "Apple beats on Services, but iPhone weak"      │
│  Source: Reuters | Sentiment: +0.65 (Bullish) | 2h ago      │
│                                                               │
│  Article 2: "Analyst downgrades Apple on China risk"        │
│  Source: Bloomberg | Sentiment: -0.72 (Bearish) | 1h ago    │
│                                                               │
│  30-Day Sentiment Average:  0.55 (Moderate Bullish)         │
│  7-Day Sentiment Average:   0.42 (Slightly Bullish)         │
│  1-Day Sentiment Average:   -0.10 (Slightly Bearish)        │
│                                                               │
│  [Sentiment Timeseries Line Chart - 30 days]                │
│                                                               │
│  Source Breakdown:                                          │
│  Reuters: 45% bullish | Bloomberg: 30% bullish             │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Macro Dashboard Tab:

┌─────────────────────────────────────────────────────────────┐
│  Federal Reserve | Economic Indicators | Recession Risk      │
│                                                               │
│  Fed Funds Rate: 5.25% (unchanged last FOMC)                │
│  Next decision: March 19, 2025                               │
│  Probability hike: 25% | Probability cut: 45%               │
│                                                               │
│  [Fed Funds Rate Timeseries - 5 year chart]                 │
│                                                               │
│  Treasury Yield Curve:                                      │
│  2Y: 4.1% | 5Y: 4.3% | 10Y: 4.5% | 30Y: 4.6%               │
│  2-10Y Spread: +40 bps (positive, no recession signal)      │
│                                                               │
│  Economic Indicators:                                       │
│  CPI (latest): +2.8% YoY (down from 3.2%)                  │
│  Unemployment: 4.2% (up from 3.9%)                          │
│  GDP Growth: +0.8% (Q4 annualized)                          │
│                                                               │
│  Recession Probability: 18% (from Fed's dynamic model)       │
│                                                               │
│  VIX Index: 16.5 (Low volatility environment)               │
│                                                               │
│  Macro Environment Score: 62 / 100 (Supportive)             │
│  └─ Inflation cooling, rates stable, no recession risk      │
│                                                               │
│  G20 Events: ECB meeting March 7 (watch this date)          │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Learn / Blog Tab:

┌─────────────────────────────────────────────────────────────┐
│  [All Posts] [Macro 101] [Trading Psychology] [Video]       │
│                                                               │
│  Featured Article:                                          │
│  "Why the 2-10 Yield Curve Matters for Stocks"              │
│  Posted 3 days ago | 5 min read | By Fin-Eye Team           │
│                                                               │
│  [Thumbnail]                                                │
│  "A flat or inverted yield curve has historically           │
│   preceded recessions. Here's what it means and how to       │
│   position yourself..."                                     │
│                                                               │
│  Recent Posts:                                              │
│  1. "Backtesting Pitfalls: Why Your Strategy Fails Live"   │
│  2. "Understanding GAS: Our Core Algorithm Explained"       │
│  3. "Retail Sentiment Spikes: When to Be Cautious"         │
│  4. "Fed Rate Hikes: Impact on Tech vs Utilities"          │
│  5. "Macro 101: GDP, Inflation, and Markets"               │
│                                                               │
│  Glossary:                                                  │
│  GAS (Global Alignment Score)                              │
│  Regime (Market environment - risk-on/off)                 │
│  Walk-forward validation (backtesting method)              │
│                                                               │
│  Video Tutorials:                                           │
│  "How to Use the Hedging Simulator" [▶ 8 min]               │
│  "Reading Macro Indicators" [▶ 12 min]                      │
│  "Backtesting Best Practices" [▶ 15 min]                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘

```

---

## 🧪 SECTION 12: TESTING & VALIDATION STRATEGY (COMPREHENSIVE)

### 12.1 Backtesting Validation (Technical)

```
GOALS:
  ✅ Ensure models are not overfit
  ✅ Realistic performance expectations
  ✅ Forward-looking validation (not past data)

WALK-FORWARD TESTING:

Train Period: 2019-2022 (3 years)
Test Period: 2023-06 to 2023-12 (6 months)
Shift: 1 month at a time (rolling window)

Iteration 1:
  Train: 2019-01 to 2022-01 → Test: 2022-02 to 2022-07
  Sharpe: 0.95
  Accuracy: 58%

Iteration 2:
  Train: 2019-02 to 2022-02 → Test: 2022-03 to 2022-08
  Sharpe: 0.87
  Accuracy: 56%

... continue for full backtest period ...

AGGREGATE STATISTICS:
  Mean Sharpe: 0.78
  Std Sharpe: 0.15
  Mean Accuracy: 55%
  Min Accuracy: 48%
  Max Accuracy: 62%

REPORT TO USERS:
  "Our models have average Sharpe of 0.78 in backtests.
   This is good, but remember: Live trading typically
   achieves 50% of backtest Sharpe due to slippage, emotions,
   and parameter overfitting. We recommend using 50% of
   backtest Sharpe as your expected live performance."

FORWARD VALIDATION (Live):

Every month, we track:
  - Predicted direction (from model)
  - Actual price move (realized)
  - Accuracy % (does prediction match reality?)
  
If live accuracy < 50% of backtest:
  → Alert: Model is degrading
  → Reweight model (reduce confidence)
  → Trigger retraining

```

### 12.2 Model Testing (ML-specific)

```
UNIT TESTS:

✅ Feature Engineering
   - Input: 10 days of OHLCV
   - Output: 25 features
   - Test: Check no NaN, values in reasonable ranges
   
✅ Model Training
   - Input: 5 years of data
   - Output: Trained model artifact
   - Test: Model saves without errors, inference < 500ms
   
✅ Prediction
   - Input: Latest 100 bars
   - Output: Buy/Neutral/Sell signal
   - Test: Output is valid, probability sums to 1

INTEGRATION TESTS:

✅ Full Pipeline (Data → Model → Inference)
   - Fetch latest OHLCV
   - Calculate features
   - Load model
   - Generate prediction
   - Save to database
   - Test: All steps execute < 5 seconds

✅ Model Drift Detection
   - Run monthly validation
   - Compare current accuracy to historical
   - Alert if drops > 20%
   - Test: Alert triggered when accuracy degrades

REGRESSION TESTS:

✅ Historical Backtests
   - Run weekly on new data
   - Compare Sharpe to previous month
   - Alert if Sharpe drops > 10%
   - Test: Ensure models not degrading over time

```

### 12.3 Sentiment Validation

```
FINBERT SENTIMENT ACCURACY:

Gold Standard: Manual labeling of 500 articles
  ✅ Manually label each article as Bullish/Neutral/Bearish
  ✅ Run FinBERT on same articles
  ✅ Compare predictions to manual labels
  ✅ Target accuracy: > 75%

If accuracy < 75%:
  → Consider alternative models (DistilBERT, custom training)
  → Add more negative examples to training
  → Use ensemble (FinBERT + rule-based keywords)

SENTIMENT CORRELATION TO RETURNS:

Hypothesis: Positive sentiment should correlate with next-day positive returns

Test: Calculate correlation between:
  - News sentiment (yesterday)
  - Price return (today)
  
Result: If correlation > 0.05, sentiment has some predictive power
        If correlation < 0.01, sentiment is noise

Action: If too low, reduce sentiment weight in GAS

```

### 12.4 User Acceptance Testing (UAT)

```
ALPHA TEST (Internal, 3 users):
  - Fin-Eye team members
  - Use for 1 week
  - Report bugs, confusing UX
  - Fix critical issues

BETA TEST (External, 50 users):
  - Finance students from universities
  - Early adopter traders (via Reddit)
  - Use for 4 weeks
  - Feedback on: UX, feature requests, bugs
  - Track: Activation rate, feature adoption, NPS

UAT CHECKLIST:

✅ Dashboard
  - GAS score visible and updating
  - Market Weather System renders correctly
  - Stock selector responsive

✅ Backtesting
  - Can select strategy
  - Can adjust parameters
  - Results display correctly
  - Live vs backtest comparison clear

✅ Macro Dashboard
  - FRED indicators load
  - Recession probability updates
  - Charts render

✅ Hedging Simulator
  - Can add hedge
  - Drawdown calculation correct
  - Payoff diagram understandable

✅ Blog/Learn
  - Articles load, readable
  - Video embeds play
  - Glossary functional

A/B TESTS (Post-Launch):

Test 1: GAS Explanation Clarity
  - Variant A: "GAS = 68 (bullish alignment)"
  - Variant B: "GAS = 68/100 (4 of 5 layers bullish)"
  - Measure: Which is clearer? (survey)

Test 2: Onboarding Flow
  - Variant A: Dashboard-first (show GAS immediately)
  - Variant B: Tutorial-first (explain before using)
  - Measure: Which has higher activation? (day 7 feature use)

Test 3: Blog Post CTA
  - Variant A: "Subscribe to Pro" CTA
  - Variant B: "Share this insight" CTA
  - Measure: Which drives more conversions? (tracked)

```

---

## 🚀 SECTION 13: GO-TO-MARKET STRATEGY (COMPREHENSIVE)

### 13.1 Phase 1: Beta Launch (Weeks 13-16)

```
OBJECTIVE: Validate product-market fit, gather feedback, launch to 50 users

TARGET USERS: Finance & economics students

CHANNELS:
  1. University partnerships
     - Email econ professors at top 20 EU universities
     - Ask to share with students (1-2 classes)
     - Offer free access for semester
     - Expected: 20-30 signups
  
  2. Reddit/Online communities
     - Post in r/stocks, r/investing, r/algotrading (organic, no ads)
     - "We built a free backtesting + macro tool, looking for feedback"
     - Share blog post links
     - Expected: 10-15 signups
  
  3. Personal network
     - Invite friends, colleagues, acquaintances
     - Expected: 5-10 signups

CONTENT:
  - 2 blog posts/week on macro basics
  - Topics: Fed rates, yield curves, recession signals, sentiment analysis
  - Goal: Build audience before launch
  - Expected: 500 blog visitors/week

METRICS TO TRACK:
  ✅ Signups: Target 50 by week 16
  ✅ Activation: % who visit dashboard, backtest something
  ✅ NPS: Target > 30 (good feedback for beta)
  ✅ Support tickets: < 2/day average
  ✅ Feature requests: Collect top 5 for Phase 2

CUSTOMER SUCCESS:
  - Respond to all support within 24h
  - Weekly feedback survey (5 questions)
  - Group call with beta users (discuss pain points)

EXIT CRITERIA:
  - 50 beta users signed up ✅
  - Activation rate > 40% ✅
  - NPS > 30 ✅
  - No major bugs ✅
  - Clear product-market fit signals ✅

```

### 13.2 Phase 2: Public Launch (Weeks 17-24)

```
OBJECTIVE: Scale to 500+ free users, 50+ paying users

CHANNELS:

1. CONTENT MARKETING (60% of effort)
   - Blog post schedule: 2/week (48 posts over 6 months)
   - Topics: "Why Fed matters," "Understanding macro," "Backtesting 101," etc.
   - SEO: Target keywords like "understand stock market macro"
   - Expected reach: 5k visitors/month by month 6
   
   Content distribution:
     ├─ Newsletter signup (from blog)
     ├─ Reddit (organic shares)
     ├─ Twitter (2x/week)
     └─ Email list (weekly digest)

2. REDDIT OUTREACH (20% of effort)
   - r/stocks (post weekly market analysis)
   - r/investing (educational posts about macro)
   - r/wallstreetbets (backtesting results, humor)
   - r/algotrading (technical posts)
   - Not ads, genuine value-add
   - Expected: 10-20 signups/week

3. TWITTER/X (10% of effort)
   - Daily market update (using GAS)
   - Tag relevant accounts (@federalreserve, finance accounts)
   - Retweet relevant threads
   - Build to 1k followers by month 24
   - Expected: 5-10 signups/week

4. PAID MARKETING (10% of effort, test only)
   - Google Ads: "Backtesting tool," "Market analysis"
   - Budget: €500/month (test)
   - Target: € 1 CAC (cost per signup)
   - Pause if CAC > €3 (LTV only €90)
   - Expected: 100-150 signups/month

PRICING MODEL:
  - Free tier: Basic dashboard, delayed data, 3 backtests/month
  - Pro tier: €14.99/month (€10 if annual)
  - Free-to-paid conversion target: 2-5%
  - Target by end of month 24: 50 paying users (€750/month)

RETENTION:
  - Onboarding email sequence (5 emails over 2 weeks)
  - Weekly blog digest (keep engaged)
  - Product improvements (based on feedback)
  - Target: < 10% monthly churn

METRICS:
  ✅ Free signups: 500+ by week 24
  ✅ Paid signups: 50+ by week 24
  ✅ DAU: 100+ by week 24
  ✅ Revenue: €750+/month by week 24
  ✅ NPS: > 40
  ✅ Blog traffic: 5k/month

```

### 13.3 Phase 3: Growth & Scaling (Months 6-12)

```
OBJECTIVE: 1000+ free users, 200+ paying, €3k+/month revenue

CHANNELS:

1. CONTENT EXPANSION (40%)
   - 2 blog posts/week continued
   - Video series on YouTube (5-10 min tutorials)
   - Podcast? (future, month 9+)
   - Guest post on popular finance blogs
   - Case studies (user success stories)

2. COMMUNITY BUILDING (30%)
   - Discord server (trading community, ~100 active members)
   - Reddit community (r/fin_eye, ~50 members)
   - Email list (2000+ subscribers)
   - Monthly webinar (market analysis, Q&A)

3. PARTNERSHIPS (20%)
   - Finance educators (affiliate: "Use Fin-Eye for your course")
   - Brokers (API partnership: white-label)
   - Finance influencers (guest appearance, collaboration)

4. PAID MARKETING (10%)
   - Google Ads (scaled if profitable)
   - Facebook Ads (test audience)
   - Budget: €1k/month (if CAC < €3)

MONETIZATION EXPANSION:
  - Annual plan: €150/year (-15% discount)
  - Team plan: €20/month per user (bulk)
  - API tier: €50/month for developers
  - Institutional: €5k+/month (white-label)

EXPECTED METRICS BY MONTH 12:
  ✅ Free users: 1000+
  ✅ Paid users: 200+
  ✅ Monthly revenue: €3000+
  ✅ DAU: 500+ (5% engagement)
  ✅ NPS: > 45
  ✅ Content subscribers: 5000+
  ✅ Brand mentions (organic): 50+/month
  ✅ Support load: < 5 tickets/week

```

---

## 💰 SECTION 14: MONETIZATION MODEL (DETAILED)

### 14.1 Pricing Tiers

```
FREE TIER (€0)
  ✅ Included:
    - Single stock GAS analysis
    - Basic dashboard (Market Weather System)
    - News sentiment (delayed 24h)
    - 1 year historical data view
    - 3 backtests/month (limited strategies)
    - Basic hedging simulator (stock + single put)
    - Basic blog access
    - Community forum (read-only)
  
  ❌ Not included:
    - Real-time macro dashboard
    - Portfolio view
    - Advanced hedging (multi-leg)
    - Unlimited backtests
    - Strategy sharing
    - API access
    - White-label

  TARGET: Students, curious learners, free users who convert

---

PRO TIER (€14.99/month)
  ✅ Included (all of Free +):
    - Real-time macro dashboard (FRED, treasury yields, VIX)
    - Real-time news sentiment
    - Portfolio view (up to 10 stocks)
    - Unlimited backtests
    - Advanced hedging (multi-leg strategies)
    - Strategy library access
    - Conflict detector (detailed alerts)
    - Push notifications (regime shifts, alerts)
    - CSV export (backtests, strategies)
    - Community forum (read/write)
    - Priority support (< 24h response)
    - Ad-free experience
  
  ANNUAL PLAN (€150/year):
    - Same features, 15% discount (€12.99/month equivalent)
    - Incentivize annual billing (better cash flow)

  TARGET: Serious traders, engaged users, higher LTV

---

TEAM/FAMILY PLAN (€25/month for 3 users)
  - Share single subscription among 3 people
  - Separate portfolios & strategies
  - Group analytics (combined view)
  - Target: Partner traders, siblings

---

INSTITUTIONAL TIER (€5k-20k/month, custom)
  ✅ Included:
    - White-label dashboard (client-facing)
    - RESTful API (real-time GAS, signals)
    - 99.9% uptime SLA
    - Webhook subscriptions
    - Bulk analysis (50+ stocks)
    - Custom reports (PDF, Excel)
    - Dedicated support
    - Feature requests (priority)
  
  TARGET: Brokers, asset managers, hedge funds

---

DEVELOPER/API TIER (€50/month)
  - API access for custom integrations
  - 1000 req/day quota
  - Webhook support
  - Community support only
  - Target: Quants, prop traders, developers

```

### 14.2 Revenue Projections

```
CONSERVATIVE SCENARIO:

Month 3:
  - Free users: 100
  - Paid users: 5 (5% conversion)
  - MRR: 5 × €14.99 = €74.95

Month 6:
  - Free users: 500
  - Paid users: 50 (10% conversion)
  - MRR: 50 × €14.99 = €749.50

Month 12:
  - Free users: 1500
  - Paid users: 200 (13% conversion)
  - Institutional: 1 contract (€5k)
  - Total MRR: (200 × €14.99) + €5000 = €7,998

Month 24:
  - Free users: 3000
  - Paid users: 500 (17% conversion)
  - Institutional: 3 contracts (€15k)
  - Total MRR: (500 × €14.99) + €15000 = €22,495

---

OPTIMISTIC SCENARIO (Viral Growth):

Month 12:
  - Free users: 5000
  - Paid users: 500 (10% conversion)
  - Institutional: 2 contracts (€10k)
  - Total MRR: (500 × €14.99) + €10000 = €17,495

Month 24:
  - Free users: 10000
  - Paid users: 1200 (12% conversion)
  - Institutional: 5 contracts (€25k)
  - Total MRR: (1200 × €14.99) + €25000 = €42,988

---

UNIT ECONOMICS:

CAC (Customer Acquisition Cost):
  - Organic (content, Reddit): €0-2 per user
  - Paid (Google Ads): €3-5 per user
  - Blended: €1-2 per free user

Free-to-Paid Conversion:
  - Industry benchmark: 2-5%
  - Fin-Eye target: 10-15% (financial SaaS, engaged audience)

LTV (Lifetime Value):
  - Assumption: 6 months retention
  - LTV: €14.99 × 6 = €89.94
  - LTV:CAC = €89.94 / €1.50 = 60:1 (excellent)

Payback Period:
  - If CAC = €1.50, payback = 1.5 months (very fast)

```

### 14.3 Monetization Expansion Opportunities

```
FUTURE REVENUE STREAMS:

1. PREMIUM COURSES (€50-200 each)
   - "Trading Psychology 101"
   - "Macro Markets Masterclass"
   - "Backtesting Like a Pro"
   - Format: Video + worksheets + community

2. COACHING / 1-ON-1 CALLS (€100-500/hour)
   - Offer call with experienced traders
   - Review user's strategies
   - Discuss macro analysis

3. DATA & SIGNALS API (€100-1000/month)
   - Provide GAS scores to other platforms
   - Sell backtesting results
   - Sell sentiment indices

4. AFFILIATE MARKETING
   - Recommend brokers (get 0.1-1% commission)
   - Recommend portfolio management platforms
   - Non-primary, but passive income

5. SPONSORSHIPS
   - Finance newsletter sponsorship (€500-2000/month)
   - podcast sponsorships
   - Trading community endorsements

6. CONTENT LICENSING
   - License blog content to financial sites
   - License model predictions to traders


18. Revenue Module – Window Showcase (Digital Product Shop)
18.1 Purpose & Strategic Goal

The Window Showcase is a built-in monetization module inside the platform (your “small Bloomberg terminal”). It serves as a curated digital storefront where users can discover premium financial tools and be redirected to your external digital product website for purchase.

This module must:

Generate recurring revenue through digital product sales

Promote proprietary financial tools (Excel + VBA, planning systems, dashboards)

Present high-value, finance-focused utilities aligned with the platform’s professional positioning

Remain lightweight and non-intrusive to core analytics functionality

The goal is not to turn the system into an e-commerce platform, but to act as a conversion-oriented showcase window.

18.2 Product Scope
Included in V1

Visual product showcase grid

Product detail modal (inside platform)

Redirect button to external sales website

Admin management panel (add/edit/remove products)

Click tracking & analytics

Product categorization

Featured / highlighted products

Excluded in V1

In-app payment system

Subscription billing engine

License management

Digital download hosting

Complex recommendation engine

All purchases happen externally.

18.3 Product Types to Be Displayed

The module will primarily contain digital financial tools such as:

1. Portfolio Tools

Portfolio Tracking Dashboard (Excel + VBA automation)

Risk-adjusted return calculators

Performance attribution sheets

2. Financial Planning Tools

Retirement planning models

Investment allocation planners

Cash flow forecasting templates

Net worth tracking systems

3. Personal Finance Tools

Expense tracking Excel sheets

Revenue & cost management tools

Household budgeting calculators

Debt amortization sheets

4. Thematic Financial Calculators

LBO modeling templates

DCF valuation sheets

Sensitivity analysis tools

Scenario simulation sheets

All products must align with finance, analytics, or productivity.

18.4 User Experience (UX) Flow
Step 1: User Enters “Window Showcase”

Access via left sidebar navigation

Clear label (e.g., “Marketplace” or “Pro Tools”)

Dedicated standalone page

Step 2: Product Grid View

Each product card displays:

Product title

Short 1–2 line description

Price (optional visibility toggle)

Product category badge

“View Details” button

Optional:

“Featured” badge

“New” badge

Step 3: Product Detail Modal

Clicking a product opens a modal containing:

Full description

Key features list

Screenshots (optional)

Use case explanation

Target audience

“Buy Now” button (redirect)

Step 4: Redirect

Opens external website in new browser tab

Append tracking parameters:

product_id

source=terminal

user_id (if allowed) 
```

---

## ✅ SUMMARY: WHAT'S COMPLETE IN PRDV3

| Section | Status | Completeness |
|---------|--------|--------------|
| Executive Summary | ✅ Complete | 100% |
| Product Overview | ✅ Complete | 100% |
| Feature Scope (MVP + P2 + P3) | ✅ Complete | 100% |
| Technical Architecture | ✅ Complete | 95% |
| ML Specifications | ✅ Complete | 95% |
| User Personas | ✅ Complete | 90% |
| KPIs & Metrics | ✅ Complete | 90% |
| Roadmap & Timeline | ✅ Complete | 90% |
| Legal & Compliance | ✅ Complete | 95% |
| Risk Assessment | ✅ Complete | 90% |
| API Integration | ✅ Complete | 85% |
| UI/UX Flows | ✅ Complete | 85% |
| Testing Strategy | ✅ Complete | 85% |
| Go-to-Market Strategy | ✅ Complete | 90% |
| Monetization Model | ✅ Complete | 95% |

---

## 🎯 NEXT STEPS (FOR YOU)

1. **Review this PRDV3** - Does it capture your vision?
2. **Choose tech stack** - Frontend, backend, DB (fill in Section 3)
3. **Consult lawyer** - Legal review is critical before launch
4. **Get design mockups** - Hire designer for UI/UX wireframes (Figma)
5. **Assemble team** - Hire: 1 backend engineer, 1 frontend engineer, 1 content writer
6. **Begin development** - Start Sprint 1 (Week 1-4)
7. **Build in public** - Share progress on Reddit, Twitter (builds audience)
8. **Launch beta** - Get 50 early adopters, collect feedback
9. **Iterate fast** - Weekly updates based on user feedback
10. **Scale to 1000 users** - Focus on retention and education

---

**PRDV3 Date:** March 1, 2026  
**Version:** 1.0 (Complete PRD)  
**Status:** Ready for development & team review  
**Next Review:** Weekly during development (adjust based on learnings)
