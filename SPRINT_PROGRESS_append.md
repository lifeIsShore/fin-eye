

---

## ✅ Bug Fix Session 1 — Complete (April 2026)

**Playbook:** `new-bugs-01-04-26.md`  
**Source:** Live code audit of 18 bugs across security, correctness, reliability, and DevOps categories.

### Applied
| Bug | Files Changed | Fix |
|-----|--------------|-----|
| BUG-016 | `app/config.py` | CORS `allowed_origins` default changed from `["*"]` to `["http://localhost:3000"]` |
| BUG-003 | `app/config.py`, `services/ml_pipeline.py` | `ML_ARTIFACT_DIR` env var added; artifact path decoupled from hardcoded local path |
| BUG-010 | `services/model_registry.py` | `FileLock` (filelock) added to `save_winner()` — prevents concurrent JSONL write corruption |
| BUG-018 | `services/backtesting_service.py` | Invalid date strings now raise HTTP 422; `start_date >= end_date` also raises 422 |
| BUG-009 | `services/gas_precompute.py` | `GAS_THRESHOLD_STRONG/MILD/MIXED/WEAK` constants defined; hardcoded numbers eliminated |

### Already Fixed (verified in code, no changes needed)
| Bug | Finding |
|-----|---------|
| BUG-011 | `volume` columns already `BigInteger` in `market.py` |
| BUG-015 | Global exception handler already present in `main.py` |
| BUG-014 | GAS cache warm already uses `asyncio.create_task` |
| BUG-004 | `_compute_technical_score` already uses `run_in_executor` |

---

## ✅ Bug Fix Session 2 — Complete (April 2026)

**Playbook:** `new-bugs-01-04-26.md` (updated)

### Applied
| Bug | Files Changed | Fix |
|-----|--------------|-----|
| BUG-005 | `app/middleware/rate_limit.py` (NEW), `app/main.py` | slowapi `Limiter` wired globally; `RateLimitExceeded` → clean 429 JSON + `Retry-After: 60`; `app.state.limiter` set |
| BUG-007 | `services/scheduler.py` | `SQLAlchemyJobStore` backed by PostgreSQL (`apscheduler_jobs` table, auto-created); `_make_scheduler()` factory with in-memory fallback for unit tests |
| BUG-002 | `backend/Dockerfile`, `backend/.dockerignore` (NEW) | Multi-stage build (builder → runtime); non-root `appuser`; `.dockerignore` excludes `.env`, logs, ML artifacts, tests, backups |
| BUG-012 | `services/gas_precompute.py` | Verified already correct — both equity and crypto paths in `_compute_sentiment_score` clamp to `[0, 100]` |

### Security Action Required
| Bug | Action |
|-----|--------|
| BUG-013 | `backend/.env` **confirmed tracked in git index** along with 3 `.joblib` model files. Run `fix_bug013.bat` from project root, then **rotate all secrets immediately**: `JWT_SECRET`, `REDIS_PASSWORD`, `FINNHUB_API_KEY`, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`, and all other keys in `backend/.env` |

### Files Created This Session
```
backend/app/middleware/rate_limit.py    NEW — slowapi limiter + 429 handler
backend/.dockerignore                   NEW — build context exclusions
fix_bug013.bat                          NEW — git untrack script (run once then delete)
```

### Scratch File to Delete
```
backend/app/services/scheduler_header.py   — safe to delete (stub only)
```

---

## Sprint 41 — Up Next

**Sources:** `todos-v3.md` §17–18 (multi-asset expansion · ML improvements) · `todos-v5.md` Phase 4.4 + 7.1

### Deliverables
- [ ] **Crypto symbol expansion** — BTC-USD, ETH-USD in `DEFAULT_SYMBOLS`; asset class badge on ticker header; Crypto Fear & Greed surfaced on dashboard
- [ ] **Commodity + FX + ETF expansion** — GC=F, CL=F, EURUSD=X, GBPUSD=X, USDJPY=X; seasonal features for commodities; interest rate differential for FX
- [ ] **Optuna hyperparameter tuning** — `tune_xgboost()` + `tune_lightgbm()` (30 trials); gated by `ENABLE_HYPERTUNING=True`; overnight scheduler job at 02:00 UTC
- [ ] **LSTM model as 4th competitor** — PyTorch `LSTMWrapper`; sequence length 20; attention mechanism; quality-gated same as others
- [ ] **Kelly Criterion position sizing** — `kelly_fraction()` in `prediction_service.py`; exposed via `GET /technical/{symbol}/position-sizing`; wired into `LLMInsightCard.tsx`
