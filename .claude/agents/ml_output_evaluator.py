"""
ml_output_evaluator.py
─────────────────────────────────────────────────────────────────────────────
Evaluates the quality of a trained fin-eye ML model using:
  1. Rule-based checks against thresholds in config.yaml
  2. LLM narrative analysis via DeepSeek R1 32B (local Ollama)

The LLM layer is optional — if Ollama is unavailable the script still runs
all numeric checks and produces a structured pass/fail report.

Usage:
  python ml_output_evaluator.py --symbol AAPL --timeframe 1h
  python ml_output_evaluator.py --from-registry --last-trained
  python ml_output_evaluator.py --from-registry --ci-mode   # no LLM, CI safe

Exit codes:
  0 = PASS or WARN
  1 = FAIL (use this to block CI pipelines)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # fin-eye root


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── Registry reader ───────────────────────────────────────────────────────────

def load_registry(config: dict) -> list[dict]:
    registry_path = PROJECT_ROOT / config["model_registry_path"]
    if not registry_path.exists():
        print(f"[ERROR] Registry not found at {registry_path}")
        return []
    records = []
    with open(registry_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def get_latest_record(records: list[dict], symbol: str, timeframe: str) -> Optional[dict]:
    matches = [r for r in records if r.get("symbol") == symbol and r.get("timeframe") == timeframe]
    return matches[-1] if matches else None


def get_last_trained_record(records: list[dict]) -> Optional[dict]:
    return records[-1] if records else None


# ── Rule-based checks ─────────────────────────────────────────────────────────

def run_rule_checks(record: dict, config: dict) -> list[dict]:
    """
    Returns a list of check result dicts:
    { "name": str, "status": "PASS"|"WARN"|"FAIL", "detail": str }
    """
    thresholds = config["ml_evaluation"]
    checks = []

    def check(name: str, condition: bool, warn_condition: bool, detail: str, warn_detail: str):
        if condition:
            checks.append({"name": name, "status": "PASS", "detail": detail})
        elif warn_condition:
            checks.append({"name": name, "status": "WARN", "detail": warn_detail})
        else:
            checks.append({"name": name, "status": "FAIL", "detail": detail})

    sharpe = record.get("validation_sharpe", -99)
    metrics = record.get("metrics", {})
    winning_model = record.get("model_name", "unknown")

    # ── Sharpe ratio ──
    min_sharpe = thresholds["min_sharpe"]
    hard_fail = thresholds["hard_fail_sharpe"]
    check(
        "Sharpe Ratio",
        sharpe >= min_sharpe,
        sharpe > hard_fail,
        f"Sharpe: {sharpe:.3f} (threshold: ≥ {min_sharpe})",
        f"Sharpe: {sharpe:.3f} — above hard floor but below deployment threshold ({min_sharpe})",
    )

    # ── Accuracy ──
    winning_metrics = metrics.get(winning_model, {})
    accuracy = winning_metrics.get("accuracy", 0)
    min_acc = thresholds["min_accuracy"]
    check(
        "Directional Accuracy",
        accuracy >= min_acc,
        accuracy >= 0.50,
        f"Accuracy: {accuracy:.1%} (threshold: ≥ {min_acc:.0%})",
        f"Accuracy: {accuracy:.1%} — barely above random (50%). Marginal signal.",
    )

    # ── Winning model is not a fallback ──
    is_fallback = winning_model == "logistic" and sharpe <= 0
    checks.append({
        "name": "Winning Model",
        "status": "WARN" if is_fallback else "PASS",
        "detail": f"Winning model: {winning_model}" + (" (WARN: possible fallback path)" if is_fallback else ""),
    })

    # ── All models reported ──
    expected_models = {"logistic", "xgboost", "prophet"}
    reported_models = set(metrics.keys())
    missing = expected_models - reported_models
    checks.append({
        "name": "All Models Trained",
        "status": "WARN" if missing else "PASS",
        "detail": f"All 3 models trained OK" if not missing else f"Missing model results: {missing}",
    })

    # ── Overfitting proxy: all models negative Sharpe ──
    all_sharpes = [m.get("sharpe_ratio", -99) for m in metrics.values()]
    all_negative = all(s < 0 for s in all_sharpes) if all_sharpes else True
    checks.append({
        "name": "Signal Exists (not all negative Sharpe)",
        "status": "FAIL" if all_negative else "PASS",
        "detail": f"Model Sharpes: { {k: round(v.get('sharpe_ratio', -99), 3) for k, v in metrics.items()} }",
    })

    # ── Training recency ──
    trained_at = record.get("trained_at", "")
    if trained_at:
        try:
            trained_dt = datetime.fromisoformat(trained_at.replace("Z", "+00:00"))
            age_days = (datetime.utcnow().replace(tzinfo=trained_dt.tzinfo) - trained_dt).days
            checks.append({
                "name": "Model Recency",
                "status": "WARN" if age_days > 30 else "PASS",
                "detail": f"Trained {age_days} day(s) ago ({trained_at[:10]})" + (" — consider retraining" if age_days > 30 else ""),
            })
        except Exception:
            checks.append({"name": "Model Recency", "status": "WARN", "detail": "Could not parse trained_at timestamp"})

    return checks


# ── Ollama LLM analysis ───────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, base_url: str, timeout: int) -> Optional[str]:
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return None


def build_llm_prompt(record: dict, checks: list[dict]) -> str:
    symbol = record.get("symbol", "?")
    timeframe = record.get("timeframe", "?")
    winning_model = record.get("model_name", "?")
    sharpe = record.get("validation_sharpe", "?")
    metrics = record.get("metrics", {})

    checks_summary = "\n".join(
        f"  [{c['status']}] {c['name']}: {c['detail']}" for c in checks
    )

    return f"""You are a quantitative finance expert reviewing an ML model training result for a stock trading signal system.

