# Fin-Eye — Infrastructure & Resource Scaling Calculation
**Status:** Planning  
**Based on:** Actual codebase audit (technical_training.py, gas_precompute.py, ml_pipeline.py, services/)  
**Date:** 2026

---

## 0. What This Document Covers

Your system runs the following compute-heavy pipelines per ticker:

| Pipeline | Frequency | Type |
|----------|-----------|------|
| **ML Training** | Weekly / on-demand | Heavy — XGBoost + Logistic Regression, walk-forward CV, multi-timeframe |
| **Technical Inference** (GAS precompute) | Every 15 min, market hours | Medium — joblib model load + prediction |
| **FinBERT Sentiment** | Per news article fetch | Heavy if running live, Light if pre-aggregated |
| **Macro Score** | Shared across all symbols, every 15 min | Light — FRED DB lookup + weighted formula |
| **GAS Batch** | Every 15 min, market hours | Scales linearly with symbol count |
| **OHLCV Fetch** | Daily / per-request | API-rate-limited |

Your architecture already has the right pattern:
- Redis cache (15 min TTL)
- DB snapshot fallback
- Macro computed once, shared across all symbols

---

## 1. Per-Ticker Data Sizing

### 1.1 Raw OHLCV Data (price history)

```
Per symbol, 5 years of daily OHLCV:
  ~1,260 trading days × 6 fields (OHLCV + timestamp)
  = ~60 KB per symbol (CSV/JSON uncompressed)
  = ~15 KB per symbol (Parquet/compressed)

Per symbol, 5 timeframes (1D, 1W, 4H, 1H, 15M):
  Daily:   60 KB
  Weekly:  12 KB
  4H:      ~300 KB (5yr of 4H bars)
  1H:      ~700 KB
  15M:     ~2.5 MB
  ───────────────
  Total raw: ~3.5 MB/symbol (uncompressed)
  Total compressed: ~800 KB/symbol
```

### 1.2 Engineered Features (FeatureBuilder output)

Your FeatureBuilder generates technical indicators per timeframe (RSI, MACD, Bollinger, ATR, volume ratios, returns, etc.).

```
Estimated features per row: ~30–50 columns
Per timeframe (daily, 5yr): ~60 KB → ~150 KB with features
Per symbol across 5 timeframes: ~750 KB (compressed)
```

### 1.3 Trained Model Artifacts (model_store)

```
XGBoost model (max_depth=4, n_estimators=100):
  Serialized size: ~200–400 KB per model

Logistic Regression baseline:
  Serialized size: ~5–20 KB per model

Per symbol, per timeframe (5 timeframes), winner only:
  ~300 KB × 5 = ~1.5 MB per symbol (model files)
  
Both models stored (pre-selection):
  ~400 KB × 5 × 2 = ~4 MB per symbol
```

### 1.4 Sentiment Data (FinBERT aggregates)

```
Per symbol, 30-day rolling sentiment aggregate stored in DB:
  ~30 rows × 200 bytes = ~6 KB per symbol (DB row)
  
Full sentiment history (1 year):
  ~365 rows × 200 bytes = ~73 KB per symbol
```

### 1.5 GAS Snapshots (DB + Redis)

```
Per symbol snapshot JSON:
  ~500 bytes (gas_score, weather_label, regime, component_scores, signals)

Redis memory per symbol: ~1 KB (with overhead)
DB row per symbol: ~500 bytes
Snapshot history (90 days × 4 snapshots/hr × 6.5 hrs):
  ~2,340 rows/symbol × 500 bytes = ~1.2 MB per symbol per year
```

---

## 2. Full Scaling Table by Symbol Count

### 2.1 Storage Summary

