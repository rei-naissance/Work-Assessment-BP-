"""
Standardized error handling for BinderPro API.

Usage:
    from app.errors import raise_error, ErrorCode

    # Raise a standardized error
    raise_error(ErrorCode.NOT_FOUND, "Binder not found")

    # With custom detail
    raise_error(ErrorCode.VALIDATION, "Invalid email", detail="Must be a valid email address")
"""
from enum import Enum
from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Standard error codes for consistent error handling."""
    # Auth errors (401, 403)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Validation errors (400, 422)
    VALIDATION = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    BINDER_NOT_FOUND = "BINDER_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"

    # Conflict errors (409)
    ALREADY_EXISTS = "ALREADY_EXISTS"
    DUPLICATE = "DUPLICATE"

    # Payment errors (402, 400)
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    INVALID_PAYMENT = "INVALID_PAYMENT"

    # Rate limiting (429)
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (500)
    INTERNAL = "INTERNAL_ERROR"
    DATABASE = "DATABASE_ERROR"
    GENERATION_FAILED = "GENERATION_FAILED"
    EMAIL_FAILED = "EMAIL_FAILED"


# Map error codes to HTTP status codes
ERROR_STATUS_CODES = {
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INVALID_TOKEN: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.VALIDATION: 422,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_FIELD: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.BINDER_NOT_FOUND: 404,
    ErrorCode.PROFILE_NOT_FOUND: 404,
    ErrorCode.ALREADY_EXISTS: 409,
    ErrorCode.DUPLICATE: 409,
    ErrorCode.PAYMENT_REQUIRED: 402,
    ErrorCode.PAYMENT_FAILED: 400,
    ErrorCode.INVALID_PAYMENT: 400,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL: 500,
    ErrorCode.DATABASE: 500,
    ErrorCode.GENERATION_FAILED: 500,
    ErrorCode.EMAIL_FAILED: 500,
}


def raise_error(
    code: ErrorCode,
    message: str,
    detail: str = None,
) -> None:
    """
    Raise a standardized HTTP exception.

    Args:
        code: ErrorCode enum value
        message: User-friendly error message
        detail: Optional technical detail for debugging
    """
    status_code = ERROR_STATUS_CODES.get(code, 500)
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code.value,
            "message": message,
            "detail": detail,
        }
    )


def handle_db_error(operation: str, error: Exception) -> None:
    """
    Handle database errors with logging and standardized response.

    Args:
        operation: Description of the operation that failed
        error: The exception that was raised
    """
    import logging
    logger = logging.getLogger("home_binder")
    logger.error(f"Database error during {operation}: {error}")
    raise_error(
        ErrorCode.DATABASE,
        f"A database error occurred while {operation}. Please try again.",
        detail=str(error) if error else None,
    )