The system trains three competing models (XGBoost, Logistic Regression, Prophet) to predict 5-period forward return direction (up/down) for a given stock. The winner is selected by highest Sharpe ratio on a validation set.

Training result for {symbol} ({timeframe} timeframe):
- Winning model: {winning_model}
- Validation Sharpe: {sharpe}
- All model metrics: {json.dumps(metrics, indent=2)}

Rule-based checks already performed:
{checks_summary}

Please provide:
1. A brief (3–5 sentence) assessment of whether this model quality is acceptable for production use in a financial signal system
2. Any specific risks or concerns a developer should know before deploying this signal
3. One concrete suggestion for how to improve signal quality if the Sharpe is below 0.5

Keep your response practical and developer-focused. Do not use overly academic language.
"""


# ── Output formatting ─────────────────────────────────────────────────────────

def determine_overall_result(checks: list[dict]) -> str:
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def print_report(record: dict, checks: list[dict], llm_analysis: Optional[str], ollama_available: bool):
    symbol = record.get("symbol", "?")
    timeframe = record.get("timeframe", "?")
    result = determine_overall_result(checks)

    icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[result]

    print()
    print("═" * 65)
    print(f"  AGENT: ml_output_evaluator")
    print(f"  SYMBOL: {symbol}  |  TIMEFRAME: {timeframe}")
    print(f"  RESULT: {result} {icon}")
    print("═" * 65)
    print()
    print("RULE-BASED CHECKS:")
    for c in checks:
        status_icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[c["status"]]
        print(f"  [{c['status']}] {status_icon}  {c['name']}: {c['detail']}")

    print()
    if not ollama_available:
        print("⚠️  Ollama unavailable — running in rule-based mode (no LLM analysis)")
    elif llm_analysis:
        print("LLM ANALYSIS (DeepSeek R1 32B):")
        for line in llm_analysis.split("\n"):
            print(f"  {line}")
    else:
        print("LLM ANALYSIS: (call failed — check Ollama is serving deepseek-r1:32b)")

    print()
    if result == "FAIL":
        print("  ⛔ RECOMMENDATION: Do NOT promote this model. Fix issues above before deploying.")
    elif result == "WARN":
        print("  ⚠️  RECOMMENDATION: Safe to promote, but review warnings before production deployment.")
    else:
        print("  ✅ RECOMMENDATION: Model passed all quality gates. Safe to promote.")
    print("═" * 65)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fin-Eye ML Output Evaluator")
    parser.add_argument("--symbol", type=str, help="Stock symbol (e.g. AAPL)")
    parser.add_argument("--timeframe", type=str, help="Timeframe (e.g. 1h, 4h)")
    parser.add_argument("--from-registry", action="store_true", help="Read from model registry")
    parser.add_argument("--last-trained", action="store_true", help="Evaluate the most recently trained model")
    parser.add_argument("--ci-mode", action="store_true", help="CI mode: skip LLM, exit 1 on FAIL")
    args = parser.parse_args()

    config = load_config()
    records = load_registry(config)

    if not records:
        print("[ERROR] No records found in model registry. Has any model been trained?")
        sys.exit(1)

    # Select which record to evaluate
    if args.last_trained:
        record = get_last_trained_record(records)
    elif args.symbol and args.timeframe:
        record = get_latest_record(records, args.symbol.upper(), args.timeframe)
    else:
        print("[ERROR] Provide --symbol and --timeframe, or use --from-registry --last-trained")
        parser.print_help()
        sys.exit(1)

    if not record:
        print(f"[ERROR] No trained model found for {args.symbol} {args.timeframe}")
        sys.exit(1)

    # Rule-based checks
    checks = run_rule_checks(record, config)

    # LLM analysis
    llm_analysis = None
    ollama_available = False

    if not args.ci_mode and config["ollama"]["enabled"]:
        base_url = config["ollama"]["base_url"]
        timeout = config["ollama"]["timeout_seconds"]
        model = config["models"]["reasoning"]

        # Check Ollama is alive
        try:
            requests.get(f"{base_url}/api/tags", timeout=3)
            ollama_available = True
        except Exception:
            ollama_available = False

        if ollama_available:
            prompt = build_llm_prompt(record, checks)
            print(f"[INFO] Calling {model} for narrative analysis... (this may take 30–60s)")
            llm_analysis = call_ollama(model, prompt, base_url, timeout)

    print_report(record, checks, llm_analysis, ollama_available)

    # Exit code for CI
    result = determine_overall_result(checks)
    sys.exit(1 if result == "FAIL" else 0)


if __name__ == "__main__":
    main()
