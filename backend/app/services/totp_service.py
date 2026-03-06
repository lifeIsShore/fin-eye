"""
app/services/totp_service.py

TOTP-based Two-Factor Authentication service (CORE-SEC-01).

Responsibilities:
  - Generate a new TOTP secret for a user
  - Build the otpauth:// URI for QR code generation
  - Verify a user-supplied TOTP code (with ±1 window for clock skew)
  - Encrypt/decrypt the TOTP secret at rest using Fernet symmetric encryption
  - Enable and disable 2FA for a user

Security design:
  - TOTP secret is never stored in plaintext. The DB column holds a
    Fernet ciphertext. The key lives in settings.totp_encryption_key.
  - If TOTP_ENCRYPTION_KEY is empty (dev/test), the secret is stored
    in plaintext with a warning. Production deployments must set this.
  - We use pyotp's default (SHA1, 6 digits, 30-second window) which is
    compatible with Google Authenticator, Authy, and 1Password.
  - Verification uses a ±1 interval window (valid_window=1) to tolerate
    up to ±30 seconds of clock drift between the server and the user's device.

Dependencies:
  - pyotp      (pip install pyotp)
  - cryptography (pip install cryptography)  — already in requirements for Fernet
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Encryption helpers ───────────────────────────────────────────────────────

def _get_fernet() -> Optional[Fernet]:
    """
    Return a Fernet instance if TOTP_ENCRYPTION_KEY is configured.
    Returns None in dev when the key is empty (plaintext fallback).
    """
    key = settings.totp_encryption_key
    if not key:
        logger.warning(
            "TOTP_ENCRYPTION_KEY is not set — TOTP secrets will be stored in plaintext. "
            "This is insecure. Set TOTP_ENCRYPTION_KEY in production."
        )
        return None
    try:
        return Fernet(key.encode())
    except Exception as exc:
        logger.error("Invalid TOTP_ENCRYPTION_KEY: %s", exc)
        return None


def _encrypt_secret(plaintext_secret: str) -> str:
    """Encrypt a TOTP secret for DB storage. Falls back to plaintext if key is unset."""
    fernet = _get_fernet()
    if fernet is None:
        return plaintext_secret  # plaintext fallback for dev
    return fernet.encrypt(plaintext_secret.encode()).decode()


def _decrypt_secret(stored_secret: str) -> str:
    """Decrypt a stored TOTP secret. Falls back to treating it as plaintext."""
    fernet = _get_fernet()
    if fernet is None:
        return stored_secret  # plaintext fallback for dev
    try:
        return fernet.decrypt(stored_secret.encode()).decode()
    except InvalidToken:
        # This can happen if the encryption key changed. Log loudly.
        logger.error(
            "Failed to decrypt TOTP secret — TOTP_ENCRYPTION_KEY may have changed. "
            "This user's 2FA will not work until their secret is regenerated."
        )
        raise ValueError("Unable to decrypt 2FA secret. Please contact support.")


# ─── TOTP operations ──────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a fresh 32-character base32 TOTP secret."""
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, user_email: str) -> str:
    """
    Build the otpauth:// URI for QR code generation.

    Example output:
      otpauth://totp/Fin-Eye:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Fin-Eye

    This URI is what gets encoded into the QR code the user scans.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user_email,
        issuer_name=settings.totp_issuer_name,
    )


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against the given secret.
    Uses valid_window=1 to accept codes from the previous and next 30-second window,
    giving a total valid window of 90 seconds to handle clock drift.
    """
    if not code or not code.strip().isdigit():
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=1)


# ─── High-level user operations ───────────────────────────────────────────────

async def begin_totp_setup(
    db: AsyncSession,
    user: User,
) -> dict[str, str]:
    """
    Phase 1 of 2FA setup: generate a new TOTP secret, store it (encrypted,
    but NOT yet enabled), and return the provisioning URI for QR generation.

    The user must then call complete_totp_setup() with a valid code to activate.
    This two-phase approach ensures we never enable 2FA if the user can't
    actually read the secret from their authenticator app.

    Returns: {"secret": <plaintext>, "uri": <otpauth://...>}
    """
    raw_secret = generate_totp_secret()
    uri = build_provisioning_uri(raw_secret, user.email)

    # Store encrypted secret (totp_enabled stays False until confirmed)
    user.totp_secret = _encrypt_secret(raw_secret)
    await db.flush()

    logger.info("TOTP setup begun for user_id=%s", user.id)
    return {"secret": raw_secret, "uri": uri}


async def complete_totp_setup(
    db: AsyncSession,
    user: User,
    code: str,
) -> bool:
    """
    Phase 2 of 2FA setup: verify the user's first TOTP code.
    If valid, set totp_enabled=True and commit.

    Returns True on success, False if code is wrong or no secret is stored.
    """
    if not user.totp_secret:
        logger.warning("complete_totp_setup called with no totp_secret for user_id=%s", user.id)
        return False

    try:
        raw_secret = _decrypt_secret(user.totp_secret)
    except ValueError:
        return False

    if not verify_totp_code(raw_secret, code):
        logger.info("TOTP enable failed — wrong code for user_id=%s", user.id)
        return False

    user.totp_enabled = True
    await db.flush()
    logger.info("2FA enabled for user_id=%s", user.id)
    return True


async def disable_totp(
    db: AsyncSession,
    user: User,
    code: str,
) -> bool:
    """
    Disable 2FA for a user after verifying a valid TOTP code.
    Clears totp_secret and sets totp_enabled=False.

    We require a valid code (not a password) so that an attacker who somehow
    obtains the user's password cannot silently disable 2FA.

    Returns True on success, False if code is wrong.
    """
    if not user.totp_enabled or not user.totp_secret:
        return False

    try:
        raw_secret = _decrypt_secret(user.totp_secret)
    except ValueError:
        return False

    if not verify_totp_code(raw_secret, code):
        logger.info("TOTP disable failed — wrong code for user_id=%s", user.id)
        return False

    user.totp_secret = None
    user.totp_enabled = False
    await db.flush()
    logger.info("2FA disabled for user_id=%s", user.id)
    return True


def check_totp_for_login(user: User, code: str) -> bool:
    """
    Verify a TOTP code during the login flow.
    Called synchronously (no DB write) — just validates the code.
    Returns True if valid, False otherwise.
    """
    if not user.totp_enabled or not user.totp_secret:
        return False
    try:
        raw_secret = _decrypt_secret(user.totp_secret)
    except ValueError:
        return False
    return verify_totp_code(raw_secret, code)
