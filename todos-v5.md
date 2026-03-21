# Fin-Eye — Todos v5
> **Version:** 5.0
> **Created:** 2026-03-21
> **Author:** Product + Dev brainstorm session
> **Status:** Next-round implementation backlog
>
> ⚠️ This file covers the NEXT ROUND of features — do not start until core v4 pipeline is stable.
> todos-v4.md = bulk seed/train pipeline, news storage, external data sources.
> todos-v5.md = UX clarity, LLM investment manager, ML improvements, prediction database, dev transparency layer.
>
> **Legend:** 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Nice-to-have · ✅ Done
> **Prefixes:** BE = Backend · FE = Frontend · DB = Database · ML = Machine Learning · LLM = LLM/AI Layer

---

## CONTEXT — Why This File Exists

This file was born from a brainstorm covering four interconnected topics:

1. **UX Clarity** — the ML signal is technically correct but users don't understand what they're looking at
2. **Dev Transparency Layer** — power users and technically-minded traders want to see under the hood
3. **LLM Investment Manager** — the LLM insight section can be dramatically more useful if given more structured inputs and a consistent persona
4. **ML Improvements** — more algorithms, hyperparameter tuning, and a prediction database that creates a live feedback loop

These are presented as phases in logical implementation order.

---

## PHASE 1 — UX: Signal Clarity (Progressive Disclosure)

> **Problem:** "Technical models predict direction" tells a user nothing. A model accuracy of 57% sounds bad. "3-day horizon" sounds arbitrary.
> **Goal:** Every user — regardless of technical background — immediately understands what the signal means, what to expect, and how confident to be.

### Design Principle: Three Layers

The correct pattern is **progressive disclosure** — the same information shown at three levels of depth, each available on demand but not forced.

```
LAYER 1 (everyone sees this — default view):
  ┌─────────────────────────────────────────────────┐
  │  📈  Likely UP in ~3 days                       │
  │      73% model confidence                       │
  │      Based on daily chart · Next update in 6h   │
  └─────────────────────────────────────────────────┘

LAYER 2 (curious users — "What drove this?" expand):
  RSI is oversold (32) ↑  ·  MACD crossed bullish ↑
  Bollinger Band bounce ↑  ·  5-day momentum neutral
  XGBoost model won this timeframe (Sharpe 0.91)

LAYER 3 (power users / devs — "Model Details" toggle):
  Model: XGBoost (beat Logistic + Prophet)
  Validation accuracy: 57.3% on 420 bars
  Sharpe ratio: 0.91 · Total return: +18.4%
  Horizon: 3 periods (daily bars) · Trained: 2026-03-18
  Feature list with weights (expandable)
  MLflow run ID: abc123 (link to MLflow UI)
```

### 1.1 FE — Signal card redesign

- [ ] 🔴 `FE` Redesign the timeframe signal tile to show Layer 1 by default:
  - Direction icon (📈 / 📉 / ➡️) + plain English label ("Likely UP in ~3 days")
  - Confidence % as a horizontal bar (not a raw number alone)
  - Timeframe label in plain language: "Daily chart → 3-day outlook" not "1d / horizon=3"
  - "Next model update" countdown (based on last trained_at + refresh interval)
  - **File:** `frontend/components/TimeframeGrid.tsx` or signal tile sub-component

- [ ] 🔴 `FE` Add **"What drove this?"** expandable section (Layer 2) to each timeframe tile:
  - Show top 3–5 features that pushed the signal in each direction, in plain English
  - Use SHAP values from backend (see ML section 4.1) if available; fall back to feature value + threshold description
  - Examples: "RSI at 32 — oversold territory, historically bullish", "MACD just crossed signal line upward"
  - Collapsed by default, expands inline on click

- [ ] 🟠 `FE` Add **multi-timeframe agreement indicator** above the grid:
  - "3 of 5 timeframes agree: UP" — shown as a summary banner
  - Colour: green if ≥3 agree, amber if split, red if ≥3 disagree with each other
  - Plain English: "Timeframes mostly agree → stronger signal" / "Timeframes conflict → wait for confirmation"

### 1.2 FE — "What does this mean?" modal for cold users

- [ ] 🟠 `FE` Add a persistent **"?"** icon on the Technical Consensus card header that opens a plain-English explainer modal:
  - "This model looks at 15 technical indicators from price and volume history."
  - "It predicts whether the price is more likely to be HIGHER or LOWER in 3 days (on the daily chart)."
  - "A 73% confidence score means: in similar past conditions, the stock went in the predicted direction 73% of the time."
  - "This is a probability, not a guarantee. Always manage your risk."
  - Keep it short, friendly, no jargon

### 1.3 FE — Confidence label system

