"""
data_quality_checker.py
─────────────────────────────────────────────────────────────────────────────
Validates OHLCV price data and macro indicator feeds before training or GAS
pre-computation. Catches silent data feed failures (e.g. the Yahoo Finance
empty 4h response class of bug) before they corrupt model training.

Uses Qwen2.5-Coder 32B (local Ollama) for structured data anomaly reasoning.
Falls back to rule-based checks only if Ollama is unavailable.

Usage:
  python data_quality_checker.py --symbol AAPL
  python data_quality_checker.py --symbol AAPL --check-macro
  python data_quality_checker.py --all-symbols

Exit codes:
  0 = PASS or WARN
  1 = FAIL
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests
import yaml

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_ohlcv_from_api(symbol: str, base_url: str, timeout: int) -> Optional[list]:
    """Fetch recent OHLCV data from the fin-eye API."""
    try:
        resp = requests.get(
            f"{base_url}/api/v1/market/ohlcv/{symbol}",
            params={"interval": "1d", "period": "60d"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] Could not fetch OHLCV from API: {e}")
        return None


def fetch_macro_from_api(base_url: str, timeout: int) -> Optional[dict]:
    """Fetch latest macro indicators from the fin-eye API."""
    try:
        resp = requests.get(f"{base_url}/api/v1/macro/latest", timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] Could not fetch macro data from API: {e}")
        return None


def fetch_sentiment_from_api(symbol: str, base_url: str, timeout: int) -> Optional[dict]:
    """Fetch recent sentiment aggregates."""
    try:
        resp = requests.get(
            f"{base_url}/api/v1/sentiment/{symbol}",
            params={"days": 7},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] Could not fetch sentiment from API: {e}")
        return None


# ── OHLCV checks ──────────────────────────────────────────────────────────────

def check_ohlcv(data: list, config: dict) -> list[dict]:
    checks = []
    thresholds = config["data_quality"]

    if not data:
        return [{"name": "OHLCV Data Exists", "status": "FAIL",
                 "detail": "No OHLCV data returned from API — feed may be broken"}]

    checks.append({
        "name": "OHLCV Data Exists",
        "status": "PASS",
        "detail": f"{len(data)} bars returned",
    })

    min_bars = thresholds["min_ohlcv_bars_for_training"]
    checks.append({
        "name": "Sufficient Bars for Training",
        "status": "PASS" if len(data) >= min_bars else "FAIL",
        "detail": f"{len(data)} bars (minimum: {min_bars})",
    })

    # Price gap check
    max_gap = thresholds["max_price_gap_pct"]
    large_gaps = []
    for i in range(1, len(data)):
        prev_close = data[i - 1].get("close", 0)
        curr_close = data[i].get("close", 0)
        if prev_close and curr_close:
            gap = abs(curr_close - prev_close) / prev_close
            if gap > max_gap:
                large_gaps.append({"bar": i, "gap_pct": round(gap * 100, 1),
                                   "date": data[i].get("timestamp", "?")})
    checks.append({
        "name": "Price Gap Check",
        "status": "WARN" if large_gaps else "PASS",
        "detail": f"No gaps > {max_gap:.0%}" if not large_gaps
                  else f"{len(large_gaps)} gap(s) > {max_gap:.0%}: {large_gaps[:3]}",
    })

    # Zero volume check
    max_zero = thresholds["max_zero_volume_bars"]
    zero_vol_streak = 0
    max_streak = 0
    for bar in data:
        if bar.get("volume", 1) == 0:
            zero_vol_streak += 1
            max_streak = max(max_streak, zero_vol_streak)
        else:
            zero_vol_streak = 0

    checks.append({
        "name": "Zero Volume Check",
        "status": "WARN" if max_streak >= max_zero else "PASS",
        "detail": f"Max consecutive zero-volume bars: {max_streak} (threshold: {max_zero})",
    })

    # Empty bars check (None values)
    null_bars = [i for i, b in enumerate(data)
                 if b.get("close") is None or b.get("open") is None]
    checks.append({
        "name": "Null Value Check",
        "status": "FAIL" if null_bars else "PASS",
        "detail": f"No null OHLC values" if not null_bars
                  else f"{len(null_bars)} bar(s) with null OHLC at indices {null_bars[:5]}",
    })

    return checks


# ── Macro checks ──────────────────────────────────────────────────────────────

def check_macro(data: dict, config: dict) -> list[dict]:
    checks = []
    staleness = config["data_quality"]["macro_staleness_days"]
    today = datetime.now(timezone.utc).date()

    if not data:
        return [{"name": "Macro Data Exists", "status": "FAIL",
                 "detail": "No macro data returned — FRED feed may be broken"}]

    checks.append({"name": "Macro Data Exists", "status": "PASS",
                   "detail": f"{len(data)} indicators present"})

    for indicator, max_days in staleness.items():
        indicator_data = data.get(indicator)
        if indicator_data is None:
            checks.append({
                "name": f"Macro: {indicator}",
                "status": "WARN",
                "detail": f"Indicator not present in latest macro data",
            })
            continue

        last_date_str = indicator_data.get("date") or indicator_data.get("last_updated")
        if not last_date_str:
            checks.append({
                "name": f"Macro: {indicator}",
                "status": "WARN",
                "detail": "No date metadata available — cannot check staleness",
            })
            continue

        try:
            last_date = datetime.fromisoformat(str(last_date_str)).date()
            age_days = (today - last_date).days
            checks.append({
                "name": f"Macro: {indicator}",
                "status": "WARN" if age_days > max_days else "PASS",
                "detail": f"Last updated {age_days}d ago (max allowed: {max_days}d)"
                          + (" — STALE" if age_days > max_days else ""),
            })
        except Exception:
            checks.append({
                "name": f"Macro: {indicator}",
                "status": "WARN",
                "detail": f"Could not parse date: {last_date_str}",
            })

    return checks


# ── Sentiment checks ──────────────────────────────────────────────────────────

def check_sentiment(data: dict, config: dict) -> list[dict]:
    checks = []
    threshold = config["data_quality"]["sentiment_concentration_threshold"]

    if not data:
        return [{"name": "Sentiment Data", "status": "WARN",
                 "detail": "No sentiment data — FinBERT pipeline may not have run yet"}]

    scores = data.get("scores", [])
    if not scores:
        return [{"name": "Sentiment Scores", "status": "WARN",
                 "detail": "Sentiment aggregate returned no scores"}]

    # Direction concentration check
    bullish = sum(1 for s in scores if s > 0.1)
    bearish = sum(1 for s in scores if s < -0.1)
    neutral = len(scores) - bullish - bearish
    total = len(scores)

    bull_pct = bullish / total if total else 0
    bear_pct = bearish / total if total else 0

    concentrated = bull_pct > threshold or bear_pct > threshold
    checks.append({
        "name": "Sentiment Distribution",
        "status": "WARN" if concentrated else "PASS",
        "detail": f"Bullish: {bull_pct:.0%}  Bearish: {bear_pct:.0%}  Neutral: {neutral/total:.0%}"
                  + (" — HIGH CONCENTRATION, possible feed issue" if concentrated else ""),
    })

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
    except Exception:
        return None


def build_llm_prompt(symbol: str, ohlcv_checks: list, macro_checks: list, sent_checks: list) -> str:
    all_checks = ohlcv_checks + macro_checks + sent_checks
    checks_text = "\n".join(f"  [{c['status']}] {c['name']}: {c['detail']}" for c in all_checks)
    fails = [c for c in all_checks if c["status"] == "FAIL"]
    warns = [c for c in all_checks if c["status"] == "WARN"]

    return f"""You are a data quality engineer reviewing financial data feeds for a stock ML pipeline.

