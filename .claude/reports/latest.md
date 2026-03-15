# Fin-Eye Model Inspection Report

**Generated:** 2026-03-16 01:31:43  
**Registry:** all  
**Symbol filter:** all  
**Total records:** 13  |  **Active models:** 8

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS — safe to deploy | 1 |
| ⚠️ WARN — review | 2 |
| ❌ FAIL — do not use | 5 |

### Models Safe for GAS

- **AAPL / 4h** — XGBOOST — Sharpe `1.847`

> ℹ️ 5 older run(s) superseded in registry.

---

## LLM Assessment (DeepSeek R1 32B)

### OVERALL HEALTH  
Most models cannot be trusted in production due to negative or low Sharpe ratios, below-random accuracy, and suspicious artifacts. Only AAPL/4h [backend] passes all checks but should be monitored for overfitting.

---

### ROOT CAUSE ANALYSIS  

1. **AAPL/1d [backend] (FAIL)**  
   - The model has a positive Sharpe (2.55) but accuracy below 50% (49%), indicating it predicts the opposite of intended.  
   - A 2.1KB logistic artifact suggests minimal data or fallback logic, leading to anti-predictive behavior.

2. **AAPL/1h [store] (FAIL)**  
   - Negative Sharpe (-0.269) and accuracy (37%) indicate the model is actively harmful.  
   - Tiny logistic artifact (1.9KB) suggests minimal data or fallback logic, likely causing poor performance.

3. **BTC-USD/1h [backend] (FAIL)**  
   - Negative Sharpe (-0.373) despite 52.2% accuracy implies the model produces unprofitable signals.  
   - Minimal logistic artifact (2.2KB) and large validation set (3415 rows) suggest data issues or poor feature engineering.

4. **AAPL/1wk [backend] (WARN)**  
   - Sharpe of 10.127 is unusually high, likely due to small validation size or overfitting.  
   - Tiny logistic artifact (2.1KB) indicates minimal data or fallback logic.

---

### PRIORITY FIXES  

1. **Fix Data Handling in AAPL/1d**  
   Investigate why a positive Sharpe exists with below-random accuracy. Validate return calculations and target distribution.  
   File: `data_processor.py`

2. **Investigate Tiny Logistic Artifacts**  
   Ensure logistic models are properly trained and saved. Check for fallback logic or data truncation.  
   File: `model_saver.py`

3. **Improve BTC-USD Models**  
   Add more features or adjust hyperparameters to capture Bitcoin's volatility better.  
   Function: `feature_engineer_bitcoin()`

4. **Adjust AAPL/1wk Validation Size**  
   Increase validation periods for weekly models to reduce overfitting risk.  
   File: `model_validator.py`

---

### SAFEST MODEL RIGHT NOW  

**AAPL/4h [backend]** is the most trustworthy due to its balanced Sharpe (1.847) and accuracy (57.7%), with no critical issues flagged. XGBoost's artifact size (111KB) confirms a full model, making it suitable for production while others are being fixed.

---

## Model Details

### AAPL / 1d &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `2.5524` |
| Trained | `2026-03-03 20:24` |
| Artifact | ✅ `AAPL_1d_winner.joblib` (2KB) |
| Horizon | `? periods` |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
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
| Winner | `XGBOOST` |
| Sharpe | `0.2452` |
| Trained | `2026-03-15 22:04` |
| Artifact | ✅ `AAPL_1h_winner.joblib` (115KB) |
| Horizon | `? periods` |
| Rows | `3380` total / `676` val |
| Target | `54.0%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
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
| Winner | `LOGISTIC` |
| Sharpe | `-0.2689` |
| Trained | `2026-03-02 22:14` |
| Artifact | ✅ `logistic.joblib` (2KB) |
| Horizon | `? periods` |

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
| Winner | `LOGISTIC` |
| Sharpe | `10.1269` |
| Trained | `2026-03-03 20:25` |
| Artifact | ✅ `AAPL_1wk_winner.joblib` (2KB) |
| Horizon | `? periods` |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
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
| Winner | `XGBOOST` |
| Sharpe | `1.8470` |
| Trained | `2026-03-15 22:04` |
| Artifact | ✅ `AAPL_4h_winner.joblib` (111KB) |
| Horizon | `? periods` |
| Rows | `1097` total / `220` val |
| Target | `55.1%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
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
| Winner | `LOGISTIC` |
| Sharpe | `-0.2689` |
| Trained | `2026-03-02 22:14` |
| Artifact | ✅ `logistic.joblib` (2KB) |
| Horizon | `? periods` |

**Issues:**

- ❌ **[NEGATIVE_SHARPE]** Sharpe is negative (-0.269) — model destroys value
- ❌ **[BELOW_RANDOM]** Accuracy 37.0% is below random (50%) — model is anti-predictive
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 1.9KB — likely fallback or minimal data

> ❌ **Do not use.** Fix errors before deploying.

---

### BTC-USD / 1h &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `-0.3731` |
| Trained | `2026-03-15 22:27` |
| Artifact | ✅ `BTC-USD_1h_winner.joblib` (2KB) |
| Horizon | `3 periods` |
| Rows | `17072` total / `3415` val |
| Target | `51.0%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ❌ `-0.373` | ✅ `52.2%` | `-0.668` | **← WINNER** |
| `xgboost` | ❌ `-0.577` | ⚠️ `51.2%` | `-1.059` | |
| `prophet` | ❌ `-0.354` | ⚠️ `50.5%` | `-0.588` | |

**Issues:**

- ❌ **[NEGATIVE_SHARPE]** Sharpe is negative (-0.373) — model destroys value
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.2KB — likely fallback or minimal data
- ℹ️ **[VALIDATION_SIZE]** Validation set: 3415 rows

> ❌ **Do not use.** Fix errors before deploying.

---

### BTC-USD / 4h &nbsp; ❌ FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `-0.4468` |
| Trained | `2026-03-15 22:27` |
| Artifact | ✅ `BTC-USD_4h_winner.joblib` (2KB) |
| Horizon | `3 periods` |
| Rows | `4232` total / `847` val |
| Target | `51.7%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ❌ `-0.447` | ⚠️ `51.7%` | `-0.398` | **← WINNER** |
| `xgboost` | ❌ `-1.200` | ❌ `49.0%` | `-1.118` | |
| `prophet` | ❌ `-1.018` | ⚠️ `50.9%` | `-0.833` | |

**Issues:**

- ❌ **[NEGATIVE_SHARPE]** Sharpe is negative (-0.447) — model destroys value
- ⚠️ **[LOW_ACCURACY]** Accuracy 51.7% below deployment threshold (52%)
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.2KB — likely fallback or minimal data
- ℹ️ **[VALIDATION_SIZE]** Validation set: 847 rows

> ❌ **Do not use.** Fix errors before deploying.

---

## Thresholds

Min Sharpe: `0.3` · Min Accuracy: `52%` · Suspicious Sharpe: `> 5.0`  
Configured in `.claude/agents/config.yaml`

*`inspect_models.py` · fin-eye · 2026-03-16 01:31:43*