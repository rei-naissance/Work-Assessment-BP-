"""Stripe payment routes."""

import hashlib
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from bson import ObjectId

import stripe
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.routes.profile import get_current_user
from app.errors import raise_error, ErrorCode, handle_db_error
from app.services.email import send_payment_confirmation

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)

# Price IDs - in production, create these in Stripe Dashboard
# For now we use inline prices
PRICES = {
    "standard": 5900,  # $59.00 in cents
    "premium": 9900,   # $99.00 in cents
}

# Stripe webhook event types this endpoint handles.
# Register all three in the Stripe Dashboard → Webhooks → "Events to send".
HANDLED_WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "checkout.session.expired",
    "payment_intent.payment_failed",
]


async def get_active_prices(db) -> dict:
    try:
        doc = await db.settings.find_one({"key": "pricing"})
    except Exception as e:
        logger.warning("Failed to load pricing settings: %s", e)
        return PRICES

    prices = doc.get("prices") if doc else None
    if not prices:
        return PRICES

    return {
        "standard": int(prices.get("standard", PRICES["standard"])),
        "premium": int(prices.get("premium", PRICES["premium"])),
    }


class CheckoutRequest(BaseModel):
    tier: str


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.get("/pricing")
async def get_pricing(request: Request):
    db = request.app.state.db
    prices = await get_active_prices(db)
    return {"prices": prices}


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout session for the selected tier."""
    if not settings.stripe_secret_key:
        raise_error(ErrorCode.INTERNAL, "Payment system not configured")

    db = request.app.state.db
    prices = await get_active_prices(db)

    if body.tier not in prices:
        raise_error(ErrorCode.INVALID_INPUT, "Invalid tier selected")

    stripe.api_key = settings.stripe_secret_key

    plan_name = "In-Depth Binder" if body.tier == "premium" else "Standard Binder"

    # Deterministic idempotency key: same user + tier + calendar day → same Stripe session
    # This lets Stripe deduplicate retries while allowing a fresh session each new day.
    idempotency_key = hashlib.sha256(
        f"checkout:{user['user_id']}:{body.tier}:{date.today().isoformat()}".encode()
    ).hexdigest()[:48]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": plan_name,
                        "description": "Personalized home operating manual - one-time purchase",
                    },
                    "unit_amount": prices[body.tier],
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{settings.frontend_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/checkout",
            customer_email=user["email"],
            metadata={
                "user_id": user["user_id"],
                "tier": body.tier,
                "idempotency_key": idempotency_key,
            },
            idempotency_key=idempotency_key,
        )
        return {"checkout_url": session.url}
    except stripe.StripeError as e:
        logger.error("Stripe error: %s", e)
        raise_error(ErrorCode.PAYMENT_FAILED, "Unable to create checkout session. Please try again.")


@router.get("/verify-session/{session_id}")
async def verify_session(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Verify a Stripe session and return payment status."""
    if not settings.stripe_secret_key:
        raise_error(ErrorCode.INTERNAL, "Payment system not configured")

    stripe.api_key = settings.stripe_secret_key
    db = request.app.state.db

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Verify this session belongs to this user
        if session.metadata.get("user_id") != user["user_id"]:
            raise_error(ErrorCode.FORBIDDEN, "Payment session does not belong to this user")

        if session.payment_status == "paid":
            tier = session.metadata.get("tier", "standard")

            # Update user record with purchase
            from bson import ObjectId
            await db.users.update_one(
                {"_id": ObjectId(user["user_id"])},
                {
                    "$set": {
                        "purchased_tier": tier,
                        "stripe_session_id": session_id,
                    }
                }
            )

            return {
                "status": "paid",
                "tier": tier,
            }
        else:
            return {
                "status": session.payment_status,
                "tier": None,
            }
    except stripe.StripeError as e:
        logger.error("Stripe error verifying session: %s", e)
        raise_error(ErrorCode.PAYMENT_FAILED, "Could not verify payment status")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks for payment confirmation."""
    if not settings.stripe_webhook_secret:
        raise_error(ErrorCode.INTERNAL, "Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise_error(ErrorCode.INVALID_INPUT, "Invalid webhook payload")
    except stripe.SignatureVerificationError:
        raise_error(ErrorCode.INVALID_INPUT, "Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        tier = session.get("metadata", {}).get("tier", "standard")
        customer_email = session.get("customer_email")
        amount_total = session.get("amount_total", 0)
        payment_intent_id = session.get("payment_intent")

        if user_id:
            db = request.app.state.db

            # Idempotency guard: skip if this session was already processed
            existing_payment = await db.payments.find_one({"stripe_session_id": session["id"]})
            if existing_payment:
                logger.info("Duplicate webhook event for session %s — skipping", session["id"])
                return {"status": "ok"}

            # Store payment receipt in database.
            # The unique index on stripe_session_id guards against concurrent
            # duplicate webhooks — catch DuplicateKeyError and treat as idempotent.
            receipt = {
                "user_id": user_id,
                "stripe_session_id": session["id"],
                "stripe_payment_intent": payment_intent_id,
                "tier": tier,
                "amount_cents": amount_total,
                "currency": session.get("currency", "usd"),
                "customer_email": customer_email,
                "status": "completed",
                "created_at": datetime.utcnow(),
            }
            try:
                await db.payments.insert_one(receipt)
            except DuplicateKeyError:
                logger.info(
                    "Duplicate webhook insert for session %s — already processed",
                    session["id"],
                )
                return {"status": "ok"}

            # Update user record with purchase
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "purchased_tier": tier,
                        "stripe_session_id": session["id"],
                        "stripe_payment_intent": payment_intent_id,
                    }
                }
            )
            logger.info("Payment completed for user %s, tier %s", user_id, tier)

            # Send payment confirmation email
            if customer_email:
                send_payment_confirmation(customer_email, tier, amount_total)

    elif event["type"] == "checkout.session.expired":
        # User abandoned the checkout (closed tab, navigated away, session timed out).
        # No action needed — the idempotency key resets each calendar day so they can
        # start a fresh session. Log for analytics/monitoring only.
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        logger.info(
            "Checkout session expired (abandoned) — user=%s session=%s",
            user_id,
            session.get("id"),
        )

    elif event["type"] == "payment_intent.payment_failed":
        # Card was declined, insufficient funds, or 3DS authentication failed.
        # Log details for support and monitoring; no DB write needed since no
        # successful payment record exists yet.
        pi = event["data"]["object"]
        error = pi.get("last_payment_error") or {}
        logger.warning(
            "Payment failed — intent=%s code=%s message=%s",
            pi.get("id"),
            error.get("code", "unknown"),
            error.get("message", "no message"),
        )

    return {"status": "ok"}
