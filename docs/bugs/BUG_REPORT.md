# Fin-Eye — Bug Report & Findings
> Generated: 2026-03-30 | Covers Sprints 1–41 | Detection only — no fixes applied yet

---

## SEVERITY LEGEND
- 🔴 **CRITICAL** — Runtime crash / data corruption / security hole
- 🟠 **HIGH** — Wrong behaviour visible to user / data silently wrong
- 🟡 **MEDIUM** — Edge-case failure / degraded experience under specific conditions
- 🔵 **LOW** — Code smell / performance issue / minor UX inconsistency
- ⚪ **INFO** — Observation, not a bug — worth tracking

---

## BACKEND BUGS

---

### 🔴 BUG-BE-01 — `LSTMWrapper` trains on training-set loss only, no separate validation split — overfitting risk
**File:** `backend/app/services/ml_pipeline.py` — `LSTMWrapper.fit()`
**Severity:** HIGH
**Detail:**
The early-stopping loop monitors `loss.item()` which is the **training** loss (computed on `X_t`, `y_t` — the full training set passed in). There is no held-out validation set inside the LSTM's own training loop. Early stopping therefore fires on train-loss plateau, not val-loss, so it provides no real overfitting protection. The outer pipeline's train/val split exists, but the LSTM never sees it during its internal epoch loop.
**Impact:** LSTM may overfit training data and pass quality gates on the outer validation set by chance; its real out-of-sample accuracy will be lower than reported.
**Fix required:** Pass a `val_frac` of ~0.2 from `X_seq/y_seq` into the fit loop; monitor val-loss for early stopping.

---

### 🔴 BUG-BE-02 — `LSTMWrapper.predict_proba()` builds O(N) sequences in a Python loop — blocks executor thread on large inputs
**File:** `backend/app/services/ml_pipeline.py` — `LSTMWrapper.predict_proba()`
**Severity:** HIGH
**Detail:**
The inference path loops `for i in range(n)` to build a sliding-window sequence for every row, then stacks them all into a single tensor `X_t = torch.from_numpy(np.array(seqs, dtype=np.float32))`. For a 5-year 1h series (~8760 rows) this creates an `(8760, 20, 26)` tensor — ~145 MB — and the Python loop itself takes several seconds. Since `compute_technical_consensus()` runs in a thread-pool executor, this blocks the executor thread for the full inference duration. Under concurrent requests, thread pool exhaustion is likely.
**Impact:** Significant latency for 1h timeframe inference; executor thread pool starvation under concurrent load.
**Fix required:** Only build sequences for the rows actually needed for inference (typically the last N rows), or batch in chunks of 256.

---

### 🔴 BUG-BE-03 — `LSTMWrapper` `best_state` can theoretically be `None` if all epochs are skipped
**File:** `backend/app/services/ml_pipeline.py` — `LSTMWrapper.fit()`
**Severity:** MEDIUM
**Detail:**
```python
best_state: Optional[dict] = None
...
for epoch in range(self.EPOCHS):
    ...
    if patience >= self.PATIENCE:
        break
if best_state:
    model.load_state_dict(best_state)
```
`best_state` is only set when `val_loss < best_loss - 1e-4`. If the very first epoch's loss does not beat `float("inf") - 1e-4` (impossible in practice, since any finite loss beats infinity), `best_state` stays `None`. The guard `if best_state:` silently skips `load_state_dict` and the model is left in its final epoch state. The bug is harmless in normal conditions but the code should be defensive.
**Fix required:** Initialise `best_state` from the model's initial weights before the loop, or guarantee it is always set after epoch 0.

---

