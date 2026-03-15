"""
cicd_model_gate.py
─────────────────────────────────────────────────────────────────────────────
Compares a newly trained challenger model against the current champion model
before promotion. Prevents regressions where a new model trains successfully
but is actually worse than what is already in production.

Uses DeepSeek R1 32B (local Ollama) for the promotion reasoning decision.
Falls back to pure numeric gate if Ollama is unavailable.

Usage:
  python cicd_model_gate.py --symbol AAPL --timeframe 1h
    (reads champion and challenger from registry — champion=second-to-last, challenger=last)

  python cicd_model_gate.py --symbol AAPL --timeframe 1h \
    --champion path/to/champion_meta.json \
    --challenger path/to/challenger_meta.json

  python cicd_model_gate.py --auto-promote   # promote if PASS (use carefully)

Exit codes:
  0 = PROMOTE or HOLD (WARN)
  1 = REJECT (challenger is worse than champion beyond tolerance)
  2 = ERROR (missing data, cannot compare)
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import requests
import yaml

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── Registry helpers ──────────────────────────────────────────────────────────

def load_registry(config: dict) -> list[dict]:
    path = PROJECT_ROOT / config["model_registry_path"]
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def get_champion_and_challenger(records: list, symbol: str, timeframe: str):
    matches = [r for r in records if r.get("symbol") == symbol and r.get("timeframe") == timeframe]
    if len(matches) < 2:
        return None, matches[-1] if matches else None
    # Champion = second-to-last, Challenger = last trained
    return matches[-2], matches[-1]


# ── Comparison checks ─────────────────────────────────────────────────────────

def compare_models(champion: dict, challenger: dict, config: dict) -> list[dict]:
    checks = []
    gate = config["model_gate"]

    champ_sharpe = champion.get("validation_sharpe", 0)
    chall_sharpe = challenger.get("validation_sharpe", 0)

    champ_metrics = champion.get("metrics", {}).get(champion.get("model_name", ""), {})
    chall_metrics = challenger.get("metrics", {}).get(challenger.get("model_name", ""), {})

    champ_acc = champ_metrics.get("accuracy", 0)
    chall_acc = chall_metrics.get("accuracy", 0)

    champ_ret = champ_metrics.get("total_return", 0)
    chall_ret = chall_metrics.get("total_return", 0)

    # ── Sharpe comparison ──
    sharpe_delta = chall_sharpe - champ_sharpe
    min_delta = gate["min_sharpe_delta"]
    checks.append({
        "name": "Sharpe Ratio",
        "champion": round(champ_sharpe, 4),
        "challenger": round(chall_sharpe, 4),
        "delta": round(sharpe_delta, 4),
        "status": "PROMOTE" if sharpe_delta >= 0 else ("HOLD" if sharpe_delta >= min_delta else "REJECT"),
        "detail": f"Champion: {champ_sharpe:.3f}  →  Challenger: {chall_sharpe:.3f}  (Δ {sharpe_delta:+.3f}, min allowed: {min_delta:+.3f})",
    })

    # ── Accuracy comparison ──
    acc_delta = chall_acc - champ_acc
    min_acc_delta = gate["min_accuracy_delta"]
    checks.append({
        "name": "Accuracy",
        "champion": round(champ_acc, 4),
        "challenger": round(chall_acc, 4),
        "delta": round(acc_delta, 4),
        "status": "PROMOTE" if acc_delta >= 0 else ("HOLD" if acc_delta >= min_acc_delta else "REJECT"),
        "detail": f"Champion: {champ_acc:.1%}  →  Challenger: {chall_acc:.1%}  (Δ {acc_delta:+.1%}, min allowed: {min_acc_delta:+.1%})",
    })

    # ── Total return comparison ──
    ret_delta = chall_ret - champ_ret
    checks.append({
        "name": "Validation Total Return",
        "champion": round(champ_ret, 4),
        "challenger": round(chall_ret, 4),
        "delta": round(ret_delta, 4),
        "status": "PROMOTE" if ret_delta >= 0 else "WARN",
        "detail": f"Champion: {champ_ret:.4f}  →  Challenger: {chall_ret:.4f}  (Δ {ret_delta:+.4f})",
    })

    # ── Model type change ──
    champ_model = champion.get("model_name", "?")
    chall_model = challenger.get("model_name", "?")
    model_changed = champ_model != chall_model
    checks.append({
        "name": "Winning Model Architecture",
        "champion": champ_model,
        "challenger": chall_model,
        "delta": None,
        "status": "WARN" if model_changed else "PASS",
        "detail": f"Champion: {champ_model}  →  Challenger: {chall_model}"
                  + (" (architecture changed — review carefully)" if model_changed else " (same architecture)"),
    })

    # ── Absolute quality floor on challenger ──
    chall_sharpe_ok = chall_sharpe >= config["ml_evaluation"]["min_sharpe"]
    checks.append({
        "name": "Challenger Meets Absolute Floor",
        "champion": None,
        "challenger": round(chall_sharpe, 4),
        "delta": None,
        "status": "PASS" if chall_sharpe_ok else "REJECT",
        "detail": f"Challenger Sharpe {chall_sharpe:.3f} {'≥' if chall_sharpe_ok else '<'} absolute floor {config['ml_evaluation']['min_sharpe']}",
    })

    return checks


def determine_gate_result(checks: list[dict]) -> str:
    statuses = [c["status"] for c in checks]
    if "REJECT" in statuses:
        return "REJECT"
    if "WARN" in statuses or "HOLD" in statuses:
        return "HOLD"
    return "PROMOTE"


# ── Ollama LLM ────────────────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, base_url: str, timeout: int) -> Optional[str]:
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        return None


def build_llm_prompt(symbol: str, timeframe: str, champion: dict, challenger: dict,
                     checks: list[dict], gate_result: str) -> str:
    checks_text = "\n".join(f"  [{c['status']}] {c['name']}: {c['detail']}" for c in checks)

    return f"""You are a senior quantitative researcher at a fintech company reviewing a model promotion decision.

