# Fin-Eye Agents — How & When to Use

This document defines **when each agent should run**, **who triggers it**, and **what to do with the output**. Think of this as the operations manual for the agent suite.

---

## Agent Overview

| Agent | Model | Purpose | Typical Runtime |
|-------|-------|---------|----------------|
| `ml_output_evaluator.py` | DeepSeek R1 32B | Judges whether a trained model's Sharpe/accuracy meets the quality bar | ~30–60s |
| `data_quality_checker.py` | Qwen2.5-Coder 32B | Validates OHLCV and macro data feeds for gaps, anomalies, staleness | ~15–30s |
| `gas_sanity_agent.py` | Gemma2 27B | Checks whether a GAS snapshot result is plausible given the components | ~20–40s |
| `cicd_model_gate.py` | DeepSeek R1 32B | Compares a newly trained challenger model against the current champion | ~45–90s |

---

## Trigger Rules — When to Run Each Agent

### 1. `ml_output_evaluator.py` — Run After Every Model Training

**Trigger:** Any time `run_training_pipeline()` in `ml_pipeline.py` completes.

**Mandatory before:**
- Merging a PR that changes `ml_pipeline.py`, `feature_builder.py`, or `technical_service.py`
- Deploying a newly trained model to production
- Changing the `FEATURES` list in `ml_pipeline.py`

**Skip if:** You are only changing non-ML code (frontend, auth, migrations, etc.)

```bash
python ml_output_evaluator.py --symbol AAPL --timeframe 1h
python ml_output_evaluator.py --symbol AAPL --timeframe 4h
# Run for each symbol/timeframe pair you just trained
```

**Pass criteria (configured in config.yaml):**
- Sharpe Ratio ≥ 0.3
- Accuracy ≥ 52%
- At least one model did not fail with an exception during training
- Confidence distribution is not degenerate (not all predictions near 50%)

**If it fails:** Do NOT promote the model. Investigate feature quality or increase training data window.

---

### 2. `data_quality_checker.py` — Run Before Training and on Schedule

**Trigger A — Before training:** Always run this before kicking off a training pipeline. Bad input data produces a confident but wrong model.

**Trigger B — Scheduled:** Run daily as part of the GAS pre-compute batch to catch feed issues early.

**Trigger C — Manual:** Run when you suspect a data feed is broken (e.g. GAS scores look frozen or implausible).

```bash
python data_quality_checker.py --symbol AAPL
python data_quality_checker.py --symbol AAPL --check-macro
python data_quality_checker.py --all-symbols   # checks all default symbols
```

**What it checks:**
- OHLCV: price gaps > 20%, volume = 0 for multiple consecutive bars, adjusted close divergence
- Macro: staleness per indicator (VIX: max 1 day, CPI: max 35 days, NFP: max 35 days, Fed rate: max 7 days)
- Sentiment: FinBERT score distribution — if > 90% of articles score the same direction over 7 days, flags as suspicious
- Yahoo Finance silent empty response detection (the 4h bug class)

**If it fails:** Fix the data feed issue before proceeding. Do not train on known-bad data.

---

### 3. `gas_sanity_agent.py` — Run After GAS Pre-Compute

**Trigger A — After batch pre-compute:** Run once per batch to spot outliers across all symbols.

**Trigger B — On large GAS movement:** If any symbol's GAS moves > 15 points between two consecutive snapshots, run automatically. (You can wire this into the scheduler — see CI/CD section below.)

**Trigger C — Manual investigation:** When a user reports "this score looks wrong."

```bash
python gas_sanity_agent.py --symbol TSLA
python gas_sanity_agent.py --all-symbols --last-snapshot
```

**What it checks:**
- Are all three components (technical, sentiment, macro) directionally consistent?
- If one component is a major outlier, is there a plausible reason?
- Did GAS move > 15 points without a significant macro or sentiment event?
- Is the regime label (Risk-On/Risk-Off) consistent with the macro score direction?
- Are timeframe signals internally consistent (not 1h Bullish + 4h Bearish with high confidence on both)?

**Output:** PASS / WARN / FAIL with plain-English explanation. WARN does not block anything — it means "investigate before trusting this score." FAIL means the snapshot is unreliable.

---

### 4. `cicd_model_gate.py` — Run When Promoting a New Model

**Trigger:** When you want to replace the current production model (`*_winner.joblib`) with a newly trained challenger.

This is the most critical gate — it prevents a regression where a new model trains successfully (passes `ml_output_evaluator`) but is worse than the existing production model.

```bash
python cicd_model_gate.py --symbol AAPL --timeframe 1h \
  --champion data/models/AAPL_1h_winner.joblib \
  --challenger data/models/AAPL_1h_challenger.joblib
```