- [ ] 🟡 `FE` Map confidence % to plain labels used everywhere in the UI:

  | Confidence | Label | Colour |
  |---|---|---|
  | ≥ 75% | Strong signal | Emerald |
  | 65–74% | Moderate signal | Emerald-muted |
  | 55–64% | Weak signal | Amber |
  | 50–54% | Uncertain | Amber |
  | < 50% | No clear signal | Gray |

  - Use these labels + colours on signal tiles, the LLM insight card, and all tooltips
  - Never show a bare decimal like "0.5731" to users — always round and label

---

## PHASE 2 — Dev Transparency Layer

> **Problem:** Technically-minded users (quant traders, developers, finance professionals) want to know exactly what the model is doing and why. Hiding this erodes trust.
> **Goal:** Make every number in the system explainable without cluttering the default view.

### Best Practice Decision

**Do NOT put a single "Dev Info" button on each page.** That gets ignored.
Instead, use an **always-accessible, per-section model details panel** that is:
- Hidden by default
- Accessible via a small "⚙ Model Details" link at the bottom of each signal section
- Persistent across page refreshes (toggled state saved in localStorage)
- Also available as a dedicated `/model-info/{symbol}` route for deep dives

### 2.1 BE — Model details endpoint

- [ ] 🟠 `BE` Add `GET /api/v1/technical/{symbol}/model-details`
  Returns per timeframe:
  ```json
  {
    "symbol": "AAPL",
    "timeframes": {
      "1d": {
        "winner_model": "xgboost",
        "all_models": {
          "xgboost":  { "accuracy": 0.573, "sharpe": 0.91, "total_return": 0.184, "disqualified": false },
          "logistic": { "accuracy": 0.541, "sharpe": 0.62, "total_return": 0.091, "disqualified": false },
          "prophet":  { "accuracy": 0.0,   "sharpe": -99,  "total_return": 0.0,   "disqualified": true, "reason": "accuracy == 0.0" }
        },
        "features_used": [
          { "name": "rsi_14",         "description": "RSI over 14 periods — momentum oscillator. >70 overbought, <30 oversold." },
          { "name": "macd_hist",      "description": "MACD histogram — difference between MACD line and signal. Positive = bullish momentum." },
          { "name": "bb_pb",          "description": "Bollinger Band %B — where price sits within the band. 0=lower band, 1=upper band." },
          { "name": "sma_cross_10_20","description": "10-period SMA divided by 20-period SMA minus 1. Positive = short-term trend above medium-term." },
          { "name": "atr_pct",        "description": "Average True Range as % of price — measures current volatility." },
          { "name": "volume_ratio",   "description": "Current volume vs 20-day average. >1 = above-average activity." },
          { "name": "ret_1",          "description": "1-period return — yesterday's price change." },
          { "name": "mom_10",         "description": "10-period momentum — % change over last 10 bars." },
          { "name": "mom_20",         "description": "20-period momentum — % change over last 20 bars." }
        ],
        "training_info": {
          "trained_at": "2026-03-18T10:00:00",
          "train_rows": 1473,
          "val_rows": 369,
          "total_rows": 1842,
          "horizon_periods": 3,
          "target_balance_up_pct": 52.1,
          "quality_gate_passed": true,
          "mlflow_run_id": "abc123def456"
        },
        "how_target_was_built": "Binary label: 1 if price is higher 3 daily bars from now, 0 if lower. 80% of data used for training (chronological split, no lookahead).",
        "how_sharpe_was_built": "Sharpe = mean(strategy_returns) / std(strategy_returns) × √252. Strategy return = actual return if model predicted UP, else 0."
      }
    }
  }
  ```
  - **File:** `backend/app/api/v1/endpoints/technical.py`

### 2.2 FE — "⚙ Model Details" panel

- [ ] 🟠 `FE` Create `frontend/components/ModelDetailsPanel.tsx`
  - Triggered by "⚙ Model Details" text link at bottom of Technical Consensus card
  - Side drawer (slides in from right) or collapsible section below the grid
  - Tabs: **Overview** · **Features** · **Training Info** · **All Models**
  - **Overview tab:** winner model, accuracy, Sharpe, horizon explanation in plain English + technical values
  - **Features tab:** table of all 15 features with name, current value for this ticker, and plain-English description. Highlight the top 3 by SHAP importance if available.
  - **Training tab:** train/val rows, trained_at date, target balance, quality gate status, MLflow run ID
  - **All Models tab:** comparison table of all 3 model results including disqualified ones and reason

### 2.3 FE — `/model-info/{symbol}` deep-dive page

- [ ] 🟡 `FE` Create a standalone route `/model-info/{symbol}` with full technical documentation for that ticker:
  - All timeframe model details in one page
  - Feature importance chart (bar chart of SHAP values — see ML section 4.1)
  - Prediction history table (see Phase 5 — prediction database)
  - Live accuracy tracker (see Phase 5)
  - Link to MLflow UI run (for devs running locally)
  - Accessible from the "⚙ Model Details" panel via "View full model report →"