| Component | Per Symbol | 200 | 500 | 1,000 | 2,000 |
|-----------|-----------|-----|-----|-------|-------|
| Raw OHLCV (compressed) | 800 KB | 160 MB | 400 MB | 800 MB | 1.6 GB |
| Feature store | 750 KB | 150 MB | 375 MB | 750 MB | 1.5 GB |
| Model artifacts (winners) | 1.5 MB | 300 MB | 750 MB | 1.5 GB | 3.0 GB |
| Model artifacts (all) | 4 MB | 800 MB | 2 GB | 4 GB | 8 GB |
| Sentiment aggregates (1yr) | 75 KB | 15 MB | 37 MB | 75 MB | 150 MB |
| GAS snapshots (1yr) | 1.2 MB | 240 MB | 600 MB | 1.2 GB | 2.4 GB |
| DB (Postgres, all tables) | ~3 MB | 600 MB | 1.5 GB | 3 GB | 6 GB |
| Redis hot cache | ~1 KB | 200 KB | 500 KB | 1 MB | 2 MB |

**Total storage estimates (storing winner models only):**

| Scale | Storage Needed |
|-------|---------------|
| 200 symbols | ~1.5 GB |
| 500 symbols | ~4 GB |
| 1,000 symbols | **~8 GB** |
| 2,000 symbols | **~15 GB** |

> These are comfortable numbers. Even 2,000 symbols fit on a single modern SSD.  
> The real bottleneck is **compute time**, not storage.

---

## 3. Compute Requirements

### 3.1 ML Training Time Per Symbol

Your training pipeline per symbol per timeframe:
- Walk-forward CV: ~5 splits
- Logistic regression: ~0.1s per split → 0.5s per timeframe
- XGBoost (100 trees, max_depth=4): ~2–5s per split → 10–25s per timeframe
- 5 timeframes total

```
Training time per symbol:
  Fast machine (8-core):  ~30–60 seconds
  Slow machine (2-core):  ~2–4 minutes
```

**Batch training (full retrain, weekly):**

| Scale | 8-core server (sequential) | 8-core (parallel, 4 workers) |
|-------|--------------------------|------------------------------|
| 200 symbols | ~2–3 hours | ~40 min |
| 500 symbols | ~5–8 hours | ~1.5–2 hours |
| 1,000 symbols | ~10–16 hours | ~3–4 hours |
| 2,000 symbols | **~20–32 hours** | **~6–8 hours** |

> **Key insight:** At 1,000+ symbols, sequential training exceeds a weekend window. You need parallelism.

### 3.2 GAS Precompute Batch (Every 15 Min, Market Hours)

Your `run_gas_precompute_batch` runs sequentially (by design — to avoid DB session overload).

Technical inference time per symbol: ~200–500ms (model load + prediction)

```
Batch time estimates (sequential):
  200 symbols:   40–100 seconds
  500 symbols:   1.5–4 minutes
  1,000 symbols: 3–8 minutes
  2,000 symbols: 6–16 minutes
```

> **Key insight:** At 1,000+ symbols, your 15-min batch window gets dangerously tight.  
> You need to switch from sequential to async/batched parallel inference.

### 3.3 RAM Requirements

```
Python process baseline: ~200 MB
Per symbol during inference (model loaded + OHLCV in memory):
  XGBoost model:     ~50–100 MB peak
  Feature DataFrame: ~5–20 MB

Concurrent inference (4 workers):
  4 × 100 MB models in memory = ~400 MB models
  4 × 20 MB dataframes = ~80 MB data
  + overhead = ~1 GB working RAM for inference workers

Redis: ~50 MB base + ~2 MB for 2,000 symbol cache = ~55 MB
Postgres: typically 256 MB–1 GB depending on config
```

**Recommended RAM per scale:**

| Scale | Minimum RAM | Recommended RAM |
|-------|-------------|-----------------|
| 200 symbols | 2 GB | 4 GB |
| 500 symbols | 4 GB | 8 GB |
| 1,000 symbols | 8 GB | 16 GB |
| 2,000 symbols | 16 GB | 32 GB |

---

## 4. Monthly Cost Scenarios

### 4.1 Scenario A — Full Cloud (AWS / Hetzner / DigitalOcean)