### 🟠 BUG-BE-04 — `engineer_features()` seasonal `sin_dow` uses period=5 but crypto/FX trade 7 days/week
**File:** `backend/app/services/ml_pipeline.py` — `engineer_features()`
**Severity:** HIGH
**Detail:**
```python
d["sin_dow"] = (day_of_week * (2 * math.pi / 5)).apply(math.sin)
```
`dayofweek` returns 0–4 for Mon–Fri for equities, but 0–6 for crypto/FX symbols that trade weekends. For a BTC-USD daily series, dayofweek values of 5 and 6 produce `sin(5 × 2π/5) = sin(2π) ≈ 0` and `sin(6 × 2π/5)` — the encoding is no longer cyclic over the actual 7-day trading week. The cos_dow has the same problem.
**Impact:** Seasonal features are meaningless/misleading for BTC-USD, ETH-USD, EURUSD=X, GBPUSD=X, USDJPY=X — all newly added Sprint 41 symbols.
**Fix required:** Use `2 * math.pi / 7` as the denominator for all symbols, which is correct for both 5-day and 7-day trading weeks. Alternatively gate on `settings.is_crypto(symbol) or settings.is_fx(symbol)` and use 7 for those.

---

### 🟠 BUG-BE-05 — `ohlcv_fetcher.py` scheduler fetcher uses `period="60d"` for intraday, but `technical_service.py` inference expects 5 years of 1h data
**File:** `backend/app/services/ohlcv_fetcher.py` — `_download_intraday()` vs `backend/app/services/technical_service.py` — `generate_timeframe_signal()`
**Severity:** HIGH
**Detail:**
`ohlcv_fetcher.py` `_download_intraday()` hardcodes `period="60d"`. The `technical_service.py` static fetch path via `market_data.OHLCVFetcher` uses `period="5y"` (which yfinance caps to 730d for 1h). The `ohlcv_intraday` table therefore only stores 60 days of data. This is fine for intraday display but means `technical_service.py` is fetching data live on every inference call (bypassing the stored table entirely) while the stored table is underutilised.
**Fix required:** Change `_download_intraday()` to `period="730d"` to maximise stored history for future use. Document that inference uses live yfinance, not the stored table, for 1h data.

---

### 🟠 BUG-BE-06 — `optuna_tuner.py` saves tuned hyperparameters but `run_training_pipeline()` never loads them
**File:** `backend/app/services/optuna_tuner.py` + `backend/app/services/ml_pipeline.py`
**Severity:** HIGH
**Detail:**
`optuna_tuner.py` exports `load_best_params(symbol, timeframe, model_name)` and writes sidecar JSON files alongside `.joblib` artifacts. The docstring explicitly says "Training pipeline reads best params file if it exists, overrides defaults." However, `run_training_pipeline()` constructs `XGBoostWrapper(n_positive=n_pos, n_negative=n_neg)` and `LightGBMWrapper(...)` with hardcoded default params and **never calls `load_best_params()`**. The overnight Optuna job runs, saves params, and they are silently ignored.
**Impact:** Optuna tuning has zero effect on model quality. Nightly compute time is wasted.
**Fix required:** In `run_training_pipeline()`, before constructing each base model wrapper, call `load_best_params(symbol, timeframe, "xgboost")` / `load_best_params(symbol, timeframe, "lightgbm")` and pass the results into the respective wrappers. Requires wrappers to accept an optional `params: dict` argument.

---

### 🟠 BUG-BE-07 — `UserResponse` schema is missing `trial_ends_at` and `paused_until`
**File:** `backend/app/schemas/auth.py` — `UserResponse`
**Severity:** HIGH
**Detail:**
The `User` DB model gained `trial_ends_at` and `paused_until` in Sprint 38. `UserResponse` (returned by `GET /auth/me` and `POST /auth/login`) does not include these fields. The frontend `User` interface in `AuthProvider.tsx` declares both as optional, but they will always be `undefined` from the API response because the serialiser never includes them.
**Impact:** The billing page trial status and pause banner can never show correct state in production — they always appear as "no trial active".
**Fix required:** Add `trial_ends_at: Optional[datetime] = None` and `paused_until: Optional[datetime] = None` to `UserResponse`.

---