---

## PHASE 3 — LLM Investment Manager

> **Problem:** The current LLM insight section receives minimal structured input and produces generic text.
> **Goal:** Feed the LLM a rich structured prompt and give it a consistent investment manager persona, producing actionable, quantified, conditional advice every time.

### 3.1 Design: LLM Input Schema

The prompt sent to the LLM should include all of the following as a structured JSON block:

```
MARKET DATA:
  - Current price, 52-week high/low, distance from each
  - ATR (absolute + % of price) — for stop/target calculation
  - Volume ratio (vs 20-day average)

ML SIGNALS (all timeframes):
  - Direction + confidence + horizon for 1h, 4h, 1d, 1wk, 1mo
  - Multi-timeframe agreement score (how many agree)
  - Whether quality gate passed for each timeframe
  - Sharpe ratio of the winning model per timeframe

TECHNICAL INDICATORS (current values):
  - RSI 14, MACD histogram, BB %B, momentum 10/20
  - SMA 10/20/50 trend (above/below)
  - Price vs SMA50

MACRO CONTEXT:
  - Macro score (0–100) + regime label
  - VIX level
  - 10Y–2Y yield spread

SENTIMENT:
  - News sentiment 1d / 7d / 30d
  - Source diversity score
  - Reddit / StockTwits sentiment (if available)

HISTORICAL CONTEXT:
  - Average return in similar signal conditions (from prediction DB — see Phase 5)
  - Maximum recorded single-period return for this symbol (safety anchor)
  - Win rate of this model on live predictions (from prediction DB)
  - How many times this signal configuration has appeared historically

PROBABILISTIC PRICE TARGETS (computed before LLM call — see 3.2):
  - Expected price in N days (current × (1 + expected_return))
  - Upside target: expected + 1 ATR
  - Downside stop: expected - 1 ATR (conservative) or current - 1 ATR
  - Confidence band (low / mid / high)
```

### 3.2 BE — Pre-LLM price target computation

- [ ] 🔴 `BE` Before calling the LLM, compute **probabilistic price targets** from existing model outputs:

  ```python
  def compute_price_targets(current_price, expected_return, atr, confidence):
      """
      All outputs are probabilistic ranges, not exact predictions.
      These are fed to the LLM as context — not shown raw to the user.
      """
      mid_target   = current_price * (1 + expected_return)
      upper_target = mid_target + atr          # optimistic scenario
      lower_stop   = current_price - atr       # conservative stop (1 ATR below current)
      
      return {
          "expected_price":  round(mid_target, 2),
          "upside_target":   round(upper_target, 2),
          "downside_stop":   round(lower_stop, 2),
          "expected_return_pct": round(expected_return * 100, 2),
          "confidence":      confidence,
          "horizon_label":   "~3 days",
          "atr_used":        round(atr, 2),
          "note": "Probabilistic estimate based on historical model behaviour. Not a guarantee."
      }
  ```

  - **File:** `backend/app/services/llm_service.py` (new function, called before LLM prompt assembly)
  - These targets feed into the LLM prompt — they are not shown directly to the user (the LLM synthesises them into prose)

### 3.3 BE — LLM persona + system prompt

- [ ] 🔴 `BE` Define a consistent system prompt in `llm_service.py`:

  ```
  PERSONA: You are a senior quantitative portfolio manager at a hedge fund. 
  You are direct, data-driven, and always quantify uncertainty. 
  You never recommend blindly — every action has a condition. 
  You always distinguish between short-term (days) and medium-term (weeks) views.
  You always include a risk note. You never promise returns.

  OUTPUT FORMAT: Always respond in this exact structure:
  
  [PRIMARY SIGNAL]
  One sentence: what the models suggest, with timeframe and confidence.
  
  [ENTRY]
  Specific price level or condition for entry (based on ATR and current price).
  
  [TARGETS]
  Short-term exit target and expected return %.
  What "great" looks like vs what is historically unusual to expect.
  
  [RISK MANAGEMENT]
  Stop-loss level. What to do if price drops X% before moving up. 
  Whether to add to position on dip and at what level.
  
  [TIMEFRAME SPLIT]
  Short-term view (1–3 days). Medium-term view (1–2 weeks). Where they agree or conflict.
  
  [MACRO CONTEXT]  
  How macro conditions support or contradict the technical signal.
  
  [CAUTION]
  One specific risk the data is showing. A historical upper bound on return.
  One sentence investment disclaimer.
  ```

  - This structure must be enforced via the system prompt — the LLM cannot deviate from it
  - Parse the LLM response by section headers for structured rendering on the frontend

### 3.4 FE — LLM insight card redesign