**Promotion criteria:**
- Challenger Sharpe ≥ Champion Sharpe − 0.05 (challenger must be within 5% of champion or better)
- Challenger accuracy ≥ Champion accuracy − 0.02
- Challenger does not have more than 2× the champion's maximum drawdown on validation set

**Output:** PROMOTE / HOLD / REJECT with full comparison table. If PROMOTE, the agent renames the challenger to `_winner.joblib` automatically (with backup of the old champion).

---

## CI/CD Integration

### Option A — Git Hooks (simplest, no extra infrastructure)

Add a pre-push hook that runs the evaluator on any changed ML files:

```bash
# .git/hooks/pre-push  (make executable: chmod +x)
#!/bin/bash
CHANGED=$(git diff --name-only HEAD~1 HEAD)

if echo "$CHANGED" | grep -qE "ml_pipeline|feature_builder|technical_service"; then
  echo "ML files changed — running ml_output_evaluator..."
  cd .claude/agents
  python ml_output_evaluator.py --from-registry --last-trained
  if [ $? -ne 0 ]; then
    echo "BLOCKED: ml_output_evaluator failed. Fix model quality before pushing."
    exit 1
  fi
fi
```

### Option B — GitHub Actions (recommended for team use)

Create `.github/workflows/ml-quality-gate.yml`:

```yaml
name: ML Quality Gate
on:
  push:
    paths:
      - 'backend/app/services/ml_pipeline.py'
      - 'backend/app/services/feature_builder.py'
      - 'backend/app/services/technical_service.py'

jobs:
  ml-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install requests pyyaml
      - name: Run ML output evaluator (no Ollama — rule-based mode)
        run: |
          cd .claude/agents
          python ml_output_evaluator.py --from-registry --ci-mode
          # In CI mode: Ollama is not available, runs rule-based checks only
```

> **Note:** GitHub Actions runners do not have Ollama. In `--ci-mode` the agents run rule-based checks only (Sharpe thresholds, accuracy floors, data staleness) without the LLM narrative layer. This is still valuable — it catches numeric failures automatically.

### Option C — Integrate into the APScheduler (for gas_sanity_agent)

In `backend/app/services/scheduler.py`, after the GAS batch completes, optionally call the sanity agent as a subprocess:

```python
import subprocess
import os

async def post_gas_batch_sanity_check(symbols: list[str]):
    agent_path = os.path.join(
        os.path.dirname(__file__), "../../../../.claude/agents/gas_sanity_agent.py"
    )
    for symbol in symbols:
        subprocess.Popen(
            ["python", agent_path, "--symbol", symbol, "--log-only"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
```

Use `--log-only` mode so the agent writes results to a log file rather than blocking the scheduler.

---

## Reading Agent Output

All agents write output in a consistent format:

```
═══════════════════════════════════════
AGENT: ml_output_evaluator
SYMBOL: AAPL | TIMEFRAME: 1h
RESULT: PASS ✅ / WARN ⚠️  / FAIL ❌
═══════════════════════════════════════
RULE-BASED CHECKS:
  [PASS] Sharpe Ratio: 0.81 (threshold: ≥ 0.30)
  [PASS] Accuracy: 54.2% (threshold: ≥ 52%)
  [PASS] Winning model: xgboost (not fallback)
  [WARN] Confidence distribution: 68% of predictions between 50–55% (low conviction)

LLM ANALYSIS (DeepSeek R1 32B):
  The Sharpe of 0.81 is acceptable but the low conviction distribution suggests
  the model is not finding strong patterns. Consider adding volume-based features
  or extending the training window before the next production deployment.

RECOMMENDATION: Safe to promote, but monitor live Sharpe over next 5 trading days.
═══════════════════════════════════════
```

**PASS** — safe to proceed.
**WARN** — proceed with awareness, investigate the flagged item.
**FAIL** — stop. Do not promote/deploy until resolved.

---

## Dependency Requirements

All agents require only:
```
requests>=2.28.0
pyyaml>=6.0
```

No fin-eye app dependencies. No database connection. Agents read from:
- `backend/data/models/model_registry.jsonl` (ml_output_evaluator, cicd_model_gate)
- The fin-eye REST API at `localhost:8000` (gas_sanity_agent, data_quality_checker)
- Or directly from `config.yaml` overrides

---

## Without Ollama

If `ollama serve` is not running or a model is not pulled, agents automatically fall back to rule-based mode. You lose the narrative LLM analysis but all numeric gates still apply. The output header will show:

```
⚠️  Ollama unavailable — running in rule-based mode (no LLM analysis)
```

This means agents are always safe to run in CI environments or on colleague machines without Ollama installed.
