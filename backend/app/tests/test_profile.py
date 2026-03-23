"""Integration tests for profile routes.

Covers: get, save, completeness, readiness, export, delete account,
        messages (list, reply, mark-read).

Run with: pytest app/tests/test_profile.py -v
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from bson import ObjectId

from app.tests.conftest import FakeCursor, make_access_token

USER_ID = "aabbccddeeff001122334455"


def _auth_headers(user_id: str = USER_ID) -> dict:
    return {"Authorization": f"Bearer {make_access_token(user_id=user_id)}"}


def _profile_doc(user_id: str = USER_ID) -> dict:
    return {
        "_id": ObjectId(),
        "user_id": user_id,
        "home_identity": {
            "address_line1": "123 Main St",
            "city": "Miami",
            "state": "FL",
            "zip_code": "33101",
            "home_type": "single_family",
        },
    }


def _user_doc(user_id: str = USER_ID) -> dict:
    return {
        "_id": ObjectId(user_id),
        "email": "test@example.com",
        "created_at": datetime.utcnow(),
        "purchased_tier": "standard",
        "stripe_session_id": "cs_test_abc",
    }


# ---------------------------------------------------------------------------
# GET /api/profile/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get("/api/profile/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_returns_default_when_none_exists(client, mock_db):
    """Returns an empty default profile when the user has not saved one yet."""
    mock_db.profiles.find_one = AsyncMock(return_value=None)
    mock_db.users.find_one = AsyncMock(return_value=None)

    resp = await client.get("/api/profile/", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER_ID


@pytest.mark.asyncio
async def test_get_profile_returns_existing(client, mock_db):
    """Returns the stored profile including purchase metadata."""
    mock_db.profiles.find_one = AsyncMock(return_value=_profile_doc())
    mock_db.users.find_one = AsyncMock(return_value=_user_doc())

    with patch("app.routes.profile.decrypt_profile_fields"):
        resp = await client.get("/api/profile/", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER_ID
    assert body["purchased_tier"] == "standard"


@pytest.mark.asyncio
async def test_get_profile_includes_purchase_meta(client, mock_db):
    """Purchase metadata from the user record is included in the profile response."""
    mock_db.profiles.find_one = AsyncMock(return_value=_profile_doc())
    mock_db.users.find_one = AsyncMock(return_value=_user_doc())

    with patch("app.routes.profile.decrypt_profile_fields"):
        resp = await client.get("/api/profile/", headers=_auth_headers())

    body = resp.json()
    assert "purchased_tier" in body
    assert "stripe_session_id" in body


# ---------------------------------------------------------------------------
# PUT /api/profile/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_profile_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.put("/api/profile/", json={"user_id": USER_ID})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_save_profile_success(client, mock_db):
    """Saves profile with upsert and returns success message."""
    mock_db.profiles.update_one = AsyncMock()

    with patch("app.routes.profile.encrypt_profile_fields"):
        resp = await client.put(
            "/api/profile/",
            json={"user_id": USER_ID},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["message"] == "Profile saved"
    mock_db.profiles.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_save_profile_sets_user_id_from_token(client, mock_db):
    """The user_id in the saved doc comes from the token, not the request body."""
    captured = {}

    async def capture_update(filter_, update, **kwargs):
        captured["filter"] = filter_
        return MagicMock(modified_count=1)

    mock_db.profiles.update_one = capture_update

    with patch("app.routes.profile.encrypt_profile_fields"):
        await client.put(
            "/api/profile/",
            json={"user_id": "should-be-ignored"},
            headers=_auth_headers(),
        )

    assert captured["filter"]["user_id"] == USER_ID


# ---------------------------------------------------------------------------
# GET /api/profile/completeness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_completeness_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get("/api/profile/completeness")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_completeness_no_profile(client, mock_db):
    """Returns zero score and can_generate=False when no profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=None)

    resp = await client.get("/api/profile/completeness", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] == 0
    assert body["can_generate"] is False
    assert len(body["blocking_issues"]) > 0


@pytest.mark.asyncio
async def test_completeness_with_profile(client, mock_db):
    """Returns scored completeness report when profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=_profile_doc())

    resp = await client.get("/api/profile/completeness", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert "overall_score" in body
    assert "can_generate" in body
    assert "sections" in body
    assert isinstance(body["overall_score"], (int, float))


# ---------------------------------------------------------------------------
# GET /api/profile/readiness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_readiness_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get("/api/profile/readiness")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_readiness_no_profile(client, mock_db):
    """Returns empty readiness report when no profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=None)

    resp = await client.get("/api/profile/readiness", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] == 0
    assert body["can_generate"] is False