- [ ] 🔴 `FE` Redesign the LLM insight section to render the structured response:
  - Each section ([PRIMARY SIGNAL], [ENTRY], etc.) renders as a distinct visual block
  - Icon per section: 🎯 Entry · 📊 Targets · 🛡️ Risk · 📅 Timeframe · 🌍 Macro · ⚠️ Caution
  - Confidence badge (Strong / Moderate / Weak / Uncertain) based on multi-timeframe agreement
  - "Based on [N] timeframes · [N] agree · Model confidence [X]%" as a sub-header
  - Small disclaimer at the bottom: "This is a probabilistic analysis, not financial advice."
  - "Regenerate" button to call the LLM again (useful if user wants a fresh synthesis)

### 3.5 FE — Timeframe view selector for LLM insight

- [ ] 🟠 `FE` Add a toggle above the LLM insight card: **Short-term** (1–3 days) | **Medium-term** (1–2 weeks) | **Long-term** (monthly)
  - Switching the view regenerates the LLM prompt with emphasis on the relevant timeframes
  - This makes the LLM insight feel personalised to the user's trading style

---

## PHASE 4 — ML Improvements

> **Goal:** Better models, tuned hyperparameters, and interpretability features that feed both the dev transparency layer and the LLM insight.

### 4.1 BE — SHAP feature importance

- [ ] 🟠 `BE` Add SHAP computation after XGBoost training:
  ```python
  import shap
  explainer  = shap.TreeExplainer(best_obj.model)
  shap_vals  = explainer.shap_values(X_val[FEATURES])
  importance = pd.DataFrame({
      "feature": FEATURES,
      "mean_abs_shap": np.abs(shap_vals).mean(axis=0)
  }).sort_values("mean_abs_shap", ascending=False)
  ```
  - Store SHAP importances in the model registry (JSON field in JSONL or separate file)
  - Expose via `GET /api/v1/technical/{symbol}/model-details` (see Phase 2.1)
  - Used to power Layer 2 "What drove this?" explanation (see Phase 1.1)
  - **File:** `backend/app/services/ml_pipeline.py`

### 4.2 BE — LightGBM as 4th competitor

- [ ] 🟠 `BE` Add LightGBM to the model competition in `ml_pipeline.py`:
  ```python
  from lightgbm import LGBMClassifier

  class LightGBMWrapper:
      def __init__(self):
          self.model = LGBMClassifier(
              n_estimators=300, max_depth=4, learning_rate=0.03,
              subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
              class_weight="balanced", random_state=42, verbose=-1,
          )
      def fit(self, X, y):        self.model.fit(X[FEATURES], y)
      def predict_proba(self, X): return self.model.predict_proba(X[FEATURES])
  ```
  - Add `"lightgbm": LightGBMWrapper()` to the `models` dict alongside existing 3
  - LightGBM is typically faster than XGBoost on tabular data and comparable in accuracy
  - Add `lightgbm` to `requirements.txt`
  - **File:** `backend/app/services/ml_pipeline.py`

### 4.3 BE — Probability-weighted ensemble (voting)

- [ ] 🟠 `BE` After all 4 models are trained, add an ensemble as a 5th "candidate":
  ```python
  class EnsembleWrapper:
      """Soft voting ensemble — weighted average of probabilities."""
      def __init__(self, trained_models: dict, weights: dict = None):
          self.models  = trained_models
          # Weight by validation Sharpe (normalized, floor at 0)
          sharpes = {n: max(0, m.get("sharpe_ratio", 0)) for n, m in results.items()}
          total   = sum(sharpes.values()) or 1
          self.weights = {n: s / total for n, s in sharpes.items()}
      
      def predict_proba(self, X):
          blended = np.zeros((len(X), 2))
          for name, model in self.models.items():
              w = self.weights.get(name, 0)
              blended += w * model.predict_proba(X)
          return blended
  ```
  - Add ensemble to `results` dict and let `select_winner` evaluate it normally
  - The ensemble will often win by Sharpe because it smooths individual model errors
  - **File:** `backend/app/services/ml_pipeline.py`

### 4.4 BE — Optuna hyperparameter tuning (XGBoost + LightGBM)

- [ ] 🟡 `BE` Add optional Optuna tuning pass before final model fit:
  ```python
  import optuna
  optuna.logging.set_verbosity(optuna.logging.WARNING)

  def tune_xgboost(X_train, y_train, X_val, y_val, n_trials=30):
      def objective(trial):
          params = {
              "n_estimators":    trial.suggest_int("n_estimators", 100, 500),
              "max_depth":       trial.suggest_int("max_depth", 3, 6),
              "learning_rate":   trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
              "subsample":       trial.suggest_float("subsample", 0.6, 1.0),
              "colsample_bytree":trial.suggest_float("colsample_bytree", 0.6, 1.0),
              "min_child_weight":trial.suggest_int("min_child_weight", 1, 10),
          }
          m = XGBClassifier(**params, eval_metric="logloss", random_state=42)
          m.fit(X_train, y_train)
          return float(np.mean(m.predict(X_val) == y_val))
      
      study = optuna.create_study(direction="maximize")
      study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
      return study.best_params
  ```
  - Tuning is optional — gated by a config flag `ENABLE_HYPERTUNING=True` in `.env`
  - Only run during full retrain, not incremental updates (too slow per-symbol)
  - Best params stored in model registry for transparency
  - Add `optuna` to `requirements.txt`
  - **File:** `backend/app/services/ml_pipeline.py`

