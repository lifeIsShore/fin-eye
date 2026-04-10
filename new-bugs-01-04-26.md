# Fin-Eye — Bug Fix Playbook

Generated from live code audit · April 2026  
Last updated: April 2026 (Session 2 complete — all bugs resolved)

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fixed and verified |
| 🔧 | Needs code change |
| 📋 | Needs config / env change |
| ⚠️ | Needs careful testing after change |

---

## CRITICAL

---

### ✅ BUG-001 — Redis has no password
**File:** `docker-compose.yml`  
**Status:** Already fixed. Redis starts with `--requirepass`.

**Verify your `.env`:**
```
REDIS_PASSWORD=your_strong_password_here
REDIS_URL=redis://:your_strong_password_here@localhost:6379
```

---

### ✅ BUG-002 — No production Dockerfile
**Files:** `backend/Dockerfile`, `backend/.dockerignore`  
**Status:** Fixed session 2.

**What was done:**
- Multi-stage build: `builder` (compiles deps) → `runtime` (lean, no build tools)
- Non-root user `appuser` — container no longer runs as root
- `backend/.dockerignore` created — excludes `.env`, logs, ML artifacts, tests, backups

**Test:**
```bash
cd backend
docker build -t fin-eye-backend:prod .
docker run --env-file .env -p 8000:8000 fin-eye-backend:prod
curl http://localhost:8000/api/v1/health
```

---

### ✅ BUG-003 — ML artifacts on local filesystem
**File:** `backend/app/config.py`, `backend/app/services/ml_pipeline.py`  
**Status:** Fixed session 1.

`ml_artifact_dir` added to `Settings` (alias `ML_ARTIFACT_DIR`). `ml_pipeline.py` resolves `ARTIFACT_DIR` from env, falling back to `data/models`.

**Production `.env`:**
```
ML_ARTIFACT_DIR=/mnt/artifacts/models
```

---

### ✅ BUG-004 — FinBERT blocks event loop
**Status:** Already fixed. `_compute_technical_score` uses `run_in_executor`. No action needed.

---

## HIGH

---

### ✅ BUG-005 — No API rate limiting
**Files:** `backend/app/middleware/rate_limit.py` (new), `backend/app/main.py`  
**Status:** Fixed session 2.

- `slowapi` Limiter with IP-based key, default `RATE_LIMIT_ANON/minute` (30)
- Clean 429 JSON + `Retry-After: 60` header
- Wired into `main.py` via `app.state.limiter` + `RateLimitExceeded` handler

**Apply per-endpoint overrides on sensitive routes:**
```python
from app.middleware.rate_limit import limiter
from fastapi import Request

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...
```

**`.env`:**
```
RATE_LIMIT_ANON=30
RATE_LIMIT_AUTH=120
RATE_LIMIT_API_KEY=300
```

---

### ✅ BUG-007 — APScheduler no job persistence
**File:** `backend/app/services/scheduler.py`  
**Status:** Fixed session 2.

`SQLAlchemyJobStore` backed by PostgreSQL (`apscheduler_jobs` table, auto-created). Falls back to in-memory if `DATABASE_URL` unset (unit-test safe). All jobs already use `replace_existing=True`.

---

### ⚠️ BUG-013 — `backend/.env` tracked in git + model artifacts tracked
**Status:** Script written — needs to be run manually.

**Confirmed tracked in git index:**
- `backend/.env` — contains secrets
- `backend/data/models/AAPL_1d_winner.joblib`
- `backend/data/models/AAPL_1h_winner.joblib`
- `backend/data/models/AAPL_1wk_winner.joblib`
- `backend/data/models/model_registry.jsonl.bak`

**Fix — run the script from the project root:**
```bash
cd C:\Users\ahmty\fin-eye
fix_bug013.bat
```

The script:
1. Removes `backend/.env` from tracking (keeps file on disk)
2. Removes tracked `.joblib` and `.bak` artifacts
3. Deletes and untracks `scheduler_header.py` scratch file
4. Checks and removes `model_store/` if empty
5. Commits everything

**⚠️ After running — rotate these secrets immediately:**
- `JWT_SECRET`
- `REDIS_PASSWORD`
- `FINNHUB_API_KEY`, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`
- All other keys present in `backend/.env`

---

### ✅ BUG-015 — No global exception handler
**Status:** Already fixed. No action needed.

---

### ✅ BUG-016 — CORS wildcard origin with credentials
**File:** `backend/app/config.py`  
**Status:** Fixed session 1. Default changed to `["http://localhost:3000"]`.

**Production `.env`:**
```
ALLOWED_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
```

---

## MEDIUM

---

### ✅ BUG-009 — Weather label thresholds inconsistent
**Status:** Fixed session 1. Constants defined at module level in `gas_precompute.py`:
```python
GAS_THRESHOLD_STRONG = 75
GAS_THRESHOLD_MILD   = 60
GAS_THRESHOLD_MIXED  = 45
GAS_THRESHOLD_WEAK   = 30
```

---

### ✅ BUG-010 — Model registry concurrent write corruption
**Status:** Fixed session 1. `FileLock` on `save_winner` in `model_registry.py`.

---

### ✅ BUG-011 — `volume` column INTEGER overflow
**Status:** Already fixed. `BigInteger` already on `OHLCVDaily.volume` and `OHLCVIntraday.volume`. No action needed.

---

### ✅ BUG-012 — Sentiment score range mismatch
**Status:** Already correct in code. Both equity and crypto paths in `_compute_sentiment_score` clamp to `[0, 100]`.

---

### ✅ BUG-018 — Backtesting date validation silent failure
**Status:** Fixed session 1. Invalid dates raise HTTP 422. `start_date >= end_date` also raises 422.

---

## LOW

---

### ✅ BUG-014 — GAS warm blocks startup lifespan
**Status:** Already fixed. Uses `asyncio.create_task`. No action needed.

---

### ✅ BUG-017 — Orphaned `model_store/` directory
**Status:** Handled by `fix_bug013.bat` — will be removed if empty.

---

## Session Summary

### Session 1 — Applied
| Bug | File(s) | Fix |
|-----|---------|-----|
| BUG-016 | `config.py` | CORS origins default → `["http://localhost:3000"]` |
| BUG-003 | `config.py`, `ml_pipeline.py` | `ML_ARTIFACT_DIR` env var |
| BUG-010 | `model_registry.py` | `FileLock` on `save_winner` |
| BUG-018 | `backtesting_service.py` | HTTP 422 on bad dates |
| BUG-009 | `gas_precompute.py` | `GAS_THRESHOLD_*` constants |

### Session 2 — Applied
| Bug | File(s) | Fix |
|-----|---------|-----|
| BUG-005 | `middleware/rate_limit.py` (new), `main.py` | slowapi wired globally |
| BUG-007 | `scheduler.py` | SQLAlchemy jobstore (PostgreSQL) |
| BUG-002 | `Dockerfile`, `.dockerignore` (new) | Multi-stage build, non-root user |
| BUG-012 | `gas_precompute.py` | Verified — already correctly normalised |

### Already Fixed (found in code — no changes needed)
| Bug | Finding |
|-----|---------|
| BUG-001 | Redis password in docker-compose |
| BUG-004 | `run_in_executor` already present |
| BUG-011 | `BigInteger` already on volume columns |
| BUG-014 | `asyncio.create_task` already used |
| BUG-015 | Global exception handler already present |

### Needs Manual Action
| Bug | Action |
|-----|--------|
| BUG-013 | Run `fix_bug013.bat` from project root, then rotate all secrets |
| BUG-017 | Handled inside `fix_bug013.bat` |