@pytest.mark.asyncio
async def test_readiness_with_profile(client, mock_db):
    """Returns goal-aware readiness report when profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=_profile_doc())

    with patch("app.routes.profile.decrypt_profile_fields"):
        resp = await client.get("/api/profile/readiness", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert "overall_score" in body
    assert "goal_reports" in body
    assert "sections" in body
    assert "active_goals" in body


# ---------------------------------------------------------------------------
# GET /api/profile/export
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get("/api/profile/export")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_returns_all_user_data(client, mock_db):
    """Returns JSON export with user, profile, binders, and payments."""
    mock_db.users.find_one = AsyncMock(return_value=_user_doc())
    mock_db.profiles.find_one = AsyncMock(return_value=None)
    mock_db.binders.find = MagicMock(return_value=FakeCursor([]))
    mock_db.payments.find = MagicMock(return_value=FakeCursor([]))

    resp = await client.get("/api/profile/export", headers=_auth_headers())

    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.json()
    assert "user" in body
    assert "profile" in body
    assert "binders" in body
    assert "payments" in body
    assert "export_date" in body


@pytest.mark.asyncio
async def test_export_includes_binders_and_payments(client, mock_db):
    """Binders and payment records are included in the export."""
    binder_doc = {
        "_id": ObjectId(),
        "user_id": USER_ID,
        "tier": "standard",
        "status": "ready",
        "pdf_path": "/data/test.pdf",
        "sitter_packet_path": "/data/test_sitter.pdf",
        "fill_in_checklist_path": "/data/test_checklist.pdf",
        "created_at": datetime.utcnow().isoformat(),
    }
    payment_doc = {
        "_id": ObjectId(),
        "user_id": USER_ID,
        "amount": 5900,
        "status": "completed",
    }

    mock_db.users.find_one = AsyncMock(return_value=_user_doc())
    mock_db.profiles.find_one = AsyncMock(return_value=None)
    mock_db.binders.find = MagicMock(return_value=FakeCursor([binder_doc]))
    mock_db.payments.find = MagicMock(return_value=FakeCursor([payment_doc]))

    resp = await client.get("/api/profile/export", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["binders"]) == 1
    assert len(body["payments"]) == 1
    # All local filesystem paths must be stripped from the export
    binder = body["binders"][0]
    assert "pdf_path" not in binder
    assert "sitter_packet_path" not in binder
    assert "fill_in_checklist_path" not in binder


# ---------------------------------------------------------------------------
# DELETE /api/profile/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_account_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.delete("/api/profile/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_removes_all_data(client, mock_db):
    """Deletes binders, profile, payments, and user record."""
    mock_db.binders.find = MagicMock(return_value=FakeCursor([]))
    mock_db.binders.delete_many = AsyncMock()
    mock_db.profiles.delete_one = AsyncMock()
    mock_db.payments.delete_many = AsyncMock()
    mock_db.users.delete_one = AsyncMock()

    resp = await client.delete("/api/profile/", headers=_auth_headers())

    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()
    mock_db.binders.delete_many.assert_called_once()
    mock_db.profiles.delete_one.assert_called_once()
    mock_db.payments.delete_many.assert_called_once()
    mock_db.users.delete_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_account_with_binder_pdfs(client, mock_db):
    """Calls secure_delete on all three PDF paths found in a binder document."""
    with (
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f1,
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f2,
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f3,
    ):
        pdf_path = f1.name
        sitter_path = f2.name
        checklist_path = f3.name

    try:
        binder_with_pdfs = {
            "_id": ObjectId(),
            "user_id": USER_ID,
            "pdf_path": pdf_path,
            "sitter_packet_path": sitter_path,
            "fill_in_checklist_path": checklist_path,
        }
        mock_db.binders.find = MagicMock(return_value=FakeCursor([binder_with_pdfs]))
        mock_db.binders.delete_many = AsyncMock()
        mock_db.profiles.delete_one = AsyncMock()
        mock_db.payments.delete_many = AsyncMock()
        mock_db.users.delete_one = AsyncMock()

        with patch("app.routes.profile.secure_delete") as mock_secure_delete:
            resp = await client.delete("/api/profile/", headers=_auth_headers())

        assert resp.status_code == 200
        mock_secure_delete.assert_has_calls([
            call(pdf_path),
            call(sitter_path),
            call(checklist_path),
        ], any_order=True)
        assert mock_secure_delete.call_count == 3
    finally:
        for p in (pdf_path, sitter_path, checklist_path):
            if os.path.exists(p):
                os.unlink(p)


# ---------------------------------------------------------------------------
# GET /api/profile/messages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_messages_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get("/api/profile/messages")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_messages_no_orders(client, mock_db):
    """Returns empty list when user has no payment orders."""
    mock_db.payments.find = MagicMock(return_value=FakeCursor([]))

    resp = await client.get("/api/profile/messages", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_messages_with_orders(client, mock_db):
    """Returns messages for the user's orders."""
    payment_id = ObjectId()
    message_doc = {
        "_id": ObjectId(),
        "order_id": str(payment_id),
        "sender": "admin",
        "message": "Your binder is ready!",
        "read": False,
        "created_at": datetime.utcnow(),
    }

    mock_db.payments.find = MagicMock(return_value=FakeCursor([{"_id": payment_id}]))
    mock_db.order_messages.find = MagicMock(return_value=FakeCursor([message_doc]))

    resp = await client.get("/api/profile/messages", headers=_auth_headers())

    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 1
    assert result[0]["sender"] == "admin"
    assert result[0]["message"] == "Your binder is ready!"


