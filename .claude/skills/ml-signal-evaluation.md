# Skill: ML Signal Evaluation
# When to load: Before reviewing any training run, before merging ML pipeline changes,
#               before promoting a model to production.

## Purpose
This skill defines the quality bar for ML models in fin-eye. A model that trains without
errors is NOT automatically good. These standards define what "good enough to deploy" means.

---

## Minimum Quality Thresholds

| Metric | Minimum | Notes |
|--------|---------|-------|
| Validation Sharpe | ≥ 0.30 | Below this, signal is too weak to be useful |
| Directional Accuracy | ≥ 52% | Must beat random (50%) with meaningful margin |
| All-model Sharpe | At least 1 positive | If all 3 competing models are negative, data is the problem |
| Train vs Val accuracy gap | < 15% | Larger gap = overfitting |

## Red Flags — Investigate Before Deploying

- **Confidence degeneration:** If > 65% of predictions fall within 50% ± 3%, the model has no conviction. It is technically predicting but not finding real patterns.
- **Prophet wins consistently:** Prophet is a trend extrapolator, not a pattern detector. If it beats XGBoost repeatedly, the price series is strongly trending and simple momentum would also work. Consider whether the ML layer is adding value.
- **High accuracy, near-zero Sharpe:** The model is correct directionally but the wins and losses are equal in magnitude. No trading edge exists.
- **All models same Sharpe:** Means the models are predicting almost identically — usually a sign the feature set is too simple or data is too short.
- **Model trained on < 300 rows:** 200 is the hard minimum but < 300 rows produces unstable estimates. Treat such models with extra caution.

## What Good Looks Like

A healthy training result for fin-eye:
- XGBoost wins (most common for structured financial data)
- Sharpe 0.5–1.5 on validation
- Accuracy 54–60% (above this on financial data usually means overfitting)
- Confidence distribution spread across 50–90% range (not clustered near 50%)
- Prophet finishes last or second-to-last (expected)

## Lookahead Bias — The Silent Killer

The most dangerous bug in financial ML. Lookahead bias occurs when features at time T
accidentally contain information from time T+1 or later.

In fin-eye's `engineer_features()`:
- The `target` column is computed as `close.shift(-5)` — this is correct, it is shifted forward
- The `target` is dropped before inference — correct
- All features (RSI, MACD, etc.) use only past data — correct as implemented

**Be very careful when adding new features.** Never use `.shift(-N)` on a feature column.
Never join a table that contains future dates. Always sanity-check: "Could this feature
value at time T have been known at time T in real life?"

## Walk-Forward Validation

The current pipeline uses a simple 80/20 split. This is acceptable for a first version.
For more robust evaluation, consider k-fold walk-forward:
- Split into N time windows
- Train on windows 1..k, validate on window k+1
- Report mean and std of Sharpe across folds
- High std means the model is unstable across market regimes

## What to Do When a Model Fails Quality Gates

1. Check data quality first (`data_quality_checker.py`) — bad data is the #1 cause of bad models
2. Extend the training window — more data almost always helps
3. Check the feature list — are all 10 features actually varying? (print `df[FEATURES].describe()`)
4. Check the target distribution — if 80% of labels are 1 (up), the model will predict mostly 1 and get poor Sharpe
5. Try rebalancing: XGBoost has `scale_pos_weight` parameter for imbalanced classes
6. Do NOT tune hyperparameters to pass the Sharpe gate on validation — that is overfitting the evaluation itself
