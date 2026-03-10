"""Stripe payment routes."""

import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from bson import ObjectId

import stripe

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

    # Generate idempotency key based on user_id and tier to prevent duplicate charges
    idempotency_key = f"checkout_{user['user_id']}_{body.tier}_{uuid.uuid4().hex[:8]}"

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

            # Store payment receipt in database
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
            await db.payments.insert_one(receipt)

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

    return {"status": "ok"}
