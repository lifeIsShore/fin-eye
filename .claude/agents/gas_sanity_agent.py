"""
gas_sanity_agent.py
─────────────────────────────────────────────────────────────────────────────
Checks whether a GAS snapshot result is plausible given its components.
Looks for internal inconsistencies — e.g. macro score dropped 20 points
but GAS rose, or all timeframes are 90%+ confident in opposite directions.

Uses Gemma2 27B (local Ollama) for narrative reasoning.
Falls back to rule-based checks if Ollama is unavailable.

Usage:
  python gas_sanity_agent.py --symbol AAPL
  python gas_sanity_agent.py --all-symbols --last-snapshot
  python gas_sanity_agent.py --symbol TSLA --log-only   # write to log, no stdout

Exit codes:
  0 = PASS or WARN
  1 = FAIL
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import yaml

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
LOG_PATH = SCRIPT_DIR / "gas_sanity.log"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_gas_snapshot(symbol: str, base_url: str, timeout: int) -> Optional[dict]:
    try:
        resp = requests.get(
            f"{base_url}/api/v1/gas/snapshot/{symbol}",
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [ERROR] Could not fetch GAS snapshot for {symbol}: {e}")
        return None


def fetch_gas_history(symbol: str, base_url: str, timeout: int, limit: int = 5) -> Optional[list]:
    """Fetch last N GAS snapshots to check for movement."""
    try:
        resp = requests.get(
            f"{base_url}/api/v1/gas/history/{symbol}",
            params={"limit": limit},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ── Rule-based sanity checks ──────────────────────────────────────────────────

def run_sanity_checks(snapshot: dict, history: Optional[list], config: dict) -> list[dict]:
    checks = []
    thresholds = config["gas_sanity"]

    gas_score = snapshot.get("gas_score", 0)
    components = snapshot.get("component_scores", {})
    technical = components.get("technical", 50)
    sentiment = components.get("sentiment", 50)
    macro = components.get("macro", 50)
    signals = snapshot.get("technical_signals", [])
    regime = snapshot.get("regime", "Transitional")
    weather = snapshot.get("weather_label", "Mixed Signals")

    # ── Score in valid range ──
    checks.append({
        "name": "GAS Score in Range",
        "status": "PASS" if 0 <= gas_score <= 100 else "FAIL",
        "detail": f"GAS = {gas_score}",
    })

    # ── Components sum to reasonable composite ──
    expected = technical * 0.40 + sentiment * 0.30 + macro * 0.30
    diff = abs(gas_score - expected)
    checks.append({
        "name": "GAS Composite Math",
        "status": "WARN" if diff > 2.0 else "PASS",
        "detail": f"GAS={gas_score:.1f}, Expected≈{expected:.1f} (diff={diff:.1f})"
                  + (" — rounding OK" if diff <= 1.0 else " — investigate" if diff > 2.0 else ""),
    })

    # ── Regime matches technical score ──
    expected_regime = "Risk-On" if technical >= 60 else "Risk-Off" if technical <= 40 else "Transitional"
    regime_match = regime == expected_regime
    checks.append({
        "name": "Regime Matches Technical Score",
        "status": "PASS" if regime_match else "WARN",
        "detail": f"Regime={regime}, Technical={technical:.1f} → expected regime: {expected_regime}",
    })

    # ── Component divergence check ──
    max_divergence = thresholds["max_component_divergence"]
    if macro < 40 and gas_score > 65:
        checks.append({
            "name": "Macro vs GAS Divergence",
            "status": "WARN",
            "detail": f"Macro={macro:.1f} (stressed) but GAS={gas_score:.1f} (supportive) — unusual divergence",
        })
    elif macro > 70 and gas_score < 35:
        checks.append({
            "name": "Macro vs GAS Divergence",
            "status": "WARN",
            "detail": f"Macro={macro:.1f} (supportive) but GAS={gas_score:.1f} (stressed) — unusual divergence",
        })
    else:
        checks.append({
            "name": "Macro vs GAS Divergence",
            "status": "PASS",
            "detail": f"Macro={macro:.1f}, GAS={gas_score:.1f} — directionally consistent",
        })

    # ── Technical vs Sentiment disagreement ──
    disagreement_threshold = thresholds["component_disagreement_threshold"]
    tech_sent_diff = abs(technical - sentiment)
    checks.append({
        "name": "Technical vs Sentiment Agreement",
        "status": "WARN" if tech_sent_diff > disagreement_threshold else "PASS",
        "detail": f"Technical={technical:.1f}, Sentiment={sentiment:.1f}, diff={tech_sent_diff:.1f}"
                  + (" — strong disagreement between signals" if tech_sent_diff > disagreement_threshold else ""),
    })

    # ── Historical movement check ──
    if history and len(history) >= 2:
        prev_gas = history[-2].get("gas_score", gas_score) if len(history) > 1 else gas_score
        movement = abs(gas_score - prev_gas)
        max_move = thresholds["max_single_cycle_gas_movement"]
        checks.append({
            "name": "Single-Cycle GAS Movement",
            "status": "WARN" if movement > max_move else "PASS",
            "detail": f"Movement from previous snapshot: {movement:.1f} pts (max: {max_move})"
                      + (" — investigate spike" if movement > max_move else ""),
        })

    # ── Timeframe signal internal consistency ──
    if signals:
        bull_signals = [s for s in signals if s.get("direction") == "Bullish"]
        bear_signals = [s for s in signals if s.get("direction") == "Bearish"]
        high_conf_bull = [s for s in bull_signals if s.get("confidence", 0) > 75]
        high_conf_bear = [s for s in bear_signals if s.get("confidence", 0) > 75]

        if high_conf_bull and high_conf_bear:
            checks.append({
                "name": "Timeframe Signal Consistency",
                "status": "WARN",
                "detail": f"{len(high_conf_bull)} high-confidence Bullish and {len(high_conf_bear)} high-confidence Bearish signals simultaneously — conflicting",
            })
        else:
            checks.append({
                "name": "Timeframe Signal Consistency",
                "status": "PASS",
                "detail": f"Signals: {len(bull_signals)} Bullish, {len(bear_signals)} Bearish — no high-confidence conflict",
            })

    # ── All components at exactly 50 (fallback values) ──
    if technical == 50.0 and sentiment == 50.0 and macro == 50.0:
        checks.append({
            "name": "Component Fallback Detection",
            "status": "WARN",
            "detail": "All components are exactly 50.0 — likely fallback defaults, real data may not have computed",
        })

    return checks


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


def build_llm_prompt(symbol: str, snapshot: dict, checks: list[dict]) -> str:
    components = snapshot.get("component_scores", {})
    signals = snapshot.get("technical_signals", [])
    checks_text = "\n".join(f"  [{c['status']}] {c['name']}: {c['detail']}" for c in checks)
    warns_fails = [c for c in checks if c["status"] in ("WARN", "FAIL")]

    return f"""You are a senior quantitative analyst reviewing an automated stock analysis score.