### 🔴 FIND-04 (promoted to BUG) — `UserResponse` has no `is_pro` field but `AuthProvider.tsx` `User` interface requires it
**File:** `backend/app/schemas/auth.py` — `UserResponse` vs `frontend/components/AuthProvider.tsx`
**Severity:** CRITICAL
**Detail:**
The frontend `User` interface has `is_pro: boolean` as a **required non-optional** field. `UserResponse` from the backend has `subscription_tier: str` but no `is_pro`. In production (when `REQUIRE_AUTH=true`), the user object is populated from the `/auth/me` JSON response which contains no `is_pro` key. So `user.is_pro` is `undefined` (falsy) for every real user. All Pro-gate checks like `user?.is_pro` will always deny access.
**Impact:** Every paying/trial Pro user sees the free tier experience in production. All Pro-gated features (Fed Policy page, Advanced Sentiment, Indicators, AI Allocator, Walk-Forward backtesting) are permanently locked for real users.
**Fix required:** Add `is_pro: bool = False` to `UserResponse` (computed from `subscription_tier in ("pro", "institutional")` OR `trial_ends_at is not None and trial_ends_at > datetime.now(timezone.utc)`).

---

### 🟡 BUG-BE-09 — Crypto GAS computation uses neutral sentiment (50) instead of Crypto Fear & Greed index
**File:** `backend/app/services/gas_precompute.py` — `_compute_sentiment_score()`
**Severity:** MEDIUM
**Detail:**
When `compute_gas_for_symbol()` runs for BTC-USD or ETH-USD, `_compute_sentiment_score()` queries `SentimentAggregate` which contains news-based equity sentiment. Crypto symbols have no rows in this table, so the function returns `50.0` (neutral). The Crypto Fear & Greed index is already fetched every hour (Sprint 40, `external_signals` table, signal_name `crypto_fear_greed_norm`) but is never fed into the GAS computation.
**Impact:** GAS scores for BTC-USD/ETH-USD ignore the most relevant sentiment signal available. The sentiment layer is always neutral regardless of actual crypto market sentiment.
**Fix required:** In `_compute_sentiment_score()`, detect crypto symbols (endswith `-USD`) and query `external_signals` for the latest `crypto_fear_greed_norm` value, mapping it to 0–100.

---

### 🟡 BUG-BE-12 — `resolve_pending_outcomes()` fetches prices serially via yfinance — slow with many symbols
**File:** `backend/app/services/prediction_service.py`
**Severity:** MEDIUM (performance)
**Detail:**
```python
for sym in symbols_needed:
    price = await _fetch_price_async(sym)
```
Each call invokes `yf.Ticker(symbol).history(period="2d")` in an executor — a separate HTTP call per symbol. With 15+ default symbols this takes 15–45 seconds per hourly cron run. yfinance supports bulk download via `yf.download(list_of_symbols, ...)` which fetches all in one HTTP call.
**Fix required:** Replace the serial loop with `yf.download(symbols_needed, period="2d", interval="1d", auto_adjust=True)` in a single executor call, then extract closing prices from the MultiIndex DataFrame.

---

### 🟡 BUG-BE-13 — `inject_external_features()` tz-mismatch silently drops all external signals on daily data
**File:** `backend/app/services/ml_pipeline.py` — `inject_external_features()`
**Severity:** MEDIUM
**Detail:**
`_download_daily()` strips timezone with `df.index = df.index.tz_localize(None)`, producing a tz-naive DatetimeIndex. `inject_external_features()` then does:
```python
aligned = s.reindex(idx.tz_convert("UTC") if idx.tz else idx, method="ffill")
```
When `idx.tz` is `None`, it uses the tz-naive `idx` to reindex against `s` whose index was set to UTC-aware via `pd.to_datetime(s.index, utc=True)`. Pandas cannot align tz-aware and tz-naive indexes without raising or silently producing all-NaN. External signals are zeroed for all daily data.
**Impact:** `fear_greed_norm`, `google_trends_norm`, `reddit_mentions_norm`, etc. are always 0 in daily model training even when data exists in `external_signals` table.
**Fix required:** When `idx.tz` is None, localize `idx` to UTC before reindexing: `idx_utc = idx.tz_localize("UTC"); s.reindex(idx_utc, method="ffill")`.

---

