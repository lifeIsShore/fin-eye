"""
inspect_models.py
─────────────────────────────────────────────────────────────────────────────
Local model registry inspector for fin-eye.

Reads both registries (backend/data/models/ and model_store/) and produces:
  1. A terminal report with rich rule-based quality checks
  2. An optional LLM evaluation via local Ollama (DeepSeek R1 32B) — STREAMING
  3. An optional markdown report saved to .claude/reports/

Quality gates (all configurable in config.yaml):
  Min Sharpe:       0.30   — below this = no edge
  Min Accuracy:     52%    — must beat random
  Min Trades:       200    — validation set floor
  Max Sharpe:       5.0    — above this = likely noise / tiny sample
  Max Drawdown:     25%    — max allowed strategy drawdown on val set
  Min Profit Factor: 1.1   — gross wins / gross losses must exceed 1.1

Sharpe tiered feedback (incremental, shown inline):
  < 0.0   FAIL  — model destroys value
  0.0–0.3 FAIL  — no usable edge
  0.3–0.5 WARN  — weak signal, marginal
  0.5–1.0 PASS  — acceptable ★
  1.0–2.0 PASS  — good ★★
  2.0–5.0 PASS  — strong ★★★  (verify not overfitted)
  > 5.0   WARN  — suspicious, likely small sample

Usage:
    python inspect_models.py                        # rule-based only
    python inspect_models.py --llm                  # + Ollama LLM streaming
    python inspect_models.py --llm --save-report    # full report saved to .md
    python inspect_models.py --registry backend
    python inspect_models.py --symbol AAPL
    python inspect_models.py --flag-issues
    python inspect_models.py --clean-test

Run from the fin-eye project root:
    python .claude/agents/inspect_models.py --llm --save-report
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

# ── Project paths ─────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
REPORTS_DIR   = SCRIPT_DIR.parent / "reports"
CONFIG_PATH   = SCRIPT_DIR / "config.yaml"

BACKEND_REGISTRY  = PROJECT_ROOT / "backend" / "data" / "models" / "model_registry.jsonl"
BACKEND_ARTIFACTS = PROJECT_ROOT / "backend" / "data" / "models"
STORE_REGISTRY    = PROJECT_ROOT / "model_store" / "registry.jsonl"

# ── Default thresholds (overridden by config.yaml if present) ─────────────────

DEFAULTS = {
    "min_sharpe":        0.30,
    "min_accuracy":      0.52,
    "min_trades":        200,       # minimum validation set rows
    "max_sharpe":        5.0,       # above = suspicious
    "max_drawdown_pct":  25.0,      # max strategy drawdown on val set (%)
    "min_profit_factor": 1.1,       # gross_wins / gross_losses
    "suspicious_sharpe": 5.0,       # alias kept for markdown report
}


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {
        "ollama": {"base_url": "http://localhost:11434", "timeout_seconds": 360, "enabled": True},
        "models": {"reasoning": "deepseek-r1:32b"},
    }


def get_thresholds(config: dict) -> dict:
    ml = config.get("ml_evaluation", {})
    return {
        "min_sharpe":        ml.get("min_sharpe",        DEFAULTS["min_sharpe"]),
        "min_accuracy":      ml.get("min_accuracy",      DEFAULTS["min_accuracy"]),
        "min_trades":        ml.get("min_trades",        DEFAULTS["min_trades"]),
        "max_sharpe":        ml.get("max_sharpe",        DEFAULTS["max_sharpe"]),
        "max_drawdown_pct":  ml.get("max_drawdown_pct",  DEFAULTS["max_drawdown_pct"]),
        "min_profit_factor": ml.get("min_profit_factor", DEFAULTS["min_profit_factor"]),
    }


# ── Registry loaders ──────────────────────────────────────────────────────────

def load_registry(path: Path, source_label: str) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                r["_registry_line"] = i
                r["_source"] = source_label
                records.append(r)
            except json.JSONDecodeError as e:
                print(f"  [WARN] Line {i} in {path.name} is not valid JSON: {e}")
    return records


def load_all_registries(which: str) -> list[dict]:
    records = []
    if which in ("backend", "all"):
        records.extend(load_registry(BACKEND_REGISTRY, "backend"))
    if which in ("store", "all"):
        records.extend(load_registry(STORE_REGISTRY, "store"))
    return records


# ── Artifact helpers ──────────────────────────────────────────────────────────

def check_artifact_exists(record: dict) -> tuple[bool, str]:
    if record.get("_source") == "backend":
        path = BACKEND_ARTIFACTS / record.get("artifact_file", "")
    else:
        path = PROJECT_ROOT / record.get("artifact_path", "")
    return path.exists(), str(path)


def get_artifact_size_kb(path_str: str) -> Optional[float]:
    try:
        return Path(path_str).stat().st_size / 1024
    except Exception:
        return None


# ── Derived metrics from registry data ───────────────────────────────────────

def compute_derived_metrics(metrics_dict: dict, winner: str) -> dict:
    """
    Compute max drawdown and profit factor from the winner's stored metrics.

    These are estimated from total_return and the binary signal pattern since
    the registry only stores aggregated metrics (not the full equity curve).

    Notes:
      - max_drawdown is estimated as abs(worst single-period loss * sqrt(val_rows))
        — this is a rough proxy, not a precise drawdown calculation.
      - profit_factor = sum(positive returns) / abs(sum(negative returns))
        We approximate using total_return and accuracy:
          gross_wins  ≈ accuracy * avg_win  (unknown, proxied)
          gross_losses ≈ (1-accuracy) * avg_loss
        Since we lack per-trade data, we use:
          profit_factor ≈ (accuracy / (1 - accuracy)) * (total_return / max(abs_loss, 1e-9))
        This is indicative only — real profit factor needs the full trade log.
    """
    m = metrics_dict.get(winner, {})
    if not m:
        return {"max_drawdown_pct": None, "profit_factor": None, "n_trades": None}

    total_return = m.get("total_return", 0)
    accuracy     = m.get("accuracy", 0.5)
    sharpe       = m.get("sharpe_ratio", 0)

    # Estimate n_trades from val_rows (each row is a potential trade signal)
    n_trades = None  # filled from diagnostics elsewhere

    # Profit factor proxy
    if accuracy > 0 and accuracy < 1 and total_return is not None:
        win_rate  = accuracy
        loss_rate = 1 - accuracy
        if loss_rate > 0 and total_return != 0:
            # Rough: assume symmetric wins/losses, scaled by total_return direction
            profit_factor = (win_rate / loss_rate) * max(1.0, 1.0 + total_return)
            profit_factor = round(min(profit_factor, 99.0), 2)
        else:
            profit_factor = None
    else:
        profit_factor = None

    # Max drawdown proxy: use Sharpe to infer volatility of returns
    # A Sharpe of S with std ~ mean/S implies potential drawdown ~ 2/S * 100%
    # Capped at 100%
    if sharpe and sharpe > 0:
        max_drawdown_pct = round(min((2.0 / sharpe) * 100.0, 100.0), 1)
    elif sharpe and sharpe < 0:
        max_drawdown_pct = 100.0  # negative Sharpe = unlimited drawdown potential
    else:
        max_drawdown_pct = None

    return {
        "max_drawdown_pct": max_drawdown_pct,
        "profit_factor":    profit_factor,
        "n_trades":         n_trades,
    }


# ── Sharpe tier ───────────────────────────────────────────────────────────────

def sharpe_tier(sharpe: float) -> tuple[str, str, str]:
    """
    Returns (tier_label, stars, description) for a given Sharpe value.
    Used for inline display and tiered feedback.
    """
    if sharpe < 0:
        return "FAIL",       "",      "destroys value"
    if sharpe < 0.30:
        return "FAIL",       "",      "no usable edge"
    if sharpe < 0.50:
        return "MARGINAL",   "★",     "weak signal — marginal"
    if sharpe < 1.00:
        return "ACCEPTABLE", "★★",    "acceptable edge"
    if sharpe < 2.00:
        return "GOOD",       "★★★",   "good edge"
    if sharpe < 5.00:
        return "STRONG",     "★★★★",  "strong — verify not overfitted"
    return "SUSPICIOUS",     "?",     "unusually high — check sample size"


# ── Rich issue detection ──────────────────────────────────────────────────────

def detect_issues(record: dict, thresholds: dict) -> list[dict]:
    """
    Returns a list of issues: {level, code, message, value (optional)}

    Levels:  ERROR  → model must not be deployed
             WARN   → review before deploying
             INFO   → informational, no action required
    """
    issues = []
    sharpe   = record.get("validation_sharpe") or record.get("sharpe_ratio")
    metrics  = record.get("metrics", {})
    winner   = record.get("model_name") or record.get("model_kind", "unknown")
    symbol   = record.get("symbol", "?")
    tf       = record.get("timeframe", "?")
    diag     = record.get("diagnostics", {})
    val_rows = diag.get("val_rows")

    accuracy = metrics.get(winner, {}).get("accuracy") if metrics else record.get("accuracy")
    derived  = compute_derived_metrics(metrics, winner)
    max_dd   = derived["max_drawdown_pct"]
    pf       = derived["profit_factor"]

    min_sh   = thresholds["min_sharpe"]
    min_acc  = thresholds["min_accuracy"]
    min_tr   = thresholds["min_trades"]
    max_sh   = thresholds["max_sharpe"]
    max_dd_t = thresholds["max_drawdown_pct"]
    min_pf   = thresholds["min_profit_factor"]

    def add(level, code, message, value=None):
        entry = {"level": level, "code": code, "message": message}
        if value is not None:
            entry["value"] = value
        issues.append(entry)

    # ── Sharpe — tiered ───────────────────────────────────────────────────────
    if sharpe is None:
        add("ERROR", "NO_SHARPE", "No Sharpe ratio recorded")
    elif sharpe < 0:
        add("ERROR", "NEGATIVE_SHARPE",
            f"Sharpe {sharpe:.3f} — model destroys value on validation set", sharpe)
    elif sharpe < min_sh:
        add("ERROR", "SHARPE_BELOW_MIN",
            f"Sharpe {sharpe:.3f} below minimum ({min_sh}) — no deployable edge", sharpe)
    elif sharpe < 0.50:
        tier, stars, desc = sharpe_tier(sharpe)
        add("WARN", "SHARPE_MARGINAL",
            f"Sharpe {sharpe:.3f} {stars} — {desc}. Usable but watch closely", sharpe)
    elif sharpe > max_sh:
        add("WARN", "SHARPE_SUSPICIOUS",
            f"Sharpe {sharpe:.3f} exceeds max ({max_sh}) — likely noise or tiny sample", sharpe)
    else:
        tier, stars, desc = sharpe_tier(sharpe)
        add("INFO", f"SHARPE_{tier}",
            f"Sharpe {sharpe:.3f} {stars} — {desc}", sharpe)

    # ── Accuracy ──────────────────────────────────────────────────────────────
    if accuracy is None:
        add("WARN", "NO_ACCURACY", "No accuracy recorded")
    elif accuracy < 0.50:
        add("ERROR", "BELOW_RANDOM",
            f"Accuracy {accuracy:.1%} is below random (50%) — anti-predictive", accuracy)
    elif accuracy < min_acc:
        add("WARN", "LOW_ACCURACY",
            f"Accuracy {accuracy:.1%} below threshold ({min_acc:.0%}) — marginal directional edge",
            accuracy)
    elif accuracy < 0.56:
        add("INFO", "ACCURACY_OK",
            f"Accuracy {accuracy:.1%} — modest but genuine edge for binary classification",
            accuracy)
    elif accuracy < 0.62:
        add("INFO", "ACCURACY_GOOD",
            f"Accuracy {accuracy:.1%} — good directional signal", accuracy)
    else:
        add("INFO", "ACCURACY_STRONG",
            f"Accuracy {accuracy:.1%} — strong directional signal (verify not overfitted)",
            accuracy)

    # ── Min trades (validation set size) ─────────────────────────────────────
    if val_rows is not None:
        if val_rows < 50:
            add("ERROR", "TINY_VALIDATION_SET",
                f"Only {val_rows} validation rows — metrics are statistically unreliable",
                val_rows)
        elif val_rows < min_tr:
            add("WARN", "SMALL_VALIDATION_SET",
                f"Validation set has {val_rows} rows (min recommended: {min_tr}) — noisy estimates",
                val_rows)
        elif val_rows < 500:
            add("INFO", "VALIDATION_SIZE",
                f"Validation set: {val_rows} rows — adequate", val_rows)
        else:
            add("INFO", "VALIDATION_SIZE_GOOD",
                f"Validation set: {val_rows} rows — statistically robust", val_rows)

    # ── Max drawdown ──────────────────────────────────────────────────────────
    if max_dd is not None:
        if max_dd > max_dd_t:
            add("WARN", "HIGH_DRAWDOWN",
                f"Estimated max drawdown ~{max_dd:.1f}% exceeds threshold ({max_dd_t}%) — high risk",
                max_dd)
        elif max_dd > 15:
            add("INFO", "DRAWDOWN_MODERATE",
                f"Estimated max drawdown ~{max_dd:.1f}% — moderate, acceptable for a signal",
                max_dd)
        else:
            add("INFO", "DRAWDOWN_LOW",
                f"Estimated max drawdown ~{max_dd:.1f}% — low drawdown risk", max_dd)

    # ── Profit factor ─────────────────────────────────────────────────────────
    if pf is not None:
        if pf < min_pf:
            add("WARN", "LOW_PROFIT_FACTOR",
                f"Estimated profit factor ~{pf:.2f} below threshold ({min_pf}) — wins barely cover losses",
                pf)
        elif pf < 1.3:
            add("INFO", "PROFIT_FACTOR_OK",
                f"Estimated profit factor ~{pf:.2f} — marginal but positive expectancy", pf)
        else:
            add("INFO", "PROFIT_FACTOR_GOOD",
                f"Estimated profit factor ~{pf:.2f} — positive expectancy", pf)

    # ── Sharpe/accuracy contradiction ─────────────────────────────────────────
    if sharpe and accuracy and sharpe > 1.0 and accuracy < 0.50:
        add("WARN", "SHARPE_ACCURACY_CONTRADICTION",
            f"Positive Sharpe ({sharpe:.2f}) with accuracy below 50% ({accuracy:.1%}) — "
            "model wins when market moves strongly but calls direction wrong overall")

    # ── Target balance ────────────────────────────────────────────────────────
    target_balance = diag.get("target_balance_up_pct")
    if target_balance is not None:
        imbalance = abs(target_balance - 50)
        if imbalance > 15:
            direction = "UP" if target_balance > 50 else "DOWN"
            add("WARN", "TARGET_IMBALANCE",
                f"Target is {target_balance:.1f}% {direction} — imbalanced labels may bias model",
                target_balance)
        else:
            add("INFO", "TARGET_BALANCED",
                f"Target balance: {target_balance:.1f}% UP / {100-target_balance:.1f}% DOWN — well balanced",
                target_balance)

    # ── Low-variance features ─────────────────────────────────────────────────
    low_var = diag.get("low_variance_features", [])
    if low_var:
        add("WARN", "LOW_VARIANCE_FEATURES",
            f"Near-zero variance features (useless to model): {low_var}")

    # ── Artifact ──────────────────────────────────────────────────────────────
    artifact_exists, artifact_path = check_artifact_exists(record)
    size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None

    if not artifact_exists:
        add("ERROR", "ARTIFACT_MISSING",
            "Joblib file not found on disk — model cannot be loaded for inference")
    elif winner == "logistic" and size_kb and size_kb < 5:
        add("WARN", "TINY_LOGISTIC",
            f"Logistic artifact is only {size_kb:.1f}KB — likely a fallback or minimal training data")
    elif winner == "xgboost" and size_kb and size_kb > 100:
        add("INFO", "XGBOOST_FULL",
            f"XGBoost artifact is {size_kb:.0f}KB — full trained model confirmed")

    # ── Prophet failure ───────────────────────────────────────────────────────
    if metrics:
        pa = metrics.get("prophet", {}).get("accuracy")
        if pa == 0.0:
            add("WARN", "PROPHET_FAILED",
                "Prophet returned 0.0 accuracy — training failed (close_raw injection issue)")

    # ── All competing models failed ───────────────────────────────────────────
    if metrics:
        all_sharpes = [m.get("sharpe_ratio", -99) for m in metrics.values()
                       if isinstance(m, dict)]
        if all(s < 0 for s in all_sharpes) and all_sharpes:
            add("ERROR", "ALL_MODELS_NEGATIVE_SHARPE",
                "All 3 competing models have negative Sharpe — data quality issue likely")

    # ── Weekly small sample ───────────────────────────────────────────────────
    if tf == "1wk" and sharpe and sharpe > max_sh:
        add("WARN", "WEEKLY_SMALL_SAMPLE",
            "Weekly timeframe: very few validation bars — high Sharpe is likely statistical noise")

    # ── Test data in registry ─────────────────────────────────────────────────
    if symbol == "TEST_SYM":
        add("WARN", "TEST_DATA_IN_REGISTRY",
            "TEST_SYM is synthetic test data — remove with --clean-test")

    # ── Model age ─────────────────────────────────────────────────────────────
    trained_at = record.get("trained_at", "")
    if trained_at:
        try:
            trained_dt = datetime.fromisoformat(trained_at.replace("Z", "+00:00"))
            age_days   = (datetime.now(tz=trained_dt.tzinfo) - trained_dt).days
            if age_days > 60:
                add("WARN", "MODEL_STALE",
                    f"Model is {age_days} days old — retraining recommended", age_days)
            elif age_days > 30:
                add("INFO", "MODEL_AGE",
                    f"Model is {age_days} days old — consider retraining soon", age_days)
        except Exception:
            pass

    return issues


# ── Verdict ───────────────────────────────────────────────────────────────────

LEVEL_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}
LEVEL_ICON  = {"ERROR": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ "}


def verdict(issues: list[dict]) -> tuple[str, str]:
    levels = [i["level"] for i in issues]
    if "ERROR" in levels:
        return "FAIL", "❌"
    if "WARN" in levels:
        return "WARN", "⚠️ "
    return "PASS", "✅"


def overall_grade(sharpe: Optional[float], accuracy: Optional[float],
                  val_rows: Optional[int], issues: list[dict]) -> str:
    """
    Single letter grade D → A+ summarising the model quality at a glance.
    Shown in the terminal header line for each model.
    """
    v_label, _ = verdict(issues)
    if v_label == "FAIL":
        return "D"
    if sharpe is None or accuracy is None:
        return "?"

    # Base score from Sharpe (0-60 points)
    if   sharpe >= 2.0: sh_pts = 60
    elif sharpe >= 1.0: sh_pts = 45
    elif sharpe >= 0.5: sh_pts = 30
    elif sharpe >= 0.3: sh_pts = 15
    else:               sh_pts = 0

    # Accuracy (0-30 points)
    if   accuracy >= 0.62: ac_pts = 30
    elif accuracy >= 0.56: ac_pts = 20
    elif accuracy >= 0.52: ac_pts = 10
    elif accuracy >= 0.50: ac_pts = 5
    else:                   ac_pts = 0

    # Val rows (0-10 points)
    if   val_rows and val_rows >= 500: vr_pts = 10
    elif val_rows and val_rows >= 200: vr_pts = 5
    else:                              vr_pts = 0

    score = sh_pts + ac_pts + vr_pts

    if   score >= 90: return "A+"
    elif score >= 75: return "A"
    elif score >= 60: return "B"
    elif score >= 45: return "C"
    else:             return "D"


# ── Active model selection ────────────────────────────────────────────────────

def get_active_models(records: list[dict]) -> dict[tuple, dict]:
    active: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("symbol"), r.get("timeframe"), r.get("_source"))
        active[key] = r
    return active


# ── Terminal output ───────────────────────────────────────────────────────────

def print_model_block(record: dict, issues: list[dict],
                      thresholds: dict, show_breakdown: bool = True):
    symbol  = record.get("symbol", "?")
    tf      = record.get("timeframe", "?")
    winner  = record.get("model_name") or record.get("model_kind", "unknown")
    sharpe  = record.get("validation_sharpe") or record.get("sharpe_ratio")
    trained = (record.get("trained_at") or "")[:16].replace("T", " ")
    source  = record.get("_source", "?")
    metrics = record.get("metrics", {})
    diag    = record.get("diagnostics", {})
    horizon = record.get("horizon_periods", "?")

    artifact_exists, artifact_path = check_artifact_exists(record)
    size_kb  = get_artifact_size_kb(artifact_path) if artifact_exists else None
    v_label, v_icon = verdict(issues)
    val_rows = diag.get("val_rows")

    # Derived metrics for winner
    derived  = compute_derived_metrics(metrics, winner)
    max_dd   = derived["max_drawdown_pct"]
    pf       = derived["profit_factor"]
    winner_m = metrics.get(winner, {})
    accuracy = winner_m.get("accuracy") if winner_m else None

    # Grade
    grade    = overall_grade(sharpe, accuracy, val_rows, issues)
    sh_tier, sh_stars, sh_desc = sharpe_tier(sharpe) if sharpe is not None else ("?", "", "?")

    # ── Header line ───────────────────────────────────────────────────────────
    grade_pad = f"  Grade: {grade:<3}"
    print(f"  ┌─ {symbol} / {tf}  [{source}]  {v_icon} {v_label}{grade_pad}")

    # ── Winner summary ────────────────────────────────────────────────────────
    if sharpe is not None:
        sh_str = f"{sharpe:.4f}  {sh_stars}  {sh_desc}"
    else:
        sh_str = "N/A"
    print(f"  │  Winner:   {winner.upper():<12}  Sharpe: {sh_str}")

    acc_str = f"{accuracy:.1%}" if accuracy is not None else "N/A"
    dd_str  = f"~{max_dd:.1f}%" if max_dd is not None else "N/A"
    pf_str  = f"~{pf:.2f}"     if pf  is not None else "N/A"
    print(f"  │  Accuracy: {acc_str:<10}  MaxDD: {dd_str:<12}  ProfitFactor: {pf_str}")
    print(f"  │  Trained:  {trained}  Artifact: {'✅ ' + f'{size_kb:.0f}KB' if artifact_exists and size_kb else '❌ MISSING'}")

    # ── Training data summary ─────────────────────────────────────────────────
    if diag:
        total_rows  = diag.get("total_rows", "?")
        target_bal  = diag.get("target_balance_up_pct", "?")
        print(
            f"  │  Data:     total={total_rows}  val={val_rows}  "
            f"target={target_bal}% UP  horizon={horizon}p"
        )

    # ── All-models competition table ──────────────────────────────────────────
    if metrics and show_breakdown:
        min_sh  = thresholds["min_sharpe"]
        min_acc = thresholds["min_accuracy"]
        print(f"  │  Model competition:")
        print(f"  │    {'Model':<10}  {'Sharpe':>8}  {'Acc':>7}  {'Return':>8}  {'Stars':<6}  Notes")
        print(f"  │    {'─'*8}  {'─'*8}  {'─'*7}  {'─'*8}  {'─'*6}  {'─'*20}")
        for m_name in ["logistic", "xgboost", "prophet"]:
            m = metrics.get(m_name, {})
            if not m:
                print(f"  │    {m_name:<10}  {'—':>8}  {'—':>7}  {'—':>8}")
                continue
            acc  = m.get("accuracy", 0)
            sh   = m.get("sharpe_ratio", -99)
            ret  = m.get("total_return", 0)
            disq = " [DISQ]" if m.get("disqualified") else ""
            mark = " ← WINNER" if m_name == winner else ""
            _, stars, _ = sharpe_tier(sh)
            sh_ok  = "✅" if sh  >= min_sh  else ("⚠️ " if sh  >= 0   else "❌")
            acc_ok = "✅" if acc >= min_acc else ("⚠️ " if acc >= 0.50 else "❌")
            notes  = (mark + disq).strip()
            print(
                f"  │    {m_name:<10}  {sh:>7.3f}{sh_ok}  "
                f"{acc:>6.1%}{acc_ok}  {ret:>+8.3f}  {stars:<6}  {notes}"
            )

    # ── Issues ────────────────────────────────────────────────────────────────
    if issues:
        # Group: errors first, then warns, then infos
        errors = [i for i in issues if i["level"] == "ERROR"]
        warns  = [i for i in issues if i["level"] == "WARN"]
        infos  = [i for i in issues if i["level"] == "INFO"]

        if errors or warns:
            print(f"  │  Issues:")
            for iss in errors + warns:
                print(f"  │    {LEVEL_ICON[iss['level']]} [{iss['code']}] {iss['message']}")

        if infos:
            print(f"  │  Metrics:")
            for iss in infos:
                print(f"  │    {LEVEL_ICON['INFO']} {iss['message']}")

    print(f"  └{'─' * 70}")


# ── Ollama LLM evaluation ─────────────────────────────────────────────────────

def check_ollama(config: dict) -> bool:
    try:
        requests.get(f"{config['ollama']['base_url']}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def build_llm_prompt(active_models: dict, all_issues: dict,
                     thresholds: dict) -> str:
    model_summaries = []

    for key, record in sorted(active_models.items(),
                               key=lambda x: (x[0][0] or "", x[0][1] or "")):
        symbol  = record.get("symbol", "?")
        tf      = record.get("timeframe", "?")
        winner  = record.get("model_name") or record.get("model_kind", "unknown")
        sharpe  = record.get("validation_sharpe") or record.get("sharpe_ratio", 0)
        metrics = record.get("metrics", {})
        diag    = record.get("diagnostics", {})
        issues  = all_issues[key]
        v_label, _ = verdict(issues)
        derived = compute_derived_metrics(metrics, winner)
        wm      = metrics.get(winner, {})

        _, stars, desc = sharpe_tier(sharpe)
        issue_lines = [f"    [{i['level']}:{i['code']}] {i['message']}" for i in issues
                       if i["level"] in ("ERROR", "WARN")]

        s = f"\n  {symbol}/{tf} [{record.get('_source')}] — {v_label}  Grade: {overall_grade(sharpe, wm.get('accuracy'), diag.get('val_rows'), issues)}"
        s += f"\n  Winner: {winner.upper()}  Sharpe={sharpe:.3f} {stars} ({desc})"
        s += f"\n  Accuracy={wm.get('accuracy',0):.1%}  EstMaxDD~{derived['max_drawdown_pct'] or '?'}%  EstPF~{derived['profit_factor'] or '?'}"
        s += f"\n  Data: {diag.get('total_rows','?')} rows  val={diag.get('val_rows','?')}  target={diag.get('target_balance_up_pct','?')}% UP  horizon={record.get('horizon_periods','?')}p"
        if issue_lines:
            s += "\n  Issues:\n" + "\n".join(issue_lines)
        model_summaries.append(s)

    return f"""You are a senior quantitative analyst reviewing ML model training results for a fintech stock signal platform (fin-eye).

