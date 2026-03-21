# Fin-Eye — Sprint Progress Tracker
> Last updated: Sprint 6 complete

## Completed Sprints

### ✅ Sprint 0 — Blockers
- LLM service rewritten (Ollama primary → Groq fallback → static)
- lightgbm, optuna, shap added to requirements.txt
- MLPrediction model + Alembic migration (v5_001)
- bulk_ops constraint bug fixed
- BackgroundTasks injection bug fixed
- Auth bypass for dev (REQUIRE_AUTH=False)

### ✅ Sprint 1 — LLM Investment Manager
- POST /api/v1/explanation/{symbol}/generate-insight (6-section structured output)
- LLMInsightCard.tsx (6 sections, consensus badge, price target band, Ollama hint)
- lib/api_llm_types.ts (shared types + fetchLLMInsight)
- lib/api_price.ts (fetchLatestPrice)
- GET /api/v1/technical/{symbol}/price (live price endpoint)
- page.tsx wired: LLMInsightCard + live price SWR

### ✅ Sprint 2 — Prediction Database
- MLPrediction SQLAlchemy model (20 columns, JSONB feature snapshot)
- Alembic migration v5_001_ml_predictions (partial index on pending outcomes)
- prediction_service.py: store_prediction(), resolve_pending_outcomes(), get_prediction_stats()
- technical_service.py: compute_and_store_consensus() async wrapper
- scheduler.py: job_resolve_prediction_outcomes() (every hour at :45)
- /{symbol}/prediction-stats endpoint wired to real service
- /{symbol}/latest endpoint now uses compute_and_store_consensus

### ✅ Sprint 3 — ML Improvements
- LightGBMWrapper as 4th competing model
- EnsembleWrapper (Sharpe-weighted soft-voting of logistic + xgboost + lightgbm)
- compute_shap_importance() (TreeExplainer, capped at 200 samples)
- Prophet removed from competition (ModelKind.PROPHET kept for compat)
- ModelKind.LIGHTGBM + ModelKind.ENSEMBLE added to technical_models.py

### ✅ Sprint 4 — Dev Transparency Layer
- GET /api/v1/technical/{symbol}/model-details (real registry data + SHAP)
- GET /api/v1/technical/{symbol}/prediction-stats (wired to real service)
- lib/api_model_details.ts (types + fetch functions)
- ModelDetailsPanel.tsx (4 tabs: Overview, Features, Training, All Models)
  - SHAP bar chart in Features tab
  - Live accuracy from prediction DB in Overview
  - All-models competition table with winner badge
  - MLflow run link in Training tab
- TimeframeGrid.tsx updated:
  - symbol prop added (optional)
  - ⚙ Model Details link below consensus summary
  - "View full model details" button in signal slide-over
  - ModelDetailsPanel rendered inline

### ✅ Sprint 5 — Price Targets + Kelly Position Sizing
- price_target_service.py:
  - fetch_live_indicators_sync(): real ATR-14 from 252 daily bars
  - compute_price_targets(): upside/expected/stop from ATR + model return
  - compute_kelly(): Half-Kelly with 25% cap + small-sample penalty
  - expected_return_from_signals(): Sharpe-weighted expected return from signals
- GET /api/v1/technical/{symbol}/price-targets UPGRADED:
  - Real ATR (not hardcoded 2%)
  - Model-driven expected return from Sharpe-weighted signals
  - Kelly Criterion from live prediction DB (falls back to validation accuracy)
  - 52-week range context
  - Risk/reward ratio
- GET /api/v1/technical/{symbol}/kelly (standalone Kelly endpoint)
- PriceTargetCard.tsx:
  - Interactive horizontal price range bar (click any level for basis tooltip)
  - Upside / Expected / Current / Stop with % change + basis
  - Risk/reward ratio
  - 52-week range bar with gradient
  - Kelly sizing: suggested %, bar (0–25%), inputs grid, formula toggle
  - Graceful empty states (no models, no price, no Kelly data)

### ✅ Sprint 6 — Optuna Tuning + Drift Alerts + /model-info Deep-Dive Page

#### Backend
- backend/app/models/model_drift_alert.py
  - ModelDriftAlert ORM model (symbol, timeframe, val_acc, live_acc, delta_pp, severity, auto_retrain)
  - Indexes: idx_drift_symbol_tf, idx_drift_unacked, idx_drift_severity
- backend/alembic/versions/v6_001_model_drift_alerts.py
  - Creates model_drift_alerts table
  - Down revision: v5_001_ml_predictions
