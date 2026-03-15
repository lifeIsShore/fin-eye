# Fin-Eye Model Inspection Report

**Generated:** 2026-03-16 02:11:40  
**Registry:** all  
**Symbol filter:** all  
**Total records:** 26  |  **Active models:** 11

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS — safe to deploy | 3 |
| ⚠️ WARN — review | 4 |
| ❌ FAIL — do not use | 4 |

### Models Safe for GAS

- **AAPL / 1h** — XGBOOST — Sharpe `1.598`
- **BTC-USD / 1d** — XGBOOST — Sharpe `2.043`
- **BTC-USD / 1wk** — XGBOOST — Sharpe `3.084`

> ℹ️ 15 older run(s) superseded in registry.

---

## LLM Assessment (DeepSeek R1 32B)

### 1. OVERALL HEALTH  
Most models are in production-ready condition, but several fail or show concerning patterns. While some models deliver strong performance (e.g., AAPL/1d backend), others (e.g., AAPL/1h [store]) should not be trusted due to negative Sharpe ratios and low accuracy. The platform’s reliability varies significantly across symbols and timeframes.

---

### 2. ROOT CAUSE ANALYSIS  

#### **FAIL Cases**  
- **AAPL/1h [store]**:  
  - Negative Sharpe (-0.269) and accuracy (37%) suggest the model is anti-predictive. Likely caused by minimal training data or overfitting, given the tiny logistic artifact (1.9KB).  
- **BTC-USD/1h [backend]**:  
  - Negative Sharpe (-0.373) for logistic and low accuracy across all models indicate poor predictive power. Despite a large validation set (3415 rows), the model fails to outperform random guessing, likely due to noisy features or insufficient signal extraction.

#### **WARN Cases**  
- **AAPL/1d [backend]**:  
  - Low accuracy (50.5%) for XGBoost despite high Sharpe suggests overfitting. The validation set size (2271 rows) is sufficient, but the model may be capturing noise rather than signal.  
- **AAPL/1mo [backend]**:  
  - Unusually high Sharpe (5.039) and tiny logistic artifact (2.2KB) suggest overfitting on a small validation set (89 rows). This is likely not representative of real-world performance.  
- **BTC-USD/4h [backend]**:  
  - Negative Sharpe (-0.447) for logistic and low accuracy (51.7%) indicate poor model performance, possibly due to noisy data or insufficient training samples.

---

### 3. PRIORITY FIXES  

1. **Fix AAPL/1h [store]**: Replace the failing logistic model with a more robust alternative like XGBoost. Investigate why the artifact is tiny (e.g., data pipeline issues).  
2. **Review AAPL/1mo [backend]**: Increase the validation set size or remove outliers to reduce overfitting. Validate Sharpe ratio on larger test sets before deployment.  
3. **Prevent Negative Sharpe Winners**: Implement a check to reject models with negative Sharpe in production. This can be added to the model selection logic (`model_selection.py`).  
4. **Improve Tiny Logistic Models**: Investigate why logistic artifacts are small (e.g., data leakage, minimal training samples). Adjust regularization or increase dataset size.

---

### 4. SAFEST MODEL RIGHT NOW  

**AAPL/1d [backend]**:  
- Sharpe=1.898 and decent accuracy (50.5%) suggest it’s the most reliable model. Despite the warning for low accuracy, its Sharpe is strong, indicating consistent risk-adjusted returns. The validation set size (2271 rows) is sufficient to trust this model in production.

---

## Model Details

### AAPL / 1d &nbsp; [!] WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `XGBOOST` |
| Sharpe | `1.8979` |
| Trained | `2026-03-15 22:50` |
| Artifact | ✅ `AAPL_1d_winner.joblib` (296KB) |
| Horizon | `3 periods` |
| Rows | `11352` total / `2271` val |
| Target | `52.3%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `1.659` | ✅ `56.8%` | `+7.384` | |
| `xgboost` | ✅ `1.898` | ⚠️ `50.5%` | `+4.656` | **← WINNER** |
| `prophet` | ✅ `1.249` | ✅ `53.5%` | `+5.081` | |

**Issues:**

- ⚠️ **[LOW_ACCURACY]** Accuracy 50.5% below deployment threshold (52%)
- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 296KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 2271 rows

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 1h &nbsp; [OK] PASS

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `XGBOOST` |
| Sharpe | `1.5979` |
| Trained | `2026-03-15 22:50` |
| Artifact | ✅ `AAPL_1h_winner.joblib` (276KB) |
| Horizon | `3 periods` |
| Rows | `3382` total / `677` val |
| Target | `52.8%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `0.931` | ⚠️ `50.5%` | `+0.123` | |
| `xgboost` | ✅ `1.598` | ✅ `53.6%` | `+0.196` | **← WINNER** |
| `prophet` | ⚠️ `0.005` | ⚠️ `51.0%` | `+0.002` | |

**Issues:**

- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 276KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 677 rows

> ✅ **Passes all quality gates.** Safe for GAS.

