import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.config import settings
from app.models.profile import Profile
from app.validation.completeness import check_completeness
from app.validation.goal_mapping import build_readiness_report
from app.errors import raise_error, ErrorCode, handle_db_error
from app.services.crypto import encrypt_profile_fields, decrypt_profile_fields, mask_profile_fields
from app.utils.secure_delete import secure_delete

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise_error(ErrorCode.UNAUTHORIZED, "Missing authentication token")
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise_error(ErrorCode.INVALID_TOKEN, "Invalid or expired token")
    return {"user_id": payload["sub"], "email": payload.get("email", "")}


@router.get("/")
async def get_profile(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    try:
        doc = await db.profiles.find_one({"user_id": user["user_id"]})
        user_doc = await db.users.find_one({"_id": ObjectId(user["user_id"])})
    except Exception as e:
        handle_db_error("fetching profile", e)
    purchase_meta = {}
    if user_doc:
        purchase_meta = {
            "purchased_tier": user_doc.get("purchased_tier", ""),
            "stripe_session_id": user_doc.get("stripe_session_id", ""),
        }
    if not doc:
        payload = Profile(user_id=user["user_id"]).model_dump()
        payload.update(purchase_meta)
        return payload
    doc.pop("_id", None)
    # Decrypt sensitive fields after read
    decrypt_profile_fields(doc)
    # Validate through Pydantic so new fields get defaults
    validated = Profile(**doc).model_dump()
    validated.update(purchase_meta)
    return validated


@router.put("/")
async def save_profile(body: Profile, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    body.user_id = user["user_id"]
    body.updated_at = datetime.utcnow()
    data = body.model_dump()
    # Encrypt sensitive fields before storage
    encrypt_profile_fields(data)
    try:
        await db.profiles.update_one(
            {"user_id": user["user_id"]},
            {"$set": data},
            upsert=True,
        )
    except Exception as e:
        handle_db_error("saving profile", e)
    return {"message": "Profile saved"}


@router.get("/completeness")
async def get_completeness(request: Request, user=Depends(get_current_user)):
    """Check profile completeness across all binder sections.

    Returns section-by-section completeness with specific missing items,
    feature-aware warnings, and overall generation readiness.
    """
    db = request.app.state.db
    try:
        doc = await db.profiles.find_one({"user_id": user["user_id"]})
    except Exception as e:
        handle_db_error("checking profile completeness", e)

    if not doc:
        return {
            "overall_score": 0,
            "can_generate": False,
            "blocking_issues": ["No profile found - please complete the assessment"],
            "sections": {},
            "feature_warnings": [],
        }

    doc.pop("_id", None)
    profile = Profile(**doc)
    result = check_completeness(profile)

    return {
        "overall_score": result.overall_score,
        "can_generate": result.can_generate,
        "blocking_issues": result.blocking_issues,
        "sections": result.sections,
        "feature_warnings": result.feature_warnings,
    }


@router.get("/readiness")
async def get_readiness(request: Request, user=Depends(get_current_user)):
    """Goal-contextualized binder readiness report.

    Returns completeness data enriched with per-goal impact analysis,
    contextual messages, and step-grouped missing items.
    """
    db = request.app.state.db
    try:
        doc = await db.profiles.find_one({"user_id": user["user_id"]})
    except Exception as e:
        handle_db_error("checking profile readiness", e)

    if not doc:
        return {
            "overall_score": 0,
            "can_generate": False,
            "blocking_issues": ["No profile found"],
            "active_goals": [],
            "goal_reports": {},
            "step_groups": {},
            "sections": {},
        }

    doc.pop("_id", None)
    # Decrypt sensitive fields so we can check them
    decrypt_profile_fields(doc)
    profile = Profile(**doc)
    profile_dict = profile.model_dump()

    # Base completeness (existing system)
    base = check_completeness(profile)

    # Determine active goals — if none selected, use ALL goals
    # so the review page always shows actionable items
    all_goal_keys = [
        "emergency_preparedness", "guest_handoff", "maintenance_tracking",
        "new_homeowner", "insurance_docs", "vendor_organization",
    ]
    goals_obj = profile.binder_goals
    user_selected = [k for k in all_goal_keys if getattr(goals_obj, k, False)]
    active_goals = user_selected if user_selected else all_goal_keys
    goals_were_selected = len(user_selected) > 0

    # Build goal-contextualized report
    readiness = build_readiness_report(profile_dict, active_goals)

    return {
        "overall_score": base.overall_score,
        "can_generate": base.can_generate,
        "blocking_issues": base.blocking_issues,
        "goals_were_selected": goals_were_selected,
        **readiness,
        "sections": base.sections,
        "feature_warnings": base.feature_warnings,
    }


@router.get("/export")
async def export_data(request: Request, user=Depends(get_current_user)):
    """Export all user data in JSON format (GDPR/CCPA compliance)."""
    db = request.app.state.db
    user_id = user["user_id"]

    try:
        # Gather all user data
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        profile_doc = await db.profiles.find_one({"user_id": user_id})

        binders = []
        async for doc in db.binders.find({"user_id": user_id}):
            doc["_id"] = str(doc["_id"])
            # Remove file paths (not needed for export)
            doc.pop("pdf_path", None)
            doc.pop("sitter_packet_path", None)
            doc.pop("fill_in_checklist_path", None)
            binders.append(doc)

        payments = []
        async for doc in db.payments.find({"user_id": user_id}):
            doc["_id"] = str(doc["_id"])
            payments.append(doc)

    except Exception as e:
        handle_db_error("exporting user data", e)

    # Build export
    export_data = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": user_id,
            "email": user_doc.get("email") if user_doc else user["email"],
            "created_at": user_doc.get("created_at").isoformat() if user_doc and user_doc.get("created_at") else None,
        },
        "profile": profile_doc if profile_doc else None,
        "binders": binders,
        "payments": payments,
    }

    # Clean up MongoDB ObjectIds
    if export_data["profile"]:
        export_data["profile"].pop("_id", None)
        # Decrypt then mask sensitive fields for export
        decrypt_profile_fields(export_data["profile"])
        mask_profile_fields(export_data["profile"])

    logger.info("Data export requested for user %s", user_id)

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=homebinder_export_{user_id}.json"
        }
    )