- backend/app/models/__init__.py — ModelDriftAlert registered
- backend/app/services/drift_service.py
  - detect_and_record_drift(): rolling 30-day accuracy vs val accuracy
  - DRIFT_THRESHOLD_PP = 10pp default; configurable via DRIFT_THRESHOLD_PP env var
  - Cooldown: 3-day repeat-alert guard per symbol/timeframe
  - Severity: "warning" (10-20pp delta) vs "critical" (>20pp)
  - Auto-retrain: fires background _trigger_retrain_async() if AUTO_RETRAIN_ON_DRIFT=True
  - get_drift_report(), acknowledge_drift_alert()
- backend/app/services/optuna_tuner.py
  - tune_xgboost(): 30-trial Bayesian tuning (n_estimators, max_depth, lr, subsample, etc.)
  - tune_lightgbm(): same search space adapted for LightGBM
  - run_tuning_for_symbol(): full pass per symbol/timeframe — fetches data, engineers features, tunes
  - load_best_params(): reads sidecar JSON — called inside run_training_pipeline() to override defaults
  - Best params stored at: backend/data/models/{symbol}_{tf}_{model}_best_params.json
  - Optuna DB stored at: backend/data/optuna/{symbol}_{tf}_{model}.db (survives restarts)
- backend/app/api/v1/endpoints/admin_ml.py
  - GET  /api/v1/admin/ml/drift-report              — all drift alerts (newest first)
  - GET  /api/v1/admin/ml/drift-report?unacked_only=true
  - POST /api/v1/admin/ml/drift-report/{id}/ack     — acknowledge alert
  - GET  /api/v1/admin/ml/drift-summary             — quick counts for badge
  - GET  /api/v1/admin/ml/optuna-params/{sym}/{tf}/{model} — best tuned params
- backend/app/main.py
  - admin_ml_router wired at /api/v1/admin/ml
- backend/app/config.py
  - enable_hypertuning: bool (ENABLE_HYPERTUNING=False)
  - auto_retrain_on_drift: bool (AUTO_RETRAIN_ON_DRIFT=False)
  - drift_threshold_pp: float (DRIFT_THRESHOLD_PP=10.0)
  - optuna_n_trials: int (OPTUNA_N_TRIALS=30)
- backend/.env.example
  - Full Sprint 6 flags section with inline documentation
- backend/app/services/scheduler.py
  - job_detect_model_drift(): every hour at :50 (after outcome resolution at :45)
  - job_run_optuna_tuning(): nightly 01:00 UTC, gated on ENABLE_HYPERTUNING=True
- backend/app/api/v1/endpoints/technical.py
  - GET /{symbol}/prediction-history — last N resolved predictions, newest first
    (used by History tab on deep-dive page)

#### Frontend
- frontend/app/model-info/[symbol]/page.tsx  ← NEW full deep-dive page
  - Breadcrumb: Dashboard / Model Deep-Dive / {SYMBOL}
  - Cross-timeframe accuracy chart (all TFs in one view)
  - Timeframe selector (1h / 4h / 1d / 1wk / 1mo)
  - 6 tabs per timeframe:
    - Overview: winner model, val/live accuracy stat grid, regime breakdown
    - Features: SHAP bars sorted by importance + feature descriptions
    - Training: data split bar, training metadata grid, MLflow run link
    - All Models: competition table with winner badge
    - History: last 30 resolved predictions table (entry/exit price, return, ✓/✗)
    - Drift: drift alerts for this symbol/tf + "what is drift?" explainer
  - Graceful empty state with "Go to Dashboard" CTA
- frontend/lib/api_admin_ml.ts  ← NEW
  - fetchDriftAlerts(symbol?) — 403 guard for non-admin users
  - acknowledgeDriftAlert(id)
  - fetchDriftSummary()
  - fetchOptunaParams(symbol, tf, model)
- frontend/components/ModelDetailsPanel.tsx
  - Footer: added "Full page →" Link to /model-info/{symbol}
  - Added `import Link from "next/link"`

## Remaining (Sprint 7+)

### Sprint 7 — Feature Analysis (3+ months of prediction data needed)
- Regime-conditional accuracy analysis (todos-v5 Phase 5.7)
- Feature value correlation with correctness
- Seasonality analysis
- Meta-model: "when to trust the base model"
- These require ≥ 90 days of resolved predictions to be statistically meaningful

## Manual steps needed after each sprint

After Sprint 2:
  alembic upgrade head  ← creates ml_predictions table

After Sprint 6:
  alembic upgrade head  ← creates model_drift_alerts table
  Then navigate to /model-info/AAPL to see the deep-dive page.
  To enable overnight Optuna tuning: set ENABLE_HYPERTUNING=True in backend/.env
  To enable auto-retrain on drift: set AUTO_RETRAIN_ON_DRIFT=True in backend/.env

After Sprint 5 (page.tsx wiring — str_replace broken on Windows paths):
  1. Add import: import PriceTargetCard from "../components/PriceTargetCard";
  2. Add JSX between Technical Consensus and LLM Insight:
     <PriceTargetCard symbol={activeSymbol} isVisible={signals.length > 0} />