Symbol: {symbol}
GAS Score: {snapshot.get('gas_score')} / 100  ({snapshot.get('weather_label')})
Regime: {snapshot.get('regime')}

Component Scores:
  Technical: {components.get('technical')} / 100
  Sentiment: {components.get('sentiment')} / 100
  Macro:     {components.get('macro')} / 100

Timeframe Signals:
{json.dumps(signals, indent=2) if signals else "  No signals available"}

Automated sanity checks:
{checks_text}

Issues flagged: {len(warns_fails)}

In 3–5 sentences, assess whether this GAS score result appears plausible and internally consistent.
If there are warnings or failures, explain in plain English what they mean for a trader or developer looking at this score.
Focus on whether the score can be trusted as-is, should be investigated, or should be discarded.
"""


# ── Output ────────────────────────────────────────────────────────────────────

def determine_result(checks: list[dict]) -> str:
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def format_report(symbol: str, snapshot: dict, checks: list[dict],
                  llm_analysis: Optional[str], ollama_available: bool) -> str:
    result = determine_result(checks)
    icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[result]
    lines = []
    lines.append("")
    lines.append("═" * 65)
    lines.append(f"  AGENT: gas_sanity_agent")
    lines.append(f"  SYMBOL: {symbol}  |  GAS: {snapshot.get('gas_score')}  |  {snapshot.get('weather_label')}")
    lines.append(f"  RESULT: {result} {icon}")
    lines.append("═" * 65)
    lines.append("")
    lines.append("SANITY CHECKS:")
    for c in checks:
        icon_map = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        lines.append(f"  [{c['status']}] {icon_map[c['status']]}  {c['name']}: {c['detail']}")
    lines.append("")
    if not ollama_available:
        lines.append("⚠️  Ollama unavailable — rule-based mode only")
    elif llm_analysis:
        lines.append("LLM ANALYSIS (Gemma2 27B):")
        for line in llm_analysis.split("\n"):
            lines.append(f"  {line}")
    lines.append("")
    if result == "FAIL":
        lines.append("  ⛔ RECOMMENDATION: GAS snapshot is unreliable. Do not serve to users.")
    elif result == "WARN":
        lines.append("  ⚠️  RECOMMENDATION: Score can be served but investigate flagged items.")
    else:
        lines.append("  ✅ RECOMMENDATION: GAS snapshot looks healthy.")
    lines.append("═" * 65)
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fin-Eye GAS Sanity Agent")
    parser.add_argument("--symbol", type=str, help="Stock symbol")
    parser.add_argument("--all-symbols", action="store_true")
    parser.add_argument("--last-snapshot", action="store_true", help="Use last cached snapshot")
    parser.add_argument("--log-only", action="store_true", help="Write to log file only, no stdout")
    parser.add_argument("--ci-mode", action="store_true")
    args = parser.parse_args()

    config = load_config()
    api_base = config["fineye_api"]["base_url"]
    api_timeout = config["fineye_api"]["timeout_seconds"]

    symbols = config["default_symbols"] if args.all_symbols else [args.symbol.upper()] if args.symbol else []
    if not symbols:
        print("[ERROR] Provide --symbol TICKER or --all-symbols")
        sys.exit(1)

    # Ollama check
    ollama_available = False
    if not args.ci_mode and config["ollama"]["enabled"]:
        try:
            requests.get(f"{config['ollama']['base_url']}/api/tags", timeout=3)
            ollama_available = True
        except Exception:
            pass

    overall_fail = False

    for symbol in symbols:
        snapshot = fetch_gas_snapshot(symbol, api_base, api_timeout)
        if not snapshot:
            print(f"[ERROR] Could not retrieve snapshot for {symbol}")
            overall_fail = True
            continue

        history = fetch_gas_history(symbol, api_base, api_timeout)
        checks = run_sanity_checks(snapshot, history, config)

        llm_analysis = None
        if ollama_available:
            prompt = build_llm_prompt(symbol, snapshot, checks)
            llm_analysis = call_ollama(
                config["models"]["narrative"],
                prompt,
                config["ollama"]["base_url"],
                config["ollama"]["timeout_seconds"],
            )

        report = format_report(symbol, snapshot, checks, llm_analysis, ollama_available)

        if args.log_only:
            with open(LOG_PATH, "a") as f:
                f.write(f"\n[{datetime.now(timezone.utc).isoformat()}]\n")
                f.write(report + "\n")
        else:
            print(report)

        if determine_result(checks) == "FAIL":
            overall_fail = True

    sys.exit(1 if overall_fail else 0)


if __name__ == "__main__":
    main()