@router.delete("/")
async def delete_account(request: Request, user=Depends(get_current_user)):
    """Delete user account and all associated data (GDPR/CCPA compliance).

    This permanently deletes:
    - User account
    - Profile data
    - All binders (and their PDF files)
    - Payment records
    """
    import os
    db = request.app.state.db
    user_id = user["user_id"]

    try:
        # Securely delete binder PDFs from filesystem (overwrite + remove)
        async for binder in db.binders.find({"user_id": user_id}):
            for path_key in ["pdf_path", "sitter_packet_path", "fill_in_checklist_path"]:
                path = binder.get(path_key)
                if path:
                    secure_delete(path)

        # Delete from database
        await db.binders.delete_many({"user_id": user_id})
        await db.profiles.delete_one({"user_id": user_id})
        await db.payments.delete_many({"user_id": user_id})
        await db.users.delete_one({"_id": ObjectId(user_id)})

    except Exception as e:
        handle_db_error("deleting user account", e)

    logger.info("Account deleted for user %s", user_id)

    return {"message": "Account and all associated data have been permanently deleted"}


# ============================================================================
# User Messages
# ============================================================================


class UserReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.get("/messages")
async def get_user_messages(request: Request, user=Depends(get_current_user)):
    """Get all messages for the current user across all orders."""
    db = request.app.state.db
    user_id = user["user_id"]

    # Find all order IDs for this user
    order_ids = []
    try:
        async for payment in db.payments.find({"user_id": user_id}, {"_id": 1}):
            order_ids.append(str(payment["_id"]))
    except Exception as e:
        handle_db_error("fetching user orders for messages", e)

    if not order_ids:
        return []

    messages = []
    try:
        async for doc in db.order_messages.find(
            {"order_id": {"$in": order_ids}}
        ).sort("created_at", -1):
            messages.append({
                "id": str(doc["_id"]),
                "order_id": doc["order_id"],
                "sender": doc["sender"],
                "message": doc["message"],
                "read": doc.get("read", False),
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        handle_db_error("fetching user messages", e)

    return messages


@router.post("/messages/{message_id}/reply")
async def reply_to_message(
    message_id: str,
    body: UserReplyRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """User replies to an admin message."""
    db = request.app.state.db
    user_id = user["user_id"]

    # Verify the message belongs to this user's order
    try:
        original = await db.order_messages.find_one({"_id": ObjectId(message_id)})
    except Exception as e:
        handle_db_error("fetching message for reply", e)

    if not original:
        raise_error(ErrorCode.NOT_FOUND, "Message not found")

    order_id = original["order_id"]

    # Verify user owns this order
    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    except Exception as e:
        handle_db_error("verifying order ownership", e)

    if not payment:
        raise_error(ErrorCode.FORBIDDEN, "Not authorized to reply to this message")

    # Mark original as read
    await db.order_messages.update_one({"_id": ObjectId(message_id)}, {"$set": {"read": True}})

    # Create reply
    reply_doc = {
        "order_id": order_id,
        "sender": "user",
        "message": body.message.strip(),
        "read": False,
        "created_at": datetime.utcnow(),
    }

    try:
        result = await db.order_messages.insert_one(reply_doc)
    except Exception as e:
        handle_db_error("creating reply", e)

    return {
        "id": str(result.inserted_id),
        "message": "Reply sent",
    }


@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Mark a message as read."""
    db = request.app.state.db
    user_id = user["user_id"]

    try:
        msg = await db.order_messages.find_one({"_id": ObjectId(message_id)})
    except Exception as e:
        handle_db_error("fetching message", e)

    if not msg:
        raise_error(ErrorCode.NOT_FOUND, "Message not found")

    # Verify user owns the order
    order_id = msg["order_id"]
    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    except Exception as e:
        handle_db_error("verifying order ownership", e)

    if not payment:
        raise_error(ErrorCode.FORBIDDEN, "Not authorized")

    await db.order_messages.update_one({"_id": ObjectId(message_id)}, {"$set": {"read": True}})
    return {"message": "Marked as read"}
