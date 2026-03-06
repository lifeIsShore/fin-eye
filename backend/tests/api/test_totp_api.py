"""
tests/api/test_totp_api.py

Test suite for CORE-SEC-01: Two-Factor Authentication (TOTP).

Coverage:
  - GET  /auth/2fa/status        — returns totp_enabled for current user
  - POST /auth/2fa/setup         — generates secret + URI; does NOT activate 2FA yet
  - POST /auth/2fa/enable        — wrong code → 400; correct code → 2FA active
  - POST /auth/2fa/disable       — wrong code → 400; correct code → 2FA disabled
  - POST /auth/login             — returns totp_required + pending_token when 2FA is on
  - POST /auth/2fa/verify        — wrong code → 401; correct code → full tokens issued
  - Security invariants:
      - Cannot enable 2FA twice
      - Cannot disable when not enabled
      - pending_token is invalid for /auth/me (type mismatch guard)
      - Expired/garbage pending_token → 401 on verify
"""

from __future__ import annotations

import pytest
import pyotp
from httpx import AsyncClient


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _get_totp_secret_for_user(client: AsyncClient, headers: dict) -> str:
    """
    Run the setup phase and return the plaintext TOTP secret.
    Does NOT enable 2FA.
    """
    res = await client.post("/api/v1/auth/2fa/setup", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "secret" in body
    assert "uri" in body
    assert body["uri"].startswith("otpauth://totp/")
    return body["secret"]


def _generate_valid_code(secret: str) -> str:
    """Generate the current valid TOTP code for a given secret."""
    return pyotp.TOTP(secret).now()


# ─── Status ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2fa_status_default_disabled(client: AsyncClient, auth_headers: dict) -> None:
    res = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["totp_enabled"] is False


@pytest.mark.asyncio
async def test_2fa_status_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/2fa/status")
    assert res.status_code == 401


# ─── Setup ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2fa_setup_returns_secret_and_uri(client: AsyncClient, auth_headers: dict) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    assert len(secret) == 32  # pyotp default base32 length


@pytest.mark.asyncio
async def test_2fa_setup_does_not_enable_2fa(client: AsyncClient, auth_headers: dict) -> None:
    await _get_totp_secret_for_user(client, auth_headers)
    res = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert res.json()["totp_enabled"] is False


# ─── Enable ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2fa_enable_with_wrong_code_returns_400(client: AsyncClient, auth_headers: dict) -> None:
    await _get_totp_secret_for_user(client, auth_headers)
    res = await client.post("/api/v1/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_2fa_enable_with_correct_code_activates(client: AsyncClient, auth_headers: dict) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    res = await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["totp_enabled"] is True

    # Confirm via status
    status_res = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_res.json()["totp_enabled"] is True


@pytest.mark.asyncio
async def test_2fa_enable_twice_returns_400(client: AsyncClient, auth_headers: dict) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    # Try to setup + enable again
    res = await client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    assert res.status_code == 400  # already enabled


# ─── Disable ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2fa_disable_when_not_enabled_returns_400(client: AsyncClient, auth_headers: dict) -> None:
    res = await client.post("/api/v1/auth/2fa/disable", json={"code": "123456"}, headers=auth_headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_2fa_disable_with_wrong_code_returns_400(client: AsyncClient, auth_headers: dict) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    res = await client.post("/api/v1/auth/2fa/disable", json={"code": "000000"}, headers=auth_headers)
    assert res.status_code == 400

    # Confirm still enabled
    status_res = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_res.json()["totp_enabled"] is True


@pytest.mark.asyncio
async def test_2fa_disable_with_correct_code(client: AsyncClient, auth_headers: dict) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    # Disable with fresh code
    disable_code = _generate_valid_code(secret)
    res = await client.post("/api/v1/auth/2fa/disable", json={"code": disable_code}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["totp_enabled"] is False

    status_res = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_res.json()["totp_enabled"] is False


# ─── Login flow with 2FA ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_with_2fa_enabled_returns_pending_token(
    client: AsyncClient,
    auth_headers: dict,
    test_user_credentials: dict,  # fixture: {"email": ..., "password": ...}
) -> None:
    # Enable 2FA for the user
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    # Log in with correct password
    res = await client.post("/api/v1/auth/login", json=test_user_credentials)
    assert res.status_code == 200
    body = res.json()
    assert body["totp_required"] is True
    assert body["pending_token"] != ""
    assert body["access_token"] == ""   # not issued yet


@pytest.mark.asyncio
async def test_verify_2fa_with_wrong_code_returns_401(
    client: AsyncClient,
    auth_headers: dict,
    test_user_credentials: dict,
) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    login_res = await client.post("/api/v1/auth/login", json=test_user_credentials)
    pending = login_res.json()["pending_token"]

    res = await client.post("/api/v1/auth/2fa/verify", json={"pending_token": pending, "code": "000000"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_verify_2fa_with_correct_code_issues_tokens(
    client: AsyncClient,
    auth_headers: dict,
    test_user_credentials: dict,
) -> None:
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    login_res = await client.post("/api/v1/auth/login", json=test_user_credentials)
    pending = login_res.json()["pending_token"]

    verify_code = _generate_valid_code(secret)
    res = await client.post("/api/v1/auth/2fa/verify", json={"pending_token": pending, "code": verify_code})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"] != ""
    assert body["refresh_token"] != ""


@pytest.mark.asyncio
async def test_verify_with_garbage_pending_token_returns_401(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"pending_token": "not.a.real.token", "code": "123456"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_pending_token_cannot_be_used_as_access_token(
    client: AsyncClient,
    auth_headers: dict,
    test_user_credentials: dict,
) -> None:
    """A 2fa_pending JWT must not grant access to protected endpoints."""
    secret = await _get_totp_secret_for_user(client, auth_headers)
    code = _generate_valid_code(secret)
    await client.post("/api/v1/auth/2fa/enable", json={"code": code}, headers=auth_headers)

    login_res = await client.post("/api/v1/auth/login", json=test_user_credentials)
    pending = login_res.json()["pending_token"]

    # Try to use it as a Bearer token on /auth/me
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {pending}"})
    assert res.status_code == 401


# ─── Code format validation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enable_rejects_non_numeric_code(client: AsyncClient, auth_headers: dict) -> None:
    await _get_totp_secret_for_user(client, auth_headers)
    res = await client.post("/api/v1/auth/2fa/enable", json={"code": "abc123"}, headers=auth_headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_enable_rejects_wrong_length_code(client: AsyncClient, auth_headers: dict) -> None:
    await _get_totp_secret_for_user(client, auth_headers)
    res = await client.post("/api/v1/auth/2fa/enable", json={"code": "12345"}, headers=auth_headers)
    assert res.status_code == 422