### 🟡 BUG-BE-14 — `gas_precompute.py` grade history always reads the NEWLY written grade — never detects changes
**File:** `backend/app/services/gas_precompute.py` — `compute_gas_for_symbol()`
**Severity:** MEDIUM (logic bug — grade history feature is non-functional)
**Detail:**
```python
snap = await upsert_snapshot(...)          # ← overwrites DB row with new grade
...
prev_snap = await _get_latest(db, symbol)  # ← reads back the row just written
prev_grade = prev_snap.signal_grade        # ← equals new_grade, always
if prev_grade != new_grade:               # ← always False
    ... # history row never written
```
The `upsert_snapshot()` call runs BEFORE reading the previous grade. The read-back always returns the grade that was just written. Grade change history is never recorded.
**Fix required:** Call `prev_snap = await _get_latest(db, symbol)` BEFORE calling `upsert_snapshot()`.

---

### 🟡 BUG-BE-15 — `technical_service.py` module-level `_registry` singleton may return stale data after new training
**File:** `backend/app/services/technical_service.py`
**Severity:** MEDIUM
**Detail:**
```python
_registry = JsonlFileModelRegistry(REGISTRY_FILE)
```
This is a module-level singleton instantiated at import time. If `JsonlFileModelRegistry` caches its contents in memory (rather than re-reading the JSONL file on each `all_champions()` call), newly trained models appended to the registry file after startup will not be visible until the process restarts. `get_trained_timeframes()` and `get_latest_model_metadata()` would return stale results after a background training run.
**Fix required:** Verify `JsonlFileModelRegistry.all_champions()` re-reads from disk on each call, OR instantiate a fresh registry object inside `get_trained_timeframes()` / `get_latest_model_metadata()`.

---

### 🔵 BUG-BE-16 — `billing.py` imports `get_current_user` from `auth.py` instead of `deps.py`
**File:** `backend/app/api/v1/endpoints/billing.py`
**Severity:** LOW
**Detail:**
```python
from app.api.v1.endpoints.auth import get_current_user   # reuse existing dep
```
The canonical location for shared dependencies is `app/api/v1/deps.py`. Every other endpoint imports `get_current_user` from `deps`. This creates a fragile cross-endpoint import that will break if `auth.py` is refactored.
**Fix required:** Change to `from app.api.v1.deps import get_current_user`.

---

### 🔵 BUG-BE-17 — `ohlcv_fetcher.py` `validate_row()` defined but never called
**File:** `backend/app/services/ohlcv_fetcher.py`
**Severity:** LOW
**Detail:**
`validate_row()` is a static method that checks for `high < low`, `close <= 0`, and `volume < 0`. It is never called in `_df_to_daily_rows()` or `_df_to_intraday_rows()`. Suspended/delisted symbols can produce junk rows via yfinance that silently enter the DB.
**Fix required:** Call `validate_row(row)` in `_df_to_daily_rows()` and skip/log invalid rows.

---

### 🔵 BUG-BE-18 — `scheduler.py` weekly digest fires at 08:00 UTC but Sprint plan says 07:00 UTC
**File:** `backend/app/services/scheduler.py`
**Severity:** LOW (documentation mismatch only)
**Detail:**
`setup_scheduler()` registers `job_weekly_digest` at `hour=8, minute=0` (08:00 UTC). Sprint 33 in `SPRINT_PROGRESS.md` says "Mondays 07:00 UTC". Minor discrepancy — both valid but should be reconciled.

---

## FRONTEND BUGS

---

### 🟠 BUG-FE-01 — Keyboard navigation broken after Sprint 41 search grouping refactor
**File:** `frontend/components/GlobalTickerSearch.tsx`
**Severity:** HIGH
**Detail:**
After grouping, the dropdown renders group header `<div>`s interleaved with result `<button>`s via an IIFE. `onMouseEnter` on each button calls `setActiveIdx(item._origIdx)` where `_origIdx` is the flat array index. If a user hovers result #4 (origIdx=4) then presses ArrowDown, the handler does `setActiveIdx((i) => Math.min(i + 1, results.length - 1))` — moving to index 5. But if the user previously hovered result #1 (origIdx=1) in a different group, `activeIdx` was set to 1, and ArrowDown correctly moves to 2. The real problem: after hovering an item in a non-first group (e.g., the first crypto result at origIdx=4 while only 2 equities exist), pressing ArrowUp moves to origIdx=3 (which is a gap — no result at that index exists in the rendered DOM for that position).
**Impact:** Arrow keys jump over invisible slots when results are grouped and mouse was used before keyboard. Tab / Enter on wrong item.
**Fix required:** Decouple hover state from keyboard state. Use a flat `activeSymbol: string | null` for hover highlighting, and keep `activeIdx` as a sequential 0–(results.length-1) keyboard counter only.

