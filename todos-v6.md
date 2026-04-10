# Fin-Eye — Todos v6
> **Version:** 6.0
> **Created:** 2026-03-21  
> **Last updated:** April 2026 — all blockers and gaps resolved
> **Author:** Full codebase audit before starting todos-v5 implementation
> **Status:** ✅ All items complete
>
> **Legend:** 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Nice-to-have
> **Prefixes:** BE = Backend · FE = Frontend · DB = Database · ML = Machine Learning

---

## WHY THIS FILE EXISTS

Before starting todos-v5, a full codebase read was done across:
- `backend/app/api/v1/endpoints/technical.py`
- `backend/app/services/technical_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/model_registry.py`
- `backend/app/services/ml_pipeline.py`
- `frontend/components/TimeframeGrid.tsx`
- `frontend/components/TickerDataPanel.tsx`
- `frontend/app/page.tsx`
- `backend/requirements.txt`

Several gaps, missing pieces, and blockers were found that todos-v3/v4/v5 either assumed were
done or didn't cover. This file documents them in priority order.

---

## PART A — BLOCKERS: Must fix before todos-v5 work begins

### A1. LLM is Ollama (local) — todos-v5 assumes Anthropic API

- [x] ✅ `BE` `ANTHROPIC_API_KEY` in `.env.example` — Done Sprint 0
- [x] ✅ `BE` `anthropic>=0.25.0` in `requirements.txt` — Done Sprint 0
- [x] ✅ `BE` `llm_service.py` rewritten with two backends — Done Sprint 0: `AnthropicBackend` primary + `OllamaBackend` fallback.

### A2. `technical.py` is missing the new endpoints todos-v5 needs

- [x] ✅ `BE` All three endpoints in `technical.py` — Done Sprint 1+: `model-details`, `prediction-stats`, `price-targets` all fully implemented.

### A3. `MLPrediction` model does not exist

- [x] ✅ `DB` `ml_prediction.py` model + Alembic migration — Done Sprint 2. Registered in `__init__.py`.

### A4. `requirements.txt` is missing all todos-v5 ML dependencies

- [x] ✅ `BE` `lightgbm`, `optuna`, `shap`, `anthropic` added to `requirements.txt` — Done Sprint 0.

---

## PART B — GAPS: Things todos-v3/v4/v5 assumed exist but don't yet

### B1. No `api_bulk.ts` frontend file exists (used by TickerDataPanel)

- [x] ✅ `FE` `frontend/lib/api_bulk.ts` exists and is complete — Verified Sprint 0+.

### B2. `admin_bulk.py` endpoint — verify it has `ticker-status/{symbol}`

- [x] ✅ `BE` `GET /api/v1/admin/ticker-status/{symbol}` exists in `admin_bulk.py` — Verified.

### B3. LLM insight is not shown on the dashboard page

- [x] ✅ `FE`+`BE` `LLMInsightCard.tsx` — Done Sprint 1+12: built with SSE streaming, progressive section rendering, wired to dashboard.

### B4. `ModelDetailsPanel.tsx` does not exist

- [x] ✅ `FE` `ModelDetailsPanel.tsx` — Done Sprint 4: side drawer with 4 tabs.

### B5. `TimeframeGrid` missing agreement banner + ModelDetailsPanel link

- [x] ✅ `FE` Multi-timeframe agreement text banner in `TimeframeGrid.tsx` — Done Sprint 33 via `signalUtils.ts`.
- [x] ✅ `FE` "⚙ Model Details →" link in slide-over — Done Sprint 6.
- [x] ✅ `FE` "What drove this?" SHAP section — Done Sprint 24 as `ShapPanel` in `app/page.tsx`.

### B6. Confidence label system is partially done but inconsistent

- [x] ✅ `FE` `frontend/lib/signalUtils.ts` — Done Sprint 33: `interpretConfidence()` + `directionConfig()` shared across `TimeframeGrid.tsx` and `LLMInsightCard.tsx`. Closes `todos-v6 B6`.

### B7. No `/model-info/{symbol}` route exists

- [x] ✅ `FE` `app/model-info/[symbol]/page.tsx` — Done Sprint 6: 7-tab deep-dive page.

---

## PART C — THINGS THAT LOOK GOOD (no action needed)

These were verified during the audit and are solid:

- ✅ `technical_service.py` — dynamic timeframe detection from registry
- ✅ `model_registry.py` — versioned, champion/retired lifecycle, JSONL + index JSON
- ✅ `ml_pipeline.py` — MLflow integration, quality gates, 3-model competition, TIMEFRAME_HORIZON
- ✅ `TimeframeGrid.tsx` — implements todos-v5 Phase 1 UX goals (confirmed Sprint 33)
- ✅ `TickerDataPanel.tsx` — todos-v4 Phase 8.2 complete
- ✅ `technical.py` — all required endpoints present
- ✅ `model_registry_index.json` is in `.gitignore`
- ✅ `backend/backups/` is in `.gitignore`

---

## PART D — RECOMMENDED IMPLEMENTATION ORDER (completed)

All sprints from this plan have been executed (Sprints 0–40). See `SPRINT_PROGRESS.md`.

---

## PART E — QUICK WINS

- [x] ✅ `BE` `ANTHROPIC_API_KEY=` in `backend/.env.example` — Done Sprint 0.
- [x] ✅ `BE` `lightgbm`, `optuna`, `shap`, `anthropic` in `requirements.txt` — Done Sprint 0.
- [x] ✅ `FE` "What drove this?" `ShapPanel` in `app/page.tsx` — Done Sprint 24.
- [x] ✅ `FE` Multi-timeframe agreement banner in `TimeframeGrid.tsx` — Done Sprint 33.
- [x] ✅ `BE` `model-details`, `prediction-stats`, `price-targets` endpoints — Done Sprint 4.

---

*todos-v6.md — Created 2026-03-21. Last updated: April 2026.*
*All blockers (Part A) and gaps (Part B/E) fully resolved across Sprints 0–40.*
*Companion files: todos-v5.md (feature specs), todos-v4.md (bulk pipeline), todos-v3.md (app polish).*
