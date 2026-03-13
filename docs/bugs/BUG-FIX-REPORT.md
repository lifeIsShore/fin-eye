# 🛠️ Fin-Eye — Bug Fix Report
> Maintained by Claude. Updated: 2026-03-10
> This file is the single source of truth for all bugs that have been **fixed** in the codebase.
> For open / unfixed bugs, see `BUG-REPORT.md`.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ Fixed | Code change applied and verified |
| ⚙️ Partial | Fix applied but requires a manual action to take effect |
| 📋 Pending | Fix documented, not yet applied |

---

## Session 1 — 2026-03-10

### FIX-001 — Timeframe Mismatch in Technical Consensus ✅
**Original Bug:** BUG-003 (from BUG-REPORT.md)
**Severity:** 🔴 Critical
**File:** `backend/app/services/technical_service.py` line ~21

**Problem:**
`TIMEFRAMES = ["1h", "1d", "1wk", "1mo"]` — the inference engine was asking for models
that were never trained. The ML pipeline only produces `1h` and `4h` artifacts. For every
symbol, `1d`/`1wk`/`1mo` signals failed silently, and since all timeframes failed for
non-AAPL symbols, `compute_technical_consensus()` raised an error, causing GAS to fall
back to `50.0` for the technical component across all symbols.

**Fix Applied:**
```python
# BEFORE
TIMEFRAMES = ["1h", "1d", "1wk", "1mo"]

# AFTER
TIMEFRAMES = ["1h", "4h"]
```

**Impact:** Technical consensus now correctly evaluates trained models instead of erroring.

---

### FIX-002 — 4h Inference: Wrong yfinance Period ✅
**Original Bug:** Newly discovered during re-audit
**Severity:** 🔴 Critical
**File:** `backend/app/services/technical_service.py` — `generate_timeframe_signal()`

**Problem:**
The inference function used `period="5y"` for the `4h` timeframe. yfinance does not
support 5-year intraday data — it silently returns an empty DataFrame. This caused every
`4h` signal to fail with `"Not enough data to run inference"`, meaning the consensus
always ran on only 1 out of 2 timeframes, and for all non-AAPL symbols failed entirely.

**Fix Applied:**
```python
# BEFORE
period = "730d" if timeframe == "1h" else "5y"

# AFTER
period = "730d" if timeframe in ("1h", "4h") else "5y"
```

---

### FIX-003 — 4h Inference: Invalid yfinance Interval ✅
**Original Bug:** Newly discovered during re-audit
**Severity:** 🔴 Critical
**File:** `backend/app/services/technical_service.py` — `generate_timeframe_signal()`

**Problem:**
The inference function passed `interval="4h"` directly to yfinance. yfinance does not
support a `4h` interval — it returns empty data. The training pipeline correctly resamples
`1h → 4h`, but the inference path did not mirror this. Result: every `4h` signal was
silently broken even when a trained model existed.

**Fix Applied:**
```python
# BEFORE
records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=timeframe)

# AFTER — fetch 1h, then resample to 4h (mirrors training pipeline exactly)
fetch_interval = "1h" if timeframe == "4h" else timeframe
records = OHLCVFetcher.fetch_historical_data(symbol, period=period, interval=fetch_interval)

if timeframe == "4h":
    df = df.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
```

---

### FIX-004 — Weather Label Thresholds Inconsistent with PRD ✅
**Original Bug:** BUG-009 (from BUG-REPORT.md)
**Severity:** 🟡 Medium
**File:** `backend/app/services/gas_precompute.py` — `_gas_to_weather()`

**Problem:**
The code had 4 labels with shifted thresholds. The PRD defines 5 labels:
Strong Tailwind (80–100), Mild Support (60–79), Mixed Signals (40–59),
Headwind (20–39), High Instability (0–19). A score of 82 showed "Mild Support"
when it should have shown "Strong Tailwind".

**Fix Applied:**
```python
# BEFORE (4 labels, wrong thresholds)
if score >= 75: return "Mild Support"
if score >= 55: return "Mixed Signals"
if score >= 35: return "Headwind"
return "High Instability"

# AFTER (5 labels, matches PRD exactly)
if score >= 80: return "Strong Tailwind"
if score >= 60: return "Mild Support"
if score >= 40: return "Mixed Signals"
if score >= 20: return "Headwind"
return "High Instability"
```

Also updated the module-level docstring to reflect the corrected thresholds.

---

### FIX-005 — GAS Cache Warm Blocks Server Startup ✅
**Original Bug:** BUG-014 (from BUG-REPORT.md)
**Severity:** 🟢 Low (🔴 in production behind a load balancer)
**File:** `backend/app/main.py` — `lifespan()`

**Problem:**
On startup, `run_gas_precompute_batch()` was awaited synchronously inside the lifespan
context before the server began serving traffic. If ML inference or FRED lookups were
slow (cold start), this could take 30–120 seconds. Any load balancer with a 30-second
health check timeout would kill the process before it served a single request.

