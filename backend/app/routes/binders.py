import os
import uuid
import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from app.config import settings
from app.models.profile import Profile
from app.models.binder import BinderRequest, BinderOut
from app.rules.engine import select_modules
from app.pdf.generator import generate_binder_pdf
from app.ai.generator import AIContentGenerator
from app.routes.profile import get_current_user
from app.outputs.sitter_packet import generate_sitter_packet
from app.outputs.fill_in_checklist import generate_fill_in_checklist, collect_unknowns_from_render
from app.templates.narrative import clear_unknown_placeholders
from app.errors import raise_error, ErrorCode, handle_db_error
from app.services.email import send_binder_ready, send_generation_failed
from app.services.crypto import decrypt_profile_fields

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_TIERS = {"standard", "premium"}


@router.post("/generate", response_model=BinderOut)
async def generate_binder(body: BinderRequest, request: Request, user=Depends(get_current_user)):
    if body.tier not in VALID_TIERS:
        raise_error(ErrorCode.INVALID_INPUT, "Invalid tier", detail="Choose 'standard' or 'premium'")

    db = request.app.state.db
    try:
        profile_doc = await db.profiles.find_one({"user_id": user["user_id"]})
    except Exception as e:
        handle_db_error("fetching profile for generation", e)
    if not profile_doc:
        raise_error(ErrorCode.PROFILE_NOT_FOUND, "Complete your profile first")

    profile_doc.pop("_id", None)
    decrypt_profile_fields(profile_doc)
    profile = Profile(**profile_doc)

    # Validate minimum required fields
    hi = profile.home_identity
    missing = []
    if not hi.address_line1:
        missing.append("address")
    if not hi.city or not hi.state:
        missing.append("city/state")
    if not hi.zip_code:
        missing.append("ZIP code")
    if not hi.home_type:
        missing.append("home type")
    if missing:
        raise_error(
            ErrorCode.VALIDATION,
            f"Please complete your profile. Missing: {', '.join(missing)}"
        )

    sections = select_modules(profile, tier=body.tier)
    module_keys = [k for sec in sections.values() for k in sec.keys()]

    # AI content generation (two-stage pipeline)
    ai_content = {}
    ai_draft = {}
    try:
        generator = AIContentGenerator()
        ai_content, ai_draft = await generator.generate(profile, sections, body.tier)
    except Exception:
        pass  # Fallback to template-only

    # Generate unique filenames for all outputs
    file_id = uuid.uuid4().hex[:8]
    pdf_path = os.path.join(settings.data_dir, f"{user['user_id']}_{file_id}.pdf")
    sitter_path = os.path.join(settings.data_dir, f"{user['user_id']}_{file_id}_sitter.pdf")
    checklist_path = os.path.join(settings.data_dir, f"{user['user_id']}_{file_id}_checklist.pdf")

    binder_doc = {
        "user_id": user["user_id"],
        "tier": body.tier,
        "profile_snapshot": profile.model_dump(),
        "modules": module_keys,
        "pdf_path": pdf_path,
        "sitter_packet_path": sitter_path,
        "fill_in_checklist_path": checklist_path,
        "status": "generating",
        "ai_content": ai_content,
        "ai_draft": ai_draft,
        "created_at": datetime.utcnow(),
    }
    try:
        result = await db.binders.insert_one(binder_doc)
    except Exception as e:
        handle_db_error("creating binder record", e)
    binder_id = str(result.inserted_id)

    try:
        # Clear unknown tracker before rendering
        clear_unknown_placeholders()

        # Stage 3: AI module enhancement (premium tier only)
        from app.templates.narrative import TemplateWriter
        writer = TemplateWriter()
        section_blocks = writer.render_all_sections(sections, profile, ai_content)

        missing_items = {}
        if body.tier == "premium":
            try:
                section_blocks, missing_items = await generator.enhance_modules(
                    section_blocks, profile, body.tier
                )
                logger.info("Stage 3 complete — %d sections enhanced, %d missing items",
                            sum(1 for k in section_blocks if k.startswith("section_")),
                            sum(len(v) for v in missing_items.values()))
            except Exception as e:
                logger.warning("Module enhancement failed, using template-only content: %s", e)

        # 1. Generate main binder PDF (with pre-enhanced blocks)
        generate_binder_pdf(profile, pdf_path, tier=body.tier,
                            ai_content=ai_content, section_blocks=section_blocks)

        # 2. Generate sitter packet
        try:
            generate_sitter_packet(profile, sitter_path, tier=body.tier, ai_content=ai_content)
        except Exception as e:
            logger.warning(f"Sitter packet generation failed: {e}")
            sitter_path = None

        # 3. Generate fill-in checklist (template unknowns + AI-identified gaps)
        unknowns = []
        try:
            unknowns = collect_unknowns_from_render()
            generate_fill_in_checklist(profile, checklist_path, unknowns=unknowns,
                                       ai_missing_items=missing_items)
        except Exception as e:
            logger.warning(f"Fill-in checklist generation failed: {e}")
            checklist_path = None

        # Set restrictive file permissions on generated PDFs
        for path in [pdf_path, sitter_path, checklist_path]:
            if path and os.path.exists(path):
                os.chmod(path, 0o600)

        # Update document with actual paths (None if failed)
        update_fields = {
            "status": "ready",
            "unknown_count": len(unknowns),
            "missing_items": missing_items,
        }
        if sitter_path is None:
            update_fields["sitter_packet_path"] = None
        if checklist_path is None:
            update_fields["fill_in_checklist_path"] = None

        await db.binders.update_one({"_id": result.inserted_id}, {"$set": update_fields})
        binder_doc["status"] = "ready"

        # Send binder ready notification email
        send_binder_ready(user["email"], body.tier)

    except Exception as e:
        await db.binders.update_one({"_id": result.inserted_id}, {"$set": {"status": "failed"}})
        logger.error(f"Binder generation failed: {e}")

        # Send generation failed notification email
        send_generation_failed(user["email"], body.tier)

        raise_error(ErrorCode.GENERATION_FAILED, "Failed to generate binder. Please try again.", detail=str(e))

    return BinderOut(id=binder_id, user_id=user["user_id"], tier=body.tier, modules=module_keys,
                     status="ready", ai_content=ai_content, missing_items=missing_items,
                     created_at=binder_doc["created_at"])