Symbol being checked: {symbol}

Data quality check results:
{checks_text}

Summary: {len(fails)} FAIL(s), {len(warns)} WARN(s)

Please provide:
1. A brief (2–4 sentence) assessment of the overall data health for this symbol
2. If there are any FAILs, explain what downstream impact they would have on ML model training
3. If there are WARNs, explain whether they are typically acceptable or should be investigated

Be direct and practical. The reader is a developer, not a data scientist.
"""


# ── Output ────────────────────────────────────────────────────────────────────

def determine_result(checks: list[dict]) -> str:
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def print_report(symbol: str, all_checks: list[dict], llm_analysis: Optional[str],
                 ollama_available: bool):
    result = determine_result(all_checks)
    icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[result]

    print()
    print("═" * 65)
    print(f"  AGENT: data_quality_checker")
    print(f"  SYMBOL: {symbol}")
    print(f"  RESULT: {result} {icon}")
    print("═" * 65)
    print()
    print("DATA QUALITY CHECKS:")
    for c in all_checks:
        icon_map = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        print(f"  [{c['status']}] {icon_map[c['status']]}  {c['name']}: {c['detail']}")

    print()
    if not ollama_available:
        print("⚠️  Ollama unavailable — running in rule-based mode (no LLM analysis)")
    elif llm_analysis:
        print("LLM ANALYSIS (Qwen2.5-Coder 32B):")
        for line in llm_analysis.split("\n"):
            print(f"  {line}")

    print()
    if result == "FAIL":
        print("  ⛔ RECOMMENDATION: Fix data issues before training. Do not proceed.")
    elif result == "WARN":
        print("  ⚠️  RECOMMENDATION: Training may proceed but investigate warnings.")
    else:
        print("  ✅ RECOMMENDATION: Data looks healthy. Safe to train.")
    print("═" * 65)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fin-Eye Data Quality Checker")
    parser.add_argument("--symbol", type=str, help="Stock symbol (e.g. AAPL)")
    parser.add_argument("--check-macro", action="store_true", help="Also check macro data feeds")
    parser.add_argument("--all-symbols", action="store_true", help="Check all default symbols")
    parser.add_argument("--ci-mode", action="store_true", help="Skip LLM, exit 1 on FAIL")
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
        print(f"\n[INFO] Checking data quality for {symbol}...")

        ohlcv_data = fetch_ohlcv_from_api(symbol, api_base, api_timeout)
        macro_data = fetch_macro_from_api(api_base, api_timeout) if args.check_macro else None
        sent_data = fetch_sentiment_from_api(symbol, api_base, api_timeout)

        ohlcv_checks = check_ohlcv(ohlcv_data or [], config)
        macro_checks = check_macro(macro_data or {}, config) if args.check_macro else []
        sent_checks = check_sentiment(sent_data or {}, config)

        all_checks = ohlcv_checks + macro_checks + sent_checks

        llm_analysis = None
        if ollama_available:
            prompt = build_llm_prompt(symbol, ohlcv_checks, macro_checks, sent_checks)
            print(f"[INFO] Calling Qwen2.5-Coder for analysis... (may take 20–40s)")
            llm_analysis = call_ollama(
                config["models"]["coder"],
                prompt,
                config["ollama"]["base_url"],
                config["ollama"]["timeout_seconds"],
            )

        print_report(symbol, all_checks, llm_analysis, ollama_available)

        if determine_result(all_checks) == "FAIL":
            overall_fail = True

    sys.exit(1 if overall_fail else 0)


if __name__ == "__main__":
    main()
