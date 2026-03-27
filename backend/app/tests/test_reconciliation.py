"""Tests for the payment reconciliation background job.

Covers: skipped when Stripe unconfigured, no-op when all synced,
        repair of missing payment records, error handling.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from app.tests.conftest import make_mock_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stripe_session(
    session_id: str = "cs_test_abc",
    user_id: str = "aabbccddeeff001122334455",
    tier: str = "standard",
    payment_status: str = "paid",
    amount_total: int = 5900,
) -> MagicMock:
    """Build a mock Stripe checkout session object."""
    session = MagicMock()
    session.id = session_id
    session.payment_status = payment_status
    session.payment_intent = f"pi_{session_id}"
    session.amount_total = amount_total
    session.currency = "usd"
    session.customer_email = "test@example.com"
    session.metadata = {"user_id": user_id, "tier": tier}
    return session


class FakeSessionList:
    """Mimics stripe.checkout.Session.list() with auto_paging_iter."""

    def __init__(self, sessions: list):
        self._sessions = sessions

    def auto_paging_iter(self):
        return iter(self._sessions)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reconciliation_skipped_when_stripe_not_configured():
    """Job returns skipped=True when Stripe key is empty."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    with patch("app.tasks.reconcile_payments.settings") as mock_settings:
        mock_settings.stripe_secret_key = ""
        result = await reconcile_payments_job({"db": MagicMock()})

    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_reconciliation_noop_when_all_synced():
    """No repairs needed when all Stripe sessions have local records."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    db = make_mock_db()
    # Local record exists for this session
    db.payments.find_one = AsyncMock(return_value={"_id": ObjectId(), "stripe_session_id": "cs_test_abc"})

    sessions = [_make_stripe_session(session_id="cs_test_abc")]

    with (
        patch("app.tasks.reconcile_payments.settings") as mock_settings,
        patch("stripe.checkout.Session.list", return_value=FakeSessionList(sessions)),
    ):
        mock_settings.stripe_secret_key = "sk_test_fake"
        result = await reconcile_payments_job({"db": db})

    assert result["checked"] == 1
    assert result["missing_locally"] == 0
    assert result["repaired"] == 0
    db.payments.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_reconciliation_repairs_missing_payment():
    """Missing local record is created and user is updated."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    db = make_mock_db()
    # No local record
    db.payments.find_one = AsyncMock(return_value=None)
    db.payments.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()

    sessions = [_make_stripe_session(session_id="cs_missing_123", user_id="aabbccddeeff001122334455")]

    with (
        patch("app.tasks.reconcile_payments.settings") as mock_settings,
        patch("stripe.checkout.Session.list", return_value=FakeSessionList(sessions)),
    ):
        mock_settings.stripe_secret_key = "sk_test_fake"
        result = await reconcile_payments_job({"db": db})

    assert result["checked"] == 1
    assert result["missing_locally"] == 1
    assert result["repaired"] == 1

    # Verify payment record was inserted
    db.payments.insert_one.assert_called_once()
    inserted = db.payments.insert_one.call_args[0][0]
    assert inserted["stripe_session_id"] == "cs_missing_123"
    assert inserted["reconciled"] is True
    assert inserted["status"] == "completed"

    # Verify user was updated
    db.users.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_reconciliation_skips_unpaid_sessions():
    """Sessions that aren't paid are skipped (no repair attempt)."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    db = make_mock_db()
    sessions = [_make_stripe_session(payment_status="unpaid")]

    with (
        patch("app.tasks.reconcile_payments.settings") as mock_settings,
        patch("stripe.checkout.Session.list", return_value=FakeSessionList(sessions)),
    ):
        mock_settings.stripe_secret_key = "sk_test_fake"
        result = await reconcile_payments_job({"db": db})

    assert result["checked"] == 1
    assert result["missing_locally"] == 0
    db.payments.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_reconciliation_skips_sessions_without_user_id():
    """Sessions without user_id in metadata are skipped."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    db = make_mock_db()
    session = _make_stripe_session()
    session.metadata = {}  # no user_id

    with (
        patch("app.tasks.reconcile_payments.settings") as mock_settings,
        patch("stripe.checkout.Session.list", return_value=FakeSessionList([session])),
    ):
        mock_settings.stripe_secret_key = "sk_test_fake"
        result = await reconcile_payments_job({"db": db})

    assert result["checked"] == 1
    assert result["missing_locally"] == 0


@pytest.mark.asyncio
async def test_reconciliation_handles_db_error_gracefully():
    """DB error during repair is counted and logged, doesn't crash the job."""
    from app.tasks.reconcile_payments import reconcile_payments_job

    db = make_mock_db()
    db.payments.find_one = AsyncMock(return_value=None)
    db.payments.insert_one = AsyncMock(side_effect=Exception("DB write failed"))

    sessions = [_make_stripe_session(session_id="cs_error_123")]

    with (
        patch("app.tasks.reconcile_payments.settings") as mock_settings,
        patch("stripe.checkout.Session.list", return_value=FakeSessionList(sessions)),
    ):
        mock_settings.stripe_secret_key = "sk_test_fake"
        result = await reconcile_payments_job({"db": db})

    assert result["errors"] == 1
    assert result["repaired"] == 0
