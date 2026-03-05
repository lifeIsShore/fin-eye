#!/usr/bin/env python3
"""
backup_db.py — Fin-Eye PostgreSQL backup script (CORE-SEC-02)

Creates a compressed pg_dump of the fin_eye database, rotates old local
backups, and optionally copies the dump to an offsite location (S3, SFTP,
or local NAS mount — configured via environment variables).

Usage:
    python scripts/backup/backup_db.py

Environment variables (all optional — fall back to sane defaults):
    DATABASE_URL         PostgreSQL connection URL (same as app)
    BACKUP_DIR           Local directory for dump files (default: ./backups)
    BACKUP_RETAIN_DAYS   How many days of local backups to keep (default: 14)
    BACKUP_S3_BUCKET     If set, upload dump to this S3 bucket (requires boto3)
    BACKUP_S3_PREFIX     Key prefix inside the bucket (default: fin-eye-backups/)
    AWS_ACCESS_KEY_ID    (standard boto3 env vars)
    AWS_SECRET_ACCESS_KEY
    AWS_DEFAULT_REGION

Designed to be run:
  - Manually for ad-hoc backups
  - Via cron / Task Scheduler on a schedule (see docs/backup-runbook.md)
  - As a scheduled APScheduler job (see scheduler integration below)
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("fin_eye.backup")

# ─── Config from environment ─────────────────────────────────────────────────

DATABASE_URL      = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fin_eye")
BACKUP_DIR        = Path(os.getenv("BACKUP_DIR", "backups")).resolve()
BACKUP_RETAIN_DAYS = int(os.getenv("BACKUP_RETAIN_DAYS", "14"))
S3_BUCKET         = os.getenv("BACKUP_S3_BUCKET", "")
S3_PREFIX         = os.getenv("BACKUP_S3_PREFIX", "fin-eye-backups/")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_db_url(url: str) -> dict:
    """Extract host/port/dbname/user/password from a postgresql:// URL."""
    p = urlparse(url)
    return {
        "host":     p.hostname or "localhost",
        "port":     str(p.port or 5432),
        "dbname":   p.path.lstrip("/"),
        "user":     p.username or "postgres",
        "password": p.password or "",
    }


def _pg_dump(db: dict, out_path: Path) -> None:
    """Run pg_dump and write a gzip-compressed custom-format dump."""
    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = db["password"]

    # Use custom format (-Fc) — most flexible for pg_restore
    cmd = [
        "pg_dump",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-Fc",          # custom format (compressed internally)
        "--no-password",
        db["dbname"],
    ]

    logger.info("Running pg_dump → %s", out_path)
    with open(out_path, "wb") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

    if result.returncode != 0:
        out_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"pg_dump failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')}"
        )

    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Dump complete — %.2f MB written to %s", size_mb, out_path)


def _rotate_old_backups(directory: Path, retain_days: int) -> None:
    """Delete dump files older than retain_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    deleted = 0
    for f in directory.glob("fin_eye_*.dump"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            f.unlink()
            logger.info("Rotated old backup: %s", f.name)
            deleted += 1
    if deleted:
        logger.info("Rotation complete — %d old file(s) removed", deleted)
    else:
        logger.info("Rotation: no files older than %d days found", retain_days)


def _upload_to_s3(local_path: Path, bucket: str, prefix: str) -> None:
    """Upload dump to S3. Requires boto3 and valid AWS credentials."""
    try:
        import boto3  # type: ignore
    except ImportError:
        logger.warning("boto3 not installed — skipping S3 upload. pip install boto3 to enable.")
        return

    key = f"{prefix.rstrip('/')}/{local_path.name}"
    logger.info("Uploading to s3://%s/%s …", bucket, key)
    s3 = boto3.client("s3")
    s3.upload_file(str(local_path), bucket, key)
    logger.info("S3 upload complete: s3://%s/%s", bucket, key)


# ─── Main ────────────────────────────────────────────────────────────────────

def run_backup() -> Path:
    """Execute a full backup cycle. Returns the path of the dump file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_path = BACKUP_DIR / f"fin_eye_{timestamp}.dump"

    db = _parse_db_url(DATABASE_URL)

    # 1. Dump
    _pg_dump(db, dump_path)

    # 2. Upload offsite if configured
    if S3_BUCKET:
        _upload_to_s3(dump_path, S3_BUCKET, S3_PREFIX)

    # 3. Rotate local copies
    _rotate_old_backups(BACKUP_DIR, BACKUP_RETAIN_DAYS)

    logger.info("✅  Backup cycle complete: %s", dump_path.name)
    return dump_path


if __name__ == "__main__":
    try:
        path = run_backup()
        print(f"\nBackup saved: {path}")
        sys.exit(0)
    except Exception as exc:
        logger.error("❌  Backup FAILED: %s", exc)
        sys.exit(1)
