import os
import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError

from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.audit import AuditLoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("home_binder")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo = AsyncIOMotorClient(settings.mongo_uri)
    app.state.db = app.state.mongo.get_default_database()
    os.makedirs(settings.data_dir, exist_ok=True)

    db = app.state.db

    # Dev-only: seed test accounts (never run in production)
    if settings.environment == "development":
        dev_accounts = [
            {"email": "admin@test.com", "is_admin": True},
            {"email": "user@test.com", "is_admin": False},
        ]
        for acct in dev_accounts:
            existing = await db.users.find_one({"email": acct["email"]})
            if not existing:
                await db.users.insert_one({
                    "email": acct["email"],
                    "is_admin": acct["is_admin"],
                    "created_at": datetime.utcnow(),
                })
                logger.info("Seeded dev account: %s (admin=%s)", acct["email"], acct["is_admin"])
            else:
                await db.users.update_one(
                    {"email": acct["email"]},
                    {"$set": {"is_admin": acct["is_admin"]}},
                )

    # Create MongoDB indexes for performance
    try:
        # Users collection
        await db.users.create_index("email", unique=True)
        await db.users.create_index("created_at")

        # Profiles collection
        await db.profiles.create_index("user_id", unique=True)
        await db.profiles.create_index("updated_at")

        # Binders collection
        await db.binders.create_index("user_id")
        await db.binders.create_index("status")
        await db.binders.create_index("created_at")
        await db.binders.create_index([("user_id", 1), ("created_at", -1)])

        # Payments collection
        await db.payments.create_index("user_id")
        await db.payments.create_index("stripe_session_id")
        await db.payments.create_index("created_at")
        await db.payments.create_index("status")

        # Refresh tokens collection
        await db.refresh_tokens.create_index("jti", unique=True)
        await db.refresh_tokens.create_index("user_id")
        await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)

        # Pending OTPs collection (TTL auto-cleanup)
        await db.pending_otps.create_index("email", unique=True)
        await db.pending_otps.create_index("expires_at", expireAfterSeconds=0)

        # Order messages collection
        await db.order_messages.create_index("order_id")
        await db.order_messages.create_index("created_at")

        logger.info("MongoDB indexes created/verified")
    except Exception as e:
        logger.warning(f"Could not create indexes (may already exist): {e}")

    yield
    app.state.mongo.close()


app = FastAPI(title="BinderPro API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Request logging middleware (adds request IDs)
app.add_middleware(RequestLoggingMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Audit logging middleware (logs sensitive data access)
app.add_middleware(AuditLoggingMiddleware)


# ============================================================================
# Global Error Handlers
# ============================================================================

def create_error_response(
    status_code: int,
    code: str,
    message: str,
    detail: str = None,
    path: str = None,
) -> dict:
    """Create standardized error response."""
    return {
        "error": True,
        "status": status_code,
        "code": code,
        "message": message,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat(),
        "path": path,
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    # Create user-friendly message
    fields = [e.get("loc", ["unknown"])[-1] for e in errors]
    message = f"Invalid input for: {', '.join(fields)}"

    logger.warning(f"Validation error on {request.url.path}: {errors}")

    return JSONResponse(
        status_code=422,
        content=create_error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=message,
            detail=str(errors),
            path=str(request.url.path),
        ),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Handle Pydantic model validation errors."""
    logger.warning(f"Pydantic validation error on {request.url.path}: {exc}")

    return JSONResponse(
        status_code=422,
        content=create_error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Invalid data format",
            detail=str(exc.errors()),
            path=str(request.url.path),
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    # Log the full traceback
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    logger.error(traceback.format_exc())

    # Don't expose internal errors to users
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again.",
            detail=None,  # Don't expose internal details
            path=str(request.url.path),
        ),
    )

from app.routes import auth, profile, binders, admin, payments, feedback  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(binders.router, prefix="/api/binders", tags=["binders"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])


@app.get("/api/health")
async def health(request: Request):
    try:
        await request.app.state.db.command("ping")
        db_status = "connected"
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "unreachable"},
        )
    return {"status": "ok", "db": db_status}


@app.get("/api/content-stats")
async def content_stats():
    from app.library.loader import get_all_modules
    from app.library.region import ZIP_PREFIX_TO_REGION
    all_mods = get_all_modules()
    regions = set(ZIP_PREFIX_TO_REGION.values())
    categories = {}
    for mod in all_mods.values():
        cat = mod.get("category") or mod.get("region") or mod.get("home_type") or mod.get("feature") or mod.get("trigger") or "general"
        categories[cat] = categories.get(cat, 0) + 1
    def _count_items(mod: dict) -> int:
        count = len(mod.get("content", []))
        # Playbooks: count phase items
        for phase in mod.get("phases", {}).values():
            count += len(phase) if isinstance(phase, list) else 0
        # Quick start: count card actions
        for card in mod.get("cards", {}).values():
            count += len(card.get("actions", []))
        # Inventory: count systems + base supplies
        count += len(mod.get("systems", []))
        count += len(mod.get("base_supplies", []))
        for supp in mod.get("region_supplements", {}).values():
            count += len(supp.get("items", []))
        return count
    total_items = sum(_count_items(mod) for mod in all_mods.values())
    return {
        "total_modules": len(all_mods),
        "total_items": total_items,
        "regions": sorted(regions),
        "categories": categories,
    }
