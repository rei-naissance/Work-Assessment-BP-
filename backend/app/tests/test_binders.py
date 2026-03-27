"""Integration tests for binder routes.

Covers: generate (auth, tier, profile validation, rate limit), status, list,
        preview, sections, section content, and download error paths.

Run with: pytest app/tests/test_binders.py -v
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.routes.binders import SECTION_META
from app.tests.conftest import FakeCursor, make_access_token

USER_ID = "aabbccddeeff001122334455"
BINDER_ID = "bbccddeeff001122334455aa"


def _auth_headers(user_id: str = USER_ID) -> dict:
    return {"Authorization": f"Bearer {make_access_token(user_id=user_id)}"}


def _minimal_profile_snapshot(user_id: str = USER_ID) -> dict:
    """Minimal profile that passes all generate-route validations."""
    return {
        "user_id": user_id,
        "home_identity": {
            "address_line1": "123 Main St",
            "city": "Miami",
            "state": "FL",
            "zip_code": "33101",
            "home_type": "single_family",
        },
    }


def _binder_doc(
    binder_id: str = BINDER_ID,
    user_id: str = USER_ID,
    status: str = "ready",
    pdf_path: str = "/tmp/test.pdf",
    sitter_path: str = "/tmp/test_sitter.pdf",
    checklist_path: str = "/tmp/test_checklist.pdf",
) -> dict:
    return {
        "_id": ObjectId(binder_id),
        "user_id": user_id,
        "tier": "standard",
        "status": status,
        "modules": ["emergency_contacts", "home_profile"],
        "profile_snapshot": _minimal_profile_snapshot(user_id),
        "ai_content": {},
        "ai_draft": {},
        "pdf_path": pdf_path,
        "sitter_packet_path": sitter_path,
        "fill_in_checklist_path": checklist_path,
        "created_at": datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# POST /api/binders/generate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.post("/api/binders/generate", json={"tier": "standard"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_invalid_tier(client, mock_db):
    """Returns 400 for an unknown tier."""
    resp = await client.post(
        "/api/binders/generate",
        json={"tier": "platinum"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_generate_no_profile_returns_404(client, mock_db):
    """Returns 404 when the user has no profile."""
    mock_db.profiles.find_one = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/binders/generate",
        json={"tier": "standard"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_missing_required_fields(client, mock_db):
    """Returns an error when profile is missing address/city/zip/home_type."""
    mock_db.profiles.find_one = AsyncMock(return_value={"user_id": USER_ID})
    mock_db.binders.count_documents = AsyncMock(return_value=0)

    with patch("app.routes.binders.decrypt_profile_fields"):
        resp = await client.post(
            "/api/binders/generate",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_success_queues_binder(client, mock_db):
    """Valid profile + tier creates a queued binder and enqueues the job."""
    mock_db.profiles.find_one = AsyncMock(return_value=_minimal_profile_snapshot())
    mock_db.binders.count_documents = AsyncMock(return_value=0)
    binder_oid = ObjectId()
    mock_db.binders.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=binder_oid)
    )

    with patch("app.routes.binders.decrypt_profile_fields"):
        resp = await client.post(
            "/api/binders/generate",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert body["tier"] == "standard"
    assert "id" in body
    mock_db.binders.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_generate_premium_tier(client, mock_db):
    """Premium tier is also accepted."""
    mock_db.profiles.find_one = AsyncMock(return_value=_minimal_profile_snapshot())
    mock_db.binders.count_documents = AsyncMock(return_value=0)
    mock_db.binders.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    with patch("app.routes.binders.decrypt_profile_fields"):
        resp = await client.post(
            "/api/binders/generate",
            json={"tier": "premium"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["tier"] == "premium"


@pytest.mark.asyncio
async def test_generate_rate_limited(client, mock_db):
    """Returns 429 when user has already generated 3 binders in the last hour."""
    mock_db.profiles.find_one = AsyncMock(return_value=_minimal_profile_snapshot())
    mock_db.binders.count_documents = AsyncMock(return_value=3)

    with patch("app.routes.binders.decrypt_profile_fields"):
        resp = await client.post(
            "/api/binders/generate",
            json={"tier": "standard"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# GET /api/binders/status/{binder_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_queued(client, mock_db):
    """Returns queued status for a recently created binder."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc(status="queued"))

    resp = await client.get(
        f"/api/binders/status/{BINDER_ID}",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert resp.json()["binder_id"] == BINDER_ID


@pytest.mark.asyncio
async def test_get_status_ready(client, mock_db):
    """Returns ready status once generation completes."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc(status="ready"))

    resp = await client.get(
        f"/api/binders/status/{BINDER_ID}",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_get_status_not_found(client, mock_db):
    """Returns 404 when binder doesn't belong to the user."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/status/{BINDER_ID}",
        headers=_auth_headers(),
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get(f"/api/binders/status/{BINDER_ID}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/binders/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_binders_empty(client, mock_db):
    """Returns empty list when user has no binders."""
    mock_db.binders.find = MagicMock(return_value=FakeCursor([]))

    resp = await client.get("/api/binders/", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_binders_returns_results(client, mock_db):
    """Returns binders belonging to the current user."""
    mock_db.binders.find = MagicMock(return_value=FakeCursor([_binder_doc()]))

    resp = await client.get("/api/binders/", headers=_auth_headers())

    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 1
    assert result[0]["status"] == "ready"
    assert result[0]["tier"] == "standard"


# ---------------------------------------------------------------------------
# GET /api/binders/preview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_no_profile(client, mock_db):
    """Returns has_profile=False when no profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=None)

    resp = await client.get("/api/binders/preview", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.json()["has_profile"] is False


@pytest.mark.asyncio
async def test_preview_with_profile(client, mock_db):
    """Returns tier module counts and insights when profile exists."""
    mock_db.profiles.find_one = AsyncMock(return_value=_minimal_profile_snapshot())

    resp = await client.get("/api/binders/preview", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_profile"] is True
    assert "standard" in body
    assert "premium" in body
    assert body["standard"]["count"] > 0
    assert body["premium"]["count"] >= body["standard"]["count"]
    assert "insights" in body


# ---------------------------------------------------------------------------
# GET /api/binders/{binder_id}/sections
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_sections_not_found(client, mock_db):
    """Returns 404 for an unknown binder."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/sections",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_sections_returns_section_list(client, mock_db):
    """Returns a list of sections with title, icon, and module list."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc())

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/sections",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == len(SECTION_META)
    for section in body:
        assert "section" in section
        assert "title" in section
        assert "icon" in section
        assert "modules" in section


@pytest.mark.asyncio
async def test_get_sections_unauthenticated(client):
    """Returns 401 without an auth token."""
    resp = await client.get(f"/api/binders/{BINDER_ID}/sections")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/binders/{binder_id}/sections/{section_key}/content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_section_content_not_found(client, mock_db):
    """Returns 404 for an unknown binder."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/sections/section_1/content",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_section_content_returns_blocks(client, mock_db):
    """Returns a block list with section_key for a valid binder section."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc())

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/sections/section_1/content",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "blocks" in body
    assert "section_key" in body
    assert body["section_key"] == "section_1"


@pytest.mark.asyncio
async def test_get_section_content_empty_section(client, mock_db):
    """Returns empty blocks list for a section with no content."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc())

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/sections/section_nonexistent/content",
        headers=_auth_headers(),
    )

    assert resp.status_code == 200
    assert resp.json()["blocks"] == []


# ---------------------------------------------------------------------------
# GET /api/binders/{binder_id}/download
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_no_token_returns_401(client):
    """Returns 401 without an auth token."""
    resp = await client.get(f"/api/binders/{BINDER_ID}/download")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_download_not_found_returns_404(client, mock_db):
    """Returns 404 when the binder doesn't exist."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_not_ready_returns_400(client, mock_db):
    """Returns 400 when binder is still queued or generating."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc(status="generating"))

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download",
        headers=_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_download_missing_pdf_returns_404(client, mock_db):
    """Returns 404 when binder is ready but the PDF file is missing from disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "missing.pdf")  # does NOT exist
        mock_db.binders.find_one = AsyncMock(
            return_value=_binder_doc(status="ready", pdf_path=pdf_path)
        )
        with patch("app.config.settings.data_dir", tmpdir):
            resp = await client.get(
                f"/api/binders/{BINDER_ID}/download",
                headers=_auth_headers(),
            )

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/binders/{binder_id}/download/sitter-packet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_sitter_not_ready_returns_400(client, mock_db):
    """Returns 400 when binder is not ready."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc(status="queued"))

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download/sitter-packet",
        headers=_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_download_sitter_not_found(client, mock_db):
    """Returns 404 when binder doesn't exist."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download/sitter-packet",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/binders/{binder_id}/download/checklist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_checklist_not_ready_returns_400(client, mock_db):
    """Returns 400 when binder is not ready."""
    mock_db.binders.find_one = AsyncMock(return_value=_binder_doc(status="queued"))

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download/checklist",
        headers=_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_download_checklist_not_found(client, mock_db):
    """Returns 404 when binder doesn't exist."""
    mock_db.binders.find_one = AsyncMock(return_value=None)

    resp = await client.get(
        f"/api/binders/{BINDER_ID}/download/checklist",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
