"""Tests for the generate_binder ARQ background task.

Covers: binder not found, success path, profile parse failure,
        AI failure fallback, PDF failure, and premium tier path.

Run with: pytest app/tests/test_generate_binder.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.tests.conftest import make_mock_db

BINDER_ID = "bbccddeeff001122334455aa"
USER_ID = "aabbccddeeff001122334455"


def _binder_doc(status: str = "queued", tier: str = "standard") -> dict:
    return {
        "_id": ObjectId(BINDER_ID),
        "user_id": USER_ID,
        "user_email": "test@example.com",
        "tier": tier,
        "status": status,
        "pdf_path": "/tmp/test_binder.pdf",
        "sitter_packet_path": "/tmp/test_sitter.pdf",
        "fill_in_checklist_path": "/tmp/test_checklist.pdf",
        "profile_snapshot": {
            "user_id": USER_ID,
            "home_identity": {
                "address_line1": "123 Main St",
                "city": "Miami",
                "state": "FL",
                "zip_code": "33101",
                "home_type": "single_family",
            },
        },
        "ai_content": {},
        "ai_draft": {},
        "modules": ["emergency_contacts"],
        "created_at": datetime.utcnow(),
    }


def _patch_generation_stack(**kwargs):
    """Context manager that patches the entire PDF generation stack."""
    defaults = dict(
        generate_binder_pdf=MagicMock(),
        generate_sitter_packet=MagicMock(),
        generate_fill_in_checklist=MagicMock(),
        collect_unknowns_return=[],
    )
    defaults.update(kwargs)

    return (
        patch("app.tasks.generate_binder.decrypt_profile_fields"),
        patch("app.tasks.generate_binder.clear_unknown_placeholders"),
        patch("app.tasks.generate_binder.generate_binder_pdf", defaults["generate_binder_pdf"]),
        patch("app.tasks.generate_binder.generate_sitter_packet", defaults["generate_sitter_packet"]),
        patch("app.tasks.generate_binder.generate_fill_in_checklist", defaults["generate_fill_in_checklist"]),
        patch("app.tasks.generate_binder.collect_unknowns_from_render",
              return_value=defaults["collect_unknowns_return"]),
        patch("os.chmod"),
        patch("os.path.exists", return_value=True),
    )


def _make_writer_mock():
    mock = MagicMock()
    mock.render_all_sections.return_value = {}
    return mock


def _make_ai_mock(generate_result=None, enhance_result=None, generate_side_effect=None):
    mock = MagicMock()
    if generate_side_effect:
        mock.generate = AsyncMock(side_effect=generate_side_effect)
    else:
        mock.generate = AsyncMock(return_value=generate_result or ({}, {}))
    mock.enhance_modules = AsyncMock(return_value=enhance_result or ({}, {}))
    return mock


# ---------------------------------------------------------------------------
# Binder not found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_binder_not_found():
    """Job exits cleanly when binder_id does not exist in the database."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=None)

    await generate_binder_job({"db": db}, BINDER_ID)

    # No status update should happen — job exits at the first check
    db.binders.update_one.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_success_updates_status_to_ready():
    """Full happy path: status transitions queued → generating → ready."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc())
    db.binders.update_one = AsyncMock()

    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=_make_ai_mock()),
        patch("app.tasks.generate_binder.send_binder_ready") as mock_email,
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "generating" in statuses
    assert "ready" in statuses
    # generating must be set BEFORE ready — ordering matters for polling clients
    assert statuses.index("generating") < statuses.index("ready")
    mock_email.assert_called_once_with("test@example.com", "standard")


@pytest.mark.asyncio
async def test_job_success_sends_binder_ready_email():
    """Confirmation email is sent after successful generation."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc())
    db.binders.update_one = AsyncMock()

    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=_make_ai_mock()),
        patch("app.tasks.generate_binder.send_binder_ready") as mock_email,
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    mock_email.assert_called_once_with("test@example.com", "standard")


