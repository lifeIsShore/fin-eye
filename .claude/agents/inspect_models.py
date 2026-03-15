"""
inspect_models.py
─────────────────────────────────────────────────────────────────────────────
Local model registry inspector for fin-eye.

Reads both registries (backend/data/models/ and model_store/) and produces
a clean terminal report AND an optional markdown file saved to
.claude/reports/model_report_YYYYMMDD_HHMMSS.md

Usage:
    python inspect_models.py                   # terminal report only
    python inspect_models.py --save-report     # terminal + save markdown file
    python inspect_models.py --registry backend
    python inspect_models.py --registry store
    python inspect_models.py --symbol AAPL
    python inspect_models.py --flag-issues     # only show problems
    python inspect_models.py --clean-test      # remove TEST_SYM entries

Run from the fin-eye project root:
    python .claude/agents/inspect_models.py --save-report
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Project paths ─────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
REPORTS_DIR   = SCRIPT_DIR.parent / "reports"

BACKEND_REGISTRY  = PROJECT_ROOT / "backend" / "data" / "models" / "model_registry.jsonl"
BACKEND_ARTIFACTS = PROJECT_ROOT / "backend" / "data" / "models"
STORE_REGISTRY    = PROJECT_ROOT / "model_store" / "registry.jsonl"
STORE_ARTIFACTS   = PROJECT_ROOT / "model_store" / "artifacts"

# ── Thresholds ────────────────────────────────────────────────────────────────

MIN_SHARPE        = 0.30
MIN_ACCURACY      = 0.52
SUSPICIOUS_SHARPE = 5.0


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


# ── Issue detection ───────────────────────────────────────────────────────────

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

    # Diagnostics block (populated by updated ml_pipeline.py)
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

    artifact_exists, artifact_path = check_artifact_exists(record)
    size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None
    label, icon = verdict(issues)

    print(f"  ┌─ {symbol} / {tf}  [{source}]  {icon} {label}")
    print(f"  │  Winner:   {winner.upper():<12}  Sharpe: {sharpe:.4f}" if sharpe else f"  │  Winner: {winner}  Sharpe: N/A")
    print(f"  │  Trained:  {trained}  Artifact: {'✅ ' + f'{size_kb:.0f}KB' if artifact_exists and size_kb else '❌ MISSING'}")

    # Show diagnostics inline if present
    if diag:
        val_rows = diag.get("val_rows", "?")
        total_rows = diag.get("total_rows", "?")
        target_bal = diag.get("target_balance_up_pct", "?")
        print(f"  │  Data:     total={total_rows} rows  val={val_rows} rows  target={target_bal}% UP")

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
            disq = " [DISQUALIFIED]" if m.get("disqualified") else ""
            mark = " ← WINNER" if m_name == winner else ""
            sh_i  = "✅" if sh >= MIN_SHARPE else ("⚠️ " if sh >= 0 else "❌")
            acc_i = "✅" if acc >= MIN_ACCURACY else ("⚠️ " if acc >= 0.50 else "❌")
            print(f"  │    {m_name:<10}  Sharpe:{sh:>7.3f} {sh_i}  Acc:{acc:.1%} {acc_i}  Return:{ret:+.3f}{mark}{disq}")

    if issues:
        print(f"  │  Issues:")
        for iss in sorted(issues, key=lambda x: LEVEL_ORDER[x["level"]]):
            print(f"  │    {LEVEL_ICON[iss['level']]} [{iss['code']}] {iss['message']}")

    print(f"  └{'─' * 60}")


# ── Markdown report builder ───────────────────────────────────────────────────

def build_markdown_report(
    all_records: list[dict],
    active_models: dict[tuple, dict],
    all_issues: dict[tuple, list],
    run_at: str,
    registry_filter: str,
    symbol_filter: Optional[str],
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
        f"**Total records in registry:** {len(all_records)}  ",
        f"**Active models (latest per symbol/timeframe):** {total}  ",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✅ PASS — safe to deploy | {passed} |",
        f"| ⚠️ WARN — review before deploying | {warned} |",
        f"| ❌ FAIL — do not use | {failed} |",
        "",
    ]

    if deployable:
        lines.append("### Models Currently Safe for GAS")
        lines.append("")
        for sym, tf, model, sh in deployable:
            lines.append(f"- **{sym} / {tf}** — {model.upper()} — Sharpe `{sh:.3f}`")
        lines.append("")
    else:
        lines += [
            "> ⚠️ **No models currently pass all quality gates.**  ",
            "> Consider retraining or running `data_quality_checker.py` first.",
            "",
        ]

    if older > 0:
        lines += [
            f"> ℹ️ {older} older training run(s) exist in the registry (superseded by latest).",
            "",
        ]

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
        v_label, v_icon = verdict(issues)

        artifact_exists, artifact_path = check_artifact_exists(record)
        size_kb = get_artifact_size_kb(artifact_path) if artifact_exists else None

        lines += [
            f"### {symbol} / {tf} &nbsp; {v_icon} {v_label}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Registry source | `{source}` |",
            f"| Winning model | `{winner.upper()}` |",
            f"| Validation Sharpe | `{sharpe:.4f}` |" if sharpe else "| Validation Sharpe | N/A |",
            f"| Trained at | `{trained}` |",
            f"| Artifact | {'✅ `' + Path(artifact_path).name + '` (' + f'{size_kb:.0f}KB)' if artifact_exists and size_kb else '❌ MISSING'} |",
        ]

        if diag:
            lines += [
                f"| Training rows | `{diag.get('total_rows', '?')}` total / `{diag.get('train_rows', '?')}` train / `{diag.get('val_rows', '?')}` val |",
                f"| Target balance | `{diag.get('target_balance_up_pct', '?')}%` UP |",
            ]
            low_var = diag.get("low_variance_features", [])
            if low_var:
                lines.append(f"| Low-variance features | `{low_var}` |")

        lines.append("")

        if metrics:
            lines += [
                "**All model results:**",
                "",
                "| Model | Sharpe | Accuracy | Total Return | Notes |",
                "|-------|--------|----------|--------------|-------|",
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
                disq = " DISQUALIFIED" if m.get("disqualified") else ""
                sh_i  = "✅" if sh >= MIN_SHARPE else ("⚠️" if sh >= 0 else "❌")
                acc_i = "✅" if acc >= MIN_ACCURACY else ("⚠️" if acc >= 0.50 else "❌")
                lines.append(
                    f"| `{m_name}` | {sh_i} `{sh:.3f}` | {acc_i} `{acc:.1%}` | `{ret:+.3f}` |{mark}{disq} |"
                )
            lines.append("")

        if issues:
            lines.append("**Issues detected:**")
            lines.append("")
            for iss in sorted(issues, key=lambda x: LEVEL_ORDER[x["level"]]):
                icon = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[iss["level"]]
                lines.append(f"- {icon} **[{iss['code']}]** {iss['message']}")
            lines.append("")

        if v_label == "FAIL":
            lines += ["> ❌ **Do not use this model.** Fix the errors above before deploying.", ""]
        elif v_label == "WARN":
            lines += ["> ⚠️ **Review warnings before deploying.**", ""]
        else:
            lines += ["> ✅ **Passes all quality gates.** Safe to use in GAS.", ""]

        lines += ["---", ""]

    lines += [
        "## Quality Gate Thresholds",
        "",
        "| Threshold | Value |",
        "|-----------|-------|",
        f"| Minimum Sharpe Ratio | `{MIN_SHARPE}` |",
        f"| Minimum Accuracy | `{MIN_ACCURACY:.0%}` |",
        f"| Suspicious Sharpe (likely noise) | `> {SUSPICIOUS_SHARPE}` |",
        "",
        "Thresholds are configured in `.claude/agents/config.yaml`.",
        "",
        "---",
        "",
        "## Next Steps",
        "",
        "**If models are failing:**",
        "1. Run `python .claude/agents/data_quality_checker.py --symbol AAPL --check-macro`",
        "2. Check OHLCV data coverage — enough bars for the timeframe?",
        "3. Retrain via the admin API, then re-run this report",
        "",
        "**If warnings about small sample / suspicious Sharpe:**",
        "- For `1wk` models: extend the training window (needs years of weekly data)",
        "- For `1d` models with accuracy < 50%: check target label distribution",
        "",
        "**To clean synthetic test data:**",
        "```bash",
        "python .claude/agents/inspect_models.py --clean-test",
        "```",
        "",
        f"*Report generated by `inspect_models.py` · fin-eye · {run_at}*",
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
            stripped = line.strip()
            if not stripped:
                continue
            try:
                r = json.loads(stripped)
                if r.get("symbol") == "TEST_SYM":
                    removed += 1
                else:
                    records.append(stripped)
            except Exception:
                records.append(stripped)

    if removed == 0:
        print(f"[INFO] No TEST_SYM entries found in {registry_path.name}")
        return

    backup = registry_path.with_suffix(".jsonl.bak")
    registry_path.rename(backup)
    print(f"[INFO] Backed up original to {backup.name}")
    with open(registry_path, "w", encoding="utf-8") as f:
        for line in records:
            f.write(line + "\n")
    print(f"[INFO] Removed {removed} TEST_SYM entries from {registry_path.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="fin-eye model registry inspector")
    parser.add_argument("--registry", choices=["backend", "store", "all"],
                        default="all")
    parser.add_argument("--symbol", type=str)
    parser.add_argument("--flag-issues", action="store_true")
    parser.add_argument("--save-report", action="store_true")
    parser.add_argument("--clean-test", action="store_true")
    parser.add_argument("--no-model-breakdown", action="store_true")
    args = parser.parse_args()

    run_at_dt = datetime.now()
    run_at    = run_at_dt.strftime("%Y-%m-%d %H:%M:%S")

    if args.clean_test:
        print("\n[INFO] Cleaning TEST_SYM entries from backend registry...")
        clean_test_entries(BACKEND_REGISTRY)
        print()

    all_records = load_all_registries(args.registry)
    if not all_records:
        print(f"\n[ERROR] No records found.")
        print(f"  Checked: {BACKEND_REGISTRY}")
        print(f"  Checked: {STORE_REGISTRY}")
        sys.exit(1)

    if args.symbol:
        all_records = [r for r in all_records if r.get("symbol") == args.symbol.upper()]
        if not all_records:
            print(f"\n[ERROR] No records found for symbol {args.symbol.upper()}")
            sys.exit(1)

    active_models = get_active_models(all_records)
    all_issues    = {key: detect_issues(record) for key, record in active_models.items()}

    print()
    print("═" * 65)
    print("  FIN-EYE MODEL REGISTRY INSPECTOR")
    print(f"  Run at: {run_at}")
    print(f"  Registries: {args.registry}   Symbol filter: {args.symbol or 'all'}")
    print(f"  Registry records: {len(all_records)}   Active models: {len(active_models)}")
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
        print("\n  ✅ All models passed. Use --flag-issues to see issues only.")

    older = len(all_records) - len(active_models)
    if older > 0:
        print(f"\n  ℹ️  {older} older training run(s) in registry (superseded — not shown).")

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
    print(f"  Total active models:   {total}")
    print(f"  ✅ PASS (deployable):  {passed}")
    print(f"  ⚠️  WARN (review):     {warned}")
    print(f"  ❌ FAIL (do not use):  {failed}")
    if deployable:
        print()
        print("  Models safe for GAS:")
        for d in deployable:
            print(f"    → {d}")
    else:
        print()
        print("  ⚠️  No models pass all quality gates right now.")
    print("═" * 65)
    print()

    if args.save_report:
        md_content  = build_markdown_report(
            all_records, active_models, all_issues,
            run_at, args.registry, args.symbol
        )
        report_path = save_markdown_report(md_content, run_at_dt)
        print(f"  📄 Markdown report saved:")
        print(f"     {report_path}")
        print(f"     {REPORTS_DIR / 'latest.md'}  ← always the most recent run")
        print()


if __name__ == "__main__":
    main()