**Client-side compute:** None (everything server-side, as you described)

#### AWS (expensive but scalable)

| Scale | Instance | Specs | Storage | Est. Monthly |
|-------|----------|-------|---------|-------------|
| 200 symbols | t3.medium | 2 vCPU / 4 GB | 50 GB SSD | ~$45 |
| 500 symbols | t3.large | 2 vCPU / 8 GB | 100 GB SSD | ~$85 |
| 1,000 symbols | m6i.xlarge | 4 vCPU / 16 GB | 200 GB SSD | ~$180 |
| 2,000 symbols | m6i.2xlarge | 8 vCPU / 32 GB | 400 GB SSD | ~$380 |

Add: RDS Postgres (~$30–100), ElastiCache Redis (~$20–50), bandwidth (~$10–30)

**Realistic AWS total:**
- 200 symbols: ~$100–120/month
- 500 symbols: ~$150–200/month
- 1,000 symbols: ~$280–350/month
- 2,000 symbols: ~$500–650/month

#### Hetzner Cloud (best price/performance, EU-based)

| Scale | Instance | Specs | Storage | Est. Monthly |
|-------|----------|-------|---------|-------------|
| 200 symbols | CX22 | 2 vCPU / 4 GB | 40 GB | €5/mo |
| 500 symbols | CX32 | 4 vCPU / 8 GB | 80 GB | €11/mo |
| 1,000 symbols | CX42 | 8 vCPU / 16 GB | 160 GB | €25/mo |
| 2,000 symbols | CX52 | 16 vCPU / 32 GB | 320 GB | €49/mo |

> Hetzner is 5–10× cheaper than AWS for the same specs. Excellent for a startup.  
> Add a Hetzner Volume for model store (~€0.05/GB/month).

**Realistic Hetzner total:**
- 200 symbols: ~€15–20/month
- 500 symbols: ~€25–35/month
- 1,000 symbols: ~€45–60/month
- 2,000 symbols: ~€70–100/month

### 4.2 Scenario B — Home Server

A home server trades monthly fees for upfront hardware cost and electricity.

**Recommended home server build for 1,000 symbols:**

```
CPU:     AMD Ryzen 7 5700G (8 cores / 16 threads) — ~$130
RAM:     32 GB DDR4 3200MHz (2× 16 GB) — ~$60
SSD:     1 TB NVMe (Samsung 970 EVO) — ~$80
Mobo:    B550 AM4 — ~$100
PSU:     Seasonic 450W 80+ Gold — ~$60
Case:    Mini-ITX or mATX — ~$50
───────────────────────────────────────
Total hardware: ~$480 USD

Electricity: 65W idle, ~150W under load
  At $0.12/kWh (US avg): ~$8–14/month
  At $0.25/kWh (EU avg): ~$14–25/month

Internet: You need a static IP or dynamic DNS.
  Most residential ISPs block inbound ports — use a $5/mo VPS as a reverse proxy/tunnel.
```

**Total home server cost:**
- Year 1 (hardware + electricity): ~$580–650
- Year 2+ (electricity only): ~$100–170/year

**Breakeven vs Hetzner (1,000 symbols):** ~8–10 months

**Home server for 2,000 symbols:**
```
CPU:   Ryzen 9 5900X (12 cores) or Intel i9-12900 — ~$180
RAM:   64 GB DDR4 — ~$120
SSD:   2 TB NVMe — ~$140
Total: ~$700
```

---

## 5. Architecture Recommendations

### 5.1 Best for Scaling: Tiered Worker Architecture

The biggest bottleneck at scale is your sequential GAS batch. Here's the fix:

