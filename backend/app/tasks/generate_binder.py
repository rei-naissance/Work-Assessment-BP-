"""ARQ background task: generate all PDFs for a binder and update its status."""

import logging
import os

from bson import ObjectId

from app.config import settings
from app.models.profile import Profile
from app.rules.engine import select_modules
from app.pdf.generator import generate_binder_pdf
from app.ai.generator import AIContentGenerator
from app.outputs.sitter_packet import generate_sitter_packet
from app.outputs.fill_in_checklist import generate_fill_in_checklist, collect_unknowns_from_render
from app.templates.narrative import clear_unknown_placeholders, TemplateWriter
from app.services.email import send_binder_ready, send_generation_failed
from app.services.crypto import decrypt_profile_fields

logger = logging.getLogger(__name__)


async def generate_binder_job(ctx: dict, binder_id: str) -> None:
    """Generate PDFs for a queued binder and update its status in MongoDB.

    The job loads everything it needs from the binder document that was already
    created by the HTTP handler, so the only argument needed is the binder_id.
    """
    db = ctx["db"]

    try:
        oid = ObjectId(binder_id)
    except Exception:
        logger.error("generate_binder_job: invalid binder_id %r — skipping", binder_id)
        return

    doc = await db.binders.find_one({"_id": oid})
    if not doc:
        logger.error("generate_binder_job: binder %s not found", binder_id)
        return

    # Pull fields from the document before entering the try block so any KeyError
    # is caught and the status can be set to "failed" instead of getting stuck.
    user_email: str | None = doc.get("user_email")

    try:
        tier: str = doc["tier"]
        pdf_path: str = doc["pdf_path"]
        sitter_path: str | None = doc.get("sitter_packet_path")
        checklist_path: str | None = doc.get("fill_in_checklist_path")

        snapshot = doc.get("profile_snapshot", {})
        decrypt_profile_fields(snapshot)

        await db.binders.update_one({"_id": oid}, {"$set": {"status": "generating"}})

        try:
            profile = Profile(**snapshot)
        except Exception as exc:
            logger.error("generate_binder_job: could not parse profile snapshot for %s: %s", binder_id, exc)
            await db.binders.update_one({"_id": oid}, {"$set": {"status": "failed"}})
            if user_email:
                send_generation_failed(user_email, tier)
            return

    except Exception as exc:
        logger.error("generate_binder_job: setup failed for %s: %s", binder_id, exc)
        await db.binders.update_one({"_id": oid}, {"$set": {"status": "failed"}})
        if user_email:
            send_generation_failed(user_email, doc.get("tier", "standard"))
        return

    try:
        sections = select_modules(profile, tier=tier)

        # Stage 1+2: AI content generation
        ai_content: dict = {}
        ai_draft: dict = {}
        generator = AIContentGenerator()
        try:
            ai_content, ai_draft = await generator.generate(profile, sections, tier)
        except Exception as exc:
            logger.warning("AI content generation failed, using template-only: %s", exc)

        # Stage 3: render all sections
        clear_unknown_placeholders()
        writer = TemplateWriter()
        section_blocks = writer.render_all_sections(sections, profile, ai_content)

        missing_items: dict = {}
        if tier == "premium":
            try:
                section_blocks, missing_items = await generator.enhance_modules(
                    section_blocks, profile, tier
                )
            except Exception as exc:
                logger.warning("Module enhancement failed, using template-only content: %s", exc)

        # 1. Main binder PDF
        generate_binder_pdf(
            profile, pdf_path, tier=tier,
            ai_content=ai_content, section_blocks=section_blocks,
        )

        # 2. Sitter packet
        try:
            generate_sitter_packet(profile, sitter_path, tier=tier, ai_content=ai_content)
        except Exception as exc:
            logger.warning("Sitter packet generation failed: %s", exc)
            sitter_path = None

        # 3. Fill-in checklist
        unknowns: list = []
        try:
            unknowns = collect_unknowns_from_render()
            generate_fill_in_checklist(
                profile, checklist_path,
                unknowns=unknowns, ai_missing_items=missing_items,
            )
        except Exception as exc:
            logger.warning("Fill-in checklist generation failed: %s", exc)
            checklist_path = None

        # Set file permissions — readable by owner, group, and world (required for serving)
        for path in [pdf_path, sitter_path, checklist_path]:
            if path and os.path.exists(path):
                os.chmod(path, 0o644)

        update_fields: dict = {
            "status": "ready",
            "ai_content": ai_content,
            "ai_draft": ai_draft,
            "unknown_count": len(unknowns),
            "missing_items": missing_items,
        }
        if sitter_path is None:
            update_fields["sitter_packet_path"] = None
        if checklist_path is None:
            update_fields["fill_in_checklist_path"] = None

        await db.binders.update_one({"_id": oid}, {"$set": update_fields})
        logger.info("generate_binder_job: binder %s ready", binder_id)

        if user_email:
            send_binder_ready(user_email, tier)

    except Exception as exc:
        await db.binders.update_one({"_id": oid}, {"$set": {"status": "failed"}})
        logger.error("generate_binder_job: binder %s failed: %s", binder_id, exc)
        if user_email:
            send_generation_failed(user_email, tier)
        raise