---

### 🟠 BUG-FE-02 — `CryptoFearGreedPanel` progress bar uses `norm` which may not exist in all API response shapes
**File:** `frontend/app/page.tsx` — `CryptoFearGreedPanel`
**Severity:** MEDIUM
**Detail:**
```typescript
const norm = data.norm ?? score / 100;
...
style={{ width: `${Math.round(norm * 100)}%` }}
```
The backend `get_latest()` on `CryptoFearGreedFetcher` returns a dict where `norm` is the stored signal value. If `score` is 0–100 (which it is), then `score / 100` is the correct fallback and produces 0–1. This is correct. However, the TypeScript type declaration is `{ score: number; label: string; norm: number; ... }` — if `norm` is absent from the response, TypeScript won't catch it at compile time since the fetch is untyped (`r.json() as Promise<...>`). The runtime fallback is correct but the type assertion provides false confidence.
**Fix required:** Low risk — the fallback is mathematically correct. Add a runtime assertion `const barPct = Math.min(100, Math.max(0, Math.round((data.norm ?? data.score / 100) * 100)))` for safety.

---

### 🟡 BUG-FE-03 — `page.tsx` header `<div>` indentation corrupted during Sprint 41 asset-class badge edit
**File:** `frontend/app/page.tsx` — ticker header section
**Severity:** MEDIUM (code quality — may cause lint/build warnings)
**Detail:**
The two-stage edit that added the asset class badge left the outer `<div className="flex items-center gap-3 flex-wrap">` at inconsistent indentation. The JSX structure is semantically correct (it will render and work) but the indentation mismatch will trigger Prettier/ESLint formatting errors and makes the code harder to maintain.
**Fix required:** Re-format the header section with consistent indentation.

---

### 🟡 BUG-FE-04 — Dev mock user in `AuthProvider.tsx` missing optional fields — billing/settings broken in dev mode
**File:** `frontend/components/AuthProvider.tsx`
**Severity:** MEDIUM
**Detail:**
```typescript
setUser({ id: "...", email: "dev@mock.local", is_pro: true, is_admin: true });
```
The mock user has no `trial_ends_at`, `paused_until`, `name`, `default_symbol`, or `risk_profile`. Components that read `user?.trial_ends_at` or `user?.risk_profile` receive `undefined` in dev mode. The billing page will always show "Start Trial" (correct for an untrialed user), but the risk profile selector in `/portfolio/allocate` will show empty state in dev.
**Fix required:** Add all optional fields to the dev mock user with sensible defaults: `name: "Dev User"`, `trial_ends_at: null`, `paused_until: null`, `default_symbol: null`, `risk_profile: "Moderate"`.

---

### 🔵 BUG-FE-05 — `GlobalTickerSearch.tsx` unused imports: `useDeferredValue` and `useSWR`
**File:** `frontend/components/GlobalTickerSearch.tsx`
**Severity:** LOW
**Detail:**
```typescript
import React, { useState, useRef, useEffect, useCallback, useDeferredValue } from "react";
import useSWR from "swr";
```
Both `useDeferredValue` and `useSWR` are imported but never used. Will trigger ESLint `no-unused-vars` warnings and add ~1KB to the bundle.
**Fix required:** Remove both from the import statements.

---

