"""
inspect_models.py
─────────────────────────────────────────────────────────────────────────────
Local model registry inspector for fin-eye.

Reads both registries (backend/data/models/ and model_store/) and produces:
  1. A terminal report with rule-based quality checks
  2. An optional LLM evaluation via local Ollama (DeepSeek R1 32B) — STREAMING
  3. An optional markdown report saved to .claude/reports/

The LLM adds a narrative layer ON TOP of the rule-based checks — it reasons
about WHY the numbers look the way they do and what to do about it.
Streaming is used so the terminal shows live output instead of hanging silently.

Usage:
    python inspect_models.py                        # rule-based only
    python inspect_models.py --llm                  # rule-based + Ollama LLM
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
STORE_ARTIFACTS   = PROJECT_ROOT / "model_store" / "artifacts"

# ── Thresholds ────────────────────────────────────────────────────────────────

MIN_SHARPE        = 0.30
MIN_ACCURACY      = 0.52
SUSPICIOUS_SHARPE = 5.0

# ── Config loader ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {
        "ollama": {"base_url": "http://localhost:11434", "timeout_seconds": 360, "enabled": True},
        "models": {"reasoning": "deepseek-r1:32b"},
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
                r["_registry_file"] = str(path)
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


# ── Rule-based issue detection ────────────────────────────────────────────────

def detect_issues(record: dict) -> list[dict]:
    issues = []
    sharpe  = record.get("validation_sharpe") or record.get("sharpe_ratio")
    metrics = record.get("metrics", {})
    winner  = record.get("model_name") or record.get("model_kind", "unknown")
    symbol  = record.get("symbol", "?")
    tf      = record.get("timeframe", "?")

    accuracy = metrics.get(winner, {}).get("accuracy") if metrics else record.get("accuracy")

    def add(level, code, message):
        issues.append({"level": level, "code": code, "message": message})

    # Sharpe
    if sharpe is None:
        add("ERROR", "NO_SHARPE", "No Sharpe ratio recorded")
    elif sharpe < 0:
        add("ERROR", "NEGATIVE_SHARPE", f"Sharpe is negative ({sharpe:.3f}) — model destroys value")
    elif sharpe < MIN_SHARPE:
        add("WARN", "LOW_SHARPE", f"Sharpe {sharpe:.3f} below deployment threshold ({MIN_SHARPE})")
    elif sharpe > SUSPICIOUS_SHARPE:
        add("WARN", "SUSPICIOUS_SHARPE", f"Sharpe {sharpe:.3f} unusually high — likely small validation set or data artifact")

    # Accuracy
    if accuracy is None:
        add("WARN", "NO_ACCURACY", "No accuracy recorded")
    elif accuracy < 0.50:
        add("ERROR", "BELOW_RANDOM", f"Accuracy {accuracy:.1%} is below random (50%) — model is anti-predictive")
    elif accuracy < MIN_ACCURACY:
        add("WARN", "LOW_ACCURACY", f"Accuracy {accuracy:.1%} below deployment threshold ({MIN_ACCURACY:.0%})")

    # Contradiction
    if sharpe and accuracy and sharpe > 1.0 and accuracy < 0.50:
        add("WARN", "SHARPE_ACCURACY_CONTRADICTION",
            f"Positive Sharpe ({sharpe:.2f}) but accuracy below 50% ({accuracy:.1%}) — validate return distribution")

    # Prophet failure
    if metrics:
        pa = metrics.get("prophet", {}).get("accuracy")
        if pa == 0.0:
            add("WARN", "PROPHET_FAILED", "Prophet returned 0.0 accuracy — likely failed during training")

    # Artifact
    artifact_exists, artifact_path = check_artifact_exists(record)
    size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None

    if not artifact_exists:
        add("ERROR", "ARTIFACT_MISSING", "Joblib file not found — model cannot be loaded for inference")
    elif winner == "logistic" and size_kb and size_kb < 5:
        add("WARN", "TINY_LOGISTIC", f"Logistic artifact is only {size_kb:.1f}KB — likely fallback or minimal data")
    elif winner == "xgboost" and size_kb and size_kb > 100:
        add("INFO", "XGBOOST_FULL", f"XGBoost artifact is {size_kb:.0f}KB — full model confirmed")

    # Diagnostics
    diag = record.get("diagnostics", {})
    val_rows       = diag.get("val_rows")
    target_balance = diag.get("target_balance_up_pct")
    low_var        = diag.get("low_variance_features", [])

    if val_rows is not None and val_rows < 50:
        add("ERROR", "TINY_VALIDATION_SET",
            f"Only {val_rows} validation rows — Sharpe and accuracy estimates are unreliable")
    elif val_rows is not None and val_rows < 100:
        add("WARN", "SMALL_VALIDATION_SET",
            f"Only {val_rows} validation rows — estimates are noisy, treat with caution")
    elif val_rows is not None:
        add("INFO", "VALIDATION_SIZE", f"Validation set: {val_rows} rows")

    if target_balance is not None and abs(target_balance - 50) > 15:
        direction = "UP" if target_balance > 50 else "DOWN"
        add("WARN", "TARGET_IMBALANCE",
            f"Target is {target_balance:.1f}% {direction} — imbalanced labels may bias model toward majority class")

    if low_var:
        add("WARN", "LOW_VARIANCE_FEATURES",
            f"Near-zero variance features detected (will not help model): {low_var}")

    # Weekly small sample
    if tf == "1wk" and sharpe and sharpe > 5.0:
        add("WARN", "WEEKLY_SMALL_SAMPLE",
            "Weekly timeframe: very few validation bars — high Sharpe is likely noise")

    # Test data
    if symbol == "TEST_SYM":
        add("WARN", "TEST_DATA_IN_REGISTRY", "TEST_SYM is synthetic — remove from production registry")

    # Age
    trained_at = record.get("trained_at", "")
    if trained_at:
        try:
            trained_dt = datetime.fromisoformat(trained_at.replace("Z", "+00:00"))
            now = datetime.now(tz=trained_dt.tzinfo)
            age_days = (now - trained_dt).days
            if age_days > 30:
                add("INFO", "MODEL_AGE", f"Model is {age_days} days old — consider retraining")
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


# ── Active model selection ────────────────────────────────────────────────────

def get_active_models(records: list[dict]) -> dict[tuple, dict]:
    active: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("symbol"), r.get("timeframe"), r.get("_source"))
        active[key] = r
    return active


# ── Ollama LLM evaluation ─────────────────────────────────────────────────────

def check_ollama(config: dict) -> bool:
    try:
        requests.get(f"{config['ollama']['base_url']}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def build_llm_prompt(active_models: dict, all_issues: dict) -> str:
    model_summaries = []

    for key, record in sorted(active_models.items(), key=lambda x: (x[0][0] or "", x[0][1] or "")):
        symbol  = record.get("symbol", "?")
        tf      = record.get("timeframe", "?")
        winner  = record.get("model_name") or record.get("model_kind", "unknown")
        sharpe  = record.get("validation_sharpe") or record.get("sharpe_ratio", 0)
        metrics = record.get("metrics", {})
        diag    = record.get("diagnostics", {})
        issues  = all_issues[key]
        v_label, _ = verdict(issues)

        issue_codes = [f"[{i['level']}:{i['code']}] {i['message']}" for i in issues]

        model_lines = []
        for m_name in ["logistic", "xgboost", "prophet"]:
            m = metrics.get(m_name, {})
            if m:
                model_lines.append(
                    f"    {m_name}: Sharpe={m.get('sharpe_ratio',-99):.3f}, "
                    f"Acc={m.get('accuracy',0):.1%}"
                )

        summary = f"\n  {symbol}/{tf} [{record.get('_source')}] — {v_label}"
        summary += f"\n  Winner: {winner.upper()}, Sharpe={sharpe:.3f}"
        if model_lines:
            summary += "\n  All models:\n" + "\n".join(model_lines)
        if diag:
            summary += (
                f"\n  Data: {diag.get('total_rows','?')} rows, "
                f"{diag.get('val_rows','?')} val, "
                f"target={diag.get('target_balance_up_pct','?')}% UP, "
                f"horizon={record.get('horizon_periods','?')} periods"
            )
        if issue_codes:
            summary += "\n  Issues:\n" + "\n".join(f"    {c}" for c in issue_codes)

        model_summaries.append(summary)

    return f"""You are a senior quantitative analyst reviewing ML model results for a fintech stock signal platform.