### 4.5 BE — Remove or demote Prophet

- [ ] 🟡 `BE` Prophet consistently gets disqualified (accuracy = 0.0) in `ml_pipeline.py`. Two options:
  - **Option A (recommended):** Remove Prophet from the per-symbol signal competition entirely. Move it to macro regime detection only (it works better on slow-moving macro series like VIX or yield spread trends). 
  - **Option B:** Keep Prophet but only allow it to vote in the ensemble (never be the solo winner), capped at 20% ensemble weight.
  - Decision: go with Option A — cleaner, faster training, less noise.

### 4.6 ML — Additional features to add to `engineer_features()`

- [ ] 🟡 `BE` Add the following features to the ML feature set in `ml_pipeline.py`:

  **Market regime features:**
  - `vix_level_norm` — VIX normalised (z-score vs 252-day mean) — distinguishes calm vs fearful market
  - `yield_spread` — 10Y–2Y spread from macro DB — regime signal for all stocks

  **Price structure features:**
  - `high_low_pct` — (high - low) / close — intraday range, measures indecision vs conviction
  - `close_position` — (close - low) / (high - low) — where price closed in the daily range (1.0 = strong close, 0.0 = weak close)
  - `gap_pct` — (open - prev_close) / prev_close — overnight gap size and direction

  **Multi-timeframe confirmation:**
  - `ret_10_vs_ret_20` — whether 10-day momentum direction matches 20-day momentum — consistency signal
  - `sma_slope_20` — slope of the 20-day SMA (rising / flat / falling)

  These 7 additional features are low-cost to compute and add meaningful signal variety.

---

## PHASE 5 — Prediction Database (Live Feedback Loop)

> **Brainstorm conclusion:** Store every model prediction in the database. After the horizon passes, compare prediction to actual outcome. This creates a live accuracy tracker, reveals model degradation, and eventually becomes new training signal.
>
> **This is one of the highest long-term value additions in this entire file.**

### Why this matters

When the model is trained, you measure accuracy on validation data from the past. But you have no idea if it's still accurate on *today's* live data. Markets change. The prediction database is the answer:

- Track real-world accuracy, not just historical validation accuracy
- Discover: "XGBoost is 61% accurate in trending markets but only 48% in choppy markets"
- Discover: "The 1d model is great for large-caps but unreliable for small-caps"
- Discover: "Accuracy drops significantly 6 weeks after training — triggers automatic retrain"
- The accumulated rows eventually become a dataset: "in what conditions does this model work?"
- Long-term: train a **meta-model** that predicts when to trust the base model

### 5.1 DB — `ml_predictions` table

- [ ] 🔴 `DB` Alembic migration:
  ```sql
  CREATE TABLE ml_predictions (
    id               BIGSERIAL PRIMARY KEY,
    symbol           VARCHAR(20)  NOT NULL,
    timeframe        VARCHAR(10)  NOT NULL,    -- '1h', '4h', '1d', '1wk', '1mo'
    model_name       VARCHAR(30)  NOT NULL,    -- 'xgboost', 'ensemble', etc.
    mlflow_run_id    VARCHAR(100),             -- links to exact trained model version
    
    predicted_at     TIMESTAMP    NOT NULL,    -- when prediction was made
    predicted_direction INTEGER  NOT NULL,     -- 1 = UP, 0 = DOWN
    confidence       FLOAT        NOT NULL,    -- probability of predicted class (0.5–1.0)
    expected_return  FLOAT,                   -- model's estimated return magnitude
    
    horizon_periods  INTEGER      NOT NULL,    -- how many periods ahead
    horizon_ends_at  TIMESTAMP    NOT NULL,    -- predicted_at + horizon (for easy lookup)
    
    price_at_prediction FLOAT     NOT NULL,    -- actual price when prediction was made
    
    -- Filled in after horizon_ends_at has passed (by outcome_resolver cron):
    price_at_outcome FLOAT,                   -- actual price at horizon end
    actual_direction INTEGER,                 -- 1 = went UP, 0 = went DOWN
    actual_return    FLOAT,                   -- actual % return over horizon
    was_correct      BOOLEAN,                 -- predicted_direction == actual_direction
    outcome_resolved_at TIMESTAMP,            -- when the outcome was filled in
    
    -- Feature snapshot at prediction time (JSON) — for later analysis
    feature_snapshot JSONB,                   -- { rsi_14: 32.1, macd_hist: 0.003, ... }
    
    -- Metadata
    macro_score_at_prediction FLOAT,          -- macro score when prediction was made
    vix_at_prediction         FLOAT,          -- VIX when prediction was made
    market_regime_at_prediction VARCHAR(30),  -- 'goldilocks', 'risk-off', etc.
    
    created_at TIMESTAMP DEFAULT NOW()
  );

  -- Indexes for common query patterns
  CREATE INDEX idx_mlpred_symbol_tf    ON ml_predictions(symbol, timeframe);
  CREATE INDEX idx_mlpred_horizon_end  ON ml_predictions(horizon_ends_at) WHERE outcome_resolved_at IS NULL;
  CREATE INDEX idx_mlpred_model        ON ml_predictions(model_name);
  CREATE INDEX idx_mlpred_correct      ON ml_predictions(was_correct, symbol);
  CREATE INDEX idx_mlpred_predicted_at ON ml_predictions(predicted_at DESC);
  ```