# ---------------------------------------------------------------------------
# POST /api/profile/messages/{message_id}/reply
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reply_message_unauthenticated(client):
    """Returns 401 without an auth token."""
    msg_id = str(ObjectId())
    resp = await client.post(
        f"/api/profile/messages/{msg_id}/reply",
        json={"message": "Thanks!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reply_message_not_found(client, mock_db):
    """Returns 404 when message does not exist."""
    mock_db.order_messages.find_one = AsyncMock(return_value=None)

    msg_id = str(ObjectId())
    resp = await client.post(
        f"/api/profile/messages/{msg_id}/reply",
        json={"message": "Thanks!"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reply_message_unauthorized_order(client, mock_db):
    """Returns 403 when the message belongs to another user's order."""
    payment_id = ObjectId()
    message_doc = {
        "_id": ObjectId(),
        "order_id": str(payment_id),
        "sender": "admin",
        "message": "Hello",
    }
    mock_db.order_messages.find_one = AsyncMock(return_value=message_doc)
    mock_db.payments.find_one = AsyncMock(return_value=None)  # not this user's order

    msg_id = str(message_doc["_id"])
    resp = await client.post(
        f"/api/profile/messages/{msg_id}/reply",
        json={"message": "Thanks!"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reply_message_success(client, mock_db):
    """Creates a reply and marks the original as read."""
    payment_id = ObjectId()
    message_id = ObjectId()
    message_doc = {
        "_id": message_id,
        "order_id": str(payment_id),
        "sender": "admin",
        "message": "Hello",
    }
    payment_doc = {"_id": payment_id, "user_id": USER_ID}
    reply_id = ObjectId()

    mock_db.order_messages.find_one = AsyncMock(return_value=message_doc)
    mock_db.payments.find_one = AsyncMock(return_value=payment_doc)
    mock_db.order_messages.update_one = AsyncMock()
    mock_db.order_messages.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=reply_id)
    )

    resp = await client.post(
        f"/api/profile/messages/{str(message_id)}/reply",
        json={"message": "Thank you!"},
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    assert "id" in resp.json()
    mock_db.order_messages.update_one.assert_called_once()  # original marked read
    mock_db.order_messages.insert_one.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/profile/messages/{message_id}/read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_read_unauthenticated(client):
    """Returns 401 without an auth token."""
    msg_id = str(ObjectId())
    resp = await client.post(f"/api/profile/messages/{msg_id}/read")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mark_read_not_found(client, mock_db):
    """Returns 404 when message does not exist."""
    mock_db.order_messages.find_one = AsyncMock(return_value=None)

    msg_id = str(ObjectId())
    resp = await client.post(
        f"/api/profile/messages/{msg_id}/read",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_success(client, mock_db):
    """Marks a message as read when the user owns the order."""
    payment_id = ObjectId()
    message_id = ObjectId()
    message_doc = {"_id": message_id, "order_id": str(payment_id)}
    payment_doc = {"_id": payment_id, "user_id": USER_ID}

    mock_db.order_messages.find_one = AsyncMock(return_value=message_doc)
    mock_db.payments.find_one = AsyncMock(return_value=payment_doc)
    mock_db.order_messages.update_one = AsyncMock()

    resp = await client.post(
        f"/api/profile/messages/{str(message_id)}/read",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    mock_db.order_messages.update_one.assert_called_once()