The platform trains XGBoost, Logistic Regression, and Prophet to predict forward price direction.
Winner per timeframe is selected by highest Sharpe on a hold-out validation set.
Sharpe is computed from real forward returns. Target is binary (up=1, down=0).

Current active models:
{"".join(model_summaries)}

Provide a structured response with these four sections:

1. OVERALL HEALTH (2-3 sentences): Can any of these be trusted in production?

2. ROOT CAUSE ANALYSIS: For each FAIL or WARN, diagnose the most likely cause.
   Be specific — reference the actual numbers.

3. PRIORITY FIXES (max 4, ordered by impact): What should the developer do first?
   Name the file or function where applicable.

4. SAFEST MODEL RIGHT NOW: Which symbol/timeframe is most trustworthy and why?

Under 400 words. Developer audience, not academic.
"""


def call_ollama(prompt: str, config: dict) -> Optional[str]:
    """
    Streaming Ollama call. Prints tokens as they arrive — no frozen terminal.
    Returns the full assembled response string.
    """
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
            "Try: increase timeout_seconds in config.yaml, "
            "or use gemma2:27b (faster) by changing models.reasoning in config.yaml."
        )
    except Exception as e:
        print()
        return f"[LLM ERROR] {e}"


# ── Terminal output ───────────────────────────────────────────────────────────

def print_model_block(record: dict, issues: list[dict], show_breakdown: bool = True):
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
    size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None
    label, icon = verdict(issues)

    print(f"  ┌─ {symbol} / {tf}  [{source}]  {icon} {label}")
    print(f"  │  Winner:   {winner.upper():<12}  Sharpe: {sharpe:.4f}" if sharpe else f"  │  Winner: {winner}  Sharpe: N/A")
    print(f"  │  Trained:  {trained}  Artifact: {'✅ ' + f'{size_kb:.0f}KB' if artifact_exists and size_kb else '❌ MISSING'}")

    if diag:
        print(
            f"  │  Data:     total={diag.get('total_rows','?')}  "
            f"val={diag.get('val_rows','?')}  "
            f"target={diag.get('target_balance_up_pct','?')}% UP  "
            f"horizon={horizon}p"
        )

    if metrics and show_breakdown:
        print(f"  │  All models:")
        for m_name in ["logistic", "xgboost", "prophet"]:
            m = metrics.get(m_name, {})
            if not m:
                print(f"  │    {m_name:<10} — not trained")
                continue
            acc  = m.get("accuracy", 0)
            sh   = m.get("sharpe_ratio", -99)
            ret  = m.get("total_return", 0)
            disq = " [DISQ]" if m.get("disqualified") else ""
            mark = " ← WINNER" if m_name == winner else ""
            sh_i  = "✅" if sh >= MIN_SHARPE else ("⚠️ " if sh >= 0 else "❌")
            acc_i = "✅" if acc >= MIN_ACCURACY else ("⚠️ " if acc >= 0.50 else "❌")
            print(f"  │    {m_name:<10}  Sharpe:{sh:>7.3f} {sh_i}  Acc:{acc:.1%} {acc_i}  Ret:{ret:+.3f}{mark}{disq}")

    if issues:
        print(f"  │  Issues:")
        for iss in sorted(issues, key=lambda x: LEVEL_ORDER[x["level"]]):
            print(f"  │    {LEVEL_ICON[iss['level']]} [{iss['code']}] {iss['message']}")

    print(f"  └{'─' * 60}")


def print_llm_section(llm_response: Optional[str], ollama_available: bool, llm_requested: bool):
    print()
    print("═" * 65)
    print("  LLM ASSESSMENT (DeepSeek R1 32B)")
    print("═" * 65)

    if not llm_requested:
        print("  ℹ️  Not requested. Run with --llm to enable.")
    elif not ollama_available:
        print("  ⚠️  Ollama is not running or unreachable.")
        print("  Start: ollama serve")
        print("  Pull:  ollama pull deepseek-r1:32b")
        print("  Faster alternative: change models.reasoning to gemma2:27b in config.yaml")
    elif llm_response and llm_response.startswith("[LLM ERROR]"):
        print(f"  {llm_response}")
    elif llm_response:
        # Already streamed to terminal — just close the section
        pass
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
) -> str:
    lines = []

    total   = len(active_models)
    passed  = sum(1 for k in active_models if verdict(all_issues[k])[0] == "PASS")
    warned  = sum(1 for k in active_models if verdict(all_issues[k])[0] == "WARN")
    failed  = sum(1 for k in active_models if verdict(all_issues[k])[0] == "FAIL")
    older   = len(all_records) - total

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
        f"**Registry:** {registry_filter}  ",
        f"**Symbol filter:** {symbol_filter or 'all'}  ",
        f"**Total records:** {len(all_records)}  |  **Active models:** {total}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✅ PASS — safe to deploy | {passed} |",
        f"| ⚠️ WARN — review | {warned} |",
        f"| ❌ FAIL — do not use | {failed} |",
        "",
    ]

    if deployable:
        lines.append("### Models Safe for GAS")
        lines.append("")
        for sym, tf, model, sh in deployable:
            lines.append(f"- **{sym} / {tf}** — {model.upper()} — Sharpe `{sh:.3f}`")
        lines.append("")
    else:
        lines += ["> ⚠️ **No models pass all quality gates.**", ""]

    if older > 0:
        lines += [f"> ℹ️ {older} older run(s) superseded in registry.", ""]

    # LLM section
    lines += ["---", "", "## LLM Assessment (DeepSeek R1 32B)", ""]

    if not llm_requested:
        lines += ["> *Run with `--llm` to include LLM assessment.*", ""]
    elif not ollama_available:
        lines += ["> ⚠️ *Ollama was not reachable at report time.*", ""]
    elif llm_response and not llm_response.startswith("[LLM ERROR]"):
        lines += [llm_response, ""]
    else:
        lines += [f"> ⚠️ *{llm_response}*", ""]

    # Per-model sections
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
        size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None

        lines += [
            f"### {symbol} / {tf} &nbsp; {v_icon} {v_label}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Source | `{source}` |",
            f"| Winner | `{winner.upper()}` |",
            f"| Sharpe | `{sharpe:.4f}` |" if sharpe else "| Sharpe | N/A |",
            f"| Trained | `{trained}` |",
            f"| Artifact | {'✅ `' + Path(artifact_path).name + f'` ({size_kb:.0f}KB)' if artifact_exists and size_kb else '❌ MISSING'} |",
            f"| Horizon | `{horizon} periods` |",
        ]

        if diag:
            lines += [
                f"| Rows | `{diag.get('total_rows','?')}` total / `{diag.get('val_rows','?')}` val |",
                f"| Target | `{diag.get('target_balance_up_pct','?')}%` UP |",
            ]
            if diag.get("low_variance_features"):
                lines.append(f"| Low-var features | `{diag['low_variance_features']}` |")

        lines.append("")

        if metrics:
            lines += [
                "**Model competition:**",
                "",
                "| Model | Sharpe | Accuracy | Return | Notes |",
                "|-------|--------|----------|--------|-------|",
            ]
            for m_name in ["logistic", "xgboost", "prophet"]:
                m = metrics.get(m_name)
                if not m:
                    lines.append(f"| {m_name} | — | — | — | not trained |")
                    continue
                acc  = m.get("accuracy", 0)
                sh   = m.get("sharpe_ratio", -99)
                ret  = m.get("total_return", 0)
                mark = " **← WINNER**" if m_name == winner else ""
                disq = " DISQ" if m.get("disqualified") else ""
                sh_i  = "✅" if sh >= MIN_SHARPE else ("⚠️" if sh >= 0 else "❌")
                acc_i = "✅" if acc >= MIN_ACCURACY else ("⚠️" if acc >= 0.50 else "❌")
                lines.append(f"| `{m_name}` | {sh_i} `{sh:.3f}` | {acc_i} `{acc:.1%}` | `{ret:+.3f}` |{mark}{disq} |")
            lines.append("")

        if issues:
            lines.append("**Issues:**")
            lines.append("")
            for iss in sorted(issues, key=lambda x: LEVEL_ORDER[x["level"]]):
                icon = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[iss["level"]]
                lines.append(f"- {icon} **[{iss['code']}]** {iss['message']}")
            lines.append("")

        rec_map = {
            "FAIL": "> ❌ **Do not use.** Fix errors before deploying.",
            "WARN": "> ⚠️ **Review warnings before deploying.**",
            "PASS": "> ✅ **Passes all quality gates.** Safe for GAS.",
        }
        lines += [rec_map[v_label], "", "---", ""]

    lines += [
        "## Thresholds",
        "",
        f"Min Sharpe: `{MIN_SHARPE}` · Min Accuracy: `{MIN_ACCURACY:.0%}` · "
        f"Suspicious Sharpe: `> {SUSPICIOUS_SHARPE}`  ",
        "Configured in `.claude/agents/config.yaml`",
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
        print(f"[INFO] No TEST_SYM entries found.")
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
    parser.add_argument("--symbol", type=str)
    parser.add_argument("--flag-issues", action="store_true")
    parser.add_argument("--llm", action="store_true",
                        help="Run streaming LLM assessment via Ollama")
    parser.add_argument("--save-report", action="store_true",
                        help="Save markdown report to .claude/reports/")
    parser.add_argument("--clean-test", action="store_true")
    parser.add_argument("--no-model-breakdown", action="store_true")
    args = parser.parse_args()

    config    = load_config()
    run_at_dt = datetime.now()
    run_at    = run_at_dt.strftime("%Y-%m-%d %H:%M:%S")

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
    all_issues    = {key: detect_issues(record) for key, record in active_models.items()}

    print()
    print("═" * 65)
    print("  FIN-EYE MODEL REGISTRY INSPECTOR")
    print(f"  Run at: {run_at}")
    print(f"  Registries: {args.registry}   Symbol: {args.symbol or 'all'}")
    print(f"  Records: {len(all_records)}   Active models: {len(active_models)}")
    print(f"  LLM: {'ENABLED — DeepSeek R1 32B (streaming)' if args.llm else 'OFF (use --llm)'}")
    print("═" * 65)

    printed = 0
    for key, record in sorted(active_models.items(), key=lambda x: (x[0][0] or "", x[0][1] or "")):
        issues  = all_issues[key]
        v_label, _ = verdict(issues)
        if args.flag_issues and v_label == "PASS":
            continue
        print()
        print_model_block(record, issues, show_breakdown=not args.no_model_breakdown)
        printed += 1

    if printed == 0:
        print("\n  ✅ All models passed.")

    older = len(all_records) - len(active_models)
    if older > 0:
        print(f"\n  ℹ️  {older} older run(s) superseded.")

    total  = len(active_models)
    passed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "PASS")
    warned = sum(1 for k in active_models if verdict(all_issues[k])[0] == "WARN")
    failed = sum(1 for k in active_models if verdict(all_issues[k])[0] == "FAIL")
    deployable = [
        f"{r.get('symbol')}/{r.get('timeframe')} "
        f"({(r.get('model_name') or r.get('model_kind','?')).upper()} "
        f"Sharpe={(r.get('validation_sharpe') or r.get('sharpe_ratio', 0)):.2f})"
        for k, r in active_models.items()
        if verdict(all_issues[k])[0] == "PASS"
    ]

    print()
    print("═" * 65)
    print("  SUMMARY")
    print("═" * 65)
    print(f"  Total: {total}  ✅ {passed}  ⚠️  {warned}  ❌ {failed}")
    if deployable:
        print("\n  Safe for GAS:")
        for d in deployable:
            print(f"    → {d}")
    else:
        print("\n  ⚠️  No models pass all quality gates.")
    print("═" * 65)

    # LLM
    llm_response     = None
    ollama_available = False

    if args.llm and config["ollama"].get("enabled", True):
        ollama_available = check_ollama(config)
        if ollama_available:
            prompt       = build_llm_prompt(active_models, all_issues)
            llm_response = call_ollama(prompt, config)
        print_llm_section(llm_response, ollama_available, args.llm)
    elif args.llm:
        print_llm_section(None, False, args.llm)

    if args.save_report:
        md = build_markdown_report(
            all_records, active_models, all_issues,
            run_at, args.registry, args.symbol,
            llm_response, ollama_available, args.llm,
        )
        path = save_markdown_report(md, run_at_dt)
        print()
        print(f"  📄 Saved: {path}")
        print(f"     {REPORTS_DIR / 'latest.md'}")
        print()


if __name__ == "__main__":
    main()
