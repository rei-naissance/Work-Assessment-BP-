import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from bson import ObjectId
import stripe

from app.config import settings
from app.routes.profile import get_current_user
from app.models.user import UserOut
from app.models.binder import BinderOut
from app.models.profile import Profile
from app.validation.completeness import check_completeness
from app.errors import raise_error, ErrorCode, handle_db_error
from app.services.email import send_order_shipped, send_order_message
from app.routes.payments import PRICES
from app.rules.engine import get_rules_tree

logger = logging.getLogger(__name__)

router = APIRouter()


async def require_admin(request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    try:
        doc = await db.users.find_one({"_id": ObjectId(user["user_id"])})
    except Exception as e:
        handle_db_error("checking admin status", e)
    if not doc or not doc.get("is_admin"):
        raise_error(ErrorCode.FORBIDDEN, "Admin access required")
    return user


@router.get("/users")
async def list_users(request: Request, user=Depends(require_admin)):
    db = request.app.state.db
    users = []
    try:
        async for doc in db.users.find().sort("created_at", -1):
            users.append(UserOut(
                id=str(doc["_id"]),
                email=doc["email"],
                is_admin=doc.get("is_admin", False),
                created_at=doc.get("created_at"),
            ).model_dump())
    except Exception as e:
        handle_db_error("listing users", e)
    return users


@router.get("/binders")
async def list_all_binders(request: Request, user=Depends(require_admin)):
    db = request.app.state.db
    binders = []
    try:
        async for doc in db.binders.find().sort("created_at", -1):
            binders.append(BinderOut(
                id=str(doc["_id"]),
                user_id=doc["user_id"],
                modules=doc.get("modules", []),
                status=doc.get("status", "unknown"),
                created_at=doc.get("created_at"),
            ).model_dump())
    except Exception as e:
        handle_db_error("listing binders", e)
    return binders


@router.post("/make-admin/{email}")
async def make_admin(email: str, request: Request, user=Depends(require_admin)):
    db = request.app.state.db
    try:
        result = await db.users.update_one({"email": email}, {"$set": {"is_admin": True}})
    except Exception as e:
        handle_db_error("updating admin status", e)
    if result.matched_count == 0:
        raise_error(ErrorCode.USER_NOT_FOUND, "User not found")
    return {"message": f"{email} is now an admin"}


class RefundRequest(BaseModel):
    reason: str = ""


class UpdateOrderRequest(BaseModel):
    fulfillment_status: str  # pending, processing, shipped, delivered, on_hold
    tracking_number: str = ""
    notes: str = ""
    hold_message: str = ""  # Required when setting on_hold


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class PricingConfig(BaseModel):
    standard_cents: int = Field(gt=0)
    premium_cents: int = Field(gt=0)


VALID_FULFILLMENT_STATUSES = {"pending", "processing", "shipped", "delivered", "on_hold"}


@router.get("/pricing")
async def get_pricing(request: Request, user=Depends(require_admin)):
    db = request.app.state.db
    try:
        doc = await db.settings.find_one({"key": "pricing"})
    except Exception as e:
        handle_db_error("fetching pricing", e)

    prices = doc.get("prices") if doc else None
    if not prices:
        prices = PRICES

    return {"prices": prices}


@router.put("/pricing")
async def update_pricing(body: PricingConfig, request: Request, user=Depends(require_admin)):
    db = request.app.state.db
    payload = {
        "key": "pricing",
        "prices": {
            "standard": body.standard_cents,
            "premium": body.premium_cents,
        },
        "updated_at": datetime.utcnow(),
    }
    try:
        await db.settings.update_one({"key": "pricing"}, {"$set": payload}, upsert=True)
    except Exception as e:
        handle_db_error("updating pricing", e)

    return {"prices": payload["prices"]}


@router.get("/rules-tree")
async def rules_tree(user=Depends(require_admin)):
    return {"tree": get_rules_tree()}


@router.get("/orders")
async def list_orders(request: Request, user=Depends(require_admin)):
    """List all orders (completed payments) with customer and binder info."""
    db = request.app.state.db
    orders = []

    try:
        # Get all completed payments (these are orders)
        async for payment in db.payments.find(
            {"status": {"$in": ["completed", "refunded"]}}
        ).sort("created_at", -1):
            user_id = payment["user_id"]

            # Get user info
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})

            # Get profile for shipping address
            profile = await db.profiles.find_one({"user_id": user_id})

            # Get binder info
            binder = await db.binders.find_one(
                {"user_id": user_id},
                sort=[("created_at", -1)]
            )

            # Count unread user replies
            order_id_str = str(payment["_id"])
            unread_count = await db.order_messages.count_documents({
                "order_id": order_id_str,
                "sender": "user",
                "read": False,
            })

            orders.append({
                "id": order_id_str,
                "user_id": user_id,
                "customer_email": payment.get("customer_email") or (user_doc["email"] if user_doc else ""),
                "customer_name": "",  # Field removed - owner_names does not exist in HomeIdentity model
                "tier": payment.get("tier", "standard"),
                "amount_cents": payment.get("amount_cents", 0),
                "payment_status": payment.get("status"),
                "fulfillment_status": payment.get("fulfillment_status", "pending"),
                "tracking_number": payment.get("tracking_number", ""),
                "notes": payment.get("notes", ""),
                "shipped_at": payment.get("shipped_at"),
                "binder_id": str(binder["_id"]) if binder else None,
                "binder_status": binder.get("status") if binder else None,
                "has_pdf": bool(binder.get("pdf_path")) if binder else False,
                "unread_messages": unread_count,
                "created_at": payment.get("created_at"),
            })
    except Exception as e:
        handle_db_error("listing orders", e)

    return orders


