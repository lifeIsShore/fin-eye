# Fin-Eye Model Inspection Report

**Generated:** 2026-03-16 01:14:31  
**Registry:** all  
**Symbol filter:** all  
**Total records in registry:** 11  
**Active models:** 6  

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS — safe to deploy | 1 |
| ⚠️ WARN — review before deploying | 2 |
| ❌ FAIL — do not use | 3 |

### Models Safe for GAS

- **AAPL / 4h** — XGBOOST — Sharpe `1.847`

> ℹ️ 5 older training run(s) superseded in registry.

---

## LLM Assessment (DeepSeek R1 32B)

> ⚠️ *LLM call failed: [LLM ERROR] Request timed out. Try increasing timeout_seconds in config.yaml.*

---

## Model Details

### AAPL / 1d &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winning model | `LOGISTIC` |
| Validation Sharpe | `2.5524` |
| Trained at | `2026-03-03 20:24` |
| Artifact | ✅ `AAPL_1d_winner.joblib` (2KB) |

**All model results:**

| Model | Sharpe | Accuracy | Total Return | Notes |
|-------|--------|----------|--------------|-------|
| `logistic` | ✅ `2.552` | ❌ `49.0%` | `+0.643` | **← WINNER** |
| `xgboost` | ❌ `-0.137` | ❌ `46.9%` | `-0.072` | |
| `prophet` | ✅ `2.032` | ✅ `54.8%` | `+1.419` | |

**Issues:**

- ❌ **[BELOW_RANDOM]** Accuracy 49.0% is below random (50%) — model is anti-predictive
- ⚠️ **[SHARPE_ACCURACY_CONTRADICTION]** Positive Sharpe (2.55) but accuracy below 50% (49.0%) — validate return distribution
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.1KB — likely fallback or minimal data

> ❌ **Do not use.** Fix errors before deploying.

---

### AAPL / 1h &nbsp; ⚠️  WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winning model | `XGBOOST` |
| Validation Sharpe | `0.2452` |
| Trained at | `2026-03-15 22:04` |
| Artifact | ✅ `AAPL_1h_winner.joblib` (115KB) |
| Data rows | `3380` total / `2704` train / `676` val |
| Target balance | `54.0%` UP |

**All model results:**

| Model | Sharpe | Accuracy | Total Return | Notes |
|-------|--------|----------|--------------|-------|
| `logistic` | ✅ `0.603` | ❌ `49.9%` | `+0.098` | |
| `xgboost` | ⚠️ `0.245` | ⚠️ `50.7%` | `+0.065` | **← WINNER** |
| `prophet` | ❌ `-0.003` | ✅ `52.4%` | `-0.002` | |

**Issues:**

- ⚠️ **[LOW_SHARPE]** Sharpe 0.245 below deployment threshold (0.3)
- ⚠️ **[LOW_ACCURACY]** Accuracy 50.7% below deployment threshold (52%)
- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 115KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 676 rows

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 1h &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `store` |
| Winning model | `LOGISTIC` |
| Validation Sharpe | `-0.2689` |
| Trained at | `2026-03-02 22:14` |
| Artifact | ✅ `logistic.joblib` (2KB) |

**Issues:**

- ❌ **[NEGATIVE_SHARPE]** Sharpe is negative (-0.269) — model destroys value
- ❌ **[BELOW_RANDOM]** Accuracy 37.0% is below random (50%) — model is anti-predictive
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 1.9KB — likely fallback or minimal data

> ❌ **Do not use.** Fix errors before deploying.

---

### AAPL / 1wk &nbsp; ⚠️  WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winning model | `LOGISTIC` |
| Validation Sharpe | `10.1269` |
| Trained at | `2026-03-03 20:25` |
| Artifact | ✅ `AAPL_1wk_winner.joblib` (2KB) |

**All model results:**

| Model | Sharpe | Accuracy | Total Return | Notes |
|-------|--------|----------|--------------|-------|
| `logistic` | ✅ `10.127` | ✅ `59.5%` | `+1.272` | **← WINNER** |
| `xgboost` | ✅ `9.928` | ✅ `64.3%` | `+1.341` | |
| `prophet` | ✅ `9.350` | ✅ `76.2%` | `+1.419` | |

**Issues:**

- ⚠️ **[SUSPICIOUS_SHARPE]** Sharpe 10.127 unusually high — likely small validation set or data artifact
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.1KB — likely fallback or minimal data
- ⚠️ **[WEEKLY_SMALL_SAMPLE]** Weekly timeframe: very few validation bars — high Sharpe is likely noise

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 4h &nbsp; ✅ PASS

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winning model | `XGBOOST` |
| Validation Sharpe | `1.8470` |
| Trained at | `2026-03-15 22:04` |
| Artifact | ✅ `AAPL_4h_winner.joblib` (111KB) |
| Data rows | `1097` total / `877` train / `220` val |
| Target balance | `55.1%` UP |

**All model results:**

| Model | Sharpe | Accuracy | Total Return | Notes |
|-------|--------|----------|--------------|-------|
| `logistic` | ⚠️ `0.000` | ✅ `57.7%` | `+0.000` | |
| `xgboost` | ✅ `1.847` | ✅ `57.7%` | `+0.233` | **← WINNER** |
| `prophet` | ❌ `-1.022` | ❌ `42.3%` | `-0.263` | |

**Issues:**

- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 111KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 220 rows

> ✅ **Passes all quality gates.** Safe for GAS.

---

### AAPL / 4h &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `store` |
| Winning model | `LOGISTIC` |
| Validation Sharpe | `-0.2689` |
| Trained at | `2026-03-02 22:14` |
| Artifact | ✅ `logistic.joblib` (2KB) |

**Issues:**

- ❌ **[NEGATIVE_SHARPE]** Sharpe is negative (-0.269) — model destroys value
- ❌ **[BELOW_RANDOM]** Accuracy 37.0% is below random (50%) — model is anti-predictive
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 1.9KB — likely fallback or minimal data

> ❌ **Do not use.** Fix errors before deploying.

---

## Quality Gate Thresholds

| Threshold | Value |
|-----------|-------|
| Minimum Sharpe | `0.3` |
| Minimum Accuracy | `52%` |
| Suspicious Sharpe | `> 5.0` |

Configured in `.claude/agents/config.yaml`

---

## Next Steps

1. Run `python .claude/agents/data_quality_checker.py --symbol AAPL --check-macro`
2. Check actual OHLCV row counts before training (see `OHLCVFetcher` in `market_data.py`)
3. After fixing data: retrain, then re-run `python .claude/agents/inspect_models.py --llm --save-report`
4. Clean test data: `python .claude/agents/inspect_models.py --clean-test`

*Generated by `inspect_models.py` · fin-eye · 2026-03-16 01:14:31*