The system trains competing ML models to predict 5-period price direction for stocks.
A new challenger model has been trained and we need to decide whether to promote it to production.

Symbol: {symbol} | Timeframe: {timeframe}
Champion (current production) model: {champion.get('model_name')} | Sharpe: {champion.get('validation_sharpe'):.3f} | Trained: {champion.get('trained_at', '?')[:10]}
Challenger (new) model: {challenger.get('model_name')} | Sharpe: {challenger.get('validation_sharpe'):.3f} | Trained: {challenger.get('trained_at', '?')[:10]}

Comparison results:
{checks_text}

Numeric gate decision: {gate_result}

In 3–5 sentences:
1. Explain whether you agree with the numeric gate decision
2. Note any concerns about the transition (especially if the architecture changed or the Sharpe improvement is very small)
3. Give a clear final recommendation: PROMOTE, HOLD FOR MORE DATA, or REJECT

Be concise and decisive. This is a production deployment decision.
"""


# ── Model promotion ───────────────────────────────────────────────────────────

def promote_challenger(challenger: dict, config: dict) -> bool:
    artifacts_dir = PROJECT_ROOT / config["model_artifacts_dir"]
    challenger_file = challenger.get("artifact_file", "")
    symbol = challenger.get("symbol", "")
    timeframe = challenger.get("timeframe", "")

    challenger_path = artifacts_dir / challenger_file
    winner_path = artifacts_dir / f"{symbol}_{timeframe}_winner.joblib"
    backup_path = artifacts_dir / f"{symbol}_{timeframe}_winner.joblib{config['model_gate']['backup_suffix']}"

    if not challenger_path.exists():
        print(f"  [ERROR] Challenger artifact not found: {challenger_path}")
        return False

    # Backup champion
    if winner_path.exists() and config["model_gate"]["backup_champion"]:
        shutil.copy2(winner_path, backup_path)
        print(f"  [INFO] Champion backed up to: {backup_path.name}")

    # Promote challenger
    shutil.copy2(challenger_path, winner_path)
    print(f"  [INFO] Challenger promoted to: {winner_path.name}")
    return True


# ── Output ────────────────────────────────────────────────────────────────────

def print_report(symbol: str, timeframe: str, champion: dict, challenger: dict,
                 checks: list[dict], gate_result: str, llm_analysis: Optional[str],
                 ollama_available: bool, promoted: bool):

    icon = {"PROMOTE": "🚀", "HOLD": "⚠️ ", "REJECT": "⛔"}[gate_result]

    print()
    print("═" * 65)
    print(f"  AGENT: cicd_model_gate")
    print(f"  SYMBOL: {symbol}  |  TIMEFRAME: {timeframe}")
    print(f"  DECISION: {gate_result} {icon}")
    print("═" * 65)
    print()
    print(f"  CHAMPION:   {champion.get('model_name', '?'):<12} Sharpe={champion.get('validation_sharpe', 0):.3f}  Trained: {champion.get('trained_at', '?')[:10]}")
    print(f"  CHALLENGER: {challenger.get('model_name', '?'):<12} Sharpe={challenger.get('validation_sharpe', 0):.3f}  Trained: {challenger.get('trained_at', '?')[:10]}")
    print()
    print("COMPARISON CHECKS:")
    for c in checks:
        icon_map = {"PROMOTE": "🚀", "PASS": "✅", "WARN": "⚠️ ", "HOLD": "⚠️ ", "REJECT": "❌"}
        s = icon_map.get(c["status"], "❓")
        print(f"  [{c['status']:<7}] {s}  {c['name']}: {c['detail']}")

    print()
    if not ollama_available:
        print("⚠️  Ollama unavailable — rule-based gate only (no LLM analysis)")
    elif llm_analysis:
        print("LLM ANALYSIS (DeepSeek R1 32B):")
        for line in llm_analysis.split("\n"):
            print(f"  {line}")

    print()
    if gate_result == "PROMOTE":
        if promoted:
            print("  🚀 ACTION TAKEN: Challenger has been promoted to winner.joblib")
        else:
            print("  🚀 RECOMMENDATION: Promote challenger. Run with --auto-promote to execute.")
    elif gate_result == "HOLD":
        print("  ⚠️  RECOMMENDATION: Do not promote yet — review warnings above.")
    else:
        print("  ⛔ RECOMMENDATION: Do NOT promote. Challenger does not meet the quality bar.")
    print("═" * 65)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fin-Eye CI/CD Model Gate")
    parser.add_argument("--symbol", type=str, required=True)
    parser.add_argument("--timeframe", type=str, required=True)
    parser.add_argument("--champion", type=str, help="Path to champion metadata JSON (optional)")
    parser.add_argument("--challenger", type=str, help="Path to challenger metadata JSON (optional)")
    parser.add_argument("--auto-promote", action="store_true", help="Automatically promote if PASS")
    parser.add_argument("--ci-mode", action="store_true")
    args = parser.parse_args()

    config = load_config()
    records = load_registry(config)

    symbol = args.symbol.upper()
    timeframe = args.timeframe

    # Load champion and challenger
    if args.champion and args.challenger:
        with open(args.champion) as f:
            champion = json.load(f)
        with open(args.challenger) as f:
            challenger = json.load(f)
    else:
        champion, challenger = get_champion_and_challenger(records, symbol, timeframe)

    if not challenger:
        print(f"[ERROR] No trained model found for {symbol} {timeframe}")
        sys.exit(2)

    if not champion:
        print(f"[INFO] No champion found for {symbol} {timeframe} — treating challenger as first model, auto-promoting.")
        print(f"  Challenger: {challenger.get('model_name')} Sharpe={challenger.get('validation_sharpe', 0):.3f}")
        if args.auto_promote:
            promote_challenger(challenger, config)
        sys.exit(0)

    checks = compare_models(champion, challenger, config)
    gate_result = determine_gate_result(checks)

    # Ollama
    ollama_available = False
    llm_analysis = None
    if not args.ci_mode and config["ollama"]["enabled"]:
        try:
            requests.get(f"{config['ollama']['base_url']}/api/tags", timeout=3)
            ollama_available = True
        except Exception:
            pass

        if ollama_available:
            prompt = build_llm_prompt(symbol, timeframe, champion, challenger, checks, gate_result)
            print(f"[INFO] Calling DeepSeek R1 for promotion reasoning... (may take 45–90s)")
            llm_analysis = call_ollama(
                config["models"]["reasoning"],
                prompt,
                config["ollama"]["base_url"],
                config["ollama"]["timeout_seconds"],
            )

    # Auto-promote if flagged
    promoted = False
    if gate_result == "PROMOTE" and args.auto_promote:
        promoted = promote_challenger(challenger, config)

    print_report(symbol, timeframe, champion, challenger, checks, gate_result,
                 llm_analysis, ollama_available, promoted)

    sys.exit(1 if gate_result == "REJECT" else 0)


if __name__ == "__main__":
    main()
