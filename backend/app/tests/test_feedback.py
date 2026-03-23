"""Integration tests for feedback route.

Covers: anonymous submission, authenticated submission, field storage,
        and input validation (max lengths).

Run with: pytest app/tests/test_feedback.py -v
"""

from unittest.mock import AsyncMock

import pytest

from app.tests.conftest import make_access_token


# ---------------------------------------------------------------------------
# POST /api/feedback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_feedback_anonymous(client, mock_db):
    """Anonymous users can submit feedback without a token."""
    mock_db.feedback.insert_one = AsyncMock()

    resp = await client.post(
        "/api/feedback",
        json={"type": "bug", "message": "Something is broken on the dashboard"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_db.feedback.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_submit_feedback_authenticated(client, mock_db):
    """Authenticated users have their user_id captured in the feedback doc."""
    mock_db.feedback.insert_one = AsyncMock()
    token = make_access_token(user_id="aabbccddeeff001122334455", email="user@example.com")

    resp = await client.post(
        "/api/feedback",
        json={"type": "feedback", "message": "Love the new feature!", "page": "/dashboard"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    doc = mock_db.feedback.insert_one.call_args[0][0]
    assert doc["user_id"] == "aabbccddeeff001122334455"
    assert doc["user_email"] == "user@example.com"
    assert doc["page"] == "/dashboard"


@pytest.mark.asyncio
async def test_submit_feedback_stores_correct_fields(client, mock_db):
    """Feedback document contains all required fields with correct defaults."""
    mock_db.feedback.insert_one = AsyncMock()

    await client.post(
        "/api/feedback",
        json={"type": "question", "message": "How does billing work?"},
    )

    doc = mock_db.feedback.insert_one.call_args[0][0]
    assert doc["type"] == "question"
    assert doc["message"] == "How does billing work?"
    assert doc["status"] == "new"
    assert doc["user_id"] is None  # anonymous
    assert "created_at" in doc


@pytest.mark.asyncio
async def test_submit_feedback_page_is_optional(client, mock_db):
    """Page field is optional — omitting it is valid."""
    mock_db.feedback.insert_one = AsyncMock()

    resp = await client.post(
        "/api/feedback",
        json={"type": "bug", "message": "Bug report without page"},
    )

    assert resp.status_code == 200
    doc = mock_db.feedback.insert_one.call_args[0][0]
    assert doc["page"] is None


@pytest.mark.asyncio
async def test_submit_feedback_message_too_long(client, mock_db):
    """Rejects messages exceeding 5000 characters."""
    resp = await client.post(
        "/api/feedback",
        json={"type": "bug", "message": "x" * 5001},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_type_too_long(client, mock_db):
    """Rejects type fields exceeding 20 characters."""
    resp = await client.post(
        "/api/feedback",
        json={"type": "a" * 21, "message": "Some feedback"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_missing_required_fields(client, mock_db):
    """Rejects requests missing type or message."""
    resp = await client.post("/api/feedback", json={"type": "bug"})
    assert resp.status_code == 422

    resp = await client.post("/api/feedback", json={"message": "Hello"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_invalid_token_treated_as_anonymous(client, mock_db):
    """An invalid token doesn't break the request — user is treated as anonymous."""
    mock_db.feedback.insert_one = AsyncMock()

    resp = await client.post(
        "/api/feedback",
        json={"type": "bug", "message": "Test with bad token"},
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert resp.status_code == 200
    doc = mock_db.feedback.insert_one.call_args[0][0]
    assert doc["user_id"] is None  # bad token → anonymous