### 5.2 BE — Prediction storage on every inference

- [ ] 🔴 `BE` Modify `technical_service.py` — every time a signal is computed for a user, store it:
  ```python
  async def store_prediction(db, symbol, timeframe, model_name, direction, 
                             confidence, expected_return, horizon_periods,
                             price_now, feature_snapshot, macro_score, vix, regime):
      horizon_ends = datetime.utcnow() + horizon_delta(timeframe, horizon_periods)
      pred = MLPrediction(
          symbol=symbol, timeframe=timeframe, model_name=model_name,
          predicted_at=datetime.utcnow(), predicted_direction=direction,
          confidence=confidence, expected_return=expected_return,
          horizon_periods=horizon_periods, horizon_ends_at=horizon_ends,
          price_at_prediction=price_now,
          feature_snapshot=feature_snapshot,
          macro_score_at_prediction=macro_score,
          vix_at_prediction=vix,
          market_regime_at_prediction=regime,
      )
      db.add(pred)
      await db.commit()
  ```
  - **Deduplication:** only store if no prediction exists for same (symbol, timeframe, day)
  - **File:** `backend/app/services/technical_service.py`

### 5.3 BE — Outcome resolver cron

- [ ] 🔴 `BE` Add to `scheduler.py` — runs every hour:
  ```python
  @scheduler.scheduled_job("interval", hours=1)
  async def resolve_prediction_outcomes():
      """
      Find all predictions where horizon_ends_at <= now and outcome_resolved_at IS NULL.
      Fetch current price from yfinance (or OHLCV DB).
      Fill in: price_at_outcome, actual_direction, actual_return, was_correct.
      """
      pending = db.query(MLPrediction).filter(
          MLPrediction.horizon_ends_at <= datetime.utcnow(),
          MLPrediction.outcome_resolved_at == None
      ).all()
      
      for pred in pending:
          price_now = await get_latest_price(pred.symbol)
          actual_return = (price_now / pred.price_at_prediction) - 1
          actual_dir    = 1 if actual_return > 0 else 0
          
          pred.price_at_outcome      = price_now
          pred.actual_return         = actual_return
          pred.actual_direction      = actual_dir
          pred.was_correct           = (actual_dir == pred.predicted_direction)
          pred.outcome_resolved_at   = datetime.utcnow()
      
      db.commit()
  ```

### 5.4 BE — Live accuracy stats endpoint

- [ ] 🟠 `BE` Add `GET /api/v1/technical/{symbol}/prediction-stats`
  Returns:
  ```json
  {
    "symbol": "AAPL",
    "timeframes": {
      "1d": {
        "total_resolved":    142,
        "correct":           84,
        "live_accuracy":     0.591,
        "val_accuracy":      0.573,
        "accuracy_delta":    "+1.8%",
        "avg_return_when_correct":    0.024,
        "avg_return_when_wrong":     -0.019,
        "by_regime": {
          "goldilocks": { "accuracy": 0.641, "n": 67 },
          "risk-off":   { "accuracy": 0.523, "n": 31 }
        },
        "recent_30d_accuracy": 0.612,
        "trend": "improving"
      }
    },
    "best_performing_timeframe": "1d",
    "model_health": "good"
  }
  ```

### 5.5 BE — Model drift alert

- [ ] 🟡 `BE` In the outcome resolver cron, after resolving, compute 30-day rolling accuracy per symbol/timeframe:
  - If live 30d accuracy drops more than 10 percentage points below training accuracy → create a `model_drift_alert` in DB
  - Add `GET /api/v1/admin/ml/drift-report` endpoint listing all drift alerts
  - Optionally: auto-trigger retrain for drifted models (flag in settings: `AUTO_RETRAIN_ON_DRIFT=True`)

