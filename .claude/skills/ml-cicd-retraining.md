# Skill: ML CI/CD Retraining
# When to load: When setting up retraining schedules, when a model's live performance
#               degrades, before adding new features to the pipeline.

## Purpose
Defines when to retrain models, how to validate before promoting, and how to detect
that a deployed model is drifting or degrading on live data.

---

## When to Retrain

### Scheduled Retraining (Recommended Defaults)

| Timeframe | Retrain Frequency | Reason |
|-----------|------------------|--------|
| 1h model | Weekly (every Monday) | Intraday patterns shift with market microstructure changes |
| 4h model | Bi-weekly | Same reason, slower cadence acceptable |
| 1d model (future) | Monthly | Daily patterns are more stable |
| 1wk / 1mo (future) | Quarterly | Long-term regime models are most stable |

### Event-Triggered Retraining

Retrain immediately (don't wait for schedule) when:
- A major market regime change occurs (e.g. Fed pivots from hiking to cutting rates)
- VIX spikes above 35 and stays there for > 5 trading days (structural volatility shift)
- The live Sharpe of a model (estimated from recent predictions vs actual outcomes) drops > 30% below its validation Sharpe
- A new data source is added to the feature set (all models must be retrained with the new features)
- A bug is fixed in `engineer_features()` that affected the original training data

### Do NOT Retrain When
- The model had one bad week — short-term noise is expected
- You want to "improve" a model that already passes quality gates — unnecessary retraining increases overfitting risk
- Market conditions are extremely unusual (e.g. COVID crash days) — waiting for conditions to normalize produces more stable models

---

## The Retraining Workflow

```
1. Run data_quality_checker.py --symbol SYMBOL
   ↓ Must PASS before proceeding
2. Run run_training_pipeline() in ml_pipeline.py
   (saves challenger artifact, logs to registry)
   ↓
3. Run ml_output_evaluator.py --symbol SYMBOL --timeframe TF
   ↓ Must PASS or WARN (not FAIL)
4. Run cicd_model_gate.py --symbol SYMBOL --timeframe TF
   ↓ Must return PROMOTE
5. Optionally: cicd_model_gate.py --auto-promote
   ↓
6. Run gas_sanity_agent.py --symbol SYMBOL
   ↓ Verify GAS snapshots still look reasonable with new model
```

---

## Detecting Live Model Drift

The current fin-eye system does not yet have a live drift detector. Here is how to add one
without a heavy MLOps framework:

### Simple Drift Check (add to scheduler)

Once a week, for each deployed model:
1. Look at the last 20 predictions stored in the registry (direction + confidence).
2. Compare to actual outcomes (did the price go up or down 5 periods later?).
3. Compute a rolling 20-prediction accuracy and Sharpe.
4. If rolling accuracy drops below 48% (worse than random) for 2 consecutive weeks → trigger retraining alert.

### Open Source Tools for Drift Detection (Optional, No Ollama Required)

**Evidently AI** (`pip install evidently`):
- Generates HTML data drift reports
- Can compare feature distributions between training data and recent live data
- Run weekly as a standalone script, save report to `backend/data/drift_reports/`
- Free, open source, no cloud required

```python
# Example: weekly drift check (add as a standalone script)
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
import pandas as pd

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=training_features_df, current_data=recent_features_df)
report.save_html("drift_report.html")
```

**MLflow** (`pip install mlflow`):
- Tracks every training run with parameters, metrics, and artifacts
- Self-hosted, free, no cloud account needed
- Integrates with the existing `model_registry.jsonl` pattern — or replaces it
- Run `mlflow ui` to see a dashboard of all training runs

To integrate MLflow into `ml_pipeline.py`:
```python
import mlflow
mlflow.set_experiment("fin-eye-technical-signals")
with mlflow.start_run():
    mlflow.log_param("symbol", symbol)
    mlflow.log_param("timeframe", timeframe)
    mlflow.log_metric("validation_sharpe", best_sharpe)
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_artifact(artifact_path)
```

---

## Feature Change Protocol

When adding or removing features from `ml_pipeline.py: FEATURES`:

1. All existing deployed models are immediately invalid — they were trained on a different feature set.
2. You MUST retrain all symbol/timeframe combinations before the new code is deployed.
3. Update the feature tables in `.claude/skills/ml-signal-evaluation.md` and `backend/README.md`.
4. Run the full agent suite for at least the top 3 symbols (AAPL, MSFT, SPY) before merging.
5. Do not add features and change model hyperparameters in the same PR — changing too many things at once makes it impossible to diagnose regressions.

---

## Champion Backup & Rollback

`cicd_model_gate.py` automatically backs up the current champion before promoting a challenger (configurable in `config.yaml: model_gate.backup_champion`). Backup files use the suffix `.champion_backup`.

To roll back manually:
```bash
cd backend/data/models
cp AAPL_1h_winner.joblib.champion_backup AAPL_1h_winner.joblib
```

Then clear the Redis cache for that symbol:
```bash
redis-cli DEL gas:snapshot:AAPL
```

The next GAS pre-compute will use the restored model.