**Fix Applied:**
Moved the GAS warm to a fire-and-forget `asyncio.create_task()` with a 10-second delay,
so the server is fully ready and health checks pass before cache warming begins.

```python
# BEFORE — blocks lifespan
async with AsyncSessionLocal() as session:
    summary = await run_gas_precompute_batch(session)

# AFTER — non-blocking background task
async def _warm_gas_cache_bg():
    await asyncio.sleep(10)  # Let health checks pass first
    ...

asyncio.create_task(_warm_gas_cache_bg())
```

---

### FIX-006 — No Global Exception Handler (Stack Traces Leaked to Clients) ✅
**Original Bug:** BUG-015 (from BUG-REPORT.md)
**Severity:** 🟠 High
**File:** `backend/app/main.py`

**Problem:**
Unhandled exceptions returned raw stack traces in HTTP 500 responses, exposing
internal file paths, library versions, and sometimes SQL query fragments.

**Fix Applied:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )
```

---

### FIX-007 — Redis Has No Password ⚙️
**Original Bug:** BUG-001 (from BUG-REPORT.md)
**Severity:** 🔴 Critical
**File:** `docker-compose.yml`

**Problem:**
Redis had no `requirepass` configuration. Any client that could reach port 6379
could read all cached GAS scores, session tokens, and macro data — or inject
arbitrary cache entries to corrupt API responses.

**Fix Applied to Code:**
```yaml
# docker-compose.yml — redis service command updated to:
command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
         --requirepass "${REDIS_PASSWORD:-changeme_set_REDIS_PASSWORD_in_env}"
```

**Manual Action Required:**
1. Generate a password: `python -c "import secrets; print(secrets.token_hex(24))"`
2. Set `REDIS_PASSWORD=<generated>` in `backend/.env`
3. Restart Redis: `docker compose up -d redis`

The `REDIS_PASSWORD` field has been added to `backend/.env` with instructions.

---

### FIX-008 — Redis Password Not Applied to Connection URL ✅
**Original Bug:** Newly discovered during re-audit
**Severity:** 🟠 High
**File:** `backend/app/db/redis_client.py`

**Problem:**
`redis_client.py` read `settings.redis_url` directly. Even after setting `REDIS_PASSWORD`
in `.env`, the URL `redis://localhost:6379` has no password, so the connection still
skipped auth. The developer had to manually keep two `.env` fields in sync.

**Fix Applied:**
Added `_build_redis_url()` which auto-injects the password into the URL:
```python
def _build_redis_url() -> str:
    url = settings.redis_url
    password = settings.redis_password
    if password and "@" not in url:
        url = url.replace("redis://", f"redis://:{password}@", 1)
    return url
```
Now only `REDIS_PASSWORD` needs to be set — `REDIS_URL` is updated automatically.

---

### FIX-009 — PostgreSQL max_connections Too Low ✅
**Original Bug:** BUG-008 (from BUG-REPORT.md)
**Severity:** 🟠 High
**File:** `docker-compose.yml`

**Problem:**
`max_connections=100` could be exhausted by 4 Uvicorn workers + APScheduler sessions
+ pgAdmin, causing `FATAL: sorry, too many clients already` 500 errors under moderate load.

**Fix Applied:**
```yaml
# BEFORE
-c max_connections=100

# AFTER
-c max_connections=200
```

---

### FIX-010 — No Production Dockerfiles ✅
**Original Bug:** BUG-002 (from BUG-REPORT.md)
**Severity:** 🔴 Critical
**Files Created:**
- `backend/Dockerfile`
- `frontend/Dockerfile`

**Problem:**
The project had no Dockerfiles, making it impossible to containerise or deploy
to any cloud platform (AWS ECS, Render, Fly.io, etc.).

**Fix Applied:**
- `backend/Dockerfile` — Python 3.11-slim, gunicorn + uvicorn workers
- `frontend/Dockerfile` — Multi-stage Node 20-alpine build with Next.js standalone output

---

### FIX-011 — Frontend Missing API Base URL ✅
**Original Bug:** BUG-006 (from BUG-REPORT.md)
**Severity:** 🟡 Medium
**File Created:** `frontend/.env.local`

**Problem:**
`lib/api.ts` fell back to `http://localhost:8000` with no explicit configuration.
In any non-standard local environment (Docker, WSL, different port) this would silently
break all API calls with no clear error.

