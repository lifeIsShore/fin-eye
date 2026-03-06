"""
app/schemas/auth.py
Pydantic schemas for auth request/response payloads.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Register ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


# ── Login ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Token responses ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Profile update ────────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)


# ── Change password ─────────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


# ── Two-Factor Authentication (CORE-SEC-01) ───────────────────────────────────

class TotpSetupResponse(BaseModel):
    """
    Returned by POST /auth/2fa/setup.
    The frontend encodes `uri` as a QR code for the user to scan.
    The `secret` is shown as a manual entry fallback.
    """
    secret: str   # plaintext base32 — show as fallback for manual entry
    uri: str      # otpauth:// URI — encode this as a QR code


class TotpVerifyRequest(BaseModel):
    """Body for POST /auth/2fa/enable and POST /auth/2fa/disable."""
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("TOTP code must be 6 digits.")
        return v


class TotpLoginRequest(BaseModel):
    """
    POST /auth/2fa/verify — exchange a short-lived 2fa_pending token + TOTP code
    for full access + refresh tokens.
    """
    pending_token: str
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("TOTP code must be 6 digits.")
        return v


class TotpStatusResponse(BaseModel):
    totp_enabled: bool


# ── Login response — may require 2FA ─────────────────────────────────────────

class LoginResponse(BaseModel):
    """
    Returned by POST /auth/login.

    If totp_required=True the caller must POST to /auth/2fa/verify with
    the pending_token + their 6-digit code to receive full tokens.
    The access_token and refresh_token will be empty strings in this case.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    totp_required: bool = False
    pending_token: str = ""   # short-lived token for 2FA step; empty when totp_required=False


# ── User responses ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]
    is_verified: bool
    is_active: bool
    is_admin: bool
    subscription_tier: str
    totp_enabled: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
