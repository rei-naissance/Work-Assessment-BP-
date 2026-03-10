"""Input validation utilities for BinderPro."""

import re
import html
from typing import Optional


# Phone number regex - accepts various US formats
PHONE_REGEX = re.compile(
    r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{4,6}[-\s\.]?[0-9]{0,4}$'
)

# US ZIP code regex - 5 digits or 5+4 format
ZIP_REGEX = re.compile(r'^[0-9]{5}(-[0-9]{4})?$')

# Email regex (basic validation)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Characters that could be used in XSS attacks
XSS_PATTERNS = [
    '<script', '</script>', 'javascript:', 'onerror=', 'onclick=',
    'onload=', 'onfocus=', 'onmouseover=', '<iframe', '<object',
    '<embed', '<svg', 'expression(', 'url(data:',
]


def validate_phone(phone: str) -> bool:
    """Validate phone number format. Returns True if valid or empty."""
    if not phone or not phone.strip():
        return True  # Empty is OK
    cleaned = phone.strip()
    return bool(PHONE_REGEX.match(cleaned))


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing extra characters."""
    if not phone:
        return ""
    # Remove common separators and clean
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    return cleaned


def validate_zip_code(zip_code: str) -> bool:
    """Validate US ZIP code format. Returns True if valid or empty."""
    if not zip_code or not zip_code.strip():
        return True  # Empty is OK
    return bool(ZIP_REGEX.match(zip_code.strip()))


def validate_email(email: str) -> bool:
    """Validate email format. Returns True if valid or empty."""
    if not email or not email.strip():
        return True  # Empty is OK
    return bool(EMAIL_REGEX.match(email.strip().lower()))


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize a string input to prevent XSS attacks.

    - HTML encodes special characters
    - Truncates to max length
    - Strips leading/trailing whitespace
    """
    if not value:
        return ""

    # Truncate first to limit processing
    if len(value) > max_length:
        value = value[:max_length]

    # HTML encode to prevent XSS
    sanitized = html.escape(value.strip())

    return sanitized


def contains_xss(value: str) -> bool:
    """Check if a string contains potential XSS patterns."""
    if not value:
        return False
    lower = value.lower()
    return any(pattern in lower for pattern in XSS_PATTERNS)


def sanitize_profile_data(data: dict) -> dict:
    """Recursively sanitize all string values in a profile dict."""
    if isinstance(data, dict):
        return {k: sanitize_profile_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_profile_data(item) for item in data]
    elif isinstance(data, str):
        return sanitize_string(data)
    return data
