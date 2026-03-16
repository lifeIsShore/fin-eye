# ML Pipeline Bug Report
> **Date:** 2026-03-16  
> **File:** `backend/app/services/ml_pipeline.py`  
> **Discovered via:** `scripts/retrain_models.py` training run logs  
> **Status:** ✅ All Fixed

---

## Bug #1 — MLflow Model Registration Fails on Every Run 🔴
**Severity:** High  

### Round 1 Fix (URI path)
**Symptom:**
```
Unable to find a logged_model with artifact_path model/BTC-USD_1h_winner.joblib under run b58e5d85...
```
**Cause:** `os.path.basename(artifact_path)` was appended to the URI, making it point at a file instead of a directory.  
**Fix:** Removed the filename suffix → `runs:/{run_id}/model`

### Round 2 Fix (artifact type mismatch)
**Symptom (persisted after Round 1):**
```
Unable to find a logged_model with artifact_path model under run 3a228a86...
```
**Root Cause:** `mlflow.log_artifact()` logs a raw file (no `MLmodel` manifest). `mlflow.register_model()` requires a **proper MLflow model** logged via `mlflow.sklearn.log_model()` which generates the `MLmodel` manifest file that the registry lookup depends on.

**Fix:** Replaced the old two-function split (`_log_winner_artifact` + `_register_model_in_mlflow`) with a single `_log_and_register_model()` function that:
1. Unwraps the winner wrapper class into a native sklearn estimator/Pipeline
2. Calls `mlflow.sklearn.log_model()` to create a proper MLflow model artifact
3. Calls `mlflow.register_model()` using the correct `runs:/{run_id}/model` URI
4. The raw `.joblib` is still logged separately under `joblib/` for download reference

```python
# Before — logged a raw file, then tried to register it as a model
mlflow.log_artifact(artifact_path, artifact_path="model")
mlflow.register_model(f"runs:/{run_id}/model", model_name)

# After — logs a proper MLflow model, then registers it
mlflow.sklearn.log_model(sk_model, artifact_path="model")
mlflow.register_model(f"runs:/{run_id}/model", model_name)
```

---

## Bug #2 — `pct_change()` FutureWarning (Pandas Deprecation) 🟡
**Severity:** Medium (will break in a future pandas version)  
**Symptom:**
```
FutureWarning: The default fill_method='pad' in Series.pct_change is deprecated
and will be removed in a future version.
```

**Fix:** Added `fill_method=None` to all five `pct_change()` calls in `engineer_features()`:
- `ret_1`, `ret_3`, `ret_5`, `mom_10`, `mom_20`

---

## Non-Bug Observations (No Code Fix Required)

### BTC-USD 1h/4h — All Models Negative Sharpe
All three models fail the quality gate on BTC-USD intraday timeframes. Pipeline correctly falls back to highest-accuracy. This is a data/market characteristic issue, not a code bug. Consider flagging intraday BTC signals as low-confidence in the UI.

### yfinance 1h Gap (Jan-Mar 2024)
Yahoo Finance only provides 1h data for the last 730 days. Handled gracefully — 17k+ bars still fetched. No fix needed.

### BTC-USD 1mo — Insufficient Data (139 rows)
Monthly bars skipped because 139 < 200 minimum threshold. Expected behaviour.

---

## Fix Summary

| # | Round | Change | Status |
|---|-------|--------|--------|
| 1a | 1 | Remove filename from MLflow model URI | Done |
| 1b | 2 | Use `mlflow.sklearn.log_model()` instead of `log_artifact()` | Done |
| 2 | 1 | Add `fill_method=None` to all `pct_change()` calls | Done |