The platform trains XGBoost, Logistic Regression, and Prophet per symbol/timeframe.
Target: predict forward price direction (binary: up=1, down=0).
Winner selected by highest Sharpe on hold-out validation set using real forward returns.

Quality thresholds in use:
  Min Sharpe: {thresholds['min_sharpe']}  |  Min Accuracy: {thresholds['min_accuracy']:.0%}
  Min Trades: {thresholds['min_trades']}  |  Max Drawdown: {thresholds['max_drawdown_pct']}%
  Min Profit Factor: {thresholds['min_profit_factor']}

Current active models:
{"".join(model_summaries)}

Provide a structured assessment:

1. OVERALL HEALTH (2-3 sentences): Which models are production-ready?

2. ROOT CAUSE (per FAIL/WARN): What is causing each problem?
   Reference specific numbers — Sharpe, accuracy, val_rows.

3. PRIORITY FIXES (max 4, by impact): What should be done first?
   Name the file/function where applicable.

4. BEST MODEL RIGHT NOW: Which single symbol/timeframe would you trust most for GAS, and why?

Under 400 words. Developer audience.
"""


def call_ollama(prompt: str, config: dict) -> Optional[str]:
    model    = config["models"]["reasoning"]
    base_url = config["ollama"]["base_url"]
    timeout  = config["ollama"]["timeout_seconds"]

    print(f"\n  [LLM] Calling {model} — streaming response:")
    print("  " + "─" * 61)

    collected = []
    try:
        with requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            timeout=timeout,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                collected.append(token)
                print(token, end="", flush=True)
                if chunk.get("done", False):
                    break
        print()
        print("  " + "─" * 61)
        return "".join(collected).strip()
    except requests.exceptions.Timeout:
        print()
        return (
            f"[LLM ERROR] Timed out after {timeout}s. "
            "Increase timeout_seconds in config.yaml or use gemma2:27b."
        )
    except Exception as e:
        print()
        return f"[LLM ERROR] {e}"


def print_llm_section(llm_response: Optional[str],
                      ollama_available: bool, llm_requested: bool):
    print()
    print("═" * 65)
    print("  LLM ASSESSMENT (DeepSeek R1 32B)")
    print("═" * 65)
    if not llm_requested:
        print("  ℹ️  Not requested. Run with --llm to enable.")
    elif not ollama_available:
        print("  ⚠️  Ollama is not running or unreachable.")
        print("      Start: ollama serve")
        print("      Pull:  ollama pull deepseek-r1:32b")
    elif llm_response and llm_response.startswith("[LLM ERROR]"):
        print(f"  {llm_response}")
    elif llm_response:
        pass  # already streamed
    else:
        print("  ⚠️  No response received.")
    print("═" * 65)


# ── Markdown report builder ───────────────────────────────────────────────────

def build_markdown_report(
    all_records: list[dict],
    active_models: dict[tuple, dict],
    all_issues: dict[tuple, list],
    run_at: str,
    registry_filter: str,
    symbol_filter: Optional[str],
    llm_response: Optional[str],
    ollama_available: bool,
    llm_requested: bool,
    thresholds: dict,
) -> str:
    lines = []

    total  = len(active_models)
    passed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "PASS")
    warned = sum(1 for k in active_models if verdict(all_issues[k])[0] == "WARN")
    failed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "FAIL")
    older  = len(all_records) - total

    deployable = [
        (r.get("symbol"), r.get("timeframe"),
         r.get("model_name") or r.get("model_kind"),
         r.get("validation_sharpe") or r.get("sharpe_ratio", 0))
        for k, r in active_models.items()
        if verdict(all_issues[k])[0] == "PASS"
    ]

    lines += [
        "# Fin-Eye Model Inspection Report",
        "",
        f"**Generated:** {run_at}  ",
        f"**Registry:** {registry_filter}  |  **Symbol filter:** {symbol_filter or 'all'}  ",
        f"**Total records:** {len(all_records)}  |  **Active models:** {total}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✅ PASS — deployable | {passed} |",
        f"| ⚠️ WARN — review | {warned} |",
        f"| ❌ FAIL — do not use | {failed} |",
        "",
    ]

    if deployable:
        lines += ["### Models Safe for GAS", ""]
        for sym, tf, model, sh in deployable:
            _, stars, desc = sharpe_tier(sh)
            lines.append(f"- **{sym} / {tf}** — `{model.upper()}` — Sharpe `{sh:.3f}` {stars} ({desc})")
        lines.append("")
    else:
        lines += ["> ⚠️ **No models currently pass all quality gates.**", ""]

    if older > 0:
        lines += [f"> ℹ️ {older} older training run(s) superseded in registry.", ""]

    # LLM
    lines += ["---", "", "## LLM Assessment (DeepSeek R1 32B)", ""]
    if not llm_requested:
        lines += ["> *Run with `--llm` to include LLM assessment.*", ""]
    elif not ollama_available:
        lines += ["> ⚠️ *Ollama was not reachable at report time.*", ""]
    elif llm_response and not llm_response.startswith("[LLM ERROR]"):
        lines += [llm_response, ""]
    else:
        lines += [f"> ⚠️ *{llm_response}*", ""]

    # Per-model
    lines += ["---", "", "## Model Details", ""]

    for key in sorted(active_models.keys(), key=lambda x: (x[0] or "", x[1] or "")):
        record  = active_models[key]
        issues  = all_issues[key]
        symbol  = record.get("symbol", "?")
        tf      = record.get("timeframe", "?")
        winner  = record.get("model_name") or record.get("model_kind", "unknown")
        sharpe  = record.get("validation_sharpe") or record.get("sharpe_ratio")
        trained = (record.get("trained_at") or "")[:16].replace("T", " ")
        source  = record.get("_source", "?")
        metrics = record.get("metrics", {})
        diag    = record.get("diagnostics", {})
        horizon = record.get("horizon_periods", "?")
        v_label, v_icon = verdict(issues)

        artifact_exists, artifact_path = check_artifact_exists(record)
        size_kb  = get_artifact_size_kb(artifact_path) if artifact_exists else None
        derived  = compute_derived_metrics(metrics, winner)
        wm       = metrics.get(winner, {})
        accuracy = wm.get("accuracy")
        val_rows = diag.get("val_rows")
        grade    = overall_grade(sharpe, accuracy, val_rows, issues)
        _, stars, sh_desc = sharpe_tier(sharpe) if sharpe else ("?", "", "?")

        lines += [
            f"### {symbol} / {tf} &nbsp; {v_icon} {v_label} &nbsp; Grade: **{grade}**",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Source | `{source}` |",
            f"| Winner | `{winner.upper()}` |",
            f"| Sharpe | `{sharpe:.4f}` {stars} — {sh_desc} |" if sharpe else "| Sharpe | N/A |",
            f"| Accuracy | `{accuracy:.1%}` |" if accuracy else "| Accuracy | N/A |",
            f"| Est. Max Drawdown | `~{derived['max_drawdown_pct']:.1f}%` |" if derived['max_drawdown_pct'] else "| Est. Max Drawdown | N/A |",
            f"| Est. Profit Factor | `~{derived['profit_factor']:.2f}` |" if derived['profit_factor'] else "| Est. Profit Factor | N/A |",
            f"| Trained | `{trained}` |",
            f"| Artifact | {'✅ `' + Path(artifact_path).name + f'` ({size_kb:.0f}KB)' if artifact_exists and size_kb else '❌ MISSING'} |",
            f"| Horizon | `{horizon} periods` |",
        ]

        if diag:
            lines += [
                f"| Training rows | `{diag.get('total_rows','?')}` total / `{diag.get('train_rows','?')}` train / `{val_rows}` val |",
                f"| Target balance | `{diag.get('target_balance_up_pct','?')}%` UP |",
            ]
            if diag.get("low_variance_features"):
                lines.append(f"| Low-var features | `{diag['low_variance_features']}` |")
        lines.append("")

        if metrics:
            lines += [
                "**Model competition:**",
                "",
                "| Model | Sharpe | Stars | Accuracy | Return | Notes |",
                "|-------|--------|-------|----------|--------|-------|",
            ]
            for m_name in ["logistic", "xgboost", "prophet"]:
                m = metrics.get(m_name)
                if not m:
                    lines.append(f"| `{m_name}` | — | — | — | — | not trained |")
                    continue
                acc  = m.get("accuracy", 0)
                sh   = m.get("sharpe_ratio", -99)
                ret  = m.get("total_return", 0)
                _, mstars, _ = sharpe_tier(sh)
                mark = " **← WINNER**" if m_name == winner else ""
                disq = " DISQ" if m.get("disqualified") else ""
                sh_i  = "✅" if sh  >= thresholds["min_sharpe"]  else ("⚠️" if sh  >= 0   else "❌")
                acc_i = "✅" if acc >= thresholds["min_accuracy"] else ("⚠️" if acc >= 0.50 else "❌")
                lines.append(
                    f"| `{m_name}` | {sh_i} `{sh:.3f}` | {mstars} | {acc_i} `{acc:.1%}` | `{ret:+.3f}` |{mark}{disq} |"
                )
            lines.append("")

        # Issues grouped
        errors = [i for i in issues if i["level"] == "ERROR"]
        warns  = [i for i in issues if i["level"] == "WARN"]
        infos  = [i for i in issues if i["level"] == "INFO"]

        if errors or warns:
            lines += ["**Issues to fix:**", ""]
            for iss in errors + warns:
                icon = "❌" if iss["level"] == "ERROR" else "⚠️"
                lines.append(f"- {icon} **[{iss['code']}]** {iss['message']}")
            lines.append("")

        if infos:
            lines += ["**Metric details:**", ""]
            for iss in infos:
                lines.append(f"- ℹ️ {iss['message']}")
            lines.append("")

        rec_map = {
            "FAIL": "> ❌ **Do not deploy.** Fix errors before use.",
            "WARN": "> ⚠️ **Review warnings before deploying.**",
            "PASS": "> ✅ **Passes all quality gates.** Safe for GAS.",
        }
        lines += [rec_map[v_label], "", "---", ""]

    # Thresholds reference
    lines += [
        "## Quality Gate Thresholds",
        "",
        "| Gate | Value | Meaning |",
        "|------|-------|---------|",
        f"| Min Sharpe | `{thresholds['min_sharpe']}` | Below = no edge |",
        f"| Min Accuracy | `{thresholds['min_accuracy']:.0%}` | Must beat random |",
        f"| Min Trades (val rows) | `{thresholds['min_trades']}` | Statistical floor |",
        f"| Max Sharpe (suspicious) | `{thresholds['max_sharpe']}` | Likely noise |",
        f"| Max Drawdown | `{thresholds['max_drawdown_pct']}%` | Risk ceiling |",
        f"| Min Profit Factor | `{thresholds['min_profit_factor']}` | Wins must cover losses |",
        "",
        "**Sharpe tier scale:**",
        "",
        "| Range | Stars | Label |",
        "|-------|-------|-------|",
        "| < 0.0 | | FAIL — destroys value |",
        "| 0.0 – 0.3 | | FAIL — no edge |",
        "| 0.3 – 0.5 | ★ | MARGINAL |",
        "| 0.5 – 1.0 | ★★ | ACCEPTABLE |",
        "| 1.0 – 2.0 | ★★★ | GOOD |",
        "| 2.0 – 5.0 | ★★★★ | STRONG |",
        "| > 5.0 | ? | SUSPICIOUS |",
        "",
        "Thresholds configured in `.claude/agents/config.yaml`",
        "",
        f"*`inspect_models.py` · fin-eye · {run_at}*",
    ]

    return "\n".join(lines)


# ── Save report ───────────────────────────────────────────────────────────────

def save_markdown_report(content: str, run_at_dt: datetime) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename    = f"model_report_{run_at_dt.strftime('%Y%m%d_%H%M%S')}.md"
    path        = REPORTS_DIR / filename
    latest_path = REPORTS_DIR / "latest.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── Registry cleaner ──────────────────────────────────────────────────────────

def clean_test_entries(registry_path: Path):
    if not registry_path.exists():
        print(f"[INFO] Registry not found: {registry_path}")
        return
    records, removed = [], 0
    with open(registry_path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
                if r.get("symbol") == "TEST_SYM":
                    removed += 1
                else:
                    records.append(s)
            except Exception:
                records.append(s)

    if removed == 0:
        print("[INFO] No TEST_SYM entries found.")
        return

    backup = registry_path.with_suffix(".jsonl.bak")
    registry_path.rename(backup)
    print(f"[INFO] Backed up to {backup.name}")
    with open(registry_path, "w", encoding="utf-8") as f:
        for line in records:
            f.write(line + "\n")
    print(f"[INFO] Removed {removed} TEST_SYM entries.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="fin-eye model registry inspector")
    parser.add_argument("--registry", choices=["backend", "store", "all"], default="all")
    parser.add_argument("--symbol",   type=str)
    parser.add_argument("--flag-issues",        action="store_true",
                        help="Only show WARN/FAIL models in terminal")
    parser.add_argument("--llm",                action="store_true",
                        help="Streaming LLM assessment via Ollama")
    parser.add_argument("--save-report",        action="store_true",
                        help="Save markdown report to .claude/reports/")
    parser.add_argument("--clean-test",         action="store_true",
                        help="Remove TEST_SYM entries from backend registry")
    parser.add_argument("--no-model-breakdown", action="store_true")
    args = parser.parse_args()

    config     = load_config()
    thresholds = get_thresholds(config)
    run_at_dt  = datetime.now()
    run_at     = run_at_dt.strftime("%Y-%m-%d %H:%M:%S")

    if args.clean_test:
        print("\n[INFO] Cleaning TEST_SYM entries...")
        clean_test_entries(BACKEND_REGISTRY)
        print()

    all_records = load_all_registries(args.registry)
    if not all_records:
        print("\n[ERROR] No records found.")
        sys.exit(1)

    if args.symbol:
        all_records = [r for r in all_records if r.get("symbol") == args.symbol.upper()]
        if not all_records:
            print(f"\n[ERROR] No records for {args.symbol.upper()}")
            sys.exit(1)

    active_models = get_active_models(all_records)
    all_issues    = {key: detect_issues(record, thresholds)
                     for key, record in active_models.items()}

    # ── Header ────────────────────────────────────────────────────────────────
    print()
    print("═" * 70)
    print("  FIN-EYE MODEL REGISTRY INSPECTOR")
    print(f"  Run at: {run_at}")
    print(f"  Registries: {args.registry}   Symbol: {args.symbol or 'all'}")
    print(f"  Records: {len(all_records)}   Active models: {len(active_models)}")
    print(f"  LLM: {'ENABLED — DeepSeek R1 32B (streaming)' if args.llm else 'OFF (use --llm)'}")
    print(f"  Thresholds: Sharpe≥{thresholds['min_sharpe']}  Acc≥{thresholds['min_accuracy']:.0%}  "
          f"Trades≥{thresholds['min_trades']}  MaxDD≤{thresholds['max_drawdown_pct']}%  "
          f"PF≥{thresholds['min_profit_factor']}")
    print("═" * 70)

    # ── Per-model blocks ──────────────────────────────────────────────────────
    printed = 0
    for key, record in sorted(active_models.items(),
                               key=lambda x: (x[0][0] or "", x[0][1] or "")):
        issues  = all_issues[key]
        v_label, _ = verdict(issues)
        if args.flag_issues and v_label == "PASS":
            continue
        print()
        print_model_block(record, issues, thresholds,
                          show_breakdown=not args.no_model_breakdown)
        printed += 1

    if printed == 0:
        print("\n  ✅ All models passed. Use --flag-issues to filter.")

    older = len(all_records) - len(active_models)
    if older > 0:
        print(f"\n  ℹ️  {older} older training run(s) superseded in registry.")

    # ── Summary ───────────────────────────────────────────────────────────────
    total  = len(active_models)
    passed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "PASS")
    warned = sum(1 for k in active_models if verdict(all_issues[k])[0] == "WARN")
    failed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "FAIL")

    deployable = []
    for k, r in active_models.items():
        if verdict(all_issues[k])[0] == "PASS":
            sh = r.get("validation_sharpe") or r.get("sharpe_ratio", 0)
            _, stars, desc = sharpe_tier(sh)
            wm  = r.get("metrics", {}).get(r.get("model_name", ""), {})
            acc = wm.get("accuracy", 0)
            deployable.append(
                f"{r.get('symbol')}/{r.get('timeframe')} "
                f"({(r.get('model_name') or '?').upper()} "
                f"Sharpe={sh:.2f} {stars}  Acc={acc:.1%})"
            )

    print()
    print("═" * 70)
    print("  SUMMARY")
    print("═" * 70)
    print(f"  Total: {total}  ✅ {passed} PASS  ⚠️  {warned} WARN  ❌ {failed} FAIL")
    if deployable:
        print("\n  Safe for GAS:")
        for d in deployable:
            print(f"    → {d}")
    else:
        print("\n  ⚠️  No models pass all quality gates right now.")
    print("═" * 70)

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_response     = None
    ollama_available = False

    if args.llm and config["ollama"].get("enabled", True):
        ollama_available = check_ollama(config)
        if ollama_available:
            prompt       = build_llm_prompt(active_models, all_issues, thresholds)
            llm_response = call_ollama(prompt, config)
        print_llm_section(llm_response, ollama_available, args.llm)
    elif args.llm:
        print_llm_section(None, False, args.llm)

    # ── Save report ───────────────────────────────────────────────────────────
    if args.save_report:
        md = build_markdown_report(
            all_records, active_models, all_issues,
            run_at, args.registry, args.symbol,
            llm_response, ollama_available, args.llm,
            thresholds,
        )
        path = save_markdown_report(md, run_at_dt)
        print()
        print(f"  📄 Saved: {path}")
        print(f"     {REPORTS_DIR / 'latest.md'}")
        print()


if __name__ == "__main__":
    main()