---

### AAPL / 1h &nbsp; [X] FAIL

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

### AAPL / 1mo &nbsp; [!] WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `5.0394` |
| Trained | `2026-03-15 22:50` |
| Artifact | ✅ `AAPL_1mo_winner.joblib` (2KB) |
| Horizon | `1 periods` |
| Rows | `445` total / `89` val |
| Target | `56.6%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `5.039` | ✅ `55.1%` | `+1.024` | **← WINNER** |
| `xgboost` | ✅ `0.999` | ❌ `38.2%` | `+0.208` | |
| `prophet` | ✅ `4.670` | ✅ `60.7%` | `+2.068` | |

**Issues:**

- ⚠️ **[SUSPICIOUS_SHARPE]** Sharpe 5.039 unusually high — likely small validation set or data artifact
- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.2KB — likely fallback or minimal data
- ⚠️ **[SMALL_VALIDATION_SET]** Only 89 validation rows — estimates are noisy, treat with caution

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 1wk &nbsp; [!] WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `3.0798` |
| Trained | `2026-03-15 22:50` |
| Artifact | ✅ `AAPL_1wk_winner.joblib` (2KB) |
| Horizon | `2 periods` |
| Rows | `2311` total / `463` val |
| Target | `55.7%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `3.080` | ✅ `59.8%` | `+4.807` | **← WINNER** |
| `xgboost` | ✅ `2.945` | ❌ `49.7%` | `+3.311` | |
| `prophet` | ✅ `3.006` | ✅ `59.8%` | `+4.719` | |

**Issues:**

- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.2KB — likely fallback or minimal data
- ℹ️ **[VALIDATION_SIZE]** Validation set: 463 rows

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 4h &nbsp; [!] WARN

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `1.5412` |
| Trained | `2026-03-15 22:50` |
| Artifact | ✅ `AAPL_4h_winner.joblib` (2KB) |
| Horizon | `3 periods` |
| Rows | `1099` total / `220` val |
| Target | `53.2%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `1.541` | ✅ `55.9%` | `+0.063` | **← WINNER** |
| `xgboost` | ✅ `1.015` | ✅ `54.5%` | `+0.122` | |
| `prophet` | ❌ `-0.844` | ❌ `45.0%` | `-0.169` | |

**Issues:**

- ⚠️ **[TINY_LOGISTIC]** Logistic artifact is only 2.2KB — likely fallback or minimal data
- ℹ️ **[VALIDATION_SIZE]** Validation set: 220 rows

> ⚠️ **Review warnings before deploying.**

---

### AAPL / 4h &nbsp; [X] FAIL

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

### BTC-USD / 1d &nbsp; [OK] PASS

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `XGBOOST` |
| Sharpe | `2.0426` |
| Trained | `2026-03-15 22:32` |
| Artifact | ✅ `BTC-USD_1d_winner.joblib` (274KB) |
| Horizon | `3 periods` |
| Rows | `4146` total / `830` val |
| Target | `54.5%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ✅ `1.217` | ❌ `47.5%` | `+0.603` | |
| `xgboost` | ✅ `2.043` | ✅ `52.5%` | `+2.328` | **← WINNER** |
| `prophet` | ⚠️ `0.244` | ❌ `48.3%` | `+0.274` | |

**Issues:**

- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 274KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 830 rows

> ✅ **Passes all quality gates.** Safe for GAS.

---

### BTC-USD / 1h &nbsp; [X] FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `-0.3731` |
| Trained | `2026-03-15 22:32` |
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

### BTC-USD / 1wk &nbsp; [OK] PASS

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `XGBOOST` |
| Sharpe | `3.0845` |
| Trained | `2026-03-15 22:32` |
| Artifact | ✅ `BTC-USD_1wk_winner.joblib` (232KB) |
| Horizon | `2 periods` |
| Rows | `549` total / `110` val |
| Target | `57.0%` UP |

**Model competition:**

| Model | Sharpe | Accuracy | Return | Notes |
|-------|--------|----------|--------|-------|
| `logistic` | ⚠️ `0.000` | ⚠️ `50.0%` | `+0.000` | |
| `xgboost` | ✅ `3.084` | ✅ `53.6%` | `+1.174` | **← WINNER** |
| `prophet` | ⚠️ `0.000` | ⚠️ `50.0%` | `+0.000` | |

**Issues:**

- ℹ️ **[XGBOOST_FULL]** XGBoost artifact is 232KB — full model confirmed
- ℹ️ **[VALIDATION_SIZE]** Validation set: 110 rows

> ✅ **Passes all quality gates.** Safe for GAS.

---

### BTC-USD / 4h &nbsp; [X] FAIL

| Field | Value |
|-------|-------|
| Source | `backend` |
| Winner | `LOGISTIC` |
| Sharpe | `-0.4468` |
| Trained | `2026-03-15 22:32` |
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

*`inspect_models.py` · fin-eye · 2026-03-16 02:11:40*