@router.get("/")
async def list_binders(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.binders.find({"user_id": user["user_id"]}).sort("created_at", -1)
    binders = []
    async for doc in cursor:
        binders.append(BinderOut(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            tier=doc.get("tier", "standard"),
            modules=doc.get("modules", []),
            status=doc.get("status", "unknown"),
            created_at=doc.get("created_at"),
        ).model_dump())
    return binders


@router.get("/preview")
async def preview_tiers(request: Request, user=Depends(get_current_user)):
    """Return module counts, premium-only modules, and profile-based insights."""
    db = request.app.state.db
    profile_doc = await db.profiles.find_one({"user_id": user["user_id"]})
    if not profile_doc:
        return {"has_profile": False}

    profile_doc.pop("_id", None)
    profile = Profile(**profile_doc)

    standard_sections = select_modules(profile, tier="standard")
    premium_sections = select_modules(profile, tier="premium")

    standard_keys = set()
    for sec in standard_sections.values():
        standard_keys.update(sec.keys())

    premium_keys = set()
    premium_all = {}
    for sec in premium_sections.values():
        premium_keys.update(sec.keys())
        premium_all.update(sec)

    premium_only_keys = premium_keys - standard_keys
    premium_only = []
    for k in sorted(premium_only_keys):
        mod = premium_all.get(k, {})
        premium_only.append({"key": k, "title": mod.get("title", k.replace("_", " ").title())})

    def _count_items(sections: dict) -> int:
        total = 0
        for sec in sections.values():
            for mod in sec.values():
                total += len(mod.get("content", []))
                for phase in mod.get("phases", {}).values():
                    total += len(phase) if isinstance(phase, list) else 0
                for card in mod.get("cards", {}).values():
                    total += len(card.get("actions", []))
                total += len(mod.get("systems", []))
                total += len(mod.get("base_supplies", []))
                for supp in mod.get("region_supplements", {}).values():
                    total += len(supp.get("items", []))
        return total

    # --- Profile-based insights ---
    # Unknown critical locations
    LOCATION_LABELS = {
        "water_shutoff": "Water Shutoff Valve",
        "gas_shutoff": "Gas Shutoff Valve",
        "electrical_panel": "Electrical Panel",
        "hvac_unit": "HVAC Unit",
        "sump_pump": "Sump Pump",
        "attic_access": "Attic Access",
        "crawlspace_access": "Crawlspace Access",
    }
    cl = profile.critical_locations.model_dump()
    unknown_locations = [LOCATION_LABELS[k] for k, v in cl.items() if v.get("status") == "unknown" and k in LOCATION_LABELS]
    known_locations = [LOCATION_LABELS[k] for k, v in cl.items() if v.get("status") == "known" and k in LOCATION_LABELS]

    # Premium-relevant features the user has checked
    FEATURE_LABELS = {
        "has_pool": "Pool", "has_hot_tub": "Hot Tub", "has_septic": "Septic System",
        "has_well_water": "Well Water", "has_solar": "Solar Panels", "has_generator": "Generator",
        "has_ev_charger": "EV Charger", "has_fireplace": "Fireplace", "has_security_system": "Security System",
        "has_smart_home": "Smart Home", "has_water_softener": "Water Softener",
        "has_water_filtration": "Water Filtration", "has_sump_pump": "Sump Pump",
        "has_battery_backup": "Battery Backup", "has_whole_house_fan": "Whole House Fan",
        "has_dehumidifier": "Dehumidifier", "has_humidifier": "Humidifier",
        "has_air_purifier": "Air Purifier", "has_radon_mitigation": "Radon Mitigation",
        "has_cameras": "Security Cameras", "has_sprinklers": "Irrigation System",
    }
    features = profile.features.model_dump()
    active_premium_features = [FEATURE_LABELS[k] for k in FEATURE_LABELS if features.get(k)]

    # Household needs
    household_needs = []
    h = profile.household
    if h.num_children > 0:
        household_needs.append(f"{h.num_children} child{'ren' if h.num_children > 1 else ''} — child-proofing & safety guides")
    if h.has_pets:
        pet_desc = h.pet_types if h.pet_types else "pets"
        household_needs.append(f"{pet_desc.capitalize()} — pet safety & sitter instructions")
    if h.has_elderly:
        household_needs.append("Elderly household members — accessibility & safety")
    if h.has_allergies:
        household_needs.append("Allergies/sensitivities — air quality & filtration")

    # Empty contacts/vendors
    cv = profile.contacts_vendors.model_dump()
    missing_providers = []
    for key, label in [("plumber", "Plumber"), ("electrician", "Electrician"), ("hvac_tech", "HVAC Tech"), ("handyman", "Handyman"), ("locksmith", "Locksmith")]:
        if not cv.get(key, {}).get("name"):
            missing_providers.append(label)

    missing_utilities = []
    for key, label in [("power", "Power"), ("gas", "Gas"), ("water", "Water"), ("isp", "Internet")]:
        if not cv.get(key, {}).get("company"):
            missing_utilities.append(label)

    has_insurance = bool(cv.get("insurance", {}).get("provider"))
    emergency_count = len(cv.get("emergency_contacts", []))

    return {
        "has_profile": True,
        "standard": {"count": len(standard_keys), "items": _count_items(standard_sections)},
        "premium": {"count": len(premium_keys), "items": _count_items(premium_sections)},
        "premium_only": premium_only,
        "insights": {
            "unknown_locations": unknown_locations,
            "known_locations": known_locations,
            "active_premium_features": active_premium_features,
            "household_needs": household_needs,
            "missing_providers": missing_providers,
            "missing_utilities": missing_utilities,
            "has_insurance": has_insurance,
            "emergency_contact_count": emergency_count,
        },
    }


SECTION_META = [
    {"key": "section_0", "title": "Cover Page", "description": "Your binder cover with home address and details.", "icon": "cover", "profile_only": True},
    {"key": "section_1", "title": "Emergency Quick Start", "description": "At-a-glance emergency reference cards for gas leaks, water shutoffs, fire, and power outages.", "icon": "emergency"},
    {"key": "section_2", "title": "Home Profile", "description": "Your home's identity — address, type, year built, square footage, and key features.", "icon": "home", "profile_only": True},
    {"key": "section_3", "title": "Emergency Playbooks", "description": "Step-by-step action plans for fire, water leaks, power outages, HVAC failure, storms, and security events.", "icon": "playbook"},
    {"key": "section_4", "title": "Guest & Sitter Mode", "description": "Instructions for guests, pet sitters, and house sitters — alarm codes, escalation contacts, and pet care.", "icon": "guest", "profile_only": True},
    {"key": "section_5", "title": "Maintenance & Seasonal", "description": "Seasonal checklists, cleaning schedules, and system-specific maintenance guides.", "icon": "maintenance"},
    {"key": "section_6", "title": "Home Inventory", "description": "Equipment checklists and emergency supply kit templates.", "icon": "inventory"},
    {"key": "section_7", "title": "Contacts & Vendors", "description": "Emergency contacts, service providers, utility companies, and insurance details.", "icon": "contacts", "profile_only": True},
    {"key": "section_8", "title": "Appendix", "description": "Profile summary, your notes, and index of all included content.", "icon": "appendix", "profile_only": True},
]


@router.get("/{binder_id}/sections")
async def get_binder_sections(binder_id: str, request: Request, user=Depends(get_current_user)):
    """Return the binder's content organized by sections with module titles."""
    db = request.app.state.db
    try:
        doc = await db.binders.find_one({"_id": ObjectId(binder_id), "user_id": user["user_id"]})
    except Exception as e:
        handle_db_error("fetching binder sections", e)
    if not doc:
        raise_error(ErrorCode.BINDER_NOT_FOUND, "Binder not found")

    snapshot = doc.get("profile_snapshot", {})
    tier = doc.get("tier", "standard")
    logger.info(f"Loading sections for binder {binder_id}, tier={tier}, snapshot keys={list(snapshot.keys())}")

    if not snapshot:
        # If no snapshot, try loading current profile
        logger.warning(f"Binder {binder_id} has no profile_snapshot, using current profile")
        profile_doc = await db.profiles.find_one({"user_id": user["user_id"]})
        if profile_doc:
            profile_doc.pop("_id", None)
            snapshot = profile_doc

    # Ensure user_id is set (required field)
    if "user_id" not in snapshot:
        snapshot["user_id"] = user["user_id"]

    # Decrypt sensitive fields in snapshot
    decrypt_profile_fields(snapshot)

    try:
        profile = Profile(**snapshot)
    except Exception as e:
        logger.error(f"Failed to parse profile snapshot: {e}")
        raise_error(ErrorCode.INTERNAL, "Could not load binder profile data", detail=str(e))

    sections = select_modules(profile, tier=tier)
    total_modules = sum(len(sec) for sec in sections.values())
    logger.info(f"select_modules returned {total_modules} modules across {len(sections)} sections")

    # Build profile summaries for profile-only sections
    hi = profile.home_identity
    cv = profile.contacts_vendors
    gm = profile.guest_sitter_mode
    cl = profile.critical_locations.model_dump()
    feat = profile.features.model_dump()

    address_parts = [p for p in [hi.address_line1, hi.city, hi.state] if p]
    address = ", ".join(address_parts) + (f" {hi.zip_code}" if hi.zip_code else "") if address_parts else "No address"

    enabled_features = [k.replace("has_", "").replace("_", " ").title() for k, v in feat.items() if v is True]

    LOCATION_LABELS = {
        "water_shutoff": "Water Shutoff", "gas_shutoff": "Gas Shutoff", "electrical_panel": "Electrical Panel",
        "hvac_unit": "HVAC Unit", "sump_pump": "Sump Pump", "attic_access": "Attic Access", "crawlspace_access": "Crawlspace Access",
    }
    known_locs = [LOCATION_LABELS[k] for k, v in cl.items() if v.get("status") == "known" and k in LOCATION_LABELS]
    unknown_locs = [LOCATION_LABELS[k] for k, v in cl.items() if v.get("status") == "unknown" and k in LOCATION_LABELS]

    PROVIDER_LABELS = {"plumber": "Plumber", "electrician": "Electrician", "hvac_tech": "HVAC Tech", "handyman": "Handyman", "locksmith": "Locksmith"}
    UTILITY_LABELS = {"power": "Power", "gas": "Gas", "water": "Water", "isp": "Internet"}
    cv_dump = cv.model_dump()
    filled_providers = [PROVIDER_LABELS[k] for k in PROVIDER_LABELS if cv_dump.get(k, {}).get("name")]
    filled_utilities = [UTILITY_LABELS[k] for k in UTILITY_LABELS if cv_dump.get(k, {}).get("company")]

    profile_data = {
        "section_0": {
            "summary": [
                {"label": "Address", "value": address},
                {"label": "Type", "value": (hi.home_type or "").replace("_", " ").title() or "Not set"},
                {"label": "Nickname", "value": hi.home_nickname or None},
            ],
        },
        "section_2": {
            "summary": [
                {"label": "Address", "value": address},
                {"label": "Type", "value": (hi.home_type or "").replace("_", " ").title() or "Not set"},
                {"label": "Year Built", "value": str(hi.year_built) if hi.year_built else "Not set"},
                {"label": "Square Feet", "value": f"{hi.square_feet:,}" if hi.square_feet else "Not set"},
                {"label": "Features", "value": f"{len(enabled_features)} selected" if enabled_features else "None"},
                {"label": "Known Locations", "value": f"{len(known_locs)} of {len(LOCATION_LABELS)}"},
            ],
        },
        "section_4": {
            "summary": [
                {"label": "General Instructions", "value": "Added" if gm.instructions else ("Skipped" if gm.skip_instructions else "Not set")},
                {"label": "Alarm Instructions", "value": "Added" if gm.alarm_instructions else ("No alarm" if gm.skip_alarm else "Not set")},
                {"label": "Escalation Contacts", "value": f"{len(gm.escalation_contacts)}" if gm.escalation_contacts else ("Skipped" if gm.skip_escalation else "None")},
                {"label": "Pet Sitter Info", "value": "Added" if (gm.pet_sitter_info.pet_names or gm.pet_sitter_info.feeding_instructions) else ("Skipped" if gm.skip_pet_sitter else "Not set")},
            ],
        },
        "section_7": {
            "summary": [
                {"label": "Emergency Contacts", "value": f"{len(cv.emergency_contacts)}" if cv.emergency_contacts else "None"},
                {"label": "Neighbors", "value": f"{len(cv.neighbors)}" if cv.neighbors else "None"},
                {"label": "Service Providers", "value": ", ".join(filled_providers) if filled_providers else "None filled"},
                {"label": "Utilities", "value": ", ".join(filled_utilities) if filled_utilities else "None filled"},
                {"label": "Insurance", "value": cv.insurance.provider if cv.insurance.provider else ("Skipped" if cv.insurance.skip else "Not set")},
            ],
        },
    }

    result = []
    for meta in SECTION_META:
        sec_key = meta["key"]
        sec_modules = sections.get(sec_key, {})
        modules_list = [
            {"key": k, "title": v.get("title", k.replace("_", " ").title())}
            for k, v in sec_modules.items()
        ]
        entry = {
            "section": meta["key"],
            "title": meta["title"],
            "description": meta["description"],
            "icon": meta["icon"],
            "profile_only": meta.get("profile_only", False),
            "modules": modules_list,
        }
        if sec_key in profile_data:
            entry["profile_summary"] = profile_data[sec_key]["summary"]
        # Include AI intro if available
        stored_ai = doc.get("ai_content", {})
        ai_intros = stored_ai.get("intros", {})
        intro = ai_intros.get(sec_key, {})
        if intro.get("text"):
            entry["ai_intro"] = intro["text"]
        # Include missing_items for this section if available
        stored_missing = doc.get("missing_items", {})
        if sec_key in stored_missing:
            entry["missing_items"] = stored_missing[sec_key]
        result.append(entry)
    return result


@router.get("/{binder_id}/sections/{section_key}/content")
async def get_section_content(binder_id: str, section_key: str, request: Request, user=Depends(get_current_user)):
    """Return rendered Block content for a specific section as JSON."""
    db = request.app.state.db
    try:
        doc = await db.binders.find_one({"_id": ObjectId(binder_id), "user_id": user["user_id"]})
    except Exception as e:
        handle_db_error("fetching binder content", e)
    if not doc:
        raise_error(ErrorCode.BINDER_NOT_FOUND, "Binder not found")

    snapshot = doc.get("profile_snapshot", {})
    tier = doc.get("tier", "standard")

    if not snapshot:
        profile_doc = await db.profiles.find_one({"user_id": user["user_id"]})
        if profile_doc:
            profile_doc.pop("_id", None)
            snapshot = profile_doc

    if "user_id" not in snapshot:
        snapshot["user_id"] = user["user_id"]

    decrypt_profile_fields(snapshot)

    try:
        profile = Profile(**snapshot)
    except Exception as e:
        raise_error(ErrorCode.INTERNAL, "Could not load binder profile data", detail=str(e))

    sections = select_modules(profile, tier=tier)
    ai_content = doc.get("ai_content", {})

    from app.templates.narrative import TemplateWriter
    writer = TemplateWriter()
    all_blocks = writer.render_all_sections(sections, profile, ai_content)

    blocks = all_blocks.get(section_key, [])
    if not blocks:
        return {"blocks": [], "section_key": section_key}

    # Convert Block objects to JSON-serializable dicts
    block_list = []
    for block in blocks:
        entry = {"type": block.type, "text": block.text}
        if block.items:
            entry["items"] = block.items
        if block.rows:
            entry["rows"] = block.rows
        if block.headers:
            entry["headers"] = block.headers
        if block.level != 1:
            entry["level"] = block.level
        if block.ai_generated:
            entry["ai_generated"] = True
        block_list.append(entry)

    return {"blocks": block_list, "section_key": section_key}


@router.get("/{binder_id}/download")
async def download_binder(binder_id: str, request: Request):
    """Download binder PDF."""
    from jose import JWTError, jwt as jose_jwt

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise_error(ErrorCode.UNAUTHORIZED, "Missing authentication token")
    token_str = auth[7:]

    try:
        payload = jose_jwt.decode(token_str, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload["sub"]
    except JWTError:
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired token")

    db = request.app.state.db
    try:
        doc = await db.binders.find_one({"_id": ObjectId(binder_id), "user_id": user_id})
    except Exception as e:
        handle_db_error("fetching binder for download", e)
    if not doc:
        raise_error(ErrorCode.BINDER_NOT_FOUND, "Binder not found")
    if doc.get("status") != "ready":
        raise_error(ErrorCode.INVALID_INPUT, "Binder is not ready for download yet")
    pdf_path = doc.get("pdf_path", "")
    real_path = os.path.realpath(pdf_path)
    real_data_dir = os.path.realpath(settings.data_dir)
    if not real_path.startswith(real_data_dir + os.sep):
        raise_error(ErrorCode.FORBIDDEN, "Invalid file path")
    if not os.path.exists(real_path):
        raise_error(ErrorCode.NOT_FOUND, "PDF file not found. Please regenerate your binder.")
    return FileResponse(real_path, media_type="application/pdf", filename="binderpro.pdf")


@router.get("/{binder_id}/download/sitter-packet")
async def download_sitter_packet(binder_id: str, request: Request):
    """Download sitter packet PDF."""
    from jose import JWTError, jwt as jose_jwt

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise_error(ErrorCode.UNAUTHORIZED, "Missing authentication token")
    token_str = auth[7:]

    try:
        payload = jose_jwt.decode(token_str, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload["sub"]
    except JWTError:
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired token")

    db = request.app.state.db
    try:
        doc = await db.binders.find_one({"_id": ObjectId(binder_id), "user_id": user_id})
    except Exception as e:
        handle_db_error("fetching sitter packet", e)
    if not doc:
        raise_error(ErrorCode.BINDER_NOT_FOUND, "Binder not found")
    if doc.get("status") != "ready":
        raise_error(ErrorCode.INVALID_INPUT, "Binder is not ready for download yet")

    sitter_path = doc.get("sitter_packet_path", "")
    if not sitter_path:
        raise_error(ErrorCode.NOT_FOUND, "Sitter packet not available")
    real_path = os.path.realpath(sitter_path)
    real_data_dir = os.path.realpath(settings.data_dir)
    if not real_path.startswith(real_data_dir + os.sep):
        raise_error(ErrorCode.FORBIDDEN, "Invalid file path")
    if not os.path.exists(real_path):
        raise_error(ErrorCode.NOT_FOUND, "Sitter packet not available")
    return FileResponse(real_path, media_type="application/pdf", filename="sitter_packet.pdf")


@router.get("/{binder_id}/download/checklist")
async def download_fill_in_checklist(binder_id: str, request: Request):
    """Download fill-in checklist PDF."""
    from jose import JWTError, jwt as jose_jwt

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise_error(ErrorCode.UNAUTHORIZED, "Missing authentication token")
    token_str = auth[7:]

    try:
        payload = jose_jwt.decode(token_str, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload["sub"]
    except JWTError:
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired token")

    db = request.app.state.db
    try:
        doc = await db.binders.find_one({"_id": ObjectId(binder_id), "user_id": user_id})
    except Exception as e:
        handle_db_error("fetching checklist", e)
    if not doc:
        raise_error(ErrorCode.BINDER_NOT_FOUND, "Binder not found")
    if doc.get("status") != "ready":
        raise_error(ErrorCode.INVALID_INPUT, "Binder is not ready for download yet")

    checklist_path = doc.get("fill_in_checklist_path", "")
    if not checklist_path:
        raise_error(ErrorCode.NOT_FOUND, "Fill-in checklist not available")
    real_path = os.path.realpath(checklist_path)
    real_data_dir = os.path.realpath(settings.data_dir)
    if not real_path.startswith(real_data_dir + os.sep):
        raise_error(ErrorCode.FORBIDDEN, "Invalid file path")
    if not os.path.exists(real_path):
        raise_error(ErrorCode.NOT_FOUND, "Fill-in checklist not available")
    return FileResponse(real_path, media_type="application/pdf", filename="fill_in_checklist.pdf")