### 5.6 FE — Live accuracy display in Model Details panel

- [ ] 🟠 `FE` In `ModelDetailsPanel.tsx` (Phase 2.2), add a "Live Performance" tab:
  - Training accuracy vs live accuracy, side by side
  - "This model has been correct N/M times on live data (last 30 days)"
  - By-regime breakdown (if enough data): "Works better in trending markets"
  - Recent prediction history: last 10 predictions with outcome (✓ / ✗)
  - Colour code: green if live accuracy ≥ validation accuracy, amber if slightly below, red if significantly below (drift)

### 5.7 ML — Feature analysis from prediction DB

- [ ] 🟢 `BE` After 3+ months of prediction data accumulate, add analysis jobs:
  - **Regime-conditional accuracy:** `SELECT market_regime, AVG(was_correct) FROM ml_predictions GROUP BY market_regime`
  - **Feature value at correct predictions vs wrong predictions:** which feature values correlate with correctness?
  - **Time-of-year effects:** is accuracy seasonal? (earnings seasons, summer lows, January effect)
  - These are SQL queries producing insights — run weekly, cache results, expose at `/admin/ml/prediction-insights`
  - Long-term: feed these insights as additional features in the next training round (closing the loop)

---

## PHASE 6 — Probabilistic Price Targets (Frontend)

> **Decision from brainstorm:** Build probabilistic price targets. Always show confidence band + horizon. Never show a single price as a certainty. This is honest, defensible, and used by Bloomberg/institutional tools.

### 6.1 FE — Price target display in LLM insight card

- [ ] 🟠 `FE` Below the LLM [TARGETS] section, render a visual price target band:

  ```
  Current:  $182.50
  ─────────────────────────────────────────────────────────
  Upside    $188.20  (+3.1%)  ─────────────────▲ optimistic
  Expected  $185.80  (+1.8%)  ──────────────── ● base case
  Current   $182.50  (0.0%)   ──────── ● now
  Stop      $179.30  (–1.7%)  ──── ▼ stop loss
  ─────────────────────────────────────────────────────────
  Horizon: ~3 days · Confidence: 73% · Based on ATR + model return
  ⚠ Probabilistic estimate. Not a price guarantee.
  ```

  - Rendered as a simple SVG range chart (not an image — generated inline)
  - Numbers come from the pre-LLM computation (Phase 3.2)
  - Clicking any level shows its calculation: "Stop = current price − 1× ATR ($3.20)"

### 6.2 BE — Probabilistic price target endpoint

- [ ] 🟠 `BE` Add `GET /api/v1/technical/{symbol}/price-targets`
  ```json
  {
    "symbol": "AAPL",
    "current_price": 182.50,
    "timeframe": "1d",
    "horizon_label": "~3 days",
    "atr_14": 3.20,
    "targets": {
      "upside":   { "price": 188.20, "pct_change": 3.1,  "basis": "expected + 1 ATR" },
      "expected": { "price": 185.80, "pct_change": 1.8,  "basis": "current × (1 + model expected return)" },
      "stop":     { "price": 179.30, "pct_change": -1.7, "basis": "current − 1 ATR" }
    },
    "confidence": 0.73,
    "model_expected_return": 0.018,
    "disclaimer": "Probabilistic estimate based on model expected return and ATR. Not a guarantee."
  }
  ```

---

## PHASE 7 — Position Sizing (Kelly Criterion)

> **Brainstorm conclusion:** Position sizing is mathematically sound, honest if framed as "suggestion based on model accuracy", and completes the trade plan the LLM produces. It is not misleading if the formula is shown.

### 7.1 BE — Kelly Criterion computation

- [ ] 🟡 `BE` Add position sizing computation to the price target endpoint or a dedicated endpoint:
  ```python
  def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
      """
      Full Kelly = (win_rate / |avg_loss|) - ((1 - win_rate) / avg_win)
      Half Kelly recommended for real trading (reduces variance significantly).
      """
      if avg_loss == 0 or avg_win == 0:
          return 0.0
      full_kelly = (win_rate / abs(avg_loss)) - ((1 - win_rate) / avg_win)
      half_kelly = full_kelly / 2
      return max(0.0, min(half_kelly, 0.25))  # cap at 25% of portfolio
  ```
  - Inputs from prediction DB: `live_accuracy`, `avg_return_when_correct`, `avg_return_when_wrong`
  - Output: suggested fraction of portfolio for this signal
  - Always accompanied by: "This is a mathematical suggestion. Adjust for your own risk tolerance."

### 7.2 FE — Position size suggestion in LLM insight