### 🔵 BUG-FE-06 — `CryptoFearGreedPanel` SWR cache lost on every symbol switch to/from crypto
**File:** `frontend/app/page.tsx`
**Severity:** LOW (performance)
**Detail:**
`useCryptoFearGreed()` is called inside `CryptoFearGreedPanel` which is only rendered when `isCrypto` is true. Each time the user switches away from a crypto symbol and back, the component unmounts/remounts and SWR may trigger a new fetch depending on its deduplication window. The SWR key `"crypto-fear-greed"` is correct and will deduplicate within the 5-min interval, but the component mount/unmount cycle is wasteful.
**Fix required:** Call `useCryptoFearGreed()` unconditionally at the `DashboardPage` level and pass `data` as a prop to `CryptoFearGreedPanel`, or accept the current behaviour (only cosmetic perf issue).

---

### 🔵 BUG-FE-07 — TradingView symbol mapping for Gold futures uses wrong exchange
**File:** `frontend/app/page.tsx` — `PriceChartWidget`
**Severity:** LOW (display only)
**Detail:**
```typescript
if (s.endsWith("=F")) return `NYMEX:${s.replace("=F", "")}`;  // GC=F → NYMEX:GC
```
Gold futures (`GC=F`) trade on COMEX (part of CME Group), not NYMEX. TradingView uses `COMEX:GC1!` for continuous gold futures. `NYMEX:GC` may resolve to a different or unavailable instrument, potentially rendering a blank chart. Crude Oil (`CL=F`) does correctly map to NYMEX.
**Fix required:** Add explicit per-symbol mapping: `"GC=F" → "COMEX:GC1!"`, `"CL=F" → "NYMEX:CL1!"`.

---

## ARCHITECTURAL FINDINGS (Not bugs per se)

---

### ⚪ FIND-01 — Two classes named `OHLCVFetcher` in different modules — naming collision
**Files:** `backend/app/services/ohlcv_fetcher.py` AND `backend/app/services/market_data.py`
**Detail:** `technical_service.py` imports `from app.services.market_data import OHLCVFetcher` (a sync live-fetch class). `data.py` and `scheduler.py` import `from app.services.ohlcv_fetcher import OHLCVFetcher` (the async DB-upsert class). Same class name, completely different responsibilities. This is a maintenance hazard — easy to import the wrong one.
**Suggested fix:** Rename `market_data.OHLCVFetcher` to `LivePriceFetcher` or `YFinanceFetcher`.

---

### ⚪ FIND-02 — Dual OHLCV read endpoints with different paths and different data sources
**Files:** `backend/app/api/v1/data.py` (`GET /api/v1/data/ohlcv/{symbol}`) and `backend/app/api/v1/endpoints/technical.py` (`GET /api/v1/technical/{symbol}/ohlcv`)
**Detail:** Two endpoints serve OHLCV data: one reads from the `ohlcv_daily` DB table (Sprint 41, for DCA page), the other calls `OHLCVFetcher.fetch_historical_data()` live from yfinance (Sprint 27, for the dashboard price chart). They have different data shapes, different sources, and serve different purposes. The naming overlap (`/data/ohlcv/` vs `/{symbol}/ohlcv`) is confusing. Document clearly which to use for what.

---

### ⚪ FIND-03 — `run_training_pipeline()` docstring still says "4 base models" — outdated
**File:** `backend/app/services/ml_pipeline.py`
**Detail:** Module docstring and `run_training_pipeline()` docstring say "logistic, xgboost, lightgbm, ensemble" — now 5 models with LSTM. Cosmetic but confusing.

---

### ⚪ FIND-04 — `technical_service.py` provides no asset-class-aware fallbacks for crypto/FX signals
**File:** `backend/app/services/technical_service.py`
**Detail:** Sprint 41 planned graceful fallbacks for crypto/FX (no earnings, no sector data). Currently `technical_service.py` treats BTC-USD identically to AAPL. The FEATURES list doesn't include earnings features so there's no crash — but the 7-day trading week means `volume_ratio` and seasonal features behave differently. No code change was made here despite being in the Sprint 41 plan.

---

## PERFORMANCE IMPROVEMENTS