```
Current (sequential):
  for symbol in symbols:
      await compute_gas_for_symbol(symbol, db)
  
  → 1,000 symbols × 500ms = ~8 minutes per batch

Recommended (concurrent workers):
  Use asyncio.gather() with a semaphore to limit concurrency.
  
  BATCH_CONCURRENCY = 20  # tune per server
  
  sem = asyncio.Semaphore(BATCH_CONCURRENCY)
  async def bounded_compute(symbol):
      async with sem:
          return await compute_gas_for_symbol(symbol, db, macro_score)
  
  await asyncio.gather(*[bounded_compute(s) for s in symbols])
  
  → 1,000 symbols ÷ 20 concurrent = 50 batches × 500ms = ~25 seconds
```

### 5.2 Best for Cost: Pre-compute Everything, Serve from Cache

You already have the right architecture (Redis → DB → live). Extend it:

```
Strategy: Never compute on user request.
  
  All signals pre-computed on schedule:
  - GAS batch: every 15 min (market hours)
  - Technical training: weekly (Sunday night batch)
  - Sentiment aggregation: daily (after market close)
  - Macro score: every 15 min (shared across symbols)
  
  User request flow:
  User → API → Redis cache (< 1ms) → done
  
  Cold start only for new/unknown symbols.
```

### 5.3 Best for Training Scale: Celery + Queue

For 1,000+ symbol weekly retrains:

```
Current: No background task queue
Problem: A full 1,000-symbol retrain blocks the server

Fix: Add Celery + Redis as broker

Architecture:
  Scheduler (APScheduler) → Celery task queue → Worker pool
  
  Worker config for 1,000 symbols:
    workers: 4
    tasks_per_worker: 250 symbols
    estimated time: ~3–4 hours (Sunday night batch)
  
  Each worker runs independently, results written to model_store.
```

### 5.4 Model Storage Strategy

```
Current: model_store/ directory (flat files via ModelArtifactStore)

For 1,000+ symbols:
  Keep flat files for MVP (works fine up to ~5,000 symbols)
  
  Structure:
    model_store/
      AAPL/
        1D_xgboost_v3.joblib
        1W_logistic_v2.joblib
        ...
      MSFT/
        ...
  
  Total size at 1,000 symbols (winners only): ~1.5 GB — no problem.
  
  For 2,000+ symbols future:
    Consider S3-compatible object storage (Hetzner Object Storage: €0.02/GB)
    Model artifacts upload after training, served on-demand to inference workers.
```

---

## 6. Full Scenario Comparison Table

| | **200 symbols** | **500 symbols** | **1,000 symbols** | **2,000 symbols** |
|---|---|---|---|---|
| **Storage needed** | 1.5 GB | 4 GB | 8 GB | 15 GB |
| **RAM needed** | 4 GB | 8 GB | 16 GB | 32 GB |
| **GAS batch (sequential)** | ~2 min | ~5 min | ~10 min ⚠️ | ~20 min ❌ |
| **GAS batch (concurrent ×20)** | ~6 sec | ~15 sec | ~30 sec ✅ | ~60 sec ✅ |
| **Weekly retrain (4 workers)** | ~40 min | ~2 hrs | ~4 hrs | ~8 hrs |
| **Hetzner cost/month** | €15–20 | €25–35 | €45–60 | €70–100 |
| **AWS cost/month** | ~$100 | ~$175 | ~$320 | ~$580 |
| **Home server (year 1)** | ~$480 | ~$480 | ~$550 | ~$700 |
| **Home server (year 2+/yr)** | ~$120 | ~$120 | ~$150 | ~$180 |
| **Recommended path** | Any | Any | Hetzner CX42 or home | Hetzner CX52 or home |

---

## 7. What to Put Client-Side vs Server-Side

### Always Server-Side (you correctly identified this)
- ML model training and storage
- GAS batch computation
- FinBERT sentiment scoring
- Macro indicator fetching (FRED)
- OHLCV historical data
- All database state (Postgres)
- Redis cache

### Can Be Client-Side (computed in browser, zero server cost)
- GAS score color mapping (already in `MarketWeatherWidget.tsx` ✅)
- Regime label derivation (already in `RegimeWidget.tsx` ✅)
- Conflict detection logic (already in `ConflictDetector` ✅)
- "Why moving" bullet construction (already in `page.tsx` ✅)
- Sentiment label display (e.g. "mild positive" → derive from score in browser)
- Score color thresholds and display formatting

