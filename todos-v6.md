# Fin-Eye — Todos v6
> **Version:** 6.0
> **Created:** 2026-03-21
> **Author:** Full codebase audit before starting todos-v5 implementation
> **Status:** Pre-flight blockers + gaps found during audit — fix these BEFORE or ALONGSIDE todos-v5
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

**What was found:** `llm_service.py` is entirely built around a local Ollama instance
(`http://localhost:11434`, model `llama3:8b`). It has one method: `get_explanation()` which
produces a short 2–3 sentence generic summary.

**What todos-v5 needs:** A structured prompt with investment manager persona, 6-section
output format, and rich inputs (ML signals, macro, sentiment, price targets). This requires
either Anthropic API (`claude-sonnet`) or OpenAI. The `.env.example` already has
`OPENAI_API_KEY` and `OPENAI_MODEL=gpt-4o-mini`. There is no Anthropic API key configured yet.

**Decision needed:** Which LLM to use?
- Option A: Anthropic (`claude-sonnet-4-20250514`) — best quality, consistent structured output
- Option B: OpenAI (`gpt-4o`) — already in `.env.example`
- Option C: Keep Ollama for local dev + add Anthropic/OpenAI for production

**Recommended:** Option A for production (Anthropic), Option C for local dev fallback.

- [x] ✅ `BE` `ANTHROPIC_API_KEY` in `.env.example` — Done Sprint 0
- [x] ✅ `BE` `anthropic>=0.25.0` in `requirements.txt` — Done Sprint 0
- [x] ✅ `BE` `llm_service.py` rewritten with two backends — Done Sprint 0: `AnthropicBackend` primary + `OllamaBackend` fallback.
  - Primary: Anthropic API (`/v1/messages`) — used when `ANTHROPIC_API_KEY` is set
  - Fallback: Ollama — used when Anthropic key is missing (local dev)
  - Shared interface: `async def generate_investment_insight(inputs: InsightInput) -> InsightOutput`
  - Keep `OllamaService` class intact — just add `AnthropicService` alongside it
  - **File:** `backend/app/services/llm_service.py`

### A2. `technical.py` is missing the new endpoints todos-v5 needs

**What was found:** `technical.py` has: `trained-symbols`, `registry-status`,
`train-status/{symbol}`, `train/{symbol}`, `/{symbol}/latest`. That's it.

**What todos-v5 requires:** Three new endpoints:
- `GET /{symbol}/model-details` — full model transparency (Phase 2.1)
- `GET /{symbol}/prediction-stats` — live accuracy from prediction DB (Phase 5.4)
- `GET /{symbol}/price-targets` — probabilistic price targets (Phase 6.2)

None of these exist yet. They need to be built as part of todos-v5 implementation.

- [x] ✅ `BE` All three endpoints in `technical.py` — Done Sprint 1+: `model-details`, `prediction-stats`, `price-targets` all fully implemented.

### A3. `MLPrediction` model does not exist

**What was found:** `backend/app/models/` has no `ml_prediction.py`.
The prediction database (todos-v5 Phase 5) has zero backend groundwork.

- [x] ✅ `DB` `ml_prediction.py` model + Alembic migration — Done Sprint 2. Registered in `__init__.py`.

### A4. `requirements.txt` is missing all todos-v5 ML dependencies

**What was found:** `requirements.txt` has `scikit-learn`, `xgboost`, `prophet`, `joblib`,
`mlflow`. It does NOT have:
- `lightgbm` — needed for todos-v5 Phase 4.2
- `optuna` — needed for todos-v5 Phase 4.4
- `shap` — needed for todos-v5 Phase 4.1

These need to be added before any ML improvement work begins.

- [x] ✅ `BE` `lightgbm`, `optuna`, `shap`, `anthropic` added to `requirements.txt` — Done Sprint 0.

---

## PART B — GAPS: Things todos-v3/v4/v5 assumed exist but don't yet

### B1. No `api_bulk.ts` frontend file exists (used by TickerDataPanel)

**What was found:** `TickerDataPanel.tsx` imports from `"../lib/api_bulk"`:
```typescript
import {
  fetchTickerStatus, seedSingleSymbol, triggerTrainSymbol,
  triggerBulkNewsSeed, type TickerStatusDto,
} from "../lib/api_bulk";
```
Let me verify this file:

- [x] ✅ `FE` `frontend/lib/api_bulk.ts` exists and is complete — Verified Sprint 0+.

### B2. `admin_bulk.py` endpoint — verify it has `ticker-status/{symbol}`

