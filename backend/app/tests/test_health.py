"""Tests for health check endpoints.

Covers: basic liveness, detailed readiness with Redis + ARQ checks,
        degraded states when components are unavailable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Basic liveness probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_liveness_ok(client, mock_db):
    """Health endpoint returns ok when DB is reachable."""
    resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["db"] == "connected"


@pytest.mark.asyncio
async def test_health_liveness_db_down(client, mock_db):
    """Health endpoint returns 503 when DB is unreachable."""
    mock_db.command = AsyncMock(side_effect=Exception("Connection refused"))

    resp = await client.get("/api/health")

    assert resp.status_code == 503
    assert resp.json()["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# Detailed readiness probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_detailed_includes_redis(client, mock_db):
    """Detailed health check includes Redis status."""
    # Mock Redis ping to succeed
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        resp = await client.get("/api/health/detailed")

    body = resp.json()
    assert "redis" in body["components"]
    assert body["components"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_detailed_redis_down_degrades(client, mock_db):
    """When Redis is unreachable, status is degraded."""
    with patch("redis.asyncio.from_url", side_effect=Exception("Connection refused")):
        resp = await client.get("/api/health/detailed")

    body = resp.json()
    assert "redis" in body["components"]
    assert body["components"]["redis"].startswith("error:")
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_detailed_includes_arq_pool(client, mock_db):
    """Detailed health check reports ARQ pool status."""
    # The test client fixture sets app.state.arq_pool to a mock
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        resp = await client.get("/api/health/detailed")

    body = resp.json()
    assert "arq_pool" in body["components"]
    assert body["components"]["arq_pool"] == "connected"


@pytest.mark.asyncio
async def test_health_detailed_includes_disk_and_stripe(client, mock_db):
    """Detailed health check includes disk and Stripe status."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        resp = await client.get("/api/health/detailed")

    body = resp.json()
    assert "disk" in body["components"]
    assert "stripe" in body["components"]
