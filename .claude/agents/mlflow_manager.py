"""
mlflow_manager.py
─────────────────────────────────────────────────────────────────────────────
Utility for managing fin-eye ML model artifacts via MLflow.

Covers everything you need without opening a browser:
  - List all runs for a symbol/timeframe
  - Promote a run to Production
  - Revert production to a previous version
  - Stage a model (None → Staging → Production → Archived)
  - Download a specific run's artifact to the active model directory

Usage (run from fin-eye project root):
  python .claude/agents/mlflow_manager.py list     --symbol AAPL --timeframe 1h
  python .claude/agents/mlflow_manager.py runs     --symbol AAPL --timeframe 1h
  python .claude/agents/mlflow_manager.py promote  --symbol AAPL --timeframe 1h --version 3
  python .claude/agents/mlflow_manager.py revert   --symbol AAPL --timeframe 1h
  python .claude/agents/mlflow_manager.py stage    --symbol AAPL --timeframe 1h --version 3 --stage Staging
  python .claude/agents/mlflow_manager.py download --symbol AAPL --timeframe 1h --version 3

The MLflow UI (http://localhost:5000) shows the same information visually.
Start it with: start_mlflow.bat
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ARTIFACT_DIR = PROJECT_ROOT / "backend" / "data" / "models"

# SQLite backend — same as ml_pipeline.py and start_mlflow.bat
_DB = PROJECT_ROOT / "backend" / "data" / "mlflow.db"
MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{_DB}",
)
VALID_STAGES = ("None", "Staging", "Production", "Archived")


# ── MLflow connection ─────────────────────────────────────────────────────────

def get_client():
    try:
        import mlflow  # noqa: PLC0415
        from mlflow.tracking import MlflowClient  # noqa: PLC0415
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        return MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
    except ImportError:
        print("❌ mlflow is not installed. Run: pip install mlflow")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to MLflow backend: {MLFLOW_TRACKING_URI}")
        print(f"   Error: {e}")
        sys.exit(1)


def model_name(symbol: str, timeframe: str) -> str:
    return f"fin-eye-{symbol}-{timeframe}".replace("/", "-")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(symbol: str, timeframe: str):
    """List all registered versions for a symbol/timeframe."""
    client = get_client()
    name   = model_name(symbol, timeframe)

    try:
        versions = client.search_model_versions(f"name='{name}'")
    except Exception as e:
        print(f"❌ Could not list versions for '{name}': {e}")
        print("   Has this model been trained at least once with MLflow enabled?")
        sys.exit(1)

    if not versions:
        print(f"  No versions found for {name}")
        print("  Train the model first: POST /api/v1/admin/ml/train")
        return

    print()
    print(f"  Model: {name}")
    print(f"  Backend: {MLFLOW_TRACKING_URI}")
    print()
    print(f"  {'Ver':<5} {'Stage':<14} {'Run ID':<14} {'Created':<22} {'Sharpe':<10} {'Acc':<8} {'Winner'}")
    print("  " + "─" * 85)

    for v in sorted(versions, key=lambda x: int(x.version), reverse=True):
        run_id  = v.run_id[:10] + "..."
        stage   = v.current_stage
        created = str(v.creation_timestamp)[:10] if v.creation_timestamp else "?"

        try:
            run    = client.get_run(v.run_id)
            sharpe = run.data.metrics.get("winner.sharpe_ratio", "?")
            acc    = run.data.metrics.get("winner.accuracy", "?")
            winner = run.data.tags.get("winner_model", "?")
            sharpe_str = f"{sharpe:.3f}" if isinstance(sharpe, float) else str(sharpe)
            acc_str    = f"{float(acc):.1%}" if isinstance(acc, (float, int)) else str(acc)
        except Exception:
            sharpe_str, acc_str, winner = "?", "?", "?"

        stage_icon = {"Production": "🚀", "Staging": "🟡", "Archived": "📦"}.get(stage, "  ")
        print(f"  {v.version:<5} {stage_icon} {stage:<12} {run_id:<14} {created:<22} {sharpe_str:<10} {acc_str:<8} {winner}")

    print()
    print("  Run `promote --version N` to set a version to Production.")
    print("  Run `revert` to roll back to the previous Production version.")
    print()


def cmd_promote(symbol: str, timeframe: str, version: int):
    """Promote a specific version to Production and install its artifact."""
    client = get_client()
    name   = model_name(symbol, timeframe)

    # Archive current Production first
    try:
        current_prod = [
            v for v in client.search_model_versions(f"name='{name}'")
            if v.current_stage == "Production"
        ]
        for v in current_prod:
            client.transition_model_version_stage(
                name=name, version=v.version, stage="Archived",
                archive_existing_versions=False,
            )
            print(f"  Archived previous Production: version {v.version}")
    except Exception as e:
        print(f"  ⚠️  Could not archive previous production: {e}")

    try:
        client.transition_model_version_stage(
            name=name, version=str(version), stage="Production",
            archive_existing_versions=True,
        )
        print(f"  ✅ Version {version} promoted to Production")
    except Exception as e:
        print(f"  ❌ Promotion failed: {e}")
        sys.exit(1)

    cmd_download(symbol, timeframe, version, install=True)


def cmd_revert(symbol: str, timeframe: str):
    """Revert to the most recently Archived version."""
    client = get_client()
    name   = model_name(symbol, timeframe)

    try:
        versions = client.search_model_versions(f"name='{name}'")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    archived = [v for v in versions if v.current_stage == "Archived"]
    if not archived:
        print("  ❌ No Archived versions found to revert to.")
        sys.exit(1)

    prev = max(archived, key=lambda v: int(v.version))
    print(f"  Reverting to version {prev.version} (most recent Archived)...")

    current_prod = [v for v in versions if v.current_stage == "Production"]
    for v in current_prod:
        client.transition_model_version_stage(
            name=name, version=v.version, stage="Archived",
            archive_existing_versions=False,
        )
        print(f"  Archived current Production: version {v.version}")

    client.transition_model_version_stage(
        name=name, version=prev.version, stage="Production",
        archive_existing_versions=False,
    )
    print(f"  ✅ Version {prev.version} restored to Production")
    cmd_download(symbol, timeframe, int(prev.version), install=True)


def cmd_stage(symbol: str, timeframe: str, version: int, stage: str):
    """Set a model version to any stage."""
    if stage not in VALID_STAGES:
        print(f"❌ Invalid stage '{stage}'. Choose from: {VALID_STAGES}")
        sys.exit(1)

    client = get_client()
    name   = model_name(symbol, timeframe)

    try:
        client.transition_model_version_stage(
            name=name, version=str(version), stage=stage,
            archive_existing_versions=(stage == "Production"),
        )
        print(f"  ✅ {name} version {version} → {stage}")
    except Exception as e:
        print(f"  ❌ Stage transition failed: {e}")
        sys.exit(1)


def cmd_download(symbol: str, timeframe: str, version: int, install: bool = False):
    """Download a version's artifact. If install=True, copy to active winner location."""
    client = get_client()
    name   = model_name(symbol, timeframe)

    try:
        mv     = client.get_model_version(name, str(version))
        run_id = mv.run_id
    except Exception as e:
        print(f"❌ Could not find version {version} for {name}: {e}")
        sys.exit(1)

    import mlflow  # noqa: PLC0415
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    try:
        local_dir = mlflow.artifacts.download_artifacts(
            run_id=run_id, artifact_path="model",
        )
    except Exception as e:
        print(f"❌ Artifact download failed: {e}")
        sys.exit(1)

    joblib_files = list(Path(local_dir).glob("*.joblib"))
    if not joblib_files:
        print(f"❌ No .joblib file found in downloaded artifacts at {local_dir}")
        sys.exit(1)

    downloaded = joblib_files[0]
    print(f"  Downloaded: {downloaded}")

    if install:
        dest_name = f"{symbol}_{timeframe}_winner.joblib"
        dest_path = ARTIFACT_DIR / dest_name

        if dest_path.exists():
            backup = ARTIFACT_DIR / f"{symbol}_{timeframe}_winner.pre_revert.joblib"
            shutil.copy2(dest_path, backup)
            print(f"  Backed up current winner to: {backup.name}")

        shutil.copy2(downloaded, dest_path)
        print(f"  ✅ Installed as active winner: {dest_path}")
        print()
        print(f"  ⚠️  Clear Redis cache for this symbol:")
        print(f"     redis-cli DEL gas:snapshot:{symbol}")
    else:
        print(f"  Downloaded to: {downloaded}")
        print("  Add --install to copy it as the active winner file.")


