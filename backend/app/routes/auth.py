import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Request, Response
from jose import jwt, JWTError

from app.config import settings
from app.models.user import OTPRequest, OTPVerify, TokenResponse
from app.errors import raise_error, ErrorCode, handle_db_error
from app.services.email import send_otp_email, send_welcome_email

router = APIRouter()
logger = logging.getLogger("home_binder.auth")

OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _create_access_token(user_id: str, email: str, is_admin: bool) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "is_admin": is_admin,
            "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _create_refresh_token(user_id: str) -> tuple[str, str]:
    """Create a refresh token JWT. Returns (token_string, jti)."""
    jti = uuid.uuid4().hex
    token = jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "jti": jti,
            "exp": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, jti


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.environment in ("production", "staging"),
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response):
    response.delete_cookie(key="refresh_token", path="/api/auth")


@router.post("/request-otp")
async def request_otp(body: OTPRequest, request: Request):
    body.email = body.email.strip().lower()
    code = f"{secrets.randbelow(1_000_000):06d}"

    db = request.app.state.db
    # Upsert: replace any existing OTP for this email
    try:
        await db.pending_otps.replace_one(
            {"email": body.email},
            {
                "email": body.email,
                "code_hash": _hash_otp(code),
                "attempts": 0,
                "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
                "created_at": datetime.utcnow(),
            },
            upsert=True,
        )
    except Exception as e:
        handle_db_error("storing OTP", e)

    if settings.environment == "development":
        logger.info("OTP for %s: %s", body.email, code)

    if settings.resend_api_key:
        success = send_otp_email(body.email, code)
        if not success:
            if settings.environment == "development":
                print(f"\n{'='*40}\n  OTP for {body.email}: {code}\n{'='*40}\n")
                return {"message": "OTP sent (check server console — email failed)"}
            raise_error(ErrorCode.EMAIL_FAILED, "Failed to send verification email. Please try again.")
    else:
        if settings.environment == "development":
            print(f"\n{'='*40}\n  OTP for {body.email}: {code}\n{'='*40}\n")
        else:
            raise_error(ErrorCode.INTERNAL, "Email service not configured")

    return {"message": "OTP sent to your email"}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: OTPVerify, request: Request, response: Response):
    body.email = body.email.strip().lower()
    db = request.app.state.db

    try:
        stored = await db.pending_otps.find_one({"email": body.email})
    except Exception as e:
        handle_db_error("looking up OTP", e)

    if not stored:
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired OTP")

    if datetime.utcnow() > stored["expires_at"]:
        await db.pending_otps.delete_one({"_id": stored["_id"]})
        raise_error(ErrorCode.TOKEN_EXPIRED, "OTP has expired. Please request a new code.")

    # Brute force protection: max attempts
    if stored.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        await db.pending_otps.delete_one({"_id": stored["_id"]})
        raise_error(ErrorCode.INVALID_TOKEN, "Too many attempts. Please request a new code.")

    if _hash_otp(body.code) != stored["code_hash"]:
        # Increment attempt counter
        await db.pending_otps.update_one(
            {"_id": stored["_id"]},
            {"$inc": {"attempts": 1}},
        )
        remaining = OTP_MAX_ATTEMPTS - stored.get("attempts", 0) - 1
        if remaining <= 0:
            await db.pending_otps.delete_one({"_id": stored["_id"]})
            raise_error(ErrorCode.INVALID_TOKEN, "Too many attempts. Please request a new code.")
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid OTP code")

    await db.pending_otps.delete_one({"_id": stored["_id"]})

    db = request.app.state.db
    is_new_user = False
    try:
        user = await db.users.find_one({"email": body.email})
        if not user:
            result = await db.users.insert_one({
                "email": body.email,
                "is_admin": False,
                "created_at": datetime.utcnow(),
            })
            user_id = str(result.inserted_id)
            is_admin = False
            is_new_user = True
        else:
            user_id = str(user["_id"])
            is_admin = user.get("is_admin", False)
    except Exception as e:
        handle_db_error("verifying OTP", e)

    if is_new_user:
        send_welcome_email(body.email)

    # Create tokens
    access_token = _create_access_token(user_id, body.email, is_admin)
    refresh_token, jti = _create_refresh_token(user_id)

    # Store refresh token in DB for revocation support
    try:
        await db.refresh_tokens.insert_one({
            "jti": jti,
            "user_id": user_id,
            "expires_at": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        handle_db_error("storing refresh token", e)

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    """Exchange a valid refresh token cookie for a new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise_error(ErrorCode.UNAUTHORIZED, "No refresh token")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        _clear_refresh_cookie(response)
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid token type")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    db = request.app.state.db

    # Verify refresh token exists in DB (not revoked)
    try:
        stored = await db.refresh_tokens.find_one({"jti": jti, "user_id": user_id})
    except Exception as e:
        handle_db_error("validating refresh token", e)

    if not stored:
        _clear_refresh_cookie(response)
        raise_error(ErrorCode.INVALID_TOKEN, "Refresh token has been revoked")

    # Get current user info
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        handle_db_error("fetching user for refresh", e)

    if not user:
        _clear_refresh_cookie(response)
        raise_error(ErrorCode.USER_NOT_FOUND, "User not found")

    # Rotate: delete old refresh token, issue new one
    try:
        await db.refresh_tokens.delete_one({"jti": jti})
    except Exception:
        pass

    new_refresh, new_jti = _create_refresh_token(user_id)
    try:
        await db.refresh_tokens.insert_one({
            "jti": new_jti,
            "user_id": user_id,
            "expires_at": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        handle_db_error("rotating refresh token", e)

    _set_refresh_cookie(response, new_refresh)

    access_token = _create_access_token(
        user_id,
        user.get("email", ""),
        user.get("is_admin", False),
    )
    return {"access_token": access_token}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Invalidate the refresh token and clear the cookie."""
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            jti = payload.get("jti")
            user_id = payload.get("sub")
            db = request.app.state.db
            await db.refresh_tokens.delete_one({"jti": jti, "user_id": user_id})
        except Exception:
            pass  # Best effort cleanup

    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.post("/dev-login")
async def dev_login(body: OTPRequest, request: Request, response: Response):
    """Skip OTP and log in directly. Development only."""
    if settings.environment != "development":
        raise_error(ErrorCode.FORBIDDEN, "Dev login is not available")

    db = request.app.state.db
    try:
        user = await db.users.find_one({"email": body.email})
    except Exception as e:
        handle_db_error("dev login", e)

    if not user:
        raise_error(ErrorCode.USER_NOT_FOUND, "No dev account for this email")

    user_id = str(user["_id"])
    is_admin = user.get("is_admin", False)

    access_token = _create_access_token(user_id, body.email, is_admin)
    refresh_token, jti = _create_refresh_token(user_id)

    try:
        await db.refresh_tokens.insert_one({
            "jti": jti,
            "user_id": user_id,
            "expires_at": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        handle_db_error("storing refresh token", e)

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)