> You've already made the right call here — all display logic is client-side,  
> all data computation is server-side.

### Optional: Lazy Client-Side Computation
For non-critical display metrics that don't need accuracy, you can derive them from the cached GAS snapshot without extra API calls:
- Technical regime (from `component_scores.technical`)
- Volatility category (from `component_scores.macro` + VIX level in snapshot)
- Signal summary text

---

## 8. Recommended Paths

### Path 1: Start Smart (0–500 symbols) — Hetzner CX32
```
Server:   Hetzner CX32 (4 vCPU / 8 GB / 80 GB SSD)
Cost:     €11/month compute + ~€5 extras = ~€16/month
Action:   Add asyncio.Semaphore(10) to GAS batch
Retrain:  Friday night cron, sequential is fine
```

### Path 2: Grow Phase (500–1,000 symbols) — Hetzner CX42
```
Server:   Hetzner CX42 (8 vCPU / 16 GB / 160 GB SSD)
Cost:     ~€35/month
Action:   Add Celery workers for training
          Increase batch concurrency to 20
          Add a 1 TB Hetzner Volume for model_store (~€5/mo)
```

### Path 3: Scale Phase (1,000–2,000 symbols) — Hetzner CX52 or Home Server
```
Option A — Hetzner CX52:
  Cost:   ~€80/month
  Pro:    No maintenance, reliable uptime
  Con:    Ongoing cost

Option B — Home Server (Ryzen 9 5900X, 64 GB RAM):
  Cost:   ~$700 upfront + ~$150/year electricity
  Pro:    Breaks even in ~9 months vs Hetzner
  Con:    No redundancy, power outages, home bandwidth limits
  Fix:    Use Cloudflare Tunnel (free) to expose securely without static IP
          Add a cheap Hetzner VPS (€4/mo) as your API entry point
          Home server does the heavy compute, VPS does SSL termination + proxy
```

### Path 4: Production SaaS (2,000+ symbols, paying users)
```
Architecture:
  - Hetzner CX52 or Dedicated AX41 (AMD EPYC) as primary compute
  - Hetzner Object Storage for model artifacts
  - Managed Postgres (Neon.tech or Supabase: ~$25/mo)
  - Upstash Redis (serverless, ~$10/mo)
  - Cloudflare for CDN + DDoS

Estimated total: ~$120–200/month
This beats AWS by ~3-4×.
```

---

## 9. Immediate Action Items (Prioritized)

### Priority 1 — Do Now (free, no infra changes needed)
- [ ] Add `asyncio.Semaphore` to `run_gas_precompute_batch` — fixes the timing bottleneck at scale
- [ ] Add model file count monitoring to ops dashboard (how many symbols have trained models)
- [ ] Add batch timing metrics (log `elapsed_ms` per symbol, not just total)

### Priority 2 — Before 500 Symbols
- [ ] Move from sequential training to parallel via Celery or `concurrent.futures.ProcessPoolExecutor`
- [ ] Add a `model_store` size health check to the ops endpoint
- [ ] Set up weekly retrain cron (Sunday 02:00 UTC)

### Priority 3 — Before 1,000 Symbols
- [ ] Migrate to Hetzner CX42 (or upgrade home server RAM to 32 GB)
- [ ] Add Hetzner Volume or S3 for model artifact storage
- [ ] Add a symbol priority queue (compute more frequently for popular/high-traffic symbols)
- [ ] Add Celery + Redis broker for training job queue

### Priority 4 — Before 2,000 Symbols
- [ ] Home server decision: buy vs keep renting
- [ ] Add Postgres read replica or connection pooling (PgBouncer)
- [ ] Add model versioning (keep last 2 versions per symbol for rollback)
- [ ] Add data retention policy (purge OHLCV beyond 5 years, compress snapshots older than 90 days)
