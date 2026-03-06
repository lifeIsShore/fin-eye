"""
app/api/v1/auth.py

Authentication endpoints:
  POST /auth/register          — create account
  POST /auth/login             — get tokens (or 2fa_pending if 2FA enabled)
  POST /auth/refresh           — exchange refresh token for new access token
  GET  /auth/me                — return current user profile
  PATCH /auth/me               — update display name
  POST /auth/change-password   — change password (requires current password)

Two-Factor Authentication (CORE-SEC-01):
  POST /auth/2fa/setup         — generate TOTP secret + QR code URI
  POST /auth/2fa/enable        — confirm first TOTP code → activates 2FA
  POST /auth/2fa/disable       — verify TOTP code → disables 2FA
  POST /auth/2fa/verify        — exchange (pending_token + code) for full tokens
  GET  /auth/2fa/status        — check if 2FA is enabled for current user

Login flow with 2FA:
  1. Client POST /auth/login with email + password.
  2a. If 2FA not enabled: response has access_token + refresh_token (no change).
  2b. If 2FA enabled: response has totp_required=true + pending_token (5min TTL).
  3. Client prompts for 6-digit TOTP code.
  4. Client POST /auth/2fa/verify with { pending_token, code }.
  5. On success: response has access_token + refresh_token.
"""

import logging
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_2fa_pending_token,
    decode_token,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    TotpLoginRequest,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    change_user_password,
    create_user,
    get_user_by_id,
    update_user_name,
)
from app.services.totp_service import (
    begin_totp_setup,
    check_totp_for_login,
    complete_totp_setup,
    disable_totp,
)
from app.schemas.analytics_models import EventName

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user = await create_user(db, email=body.email, password=body.password, name=body.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    try:
        from app.services.analytics_service import record_event  # noqa: PLC0415
        await record_event(
            db,
            EventName.USER_SIGNED_UP,
            user_id=user.id,
            properties={"subscription_tier": user.subscription_tier},
        )
        await db.commit()
    except Exception:
        logger.warning("Analytics: failed to record user_signed_up", exc_info=True)

    # ── Trigger onboarding email sequence (CORE-EMAIL-01) ──────────────────
    try:
        from app.services.onboarding_email_service import trigger_onboarding_welcome  # noqa: PLC0415
        await trigger_onboarding_welcome(db, user)
        await db.commit()
    except Exception:
        logger.warning("Email: failed to send welcome email for user_id=%s", user.id, exc_info=True)

    return user


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login — returns tokens, or a pending_token if 2FA is enabled",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await authenticate_user(db, email=body.email, password=body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── 2FA gate ──────────────────────────────────────────────────────────────
    if user.totp_enabled:
        # Credentials are valid but 2FA is required.
        # Return a short-lived pending token — no access token yet.
        pending = create_2fa_pending_token(str(user.id))
        logger.info("Login step 1 (2FA required) for user_id=%s", user.id)
        return LoginResponse(
            access_token="",
            refresh_token="",
            totp_required=True,
            pending_token=pending,
        )

    # ── No 2FA — issue full tokens immediately ────────────────────────────────
    try:
        from app.services.analytics_service import record_event  # noqa: PLC0415
        await record_event(
            db,
            EventName.USER_LOGGED_IN,
            user_id=user.id,
            properties={"subscription_tier": user.subscription_tier},
        )
        await db.commit()
    except Exception:
        logger.warning("Analytics: failed to record user_logged_in", exc_info=True)

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ─── Refresh ──────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Get a new access token using a refresh token",
)
async def refresh(body: RefreshRequest) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    user_id: str = payload["sub"]
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


# ─── Me ───────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update display name",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> User:
    return await update_user_name(db, current_user, name=body.name)


# ─── Change password ──────────────────────────────────────────────────────────

@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password — requires current password for verification",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await change_user_password(
        db,
        current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )


# ─── 2FA: Setup ───────────────────────────────────────────────────────────────

@router.post(
    "/2fa/setup",
    response_model=TotpSetupResponse,
    summary="Phase 1: Generate a new TOTP secret and QR code URI",
    description=(
        "Generates a TOTP secret and returns an otpauth:// URI for QR code rendering. "
        "The secret is stored (encrypted) but 2FA is NOT enabled yet. "
        "The user must scan the QR code and then call POST /auth/2fa/enable with a valid code."
    ),
)
async def setup_2fa(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TotpSetupResponse:
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first before setting up again.",
        )
    result = await begin_totp_setup(db, current_user)
    await db.commit()
    return TotpSetupResponse(secret=result["secret"], uri=result["uri"])


# ─── 2FA: Enable ──────────────────────────────────────────────────────────────

@router.post(
    "/2fa/enable",
    response_model=TotpStatusResponse,
    summary="Phase 2: Confirm TOTP code to activate 2FA",
    description=(
        "Submit the 6-digit code from your authenticator app. "
        "If valid, 2FA is activated on your account. "
        "Future logins will require your password AND a TOTP code."
    ),
)
async def enable_2fa(
    body: TotpVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TotpStatusResponse:
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled.",
        )
    ok = await complete_totp_setup(db, current_user, code=body.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Make sure your authenticator app is synced.",
        )
    await db.commit()
    logger.info("2FA activated for user_id=%s", current_user.id)
    return TotpStatusResponse(totp_enabled=True)


# ─── 2FA: Disable ─────────────────────────────────────────────────────────────

@router.post(
    "/2fa/disable",
    response_model=TotpStatusResponse,
    summary="Disable 2FA — requires a valid TOTP code",
    description=(
        "Disables 2FA after verifying a valid TOTP code. "
        "Requiring a code (not just a password) prevents an attacker with a stolen "
        "password from silently disabling 2FA."
    ),
)
async def disable_2fa(
    body: TotpVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TotpStatusResponse:
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled on this account.",
        )
    ok = await disable_totp(db, current_user, code=body.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code.",
        )
    await db.commit()
    logger.info("2FA deactivated for user_id=%s", current_user.id)
    return TotpStatusResponse(totp_enabled=False)


# ─── 2FA: Verify (login step 2) ───────────────────────────────────────────────

@router.post(
    "/2fa/verify",
    response_model=TokenResponse,
    summary="Login step 2: exchange pending_token + TOTP code for full tokens",
    description=(
        "Called after POST /auth/login returns totp_required=true. "
        "Submit the pending_token from the login response and the 6-digit "
        "code from your authenticator app. Returns full access + refresh tokens."
    ),
)
async def verify_2fa_login(
    body: TotpLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Validate the pending token
    payload = decode_token(body.pending_token)
    if payload is None or payload.get("type") != "2fa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    try:
        user = await get_user_by_id(db, uuid.UUID(user_id_str))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Verify the TOTP code
    if not check_totp_for_login(user, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code.",
        )

    # Issue full tokens
    try:
        from app.services.analytics_service import record_event  # noqa: PLC0415
        await record_event(
            db,
            EventName.USER_LOGGED_IN,
            user_id=user.id,
            properties={"subscription_tier": user.subscription_tier, "totp": True},
        )
        await db.commit()
    except Exception:
        logger.warning("Analytics: failed to record user_logged_in (2FA)", exc_info=True)

    logger.info("2FA login complete for user_id=%s", user.id)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ─── 2FA: Status ──────────────────────────────────────────────────────────────

@router.get(
    "/2fa/status",
    response_model=TotpStatusResponse,
    summary="Check whether 2FA is enabled for the current user",
)
async def get_2fa_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> TotpStatusResponse:
    return TotpStatusResponse(totp_enabled=current_user.totp_enabled)
