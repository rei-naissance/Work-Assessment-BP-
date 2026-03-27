"""Tests for the Redis-backed rate limit middleware.

Covers: Retry-After header presence, correct 429 status, response body structure.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.tests.conftest import make_access_token


# ---------------------------------------------------------------------------
# Retry-After header on 429 responses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_429_includes_retry_after_header(client, mock_db):
    """When rate limit is exceeded, the 429 response includes a Retry-After header."""
    # Patch _check_rate to always return (False, 42) — rate limited with 42s retry
    with patch("app.middleware.rate_limit._check_rate", new=AsyncMock(return_value=(False, 42))):
        resp = await client.post(
            "/api/auth/request-otp",
            json={"email": "test@example.com"},
        )

    assert resp.status_code == 429
    assert "retry-after" in resp.headers
    assert resp.headers["retry-after"] == "42"


@pytest.mark.asyncio
async def test_rate_limit_429_body_contains_retry_after(client, mock_db):
    """The 429 JSON body includes a retry_after field."""
    with patch("app.middleware.rate_limit._check_rate", new=AsyncMock(return_value=(False, 30))):
        resp = await client.post(
            "/api/auth/request-otp",
            json={"email": "test@example.com"},
        )

    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["retry_after"] == 30


@pytest.mark.asyncio
async def test_rate_limit_generation_path_429(client, mock_db):
    """Generation endpoint rate limit returns 429 with Retry-After."""
    token = make_access_token()

    with patch("app.middleware.rate_limit._check_rate", new=AsyncMock(return_value=(False, 55))):
        resp = await client.post(
            "/api/binders/generate",
            json={"tier": "standard"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "55"


@pytest.mark.asyncio
async def test_rate_limit_allows_when_under_limit(client, mock_db):
    """Requests under the limit pass through normally."""
    mock_db.pending_otps.replace_one = AsyncMock()

    # Explicitly mock _check_rate to return (allowed=True) so the test
    # is deterministic regardless of whether Redis is reachable.
    with patch("app.middleware.rate_limit._check_rate", new=AsyncMock(return_value=(True, 0))):
        resp = await client.post(
            "/api/auth/request-otp",
            json={"email": "test@example.com"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_api_path_429(client, mock_db):
    """General API rate limit returns 429 with Retry-After."""
    token = make_access_token()

    with patch("app.middleware.rate_limit._check_rate", new=AsyncMock(return_value=(False, 10))):
        resp = await client.get(
            "/api/profile/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 429
    assert resp.headers["retry-after"] == "10"
    assert resp.json()["retry_after"] == 10