@router.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request, user=Depends(require_admin)):
    """Get detailed order info including shipping address."""
    db = request.app.state.db

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    user_id = payment["user_id"]
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    profile = await db.profiles.find_one({"user_id": user_id})
    binder = await db.binders.find_one({"user_id": user_id}, sort=[("created_at", -1)])

    # Extract address from profile
    address = {}
    if profile:
        home = profile.get("home_identity", {})
        address = {
            "name": "",  # Field removed - owner_names does not exist in HomeIdentity model
            "street": home.get("address_line1", ""),
            "city": home.get("city", ""),
            "state": home.get("state", ""),
            "zip": home.get("zip_code", ""),
        }

    return {
        "id": str(payment["_id"]),
        "user_id": user_id,
        "customer_email": payment.get("customer_email") or (user_doc["email"] if user_doc else ""),
        "address": address,
        "tier": payment.get("tier", "standard"),
        "amount_cents": payment.get("amount_cents", 0),
        "payment_status": payment.get("status"),
        "fulfillment_status": payment.get("fulfillment_status", "pending"),
        "tracking_number": payment.get("tracking_number", ""),
        "notes": payment.get("notes", ""),
        "shipped_at": payment.get("shipped_at"),
        "binder_id": str(binder["_id"]) if binder else None,
        "binder_status": binder.get("status") if binder else None,
        "pdf_path": binder.get("pdf_path") if binder else None,
        "created_at": payment.get("created_at"),
    }


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: str,
    body: UpdateOrderRequest,
    request: Request,
    user=Depends(require_admin)
):
    """Update order fulfillment status, tracking, notes."""
    db = request.app.state.db

    if body.fulfillment_status not in VALID_FULFILLMENT_STATUSES:
        raise_error(
            ErrorCode.VALIDATION,
            f"Invalid status. Must be one of: {', '.join(VALID_FULFILLMENT_STATUSES)}"
        )

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order for update", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    old_status = payment.get("fulfillment_status", "pending")

    # Require a message when putting on hold
    if body.fulfillment_status == "on_hold" and old_status != "on_hold" and not body.hold_message.strip():
        raise_error(ErrorCode.VALIDATION, "A message is required when putting an order on hold")

    update_data = {
        "fulfillment_status": body.fulfillment_status,
        "tracking_number": body.tracking_number,
        "notes": body.notes,
    }

    # Set shipped_at timestamp when marking as shipped
    if body.fulfillment_status == "shipped" and old_status != "shipped":
        update_data["shipped_at"] = datetime.utcnow()

    try:
        await db.payments.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_data}
        )
    except Exception as e:
        handle_db_error("updating order", e)

    # Send shipping notification email when status changes to shipped
    if body.fulfillment_status == "shipped" and old_status != "shipped":
        customer_email = payment.get("customer_email")
        if customer_email:
            send_order_shipped(
                to=customer_email,
                tracking_number=body.tracking_number,
                tier=payment.get("tier", "standard")
            )
            logger.info("Shipping notification sent to %s", customer_email)

    # Auto-send hold message when putting on hold
    if body.fulfillment_status == "on_hold" and old_status != "on_hold" and body.hold_message.strip():
        customer_email = payment.get("customer_email")
        try:
            await db.order_messages.insert_one({
                "order_id": order_id,
                "sender": "admin",
                "message": body.hold_message.strip(),
                "read": False,
                "created_at": datetime.utcnow(),
            })
            if customer_email:
                send_order_message(to=customer_email, message_preview=body.hold_message.strip()[:200])
                logger.info("Hold message sent to %s", customer_email)
        except Exception as e:
            logger.warning("Failed to create hold message: %s", e)

    logger.info(
        "Order updated: id=%s, status=%s, by=%s",
        order_id, body.fulfillment_status, user["email"]
    )

    return {"message": "Order updated successfully"}


