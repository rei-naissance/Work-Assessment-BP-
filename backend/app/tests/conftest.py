"""
Shared test fixtures for BinderPro API integration tests.

Uses httpx.AsyncClient with ASGITransport so every test hits the real
FastAPI routing, middleware, and validation stack — only the external
I/O (MongoDB, email, Stripe) is mocked.
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings


# ---------------------------------------------------------------------------
# Async cursor helper (mimics motor AIOMotorCursor)
# ---------------------------------------------------------------------------

class FakeCursor:
    """Async iterator that mimics AIOMotorCursor with common chaining methods."""

    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._index = 0

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def allow_disk_use(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return list(self._docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._index]
        self._index += 1
        return doc


# ---------------------------------------------------------------------------
# Mock DB factory
# ---------------------------------------------------------------------------

def _make_collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
    col.replace_one = AsyncMock(return_value=MagicMock(modified_count=1, upserted_id=None))
    col.count_documents = AsyncMock(return_value=0)
    col.create_index = AsyncMock()
    col.find = MagicMock(return_value=FakeCursor([]))
    return col


def make_mock_db():
    db = MagicMock()
    db.command = AsyncMock(return_value={"ok": 1})
    for name in [
        "users", "pending_otps", "refresh_tokens", "binders",
        "payments", "profiles", "settings", "order_messages", "audit_logs", "feedback",
    ]:
        setattr(db, name, _make_collection())
    return db


# ---------------------------------------------------------------------------
# JWT helpers for tests
# ---------------------------------------------------------------------------

def make_access_token(
    user_id: str = "aabbccddeeff001122334455",
    email: str = "test@example.com",
    is_admin: bool = False,
    expire_minutes: int = 15,
) -> str:
    now = datetime.utcnow()
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "is_admin": is_admin,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=expire_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def make_refresh_token(
    user_id: str = "aabbccddeeff001122334455",
    jti: str = "testjti0001",
    expire_days: int = 7,
) -> str:
    now = datetime.utcnow()
    return jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "jti": jti,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(days=expire_days),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


# ---------------------------------------------------------------------------
# Stripe webhook helper
# ---------------------------------------------------------------------------

def make_stripe_webhook_payload(
    session_id: str = "cs_test_123",
    user_id: str = "aabbccddeeff001122334455",
    tier: str = "standard",
    payment_status: str = "paid",
) -> bytes:
    event = {
        "id": f"evt_{session_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": payment_status,
                "payment_intent": f"pi_{session_id}",
                "amount_total": 5900,
                "currency": "usd",
                "customer_email": "test@example.com",
                "metadata": {
                    "user_id": user_id,
                    "tier": tier,
                },
            }
        },
    }
    return json.dumps(event).encode()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    return make_mock_db()


@pytest_asyncio.fixture
async def client(mock_db):
    """
    ASGI test client with:
    - MongoDB replaced by an in-memory mock
    - All email functions no-op'ed
    - Environment forced to 'development' so OTP is logged, not emailed
    """
    # Mock ARQ pool: enqueue_job is a no-op in tests
    mock_arq_pool = MagicMock()
    mock_arq_pool.enqueue_job = AsyncMock(return_value=None)
    mock_arq_pool.close = AsyncMock()

    with (
        patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_motor_cls,
        patch("arq.create_pool", new=AsyncMock(return_value=mock_arq_pool)),
        # Note: resend_api_key="" means the real send_otp_email is never called
        # (auth.py guards on `if settings.resend_api_key`). This patch is a
        # safety net in case that guard is removed or bypassed.
        patch("app.services.email.send_otp_email", return_value=True),
        patch("app.services.email.send_welcome_email", return_value=True),
        patch("app.services.email.send_payment_confirmation", return_value=True),
        patch("app.services.email.send_binder_ready", return_value=True),
        patch("app.services.email.send_generation_failed", return_value=True),
        patch.object(settings, "environment", "development"),
        patch.object(settings, "resend_api_key", ""),  # no real email in tests
        patch.object(settings, "stripe_secret_key", "sk_test_fake"),
    ):
        mock_motor_instance = MagicMock()
        mock_motor_instance.get_default_database.return_value = mock_db
        mock_motor_cls.return_value = mock_motor_instance

        # Import app here so the lifespan uses the patched motor client
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            # Ensure the db and arq_pool state always point to our mocks
            app.state.db = mock_db
            app.state.arq_pool = mock_arq_pool
            yield c