**Fix Applied:**
Created `frontend/.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

### FIX-012 — .env File Could Be Accidentally Committed ✅
**Original Bug:** BUG-013 (from BUG-REPORT.md)
**Severity:** 🟠 High
**File:** `.gitignore`

**Problem:**
`.gitignore` had a generic `.env` rule but not the explicit paths `backend/.env`
and `frontend/.env.local`. A developer running `git add .` from a subdirectory
could accidentally stage real secrets.

**Fix Applied:**
Added explicit entries to `.gitignore`:
```
backend/.env
frontend/.env.local
```

---

### FIX-013 — Backtesting Accepts Invalid Date Ranges ✅
**Original Bug:** BUG-018 (from BUG-REPORT.md)
**Severity:** 🟡 Medium
**File:** `backend/app/schemas/backtest_models.py`

**Problem:**
No server-side validation on `start_date` / `end_date`. Users could submit:
- Future dates (empty results, no error)
- Reversed ranges (`start > end`, pandas crash)
- 20-year ranges (OOM crash)
- Ranges under 1 year (below ML feature engineering minimum)

**Fix Applied:**
Added Pydantic v2 validators to `BacktestRequest`:
- Date format validation (YYYY-MM-DD)
- Future date rejection
- `end_date > start_date` enforcement
- Minimum 1-year range required
- Maximum 20-year range cap

---

### FIX-014 — Technical Endpoints Blocked Event Loop ✅
**Original Bug:** Newly discovered during re-audit
**Severity:** 🟠 High
**File:** `backend/app/api/v1/endpoints/technical.py`

**Problem:**
Both `train_technical_models` and `get_latest_technical_consensus` were defined as
synchronous `def` functions inside a FastAPI async application.
- The training endpoint blocked during background task setup
- The consensus endpoint ran CPU-bound ML inference (joblib/sklearn) directly on
  the asyncio event loop, stalling all other requests for up to 2–3 seconds per call

**Fix Applied:**
- Both functions changed to `async def`
- `get_latest_technical_consensus` now uses `run_in_executor` for the CPU-bound call:
```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, compute_technical_consensus, symbol.upper())
```

---

### FIX-015 — Data Seeding URLs Were Wrong in EXECUTION-PLAN.md ✅
**Original Bug:** Newly discovered during re-audit
**Severity:** 🟡 Medium (causes confusion / failed curl commands)
**File:** `EXECUTION-PLAN.md`

**Problem:**
The plan documented URLs with hyphens (`/fetch-ohlcv`, `/fetch-macro`, `/fetch-news`)
but the actual FastAPI router uses forward-slashes (`/fetch/ohlcv`, `/fetch/macro`,
`/fetch/news`). Every curl command in the plan would have returned 404.

**Fix Applied:**
All three endpoint references corrected throughout the document, including the
Quick Reference table at the bottom.

**Correct URLs:**
```
POST /api/v1/data/fetch/ohlcv
POST /api/v1/data/fetch/macro
POST /api/v1/data/fetch/news?lookback_days=7
```

---

## Bugs Still Open (Not Yet Fixed)

These are documented in `BUG-REPORT.md` and have not been addressed in code yet.
They require either infrastructure work, significant refactoring, or external dependencies.

| ID | Title | Severity | Reason Not Fixed Yet |
|---|---|---|---|
| BUG-003 | ML artifacts on local filesystem (no S3) | 🔴 Critical | Requires AWS S3 setup |
| BUG-004 | FinBERT blocks event loop | 🔴 Critical | Requires Celery/worker refactor |
| BUG-005 | No API rate limiting | 🟠 High | Requires `slowapi` install + integration |
| BUG-006 | LSTM model not implemented | 🟠 High | Requires ML development work |
| BUG-007 | APScheduler no job persistence | 🟠 High | Requires SQLAlchemy jobstore setup |
| BUG-010 | Model registry is a flat file | 🟡 Medium | Requires DB migration + refactor |
| BUG-011 | volume column INTEGER overflow | 🟡 Medium | ⚙️ Migration written, needs `alembic upgrade head` |
| BUG-016 | CORS + credentials risk | 🟠 High | Needs production origin list |
| BUG-017 | Orphaned model_store/ directory | 🟢 Low | Needs cleanup decision |

> **BUG-011 note:** The Alembic model fix is done. Run this to apply it to the DB:
> ```bash
> cd backend
> alembic revision --autogenerate -m "volume_bigint"
> alembic upgrade head
> ```

---

## Fix Statistics

| Session | Date | Bugs Fixed | New Bugs Found | Files Changed |
|---|---|---|---|---|
| Session 1 | 2026-03-10 | 15 | 5 (NEW-A through NEW-E) | 10 |

**Files modified in Session 1:**
- `backend/app/services/technical_service.py`
- `backend/app/services/gas_precompute.py`
- `backend/app/main.py`
- `backend/app/db/redis_client.py`
- `backend/app/api/v1/endpoints/technical.py`
- `backend/app/schemas/backtest_models.py`
- `docker-compose.yml`
- `.gitignore`
- `EXECUTION-PLAN.md`

**Files created in Session 1:**
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/.env.local`

---

*Report generated: 2026-03-10 | Author: Claude Sonnet 4.6*