| ID | File | Issue | Impact |
|----|------|--------|--------|
| PERF-01 | ml_pipeline.py | `_make_sequences()` uses Python loops — use numpy stride_tricks | 50-100x faster sequence building |
| PERF-02 | gas_precompute.py | Symbols processed serially — use asyncio.gather with semaphore | Batch time: 15×T → ~4×T |
| PERF-03 | ml_pipeline.py | `import math` inside `engineer_features()` function body | Minor — move to module level |
| PERF-04 | ml_pipeline.py | `inject_external_features()` sorts readings inside loop | Minor — pre-sort when grouping |
| PERF-05 | prediction_service.py | `resolve_pending_outcomes()` serial price fetches via yfinance | Replace with bulk yf.download() |

---

## SUMMARY TABLE

| ID | Severity | File | Description |
|----|----------|------|-------------|
| ✅ BUG-BE-01 | 🟠 HIGH | ml_pipeline.py | LSTM trains on train loss only — no real early stopping |
| ✅ BUG-BE-02 | 🔴 CRITICAL | ml_pipeline.py | LSTM predict_proba O(N) Python loop — blocks executor thread on 1h series |
| ✅ BUG-BE-03 | 🟡 MEDIUM | ml_pipeline.py | LSTM best_state can be None on degenerate case |
| ✅ BUG-BE-04 | 🟠 HIGH | ml_pipeline.py | sin_dow/cos_dow period=5 wrong for crypto/FX 7-day trading week |
| ✅ BUG-BE-05 | 🟠 HIGH | ohlcv_fetcher.py | Intraday scheduler uses period=60d; inference expects 730d |
| ✅ BUG-BE-06 | 🟠 HIGH | optuna_tuner.py + ml_pipeline.py | Optuna best params saved but never loaded in training pipeline |
| ✅ BUG-BE-07 | 🟠 HIGH | schemas/auth.py | UserResponse missing trial_ends_at and paused_until |
| ✅ FIND-04 | 🔴 CRITICAL | schemas/auth.py + AuthProvider.tsx | UserResponse has no is_pro field — Pro features always denied in production |
| ✅ BUG-BE-09 | 🟡 MEDIUM | gas_precompute.py | Crypto GAS uses neutral sentiment; ignores Crypto Fear & Greed |
| ✅ BUG-BE-12 | 🟡 MEDIUM | prediction_service.py | Outcome resolver serial price fetches — slow with many symbols |
| ✅ BUG-BE-13 | 🟡 MEDIUM | ml_pipeline.py | inject_external_features tz-mismatch — silently zeros all external signals on daily data |
| ✅ BUG-BE-14 | 🟡 MEDIUM | gas_precompute.py | Grade history reads post-upsert grade — never records changes |
| ✅ BUG-BE-15 | 🟡 MEDIUM | technical_service.py | Module-level registry singleton may be stale after new training |
| ✅ BUG-BE-16 | 🔵 LOW | billing.py | Imports get_current_user from auth.py instead of deps.py |
| ✅ BUG-BE-17 | 🔵 LOW | ohlcv_fetcher.py | validate_row() defined but never called |
| ✅ BUG-BE-18 | 🔵 LOW | scheduler.py | weekly_digest cron time (08:00) vs plan doc (07:00) mismatch |
| ✅ BUG-FE-01 | 🟠 HIGH | GlobalTickerSearch.tsx | Keyboard nav broken — mouse hover creates gaps in activeIdx |
| ✅ BUG-FE-02 | 🟡 MEDIUM | page.tsx | CryptoFearGreedPanel norm fallback type assertion fragile |
| ✅ BUG-FE-03 | 🟡 MEDIUM | page.tsx | Header div indentation corruption from Sprint 41 edit |
| ✅ BUG-FE-04 | 🟡 MEDIUM | AuthProvider.tsx | Dev mock user missing optional fields — billing broken in dev |
| ✅ BUG-FE-05 | 🔵 LOW | GlobalTickerSearch.tsx | useDeferredValue + useSWR imported but unused |
| ✅ BUG-FE-06 | 🔵 LOW | page.tsx | CryptoFearGreedPanel SWR cache lost on symbol switch |
| ✅ BUG-FE-07 | 🔵 LOW | page.tsx | Gold futures mapped to NYMEX:GC — should be COMEX:GC1! |

**Total: 23 bugs, 4 architectural findings, 5 performance improvements**
**Critical: 2 | High: 7 | Medium: 8 | Low: 6**