# ---------------------------------------------------------------------------
# Profile parse failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_bad_profile_snapshot_marks_failed():
    """Unparseable profile snapshot sets status to failed and sends failure email."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    bad_doc = _binder_doc()
    bad_doc["profile_snapshot"] = {"completely": "wrong", "keys": True}
    db.binders.find_one = AsyncMock(return_value=bad_doc)
    db.binders.update_one = AsyncMock()

    with (
        patch("app.tasks.generate_binder.decrypt_profile_fields"),
        patch("app.tasks.generate_binder.send_generation_failed") as mock_fail,
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "failed" in statuses
    mock_fail.assert_called_once()


# ---------------------------------------------------------------------------
# AI failure falls back to template-only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_ai_failure_falls_back_to_templates():
    """AI generation failure is caught and the job continues with template content."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc())
    db.binders.update_one = AsyncMock()

    ai_mock = _make_ai_mock(generate_side_effect=Exception("Claude unavailable"))
    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=ai_mock),
        patch("app.tasks.generate_binder.send_binder_ready"),
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    # Should still complete as "ready" despite AI failure
    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "ready" in statuses
    assert "failed" not in statuses


# ---------------------------------------------------------------------------
# PDF generation failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_pdf_failure_marks_failed_and_reraises():
    """Hard PDF generation failure marks binder as failed and re-raises the exception."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc())
    db.binders.update_one = AsyncMock()

    with (
        patch("app.tasks.generate_binder.decrypt_profile_fields"),
        patch("app.tasks.generate_binder.clear_unknown_placeholders"),
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=_make_ai_mock()),
        patch("app.tasks.generate_binder.generate_binder_pdf",
              side_effect=Exception("ReportLab error")),
        patch("app.tasks.generate_binder.generate_sitter_packet"),
        patch("app.tasks.generate_binder.generate_fill_in_checklist"),
        patch("app.tasks.generate_binder.collect_unknowns_from_render", return_value=[]),
        patch("app.tasks.generate_binder.send_generation_failed") as mock_fail,
    ):
        with pytest.raises(Exception, match="ReportLab error"):
            await generate_binder_job({"db": db}, BINDER_ID)

    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "failed" in statuses
    mock_fail.assert_called_once_with("test@example.com", "standard")


# ---------------------------------------------------------------------------
# Premium tier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_premium_tier_calls_enhance_modules():
    """Premium tier invokes enhance_modules for AI-enriched content."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc(tier="premium"))
    db.binders.update_one = AsyncMock()

    ai_mock = _make_ai_mock(enhance_result=({}, {}))
    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=ai_mock),
        patch("app.tasks.generate_binder.send_binder_ready"),
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    ai_mock.enhance_modules.assert_called_once()


@pytest.mark.asyncio
async def test_job_standard_tier_skips_enhance_modules():
    """Standard tier does NOT call enhance_modules."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc(tier="standard"))
    db.binders.update_one = AsyncMock()

    ai_mock = _make_ai_mock()
    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=ai_mock),
        patch("app.tasks.generate_binder.send_binder_ready"),
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    ai_mock.enhance_modules.assert_not_called()


# ---------------------------------------------------------------------------
# Sitter packet and checklist failure (non-fatal)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_premium_enhance_modules_failure_is_nonfatal():
    """Premium enhance_modules failure falls back to template content — job still completes."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc(tier="premium"))
    db.binders.update_one = AsyncMock()

    ai_mock = _make_ai_mock()
    ai_mock.enhance_modules = AsyncMock(side_effect=Exception("Claude timeout"))

    patches = _patch_generation_stack()
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=ai_mock),
        patch("app.tasks.generate_binder.send_binder_ready"),
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "ready" in statuses
    assert "failed" not in statuses


@pytest.mark.asyncio
async def test_job_sitter_packet_failure_is_nonfatal():
    """Sitter packet failure is logged but does not prevent binder from completing."""
    from app.tasks.generate_binder import generate_binder_job

    db = make_mock_db()
    db.binders.find_one = AsyncMock(return_value=_binder_doc())
    db.binders.update_one = AsyncMock()

    patches = _patch_generation_stack(
        generate_sitter_packet=MagicMock(side_effect=Exception("Sitter error")),
    )
    with (
        patches[0], patches[1], patches[2], patches[3], patches[4],
        patches[5], patches[6], patches[7],
        patch("app.tasks.generate_binder.TemplateWriter", return_value=_make_writer_mock()),
        patch("app.tasks.generate_binder.AIContentGenerator", return_value=_make_ai_mock()),
        patch("app.tasks.generate_binder.send_binder_ready"),
    ):
        await generate_binder_job({"db": db}, BINDER_ID)

    calls = db.binders.update_one.call_args_list
    statuses = [c[0][1]["$set"]["status"] for c in calls if "status" in c[0][1].get("$set", {})]
    assert "ready" in statuses
    assert "failed" not in statuses
