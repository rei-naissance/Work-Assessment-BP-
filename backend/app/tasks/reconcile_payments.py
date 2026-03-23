"""ARQ periodic task: reconcile Stripe payments against the local database.

Runs on a schedule (default: every 6 hours) to catch missed webhooks,
state drift, or partial failures.  Any discrepancies are logged and
automatically repaired when the fix is unambiguous (e.g. a paid session
that has no local payment record).
"""

import logging
from datetime import datetime, timedelta

import stripe
from bson import ObjectId

from app.config import settings

logger = logging.getLogger("home_binder.reconcile")

# How far back to look on each run (overlap ensures we don't miss stragglers)
LOOKBACK_HOURS = 24


async def reconcile_payments_job(ctx: dict) -> dict:
    """Compare recent Stripe checkout sessions with local payment records.

    Returns a summary dict for observability (logged by ARQ on completion).
    """
    if not settings.stripe_secret_key:
        logger.info("Stripe not configured — skipping reconciliation")
        return {"skipped": True}

    stripe.api_key = settings.stripe_secret_key
    db = ctx["db"]

    cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    cutoff_ts = int(cutoff.timestamp())

    stats = {"checked": 0, "missing_locally": 0, "repaired": 0, "errors": 0}

    try:
        # Paginate through recent completed checkout sessions from Stripe
        sessions = stripe.checkout.Session.list(
            limit=100,
            created={"gte": cutoff_ts},
            status="complete",
        )

        for session in sessions.auto_paging_iter():
            stats["checked"] += 1

            if session.payment_status != "paid":
                continue

            session_id = session.id
            user_id = (session.metadata or {}).get("user_id")
            tier = (session.metadata or {}).get("tier", "standard")

            if not user_id:
                continue

            # Check if we already have a local payment record
            existing = await db.payments.find_one({"stripe_session_id": session_id})
            if existing:
                # Payment record exists, but the user update may have failed in a
                # previous run.  Repair it now so we always reach a consistent state.
                try:
                    await db.users.update_one(
                        {"_id": ObjectId(existing["user_id"])},
                        {
                            "$set": {
                                "purchased_tier": existing["tier"],
                                "stripe_session_id": session_id,
                                "stripe_payment_intent": existing.get("stripe_payment_intent"),
                            }
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "Reconciliation: could not repair user for existing session %s: %s",
                        session_id, exc,
                    )
                continue

            # Missing locally — create the record
            stats["missing_locally"] += 1
            logger.warning(
                "Reconciliation: session %s (user=%s, tier=%s) missing locally — repairing",
                session_id, user_id, tier,
            )

            try:
                # Update the user first — if this succeeds but insert fails we can
                # still detect and repair on the next run (user will be correct but
                # payment record will be re-created then).
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$set": {
                            "purchased_tier": tier,
                            "stripe_session_id": session_id,
                            "stripe_payment_intent": session.payment_intent,
                        }
                    },
                )

                receipt = {
                    "user_id": user_id,
                    "stripe_session_id": session_id,
                    "stripe_payment_intent": session.payment_intent,
                    "tier": tier,
                    "amount_cents": session.amount_total or 0,
                    "currency": session.currency or "usd",
                    "customer_email": session.customer_email,
                    "status": "completed",
                    "reconciled": True,
                    "created_at": datetime.utcnow(),
                }
                await db.payments.insert_one(receipt)
                stats["repaired"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.error(
                    "Reconciliation: failed to repair session %s: %s",
                    session_id, exc,
                )

    except stripe.StripeError as exc:
        stats["errors"] += 1
        logger.error("Reconciliation: Stripe API error: %s", exc)

    logger.info("Payment reconciliation complete: %s", stats)
    return stats
