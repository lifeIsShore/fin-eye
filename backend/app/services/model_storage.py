"""
app/services/model_storage.py
─────────────────────────────────────────────────────────────────────────────
SEC-08 — ML Model Artifacts to Cloud Storage (Cloudflare R2 / S3-compatible)

Uploads trained .joblib model artifacts to R2 after every successful training
run, and downloads them on startup for any model in the registry but missing
locally. This ensures model artifacts survive server restarts, deployments,
and ephemeral container environments.

Configuration (all optional — falls back to local-only if unset):
    R2_ACCOUNT_ID         — Cloudflare account ID
    R2_ACCESS_KEY_ID      — R2 API token access key
    R2_SECRET_ACCESS_KEY  — R2 API token secret key
    R2_BUCKET             — bucket name (default: fin-eye-models)
    R2_ENDPOINT           — https://{account_id}.r2.cloudflarestorage.com

Usage:
    from app.services.model_storage import upload_model, download_model_if_missing, sync_models_from_r2

    # After training — upload the .joblib to R2
    await upload_model(local_path)

    # On startup — download any missing artifacts
    await sync_models_from_r2()
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_s3_client():
    """
    Create a boto3 S3 client pointed at the Cloudflare R2 endpoint.
    Returns None if R2 is not configured (local-only mode).
    """
    try:
        import boto3  # noqa: PLC0415
    except ImportError:
        logger.debug("boto3 not installed — model cloud storage disabled")
        return None

    from app.config import get_settings  # noqa: PLC0415
    s = get_settings()

    if not all([s.r2_access_key_id, s.r2_secret_access_key, s.r2_endpoint]):
        logger.debug("R2 credentials not configured — model cloud storage disabled")
        return None

    return boto3.client(
        "s3",
        endpoint_url=s.r2_endpoint,
        aws_access_key_id=s.r2_access_key_id,
        aws_secret_access_key=s.r2_secret_access_key,
        region_name="auto",
    )


def _bucket() -> str:
    from app.config import get_settings  # noqa: PLC0415
    return get_settings().r2_bucket or "fin-eye-models"


def _remote_key(local_path: Path) -> str:
    """Use just the filename as the R2 object key."""
    return f"models/{local_path.name}"


# ── Upload ─────────────────────────────────────────────────────────────────────

async def upload_model(local_path: Path) -> bool:
    """
    Upload a .joblib artifact to R2 after successful training.
    Non-blocking — runs in executor. Returns True on success, False otherwise.
    Silently no-ops if R2 is not configured.
    """
    if not local_path.exists():
        logger.warning("upload_model: file not found: %s", local_path)
        return False

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload_sync, local_path)


def _upload_sync(local_path: Path) -> bool:
    client = _get_s3_client()
    if client is None:
        return False

    key = _remote_key(local_path)
    bucket = _bucket()
    try:
        client.upload_file(
            str(local_path),
            bucket,
            key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )
        size_mb = local_path.stat().st_size / 1_048_576
        logger.info("R2 upload: %s → s3://%s/%s (%.1f MB)", local_path.name, bucket, key, size_mb)
        return True
    except Exception as exc:
        logger.warning("R2 upload failed for %s: %s", local_path.name, exc)
        return False


# ── Download ───────────────────────────────────────────────────────────────────

async def download_model_if_missing(local_path: Path) -> bool:
    """
    Download a model from R2 if it's missing locally.
    Returns True if the file now exists locally (either was present or downloaded).
    """
    if local_path.exists():
        return True

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_sync, local_path)


def _download_sync(local_path: Path) -> bool:
    client = _get_s3_client()
    if client is None:
        return False

    key = _remote_key(local_path)
    bucket = _bucket()
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, str(local_path))
        size_mb = local_path.stat().st_size / 1_048_576
        logger.info("R2 download: s3://%s/%s → %s (%.1f MB)", bucket, key, local_path.name, size_mb)
        return True
    except Exception as exc:
        # Object may not exist yet (model never trained on this server)
        logger.debug("R2 download skipped for %s: %s", local_path.name, exc)
        return False


def model_exists_remote(artifact_name: str) -> bool:
    """Check whether a model artifact exists in R2 (sync, for startup use)."""
    client = _get_s3_client()
    if client is None:
        return False

    key = f"models/{artifact_name}"
    bucket = _bucket()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


# ── Startup sync ───────────────────────────────────────────────────────────────

async def sync_models_from_r2() -> dict:
    """
    On startup: read the model registry and download any .joblib files that are
    listed in the registry but missing from the local artifact directory.

    Called from main.py lifespan startup event (non-blocking via asyncio.create_task).

    Returns: { "checked": N, "downloaded": N, "missing": N, "errors": N }
    """
    import json  # noqa: PLC0415

    from app.services.ml_pipeline import ARTIFACT_DIR, REGISTRY_FILE  # noqa: PLC0415

    stats = {"checked": 0, "downloaded": 0, "missing": 0, "errors": 0}

    if not os.path.exists(REGISTRY_FILE):
        logger.debug("sync_models_from_r2: registry not found — skipping")
        return stats

    client = _get_s3_client()
    if client is None:
        logger.debug("sync_models_from_r2: R2 not configured — skipping")
        return stats

    # Read registry to find all known artifact files
    artifact_names: set[str] = set()
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    fname = rec.get("artifact_file", "")
                    if fname:
                        artifact_names.add(fname)
                except Exception:
                    continue
    except Exception as exc:
        logger.warning("sync_models_from_r2: could not read registry: %s", exc)
        return stats

    logger.info("sync_models_from_r2: checking %d registered artifacts...", len(artifact_names))

    loop = asyncio.get_event_loop()
    for fname in artifact_names:
        local_path = Path(ARTIFACT_DIR) / fname
        stats["checked"] += 1

        if local_path.exists():
            continue

        stats["missing"] += 1
        logger.info("sync_models_from_r2: %s missing locally — downloading from R2...", fname)

        ok = await loop.run_in_executor(None, _download_sync, local_path)
        if ok:
            stats["downloaded"] += 1
        else:
            stats["errors"] += 1

    logger.info(
        "sync_models_from_r2 complete: checked=%d downloaded=%d missing=%d errors=%d",
        stats["checked"], stats["downloaded"], stats["missing"], stats["errors"],
    )
    return stats