- [ ] 🟡 `FE` In the [RISK MANAGEMENT] section of the LLM insight card, add:
  ```
  Suggested position size: ~8% of portfolio (Half-Kelly, based on 59% live win rate)
  If price drops to stop: add up to half your initial position (avg down)
  ```
  - Show Kelly formula in a tooltip: "Kelly Criterion: based on this model's live win rate and average wins/losses"
  - Clearly marked as a suggestion, not advice

---

## SUMMARY: New Files This Round

### Backend — Create
```
backend/app/models/ml_prediction.py           # MLPrediction SQLAlchemy model
backend/alembic/versions/xxxx_ml_predictions.py  # Migration for ml_predictions table
```

### Backend — Modify
```
backend/app/services/ml_pipeline.py           # Add LightGBM, ensemble, SHAP, Optuna, remove Prophet from competition
backend/app/services/technical_service.py     # Store prediction on every inference call
backend/app/services/llm_service.py           # Structured prompt, persona, pre-LLM price targets
backend/app/services/scheduler.py             # Outcome resolver cron + drift alerts
backend/app/api/v1/endpoints/technical.py     # model-details, prediction-stats, price-targets endpoints
backend/requirements.txt                      # Add: lightgbm, optuna, shap
```

### Frontend — Create
```
frontend/components/ModelDetailsPanel.tsx     # Dev transparency side drawer
frontend/components/PriceTargetChart.tsx      # SVG probabilistic target range chart
frontend/app/model-info/[symbol]/page.tsx     # Full model deep-dive route
```

### Frontend — Modify
```
frontend/components/TimeframeGrid.tsx         # Layer 1 signal card redesign + Layer 2 expandable
frontend/components/LLMInsightCard.tsx        # Structured output rendering + persona sections
frontend/lib/api.ts                           # New endpoint calls
```

---

## IMPLEMENTATION ORDER (Suggested Sprints)

```
Sprint 1 — Signal UX (highest user impact, no DB work needed)
  Phase 1.1: Signal card redesign (Layer 1 + Layer 2)
  Phase 1.2: "What does this mean?" modal
  Phase 1.3: Confidence label system

Sprint 2 — LLM Investment Manager (biggest differentiator)
  Phase 3.2: Pre-LLM price target computation (BE)
  Phase 3.3: LLM persona + system prompt (BE)
  Phase 3.4: LLM insight card redesign (FE)

Sprint 3 — Prediction Database (long-term strategic value)
  Phase 5.1: ml_predictions table migration
  Phase 5.2: Store prediction on inference (BE)
  Phase 5.3: Outcome resolver cron (BE)
  Phase 5.4: Live accuracy stats endpoint (BE)

Sprint 4 — ML Improvements
  Phase 4.1: SHAP feature importance
  Phase 4.2: LightGBM as 4th model
  Phase 4.3: Ensemble voting
  Phase 4.5: Remove Prophet from competition

Sprint 5 — Dev Transparency Layer
  Phase 2.1: Model details endpoint (BE)
  Phase 2.2: ModelDetailsPanel component (FE)
  Phase 5.6: Live accuracy in Model Details panel (FE)

Sprint 6 — Price Targets + Position Sizing
  Phase 6.1–6.2: Probabilistic price target display
  Phase 7.1–7.2: Kelly Criterion position sizing

Sprint 7 — Advanced (after 3+ months of prediction data)
  Phase 4.4: Optuna hyperparameter tuning
  Phase 5.5: Model drift alerts + auto-retrain
  Phase 5.7: Feature analysis from prediction DB
  Phase 2.3: /model-info/{symbol} deep-dive page
```

---

## OPEN QUESTIONS FOR NEXT SESSION

| # | Question | Options |
|---|---|---|
| 1 | Prophet: remove from competition entirely or keep in ensemble? | Recommended: remove. Move to macro regime only. |
| 2 | Optuna tuning: run per-symbol at training time or as a separate overnight job? | Separate overnight job — too slow per-symbol in real-time. |
| 3 | Prediction DB: store on every API call or only once per day per symbol/timeframe? | Once per day per symbol/timeframe (deduplicated). |
| 4 | LLM persona: which model to use? | claude-sonnet-4-20250514 via Anthropic API (already configured). |
| 5 | Kelly Criterion: show it or hide it behind an "Advanced" toggle? | Show it but with clear "this is a mathematical suggestion" label. |
| 6 | Price targets: show in main view or only in LLM insight card? | LLM insight card only for now — add to main view in a later sprint. |

---

*todos-v5.md — Created 2026-03-21.*
*Covers: UX signal clarity · Dev transparency layer · LLM investment manager persona · ML improvements (LightGBM, ensemble, SHAP, Optuna) · Prediction database + live accuracy feedback loop · Probabilistic price targets · Kelly position sizing.*
*Companion files: todos-v4.md (bulk pipeline), todos-v3.md (app polish + security), todos.md (original UX backlog).*