@router.get("/orders/{order_id}/pdf")
async def get_order_pdf(order_id: str, request: Request, user=Depends(require_admin)):
    """Get the PDF download path for an order."""
    from fastapi.responses import FileResponse
    import os

    db = request.app.state.db

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order for PDF", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    user_id = payment["user_id"]
    binder = await db.binders.find_one({"user_id": user_id}, sort=[("created_at", -1)])

    if not binder or not binder.get("pdf_path"):
        raise_error(ErrorCode.NOT_FOUND, "No PDF available for this order")

    pdf_path = binder["pdf_path"]

    # Validate path to prevent directory traversal
    real_path = os.path.realpath(pdf_path)
    real_data_dir = os.path.realpath(settings.data_dir)
    if not real_path.startswith(real_data_dir + os.sep):
        raise_error(ErrorCode.FORBIDDEN, "Invalid file path")

    if not os.path.exists(real_path):
        raise_error(ErrorCode.NOT_FOUND, "PDF file not found on server")

    # Generate filename for download
    customer_email = payment.get("customer_email", "customer")
    safe_email = customer_email.split("@")[0].replace(".", "_")
    filename = f"binderpro_{safe_email}.pdf"

    return FileResponse(
        path=real_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/payments")
async def list_payments(request: Request, user=Depends(require_admin)):
    """List all payments for admin review."""
    db = request.app.state.db
    payments = []
    try:
        async for doc in db.payments.find().sort("created_at", -1).limit(100):
            payments.append({
                "id": str(doc["_id"]),
                "user_id": doc["user_id"],
                "stripe_session_id": doc.get("stripe_session_id"),
                "stripe_payment_intent": doc.get("stripe_payment_intent"),
                "tier": doc.get("tier"),
                "amount_cents": doc.get("amount_cents"),
                "status": doc.get("status"),
                "customer_email": doc.get("customer_email"),
                "refunded_at": doc.get("refunded_at"),
                "refund_reason": doc.get("refund_reason"),
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        handle_db_error("listing payments", e)
    return payments


@router.post("/refund/{payment_id}")
async def process_refund(
    payment_id: str,
    body: RefundRequest,
    request: Request,
    user=Depends(require_admin)
):
    """Process a refund for a payment."""
    if not settings.stripe_secret_key:
        raise_error(ErrorCode.INTERNAL, "Payment system not configured")

    db = request.app.state.db
    stripe.api_key = settings.stripe_secret_key

    # Get the payment record
    try:
        payment = await db.payments.find_one({"_id": ObjectId(payment_id)})
    except Exception as e:
        handle_db_error("fetching payment for refund", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Payment not found")

    if payment.get("status") == "refunded":
        raise_error(ErrorCode.INVALID_INPUT, "Payment has already been refunded")

    payment_intent_id = payment.get("stripe_payment_intent")
    if not payment_intent_id:
        raise_error(ErrorCode.INVALID_INPUT, "No payment intent found for this payment")

    # Process refund via Stripe
    try:
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            reason="requested_by_customer" if not body.reason else None,
            metadata={
                "admin_id": user["user_id"],
                "reason": body.reason,
            }
        )
    except stripe.StripeError as e:
        logger.error("Stripe refund error: %s", e)
        raise_error(ErrorCode.PAYMENT_FAILED, f"Refund failed: {str(e)}")

    # Update payment record
    try:
        await db.payments.update_one(
            {"_id": ObjectId(payment_id)},
            {
                "$set": {
                    "status": "refunded",
                    "refunded_at": datetime.utcnow(),
                    "refund_reason": body.reason,
                    "stripe_refund_id": refund.id,
                    "refunded_by": user["user_id"],
                }
            }
        )

        # Also update user record to remove purchased_tier
        await db.users.update_one(
            {"_id": ObjectId(payment["user_id"])},
            {
                "$unset": {
                    "purchased_tier": "",
                    "stripe_session_id": "",
                    "stripe_payment_intent": "",
                }
            }
        )
    except Exception as e:
        handle_db_error("updating refund status", e)

    logger.info(
        "Refund processed: payment_id=%s, amount=%s, by=%s",
        payment_id, payment.get("amount_cents"), user["email"]
    )

    return {
        "message": "Refund processed successfully",
        "refund_id": refund.id,
        "amount_refunded": refund.amount,
    }


# ============================================================================
# Order Readiness
# ============================================================================


@router.get("/orders/{order_id}/readiness")
async def get_order_readiness(order_id: str, request: Request, user=Depends(require_admin)):
    """Get binder readiness score for an order's user profile."""
    db = request.app.state.db

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order for readiness", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    user_id = payment["user_id"]

    # Load profile and run completeness check
    profile_doc = await db.profiles.find_one({"user_id": user_id})
    if not profile_doc:
        return {
            "overall_score": 0,
            "can_generate": False,
            "blocking_issues": ["No profile found"],
            "sections": {},
            "feature_warnings": [],
            "unknown_count": None,
        }

    profile_doc.pop("_id", None)
    profile = Profile(**profile_doc)
    result = check_completeness(profile)

    # Get unknown_count from latest binder
    binder = await db.binders.find_one({"user_id": user_id}, sort=[("created_at", -1)])
    unknown_count = binder.get("unknown_count") if binder else None

    return {
        "overall_score": result.overall_score,
        "can_generate": result.can_generate,
        "blocking_issues": result.blocking_issues,
        "sections": result.sections,
        "feature_warnings": result.feature_warnings,
        "unknown_count": unknown_count,
    }


# ============================================================================
# Order Messages
# ============================================================================


@router.get("/orders/{order_id}/messages")
async def get_order_messages(order_id: str, request: Request, user=Depends(require_admin)):
    """Get message thread for an order."""
    db = request.app.state.db

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order for messages", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    messages = []
    try:
        async for doc in db.order_messages.find({"order_id": order_id}).sort("created_at", 1):
            messages.append({
                "id": str(doc["_id"]),
                "order_id": doc["order_id"],
                "sender": doc["sender"],
                "message": doc["message"],
                "read": doc.get("read", False),
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        handle_db_error("listing order messages", e)

    return messages


@router.post("/orders/{order_id}/messages")
async def send_admin_message(
    order_id: str,
    body: SendMessageRequest,
    request: Request,
    user=Depends(require_admin),
):
    """Admin sends a message to the user on an order."""
    db = request.app.state.db

    try:
        payment = await db.payments.find_one({"_id": ObjectId(order_id)})
    except Exception as e:
        handle_db_error("fetching order for message", e)

    if not payment:
        raise_error(ErrorCode.NOT_FOUND, "Order not found")

    msg_doc = {
        "order_id": order_id,
        "sender": "admin",
        "message": body.message.strip(),
        "read": False,
        "created_at": datetime.utcnow(),
    }

    try:
        result = await db.order_messages.insert_one(msg_doc)
    except Exception as e:
        handle_db_error("creating order message", e)

    # Email the user
    customer_email = payment.get("customer_email")
    if customer_email:
        send_order_message(to=customer_email, message_preview=body.message.strip()[:200])
        logger.info("Order message notification sent to %s", customer_email)

    return {
        "id": str(result.inserted_id),
        "message": "Message sent",
    }


# ============================================================================
# Feedback Management
# ============================================================================


@router.get("/feedback")
async def list_feedback(request: Request, user=Depends(require_admin)):
    """List all feedback submissions."""
    db = request.app.state.db
    feedback_list = []
    try:
        async for doc in db.feedback.find().sort("created_at", -1).limit(100):
            feedback_list.append({
                "id": str(doc["_id"]),
                "type": doc.get("type"),
                "message": doc.get("message"),
                "page": doc.get("page"),
                "user_email": doc.get("user_email"),
                "status": doc.get("status", "new"),
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        handle_db_error("listing feedback", e)
    return feedback_list


class UpdateFeedbackRequest(BaseModel):
    status: str  # new, reviewed, resolved


@router.patch("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    body: UpdateFeedbackRequest,
    request: Request,
    user=Depends(require_admin),
):
    """Update feedback status."""
    db = request.app.state.db
    try:
        result = await db.feedback.update_one(
            {"_id": ObjectId(feedback_id)},
            {"$set": {"status": body.status, "reviewed_by": user["user_id"], "reviewed_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            raise_error(ErrorCode.NOT_FOUND, "Feedback not found")
    except Exception as e:
        if "NOT_FOUND" not in str(e):
            handle_db_error("updating feedback", e)
        raise
    return {"success": True}


# ============================================================================
# AI Usage Stats
# ============================================================================


@router.get("/ai-usage")
async def get_ai_usage(request: Request, user=Depends(require_admin)):
    """AI enhancement usage summary — tokens used per binder, totals, averages."""
    db = request.app.state.db
    pipeline = [
        {"$match": {"ai_tokens_used": {"$gt": 0}}},
        {"$group": {
            "_id": None,
            "total_tokens": {"$sum": "$ai_tokens_used"},
            "total_binders": {"$sum": 1},
            "avg_tokens": {"$avg": "$ai_tokens_used"},
            "max_tokens": {"$max": "$ai_tokens_used"},
        }},
    ]

    try:
        result = await db.binders.aggregate(pipeline).to_list(1)
    except Exception as e:
        handle_db_error("aggregating AI usage", e)

    stats = result[0] if result else {
        "total_tokens": 0, "total_binders": 0, "avg_tokens": 0, "max_tokens": 0,
    }
    stats.pop("_id", None)
    stats["avg_tokens"] = int(stats.get("avg_tokens") or 0)

    # Recent binders with AI usage
    recent = []
    try:
        async for doc in db.binders.find(
            {"ai_tokens_used": {"$gt": 0}},
            {"user_id": 1, "tier": 1, "ai_tokens_used": 1, "created_at": 1}
        ).sort("created_at", -1).limit(20):
            recent.append({
                "binder_id": str(doc["_id"]),
                "user_id": doc["user_id"],
                "tier": doc.get("tier", "standard"),
                "ai_tokens_used": doc["ai_tokens_used"],
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        handle_db_error("fetching recent AI usage", e)

    return {"stats": stats, "recent": recent}