**What was found:** `admin_bulk.py` exists in endpoints but was not read.
`TickerDataPanel` calls `fetchTickerStatus(symbol)` which maps to
`GET /api/v1/admin/ticker-status/{symbol}` (todos-v4 Phase 8.1).
Need to verify this endpoint exists.

- [x] ✅ `BE` `GET /api/v1/admin/ticker-status/{symbol}` exists in `admin_bulk.py` — Verified.

### B3. LLM insight is not shown on the dashboard page

**What was found:** `frontend/app/page.tsx` imports: `MarketWeatherWidget`, `RegimeWidget`,
`TimeframeGrid`, `WhyMovingPanel`, `ConflictDetector`, `WatchlistWidget`, `TickerDataPanel`,
`ScoreExplainPanel`. There is NO LLM insight card / component on the dashboard.

The `llm_service.py` exists but there is no frontend component rendering LLM output.

- [x] ✅ `FE`+`BE` `LLMInsightCard.tsx` — Done Sprint 1+12: built with SSE streaming, progressive section rendering, wired to dashboard.

### B4. `ModelDetailsPanel.tsx` does not exist

`TimeframeGrid.tsx` has excellent Layer 1 (signal tile) and a good slide-over panel
with confidence/Sharpe explanations, but there is no `ModelDetailsPanel.tsx` for
the deep dev transparency layer (todos-v5 Phase 2.2). This is a net-new component.

- [x] ✅ `FE` `ModelDetailsPanel.tsx` — Done Sprint 4: side drawer with 4 tabs.

### B5. `TimeframeGrid` already has most of Layer 1 and Layer 2 built

**Good news from the audit:** `TimeframeGrid.tsx` is already much better than expected:
- ✅ Direction icon + label ("Bullish / Bearish / Neutral")
- ✅ Horizon label per timeframe ("Next 3–5 days")
- ✅ Confidence bar + percentage
- ✅ Confidence interpretation (Very High / High / Moderate / Low) with colour
- ✅ Slide-over detail panel with plain-English explanations
- ✅ Sharpe ratio display with explanation tooltip
- ✅ "How to use this signal" checklist
- ✅ Consensus summary row (agreement bar + bullish/bearish/neutral count)

**What's still missing for todos-v5:**
- ❌ "What drove this?" SHAP-based feature breakdown (Layer 2) — needs SHAP backend first
- ❌ Multi-timeframe agreement banner above the grid (plain text, not just the bar)
- ❌ Link to `ModelDetailsPanel` from the slide-over ("View full model report →")

- [ ] 🟡 `FE` Add multi-timeframe agreement text banner above the grid in `TimeframeGrid.tsx`:
  "3 of 5 timeframes agree: UP → stronger signal" / "Timeframes conflict → wait for confirmation"
- [ ] 🟡 `FE` Add "⚙ Model Details →" link at bottom of the slide-over panel that opens `ModelDetailsPanel`
- [ ] 🟡 `FE` Add "What drove this?" section to the slide-over (stub with placeholder until SHAP is ready)

### B6. Confidence label system is partially done but inconsistent

`TimeframeGrid.tsx` uses "Very High / High / Moderate / Low" labelling internally.
The todos-v5 Phase 1.3 system adds "Strong signal / Moderate signal / Weak signal /
Uncertain / No clear signal" as a global standard used everywhere.
These two systems need to be reconciled into one shared utility.

- [ ] 🟡 `FE` Create `frontend/lib/signalUtils.ts` — shared utility with:
  - `interpretConfidence(conf: number)` — returns label, colour, description
  - `directionConfig(direction: string)` — returns icon, colours, plain-text label
  - Import these in `TimeframeGrid.tsx`, `LLMInsightCard.tsx`, and any other signal-rendering component
  - This prevents the two components from drifting apart

### B7. No `/model-info/{symbol}` route exists

todos-v5 Phase 2.3 calls for a standalone deep-dive page. No such route exists in
`frontend/app/`. This is a net-new page.

- [x] ✅ `FE` `app/model-info/[symbol]/page.tsx` — Done Sprint 6: 7-tab deep-dive page.

---

## PART C — THINGS THAT LOOK GOOD (no action needed)

These were verified during the audit and are solid:

