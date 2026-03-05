#!/usr/bin/env python3
"""
restore_db.py — Fin-Eye PostgreSQL restore script (CORE-SEC-02)

Restores a pg_dump custom-format (.dump) file into the fin_eye database.

Usage:
    python scripts/backup/restore_db.py --file backups/fin_eye_20260306T120000Z.dump

Options:
    --file PATH        Path to the .dump file to restore (required)
    --drop             DROP and re-CREATE the target database before restore
                       (use with caution — destroys all current data)
    --dry-run          Print the pg_restore command without executing it

Environment variables:
    DATABASE_URL       PostgreSQL connection URL (same as app)
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("fin_eye.restore")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fin_eye")


def _parse_db_url(url: str) -> dict:
    p = urlparse(url)
    return {
        "host":     p.hostname or "localhost",
        "port":     str(p.port or 5432),
        "dbname":   p.path.lstrip("/"),
        "user":     p.username or "postgres",
        "password": p.password or "",
    }


def _run(cmd: list[str], env: dict, dry_run: bool) -> None:
    logger.info("CMD: %s", " ".join(cmd))
    if dry_run:
        logger.info("DRY RUN — command not executed.")
        return
    result = subprocess.run(cmd, env=env, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')}"
        )


def restore(dump_file: Path, drop_first: bool = False, dry_run: bool = False) -> None:
    if not dump_file.exists():
        raise FileNotFoundError(f"Dump file not found: {dump_file}")

    db = _parse_db_url(DATABASE_URL)
    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = db["password"]

    base_args = ["-h", db["host"], "-p", db["port"], "-U", db["user"]]

    if drop_first:
        logger.warning("--drop specified: dropping database '%s'", db["dbname"])
        _run(
            ["dropdb", *base_args, "--if-exists", db["dbname"]],
            env, dry_run,
        )
        logger.info("Creating fresh database '%s'", db["dbname"])
        _run(
            ["createdb", *base_args, db["dbname"]],
            env, dry_run,
        )

    logger.info("Restoring %s → %s …", dump_file.name, db["dbname"])
    _run(
        [
            "pg_restore",
            *base_args,
            "-d", db["dbname"],
            "--no-password",
            "--clean",           # drop objects before recreating
            "--if-exists",       # don't error if object doesn't exist
            "--no-owner",        # skip ownership commands
            "--exit-on-error",
            str(dump_file),
        ],
        env, dry_run,
    )

    logger.info("✅  Restore complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore a Fin-Eye PostgreSQL backup.")
    parser.add_argument("--file", required=True, type=Path, help="Path to .dump file")
    parser.add_argument("--drop", action="store_true", help="Drop and recreate DB before restore")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    try:
        restore(args.file, drop_first=args.drop, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("❌  Restore FAILED: %s", exc)
        sys.exit(1)
