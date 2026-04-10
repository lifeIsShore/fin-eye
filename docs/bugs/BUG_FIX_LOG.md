# Fin-Eye — Bug Fix Log
> Tracks all bug fix sessions separately from the sprint log.
> Reference: `new-bugs-01-04-26.md` for full playbook.

---

## Session 1 — April 2026

**Bugs fixed:** BUG-003, BUG-009, BUG-010, BUG-016, BUG-018  
**Bugs verified already fixed:** BUG-004, BUG-011, BUG-014, BUG-015

| Bug | File(s) | Change |
|-----|---------|--------|
| BUG-016 | `app/config.py` | `allowed_origins` default `["*"]` → `["http://localhost:3000"]` |
| BUG-003 | `app/config.py`, `services/ml_pipeline.py` | `ML_ARTIFACT_DIR` env var; path decoupled |
| BUG-010 | `services/model_registry.py` | `FileLock` on `save_winner()` |
| BUG-018 | `services/backtesting_service.py` | HTTP 422 on invalid/inverted dates |
| BUG-009 | `services/gas_precompute.py` | `GAS_THRESHOLD_*` named constants |

---

## Session 2 — April 2026

**Bugs fixed:** BUG-002, BUG-005, BUG-007  
**Bugs verified already fixed:** BUG-001, BUG-012  
**Security action required:** BUG-013

| Bug | File(s) | Change |
|-----|---------|--------|
| BUG-005 | `middleware/rate_limit.py` (NEW), `main.py` | slowapi rate limiting wired globally |
| BUG-007 | `services/scheduler.py` | SQLAlchemy jobstore (PostgreSQL) via `_make_scheduler()` |
| BUG-002 | `Dockerfile`, `.dockerignore` (NEW) | Multi-stage build; non-root `appuser` |

**BUG-013 — ⚠️ Action required:**
- `backend/.env` confirmed tracked in git index
- `backend/data/models/AAPL_*.joblib` confirmed tracked
- Fix script: run `fix_bug013.bat` from project root
- After running: rotate `JWT_SECRET`, `REDIS_PASSWORD`, and all API keys in `backend/.env`

**New files created:**
- `backend/app/middleware/rate_limit.py`
- `backend/.dockerignore`
- `fix_bug013.bat` ← run once then delete

**Scratch file to delete:**
- `backend/app/services/scheduler_header.py`

---

## Open Items

| Item | Status |
|------|--------|
| Run `fix_bug013.bat` | ⚠️ Pending — must be done manually |
| Rotate all secrets after BUG-013 fix | ⚠️ Pending |
| Delete `scheduler_header.py` | ⚠️ Handled by `fix_bug013.bat` |
| Delete `model_store/` if empty | ⚠️ Handled by `fix_bug013.bat` |
| Add `@limiter.limit()` to auth endpoints | 🔧 Next sprint |