- ✅ `technical_service.py` — BUG-003 fix is solid; dynamic timeframe detection from registry
- ✅ `model_registry.py` — versioned, champion/retired lifecycle, JSONL + index JSON — well built
- ✅ `ml_pipeline.py` — MLflow integration, quality gates, 3-model competition, TIMEFRAME_HORIZON
- ✅ `TimeframeGrid.tsx` — already implements most of todos-v5 Phase 1 UX goals
- ✅ `TickerDataPanel.tsx` — todos-v4 Phase 8.2 complete, OHLCV/ML/News status with action buttons
- ✅ `technical.py` — registry-status, train-status, train endpoints all exist and are correct
- ✅ `model_registry_index.json` is in `.gitignore` (just added)
- ✅ `backend/backups/` is in `.gitignore` (just added)

---

## PART D — RECOMMENDED IMPLEMENTATION ORDER (revised from todos-v5)

Given the gaps found, here is the corrected sprint order:

```
Sprint 0 — Blockers (do this FIRST, before any todos-v5 feature work):
  A1: Add anthropic to requirements.txt + .env.example
  A1: Rewrite llm_service.py with Anthropic primary + Ollama fallback
  A3: Create ml_prediction.py model + Alembic migration
  A4: Add lightgbm, optuna, shap to requirements.txt
  B1: Verify/create api_bulk.ts in frontend
  B2: Verify admin_bulk.py has ticker-status/{symbol}

Sprint 1 — LLM Investment Manager (biggest user-facing win):
  A2: Add 3 stub endpoints to technical.py (model-details, prediction-stats, price-targets)
  B3: Create LLMInsightCard.tsx + POST /api/v1/llm/insight/{symbol}
  todos-v5 Phase 3.2: Pre-LLM price target computation
  todos-v5 Phase 3.3: LLM persona + structured system prompt
  todos-v5 Phase 3.4: LLM insight card frontend rendering

Sprint 2 — Prediction Database:
  todos-v5 Phase 5.2: Store prediction on every inference
  todos-v5 Phase 5.3: Outcome resolver cron
  todos-v5 Phase 5.4: Live accuracy stats endpoint

Sprint 3 — ML Improvements:
  todos-v5 Phase 4.1: SHAP feature importance
  todos-v5 Phase 4.2: LightGBM as 4th model
  todos-v5 Phase 4.3: Ensemble voting
  todos-v5 Phase 4.5: Remove Prophet from signal competition

Sprint 4 — TimeframeGrid + Dev Transparency:
  B5: Multi-timeframe agreement banner + ModelDetailsPanel link
  B6: signalUtils.ts shared utilities
  todos-v5 Phase 2.1: Model details endpoint (wire real data from registry + SHAP)
  todos-v5 Phase 2.2: ModelDetailsPanel.tsx (tabs: Overview, Features, Training, All Models)
  todos-v5 Phase 5.6: Live accuracy tab in ModelDetailsPanel

Sprint 5 — Price Targets + Position Sizing:
  todos-v5 Phase 6.1–6.2: Probabilistic price target display
  todos-v5 Phase 7.1–7.2: Kelly Criterion position sizing

Sprint 6 — Advanced / Deferred:
  todos-v5 Phase 4.4: Optuna hypertuning
  todos-v5 Phase 5.5: Drift alerts + auto-retrain
  todos-v5 Phase 5.7: Feature analysis from prediction DB
  B7: /model-info/{symbol} deep-dive page
```

---

## PART E — QUICK WINS (can do in under 1 hour each, any time)

These are small gaps with big impact that can be done between sprints:

- [ ] 🟡 `BE` Add `ANTHROPIC_API_KEY=` line to `backend/.env.example` (5 min)
- [ ] 🟡 `BE` Add `lightgbm>=4.3.0`, `optuna>=3.6.0`, `shap>=0.45.0`, `anthropic>=0.25.0`
  to `requirements.txt` and run `pip install` (10 min)
- [ ] 🟡 `FE` Add `"What drove this?"` stub section (static text "Feature breakdown coming soon")
  to the `TimeframeDetailPanel` slide-over in `TimeframeGrid.tsx` (15 min)
- [ ] 🟡 `FE` Add the multi-timeframe agreement text banner above the grid tiles in
  `TimeframeGrid.tsx` — logic is already in `ConsensusSummary`, just needs a text line (20 min)
- [ ] 🟡 `BE` Add `model-details`, `prediction-stats`, `price-targets` stub endpoints
  to `technical.py` returning empty placeholder responses (30 min — prevents frontend 404s)

---

*todos-v6.md — Created 2026-03-21.*
*Purpose: pre-flight audit before todos-v5 implementation. Fix blockers in Part A first.*
*Companion files: todos-v5.md (feature specs), todos-v4.md (bulk pipeline), todos-v3.md (app polish).*
