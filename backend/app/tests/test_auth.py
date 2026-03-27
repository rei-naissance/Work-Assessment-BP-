"""
Integration tests for authentication routes.

Covers: request-otp, verify-otp (success, invalid, expired, brute-force),
        token refresh, and logout.

Run with: pytest app/tests/test_auth.py -v
"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from jose import jwt

from app.config import settings
from app.tests.conftest import make_access_token, make_refresh_token


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _stored_otp(code: str = "123456", attempts: int = 0, expired: bool = False) -> dict:
    expires_at = (
        datetime.utcnow() - timedelta(minutes=1)
        if expired
        else datetime.utcnow() + timedelta(minutes=10)
    )
    return {
        "_id": ObjectId(),
        "email": "test@example.com",
        "code_hash": _hash_otp(code),
        "attempts": attempts,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# request-otp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_otp_valid_email(client, mock_db):
    """Valid email returns 200 with a confirmation message."""
    mock_db.pending_otps.replace_one = AsyncMock()

    resp = await client.post("/api/auth/request-otp", json={"email": "user@example.com"})

    assert resp.status_code == 200
    assert "message" in resp.json()
    mock_db.pending_otps.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_request_otp_invalid_email(client):
    """Malformed email is rejected with 422."""
    resp = await client.post("/api/auth/request-otp", json={"email": "not-an-email"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_request_otp_missing_email(client):
    """Missing email field is rejected with 422."""
    resp = await client.post("/api/auth/request-otp", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# verify-otp — success path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_otp_returns_access_token(client, mock_db):
    """Valid OTP returns a JWT access token and sets refresh cookie."""
    mock_db.pending_otps.find_one = AsyncMock(return_value=_stored_otp("654321"))
    mock_db.pending_otps.delete_one = AsyncMock()
    mock_db.users.find_one = AsyncMock(return_value=None)  # new user
    user_id = ObjectId()
    mock_db.users.insert_one = AsyncMock(return_value=type("R", (), {"inserted_id": user_id})())
    mock_db.refresh_tokens.insert_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "654321"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"

    # Refresh token cookie must be set
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_verify_otp_existing_user(client, mock_db):
    """Returning user gets a token without creating a new account."""
    user_id = ObjectId()
    mock_db.pending_otps.find_one = AsyncMock(return_value=_stored_otp("111111"))
    mock_db.pending_otps.delete_one = AsyncMock()
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": user_id, "email": "test@example.com", "is_admin": False,
    })
    mock_db.refresh_tokens.insert_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "111111"},
    )

    assert resp.status_code == 200
    mock_db.users.insert_one.assert_not_called()


# ---------------------------------------------------------------------------
# verify-otp — failure paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_otp_wrong_code(client, mock_db):
    """Wrong OTP returns 401."""
    mock_db.pending_otps.find_one = AsyncMock(return_value=_stored_otp("999999"))
    mock_db.pending_otps.update_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "000000"},
    )

    assert resp.status_code == 401
    mock_db.pending_otps.update_one.assert_called_once()  # attempt counter incremented


@pytest.mark.asyncio
async def test_verify_otp_no_pending_otp(client, mock_db):
    """No OTP on record returns 401."""
    mock_db.pending_otps.find_one = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "nobody@example.com", "code": "123456"},
    )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_otp_expired(client, mock_db):
    """Expired OTP returns 401."""
    mock_db.pending_otps.find_one = AsyncMock(return_value=_stored_otp("777777", expired=True))
    mock_db.pending_otps.delete_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "777777"},
    )

    assert resp.status_code == 401
    mock_db.pending_otps.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_verify_otp_max_attempts_exceeded(client, mock_db):
    """OTP with 5+ failed attempts is rejected and deleted."""
    mock_db.pending_otps.find_one = AsyncMock(
        return_value=_stored_otp("888888", attempts=5)
    )
    mock_db.pending_otps.delete_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "888888"},
    )

    assert resp.status_code == 401
    mock_db.pending_otps.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_verify_otp_exactly_four_attempts_still_allowed(client, mock_db):
    """OTP with exactly 4 prior failed attempts is NOT yet locked — correct code should succeed.

    Guards the off-by-one boundary: the lock fires at attempts >= 5,
    so attempts=4 must still pass through to code verification.
    """
    user_id = ObjectId()
    mock_db.pending_otps.find_one = AsyncMock(
        return_value=_stored_otp("444444", attempts=4)
    )
    mock_db.pending_otps.delete_one = AsyncMock()
    mock_db.users.find_one = AsyncMock(return_value=None)
    mock_db.users.insert_one = AsyncMock(return_value=type("R", (), {"inserted_id": user_id})())
    mock_db.refresh_tokens.insert_one = AsyncMock()

    resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "test@example.com", "code": "444444"},
    )

    # attempts=4 is still under the limit → correct code must succeed
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_valid_token(client, mock_db):
    """Valid refresh cookie returns a new access token."""
    user_id = "aabbccddeeff001122334455"
    jti = "jti-refresh-001"
    token = make_refresh_token(user_id=user_id, jti=jti)

    mock_db.refresh_tokens.find_one = AsyncMock(return_value={
        "_id": ObjectId(), "jti": jti, "user_id": user_id,
    })
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": ObjectId(user_id), "email": "test@example.com", "is_admin": False,
    })

    resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": token},
    )

    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_no_cookie_returns_401(client):
    """Missing refresh cookie returns 401."""
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_revoked_token_returns_401(client, mock_db):
    """Revoked (deleted from DB) refresh token returns 401."""
    token = make_refresh_token()
    mock_db.refresh_tokens.find_one = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": token},
    )

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_clears_refresh_cookie(client, mock_db):
    """Logout endpoint clears the refresh token cookie."""
    token = make_refresh_token()
    mock_db.refresh_tokens.find_one = AsyncMock(return_value={
        "_id": ObjectId(), "jti": "testjti0001",
    })
    mock_db.refresh_tokens.delete_one = AsyncMock()

    resp = await client.post(
        "/api/auth/logout",
        cookies={"refresh_token": token},
    )

    assert resp.status_code == 200
    # Cookie should be cleared (max-age=0 or deleted)
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token" in set_cookie
    # Refresh token must be deleted from the database
    mock_db.refresh_tokens.delete_one.assert_called_once()


# ---------------------------------------------------------------------------
# Protected endpoint access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_401(client):
    """Requests to protected routes without a token are rejected."""
    resp = await client.get("/api/profile/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client, mock_db):
    """Valid token grants access to protected routes."""
    user_id = "aabbccddeeff001122334455"
    token = make_access_token(user_id=user_id)
    mock_db.profiles.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {token}"},
    )

    # profiles.find_one returns None → route returns a default empty profile (200)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_with_expired_token(client):
    """Expired token is rejected with 401."""
    expired = make_access_token(expire_minutes=-1)

    resp = await client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert resp.status_code == 401
