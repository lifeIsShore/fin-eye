"""
app/api/v1/auth.py

Authentication endpoints (Sprint 7 security hardening — SEC-03, SEC-04, SEC-05):

  POST /auth/register          — create account        [rate-limited: 5/min/IP]
  POST /auth/login             — get tokens            [rate-limited: 10/min/IP + lockout]
  POST /auth/logout            — revoke refresh token  [blacklists JTI in Redis]
  POST /auth/refresh           — rotate refresh token  [validates + rotates JTI]
  GET  /auth/me                — current user profile
  PATCH /auth/me               — update display name
  POST /auth/change-password   — change password

Two-Factor Authentication (CORE-SEC-01):
  POST /auth/2fa/setup         — generate TOTP secret + QR code URI
  POST /auth/2fa/enable        — confirm first TOTP code → activates 2FA
  POST /auth/2fa/disable       — verify TOTP code → disables 2FA
  POST /auth/2fa/verify        — exchange (pending_token + code) for full tokens  [rate-limited: 5/min/IP]
  GET  /auth/2fa/status        — check if 2FA is enabled

Security additions (todos-v3.md SEC-03, SEC-04, SEC-05):
  - Rate limiting on register/login/2fa-verify via Redis sliding-window counters
  - Account lockout after 10 failed logins in 15 min → 30-min lockout
  - Refresh tokens carry a JTI; /auth/logout blacklists the JTI
  - /auth/refresh rotates the JTI (old blacklisted, new issued)
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_2fa_pending_token,
    decode_token,
)
from app.db.database import get_db
from app.db.redis_client import get_redis
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
    update_streak,
)
from app.services.auth_security import (
    check_login_rate_limit,
    check_register_rate_limit,
    check_totp_rate_limit,
    check_account_lockout,
    record_failed_login,
    clear_failed_logins,
    blacklist_jti,
    is_jti_blacklisted,
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

# ── JTI TTL helper ────────────────────────────────────────────────────────────

def _refresh_ttl_seconds() -> int:
    from app.config import get_settings  # noqa: PLC0415
    s = get_settings()
    return int(timedelta(days=s.refresh_token_expire_days).total_seconds())


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    ref: Optional[str] = None,  # Sprint 50: referral code from ?ref=CODE
) -> User:
    # SEC-03: rate limit registrations per IP
    try:
        redis = get_redis()
        await check_register_rate_limit(request, redis)
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — fail-open

    try:
        user = await create_user(
            db,
            email=body.email,
            password=body.password,
            name=body.name,
            ref_code=ref,  # Sprint 50: link referrer
        )
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

    try:
        from app.services.onboarding_email_service import trigger_onboarding_welcome  # noqa: PLC0415
        await trigger_onboarding_welcome(db, user)
        await db.commit()
    except Exception:
        logger.warning("Email: failed to send welcome email for user_id=%s", user.id, exc_info=True)

    # SEC-07: Send email verification link
    try:
        from app.services.email_service import send_verification_email  # noqa: PLC0415
        if user.verification_token:
            await send_verification_email(user.email, user.verification_token)
    except Exception:
        logger.warning("Email: failed to send verification email for user_id=%s", user.id, exc_info=True)

    return user


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login — returns tokens, or a pending_token if 2FA is enabled",
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    redis = None
    try:
        redis = get_redis()
        # SEC-03: rate limit per IP
        await check_login_rate_limit(request, redis)
        # SEC-05: check if account is locked out before even touching DB
        await check_account_lockout(body.email, redis)
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — fail-open

    user = await authenticate_user(db, email=body.email, password=body.password)
    if not user:
        # SEC-05: record failed attempt
        if redis:
            await record_failed_login(body.email, redis)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful auth — clear fail counter
    if redis:
        await clear_failed_logins(body.email, redis)

    # ── 2FA gate ──────────────────────────────────────────────────────────────
    if user.totp_enabled:
        pending = create_2fa_pending_token(str(user.id))
        logger.info("Login step 1 (2FA required) for user_id=%s", user.id)
        return LoginResponse(
            access_token="",
            refresh_token="",
            totp_required=True,
            pending_token=pending,
        )

    # ── No 2FA — issue full tokens ────────────────────────────────────────────
    refresh_token, jti = create_refresh_token(str(user.id))

    # Sprint 49 — update login streak (non-fatal)
    try:
        update_streak(user)
    except Exception:
        pass

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
        refresh_token=refresh_token,
    )


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout — revoke the refresh token (blacklists its JTI)",
)
async def logout(body: RefreshRequest) -> None:
    """
    SEC-04: Blacklist the JTI of the provided refresh token.
    The access token expires on its own (short TTL).
    After calling this, the refresh token can no longer be used to get new tokens.
    """
    payload = decode_token(body.refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti")
        if jti:
            try:
                redis = get_redis()
                exp = payload.get("exp", 0)
                remaining = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
                await blacklist_jti(jti, remaining, redis)
                logger.info("Refresh token revoked (logout) — jti=%s", jti)
            except Exception as exc:
                logger.warning("Logout blacklist failed (non-fatal): %s", exc)
    # Always return 204 — don't leak whether the token was valid


# ─── Refresh ──────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token — validates JTI, issues new token pair",
)
async def refresh(body: RefreshRequest) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    jti = payload.get("jti")

    # SEC-04: reject blacklisted tokens (logged out or already rotated)
    if jti:
        try:
            redis = get_redis()
            if await is_jti_blacklisted(jti, redis):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked. Please log in again.",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # Redis unavailable — fail-open

    user_id: str = payload["sub"]

    # SEC-04: blacklist the old JTI and issue a new token with a fresh JTI
    if jti:
        try:
            redis = get_redis()
            exp = payload.get("exp", 0)
            remaining = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
            await blacklist_jti(jti, remaining, redis)
        except Exception:
            pass

    new_refresh_token, _new_jti = create_refresh_token(user_id)
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=new_refresh_token,
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
    summary="Update display name and preferences",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> User:
    return await update_user_name(
        db,
        current_user,
        name=body.name,
        default_symbol=body.default_symbol,
        risk_profile=body.risk_profile,
    )


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
        db, current_user,
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
)
async def enable_2fa(
    body: TotpVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TotpStatusResponse:
    if current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled.")
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
)
async def disable_2fa(
    body: TotpVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> TotpStatusResponse:
    if not current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled on this account.")
    ok = await disable_totp(db, current_user, code=body.code)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code.")
    await db.commit()
    logger.info("2FA deactivated for user_id=%s", current_user.id)
    return TotpStatusResponse(totp_enabled=False)


# ─── 2FA: Verify (login step 2) ───────────────────────────────────────────────

@router.post(
    "/2fa/verify",
    response_model=TokenResponse,
    summary="Login step 2: exchange pending_token + TOTP code for full tokens",
)
async def verify_2fa_login(
    request: Request,
    body: TotpLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # SEC-03: rate limit 2FA verify per IP
    try:
        redis = get_redis()
        await check_totp_rate_limit(request, redis)
    except HTTPException:
        raise
    except Exception:
        pass

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

    if not check_totp_for_login(user, body.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code.")

    refresh_token, _jti = create_refresh_token(str(user.id))

    # Sprint 49 — update login streak (non-fatal)
    try:
        update_streak(user)
    except Exception:
        pass

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
        refresh_token=refresh_token,
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