def cmd_runs(symbol: str, timeframe: str, limit: int = 10):
    """List recent MLflow experiment runs for a symbol/timeframe."""
    try:
        import mlflow  # noqa: PLC0415
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    except Exception:
        sys.exit(1)

    client = get_client()
    experiment_name = "fin-eye-technical-signals"

    try:
        exp = client.get_experiment_by_name(experiment_name)
        if not exp:
            print(f"  No experiment '{experiment_name}' found.")
            print("  Run a training job first.")
            return
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string=f"tags.symbol = '{symbol}' AND tags.timeframe = '{timeframe}'",
        order_by=["start_time DESC"],
        max_results=limit,
    )

    if not runs:
        print(f"  No runs found for {symbol}/{timeframe}")
        return

    print()
    print(f"  Recent runs for {symbol}/{timeframe} (last {limit}):")
    print()
    print(f"  {'Run ID':<14} {'Started':<22} {'Winner':<12} {'Sharpe':<10} {'Acc':<8} {'Gate'}")
    print("  " + "─" * 75)

    for r in runs:
        run_id  = r.info.run_id[:10] + "..."
        started = str(r.info.start_time)[:10] if r.info.start_time else "?"
        winner  = r.data.tags.get("winner_model", "?")
        gate    = r.data.tags.get("quality_gate", "?")
        sharpe  = r.data.metrics.get("winner.sharpe_ratio", "?")
        acc     = r.data.metrics.get("winner.accuracy", "?")

        sharpe_str = f"{sharpe:.3f}" if isinstance(sharpe, float) else str(sharpe)
        acc_str    = f"{float(acc):.1%}" if isinstance(acc, (float, int)) else str(acc)
        gate_icon  = "✅" if gate == "pass" else "⚠️ "

        print(f"  {run_id:<14} {started:<22} {winner:<12} {sharpe_str:<10} {acc_str:<8} {gate_icon} {gate}")

    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="fin-eye MLflow model manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mlflow_manager.py list     --symbol AAPL --timeframe 1h
  python mlflow_manager.py runs     --symbol AAPL --timeframe 1h
  python mlflow_manager.py promote  --symbol AAPL --timeframe 1h --version 3
  python mlflow_manager.py revert   --symbol AAPL --timeframe 1h
  python mlflow_manager.py stage    --symbol AAPL --timeframe 1h --version 2 --stage Staging
  python mlflow_manager.py download --symbol AAPL --timeframe 1h --version 2 --install
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_sym_tf(p):
        p.add_argument("--symbol",    required=True, type=str.upper)
        p.add_argument("--timeframe", required=True)

    p_list = subparsers.add_parser("list",     help="List registered model versions")
    add_sym_tf(p_list)

    p_runs = subparsers.add_parser("runs",     help="List recent experiment runs")
    add_sym_tf(p_runs)
    p_runs.add_argument("--limit", type=int, default=10)

    p_promote = subparsers.add_parser("promote", help="Promote a version to Production")
    add_sym_tf(p_promote)
    p_promote.add_argument("--version", required=True, type=int)

    p_revert = subparsers.add_parser("revert",  help="Revert to previous Production")
    add_sym_tf(p_revert)

    p_stage = subparsers.add_parser("stage",   help="Set a version to any stage")
    add_sym_tf(p_stage)
    p_stage.add_argument("--version", required=True, type=int)
    p_stage.add_argument("--stage",   required=True, choices=VALID_STAGES)

    p_dl = subparsers.add_parser("download",   help="Download a version's artifact")
    add_sym_tf(p_dl)
    p_dl.add_argument("--version", required=True, type=int)
    p_dl.add_argument("--install", action="store_true",
                       help="Install as active winner file")

    args = parser.parse_args()

    print()
    print(f"  fin-eye MLflow Manager  |  {MLFLOW_TRACKING_URI}")
    print()

    if   args.command == "list":     cmd_list(args.symbol, args.timeframe)
    elif args.command == "runs":     cmd_runs(args.symbol, args.timeframe, args.limit)
    elif args.command == "promote":  cmd_promote(args.symbol, args.timeframe, args.version)
    elif args.command == "revert":   cmd_revert(args.symbol, args.timeframe)
    elif args.command == "stage":    cmd_stage(args.symbol, args.timeframe, args.version, args.stage)
    elif args.command == "download": cmd_download(args.symbol, args.timeframe, args.version, args.install)


if __name__ == "__main__":
    main()
