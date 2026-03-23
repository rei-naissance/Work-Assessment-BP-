"""
Integration tests for payment routes.

Covers: checkout session creation, Stripe webhook first delivery,
        webhook duplicate idempotency, invalid signature rejection,
        and verify-session endpoint.

Run with: pytest app/tests/test_payments.py -v
"""

import hashlib
import json
import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import stripe
from bson import ObjectId

from app.config import settings
from app.tests.conftest import make_access_token, make_stripe_webhook_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aabbccddeeff001122334455"
SESSION_ID = "cs_test_abc123"


def _auth_headers(user_id: str = USER_ID) -> dict:
    return {"Authorization": f"Bearer {make_access_token(user_id=user_id)}"}


def hmac_sha256(secret: str, payload: str) -> str:
    import hmac as _hmac
    return _hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# /api/payments/create-checkout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_checkout_unauthenticated(client):
    """Checkout requires authentication — returns 401 without a token."""
    resp = await client.post(
        "/api/payments/create-checkout",
        json={"tier": "standard"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_checkout_stripe_error(client, mock_db):
    """StripeError during session creation returns a 502 or 500."""
    mock_db.settings.find_one = AsyncMock(return_value=None)

    with patch(
        "stripe.checkout.Session.create",
        side_effect=stripe.StripeError("Stripe unavailable"),
    ):
        resp = await client.post(
            "/api/payments/create-checkout",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )

    assert resp.status_code in (400, 500, 502)


@pytest.mark.asyncio
async def test_create_checkout_invalid_tier(client, mock_db):
    """Non-existent tier returns 400."""
    mock_db.settings.find_one = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/payments/create-checkout",
        json={"tier": "ultra"},
        headers=_auth_headers(),
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_checkout_valid_tier(client, mock_db):
    """Valid tier returns a checkout URL from Stripe."""
    mock_db.settings.find_one = AsyncMock(return_value=None)

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test_fake"

    with patch("stripe.checkout.Session.create", return_value=fake_session) as mock_create:
        resp = await client.post(
            "/api/payments/create-checkout",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert "checkout_url" in resp.json()
    assert resp.json()["checkout_url"].startswith("https://")


@pytest.mark.asyncio
async def test_create_checkout_idempotency_key_is_deterministic(client, mock_db):
    """Two calls for the same user+tier+day produce the same idempotency key."""
    mock_db.settings.find_one = AsyncMock(return_value=None)
    captured_keys: list[str] = []

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test_fake"

    def capture_key(**kwargs):
        captured_keys.append(kwargs.get("idempotency_key", ""))
        return fake_session

    fixed_date = date(2026, 1, 15)
    with (
        patch("stripe.checkout.Session.create", side_effect=capture_key),
        patch("app.routes.payments.date") as mock_date,
    ):
        mock_date.today.return_value = fixed_date
        await client.post(
            "/api/payments/create-checkout",
            json={"tier": "premium"},
            headers=_auth_headers(),
        )
        await client.post(
            "/api/payments/create-checkout",
            json={"tier": "premium"},
            headers=_auth_headers(),
        )

    assert len(captured_keys) == 2
    assert captured_keys[0] == captured_keys[1], (
        "Idempotency keys must be identical for same user+tier+day"
    )


@pytest.mark.asyncio
async def test_create_checkout_different_tiers_different_keys(client, mock_db):
    """Different tiers produce different idempotency keys (no cross-tier collision)."""
    mock_db.settings.find_one = AsyncMock(return_value=None)
    captured_keys: list[str] = []

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/pay/cs_test_fake"

    def capture_key(**kwargs):
        captured_keys.append(kwargs.get("idempotency_key", ""))
        return fake_session

    with patch("stripe.checkout.Session.create", side_effect=capture_key):
        await client.post(
            "/api/payments/create-checkout",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )
        await client.post(
            "/api/payments/create-checkout",
            json={"tier": "premium"},
            headers=_auth_headers(),
        )

    assert len(captured_keys) == 2
    assert captured_keys[0] != captured_keys[1]


# ---------------------------------------------------------------------------
# /api/payments/webhook
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_webhook_first_delivery_creates_records(client, mock_db):
    """First webhook delivery inserts a payment receipt and updates the user."""
    mock_db.payments.find_one = AsyncMock(return_value=None)  # no existing record
    mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())
    mock_db.users.update_one = AsyncMock()

    payload = make_stripe_webhook_payload(session_id=SESSION_ID, user_id=USER_ID)
    ts = int(time.time())
    signed = f"{ts}.{payload.decode()}"
    sig = hmac_sha256(settings.stripe_webhook_secret or "test_secret", signed)
    headers = {"stripe-signature": f"t={ts},v1={sig}"}

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": SESSION_ID,
                "payment_status": "paid",
                "payment_intent": "pi_test",
                "amount_total": 5900,
                "currency": "usd",
                "customer_email": "test@example.com",
                "metadata": {"user_id": USER_ID, "tier": "standard"},
            }
        },
    }

    with (
        patch("stripe.Webhook.construct_event", return_value=fake_event),
        patch.object(settings, "stripe_webhook_secret", "test_secret"),
    ):
        resp = await client.post("/api/payments/webhook", content=payload, headers=headers)

    assert resp.status_code == 200
    mock_db.payments.insert_one.assert_called_once()
    mock_db.users.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_duplicate_delivery_is_idempotent(client, mock_db):
    """Second delivery of the same webhook event is silently skipped."""
    existing_record = {"_id": ObjectId(), "stripe_session_id": SESSION_ID, "status": "completed"}
    mock_db.payments.find_one = AsyncMock(return_value=existing_record)

    payload = make_stripe_webhook_payload(session_id=SESSION_ID, user_id=USER_ID)

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": SESSION_ID,
                "payment_status": "paid",
                "payment_intent": "pi_test",
                "amount_total": 5900,
                "currency": "usd",
                "customer_email": "test@example.com",
                "metadata": {"user_id": USER_ID, "tier": "standard"},
            }
        },
    }

    ts = int(time.time())
    signed = f"{ts}.{payload.decode()}"
    sig = hmac_sha256("test_secret", signed)
    headers = {"stripe-signature": f"t={ts},v1={sig}"}

    with (
        patch("stripe.Webhook.construct_event", return_value=fake_event),
        patch.object(settings, "stripe_webhook_secret", "test_secret"),
    ):
        resp = await client.post("/api/payments/webhook", content=payload, headers=headers)

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    # Must NOT insert a second payment record
    mock_db.payments.insert_one.assert_not_called()
    mock_db.users.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_invalid_signature_returns_400(client, mock_db):
    """Webhook with an invalid Stripe signature is rejected."""
    payload = make_stripe_webhook_payload()

    with patch.object(settings, "stripe_webhook_secret", "test_secret"):
        resp = await client.post(
            "/api/payments/webhook",
            content=payload,
            headers={"stripe-signature": "t=0,v1=badsig"},
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_ignores_non_checkout_events(client, mock_db):
    """Events other than checkout.session.completed are acknowledged but not processed."""
    payload = b'{"id":"evt_other","type":"payment_intent.created","data":{"object":{}}}'

    fake_event = {
        "type": "payment_intent.created",
        "data": {"object": {}},
    }

    with (
        patch("stripe.Webhook.construct_event", return_value=fake_event),
        patch.object(settings, "stripe_webhook_secret", "test_secret"),
    ):
        resp = await client.post("/api/payments/webhook", content=payload)

    assert resp.status_code == 200
    mock_db.payments.insert_one.assert_not_called()


# ---------------------------------------------------------------------------
# /api/payments/pricing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pricing_returns_prices(client, mock_db):
    """Pricing endpoint returns standard and premium prices."""
    mock_db.settings.find_one = AsyncMock(return_value=None)

    resp = await client.get("/api/payments/pricing")

    assert resp.status_code == 200
    body = resp.json()
    assert "prices" in body
    assert "standard" in body["prices"]
    assert "premium" in body["prices"]
    assert body["prices"]["standard"] > 0
    assert body["prices"]["premium"] > 0
