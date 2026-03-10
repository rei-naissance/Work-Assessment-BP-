"""Field-level encryption for sensitive profile data.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
Auto-generates a key in development mode if not set.
"""

import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

# Sensitive fields that get encrypted before MongoDB storage
ENCRYPTED_FIELDS = {
    "guest_sitter_mode.wifi_password",
    "guest_sitter_mode.garage_code",
    "guest_sitter_mode.alarm_instructions",
    "contacts_vendors.insurance.policy_number",
}

# Prefix to identify encrypted values (avoids double-encryption)
ENCRYPTED_PREFIX = "enc:1:"


def _get_fernet() -> Fernet | None:
    key = settings.encryption_key
    if not key:
        if settings.environment == "production":
            logger.error("ENCRYPTION_KEY is required in production")
            return None
        return None

    try:
        # Ensure valid Fernet key (32 url-safe base64-encoded bytes)
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error("Invalid ENCRYPTION_KEY: %s", e)
        return None


def encrypt_value(value: str) -> str:
    if not value or not value.strip():
        return value
    if value.startswith(ENCRYPTED_PREFIX):
        return value  # Already encrypted

    f = _get_fernet()
    if not f:
        if settings.environment == "production":
            raise RuntimeError("Encryption key required in production — cannot store sensitive data unencrypted")
        return value  # No key configured — store plaintext (dev mode)

    try:
        encrypted = f.encrypt(value.encode())
        return ENCRYPTED_PREFIX + encrypted.decode()
    except Exception as e:
        if settings.environment == "production":
            raise RuntimeError(f"Encryption failed in production: {e}")
        logger.warning("Encryption failed: %s", e)
        return value


def decrypt_value(value: str) -> str:
    if not value or not value.startswith(ENCRYPTED_PREFIX):
        return value  # Not encrypted — return as-is

    f = _get_fernet()
    if not f:
        logger.warning("Cannot decrypt: no ENCRYPTION_KEY configured")
        return "[encrypted — key unavailable]"

    try:
        token = value[len(ENCRYPTED_PREFIX):].encode()
        return f.decrypt(token).decode()
    except InvalidToken:
        logger.warning("Decryption failed: invalid token (key rotation?)")
        return "[encrypted — decryption failed]"
    except Exception as e:
        logger.warning("Decryption error: %s", e)
        return value


def _get_nested(data: dict, path: str):
    """Get a nested dict value by dot-separated path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _set_nested(data: dict, path: str, value):
    """Set a nested dict value by dot-separated path."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            return
        current = current[key]
    current[keys[-1]] = value


def encrypt_profile_fields(profile_data: dict) -> dict:
    """Encrypt sensitive fields in a profile dict before MongoDB storage."""
    for field_path in ENCRYPTED_FIELDS:
        val = _get_nested(profile_data, field_path)
        if val and isinstance(val, str):
            _set_nested(profile_data, field_path, encrypt_value(val))
    return profile_data


def decrypt_profile_fields(profile_data: dict) -> dict:
    """Decrypt sensitive fields in a profile dict after MongoDB read."""
    for field_path in ENCRYPTED_FIELDS:
        val = _get_nested(profile_data, field_path)
        if val and isinstance(val, str):
            _set_nested(profile_data, field_path, decrypt_value(val))
    return profile_data


def mask_value(value: str, show_last: int = 4) -> str:
    """Mask a sensitive value for export/display, showing only last N chars."""
    if not value or not value.strip():
        return value
    if value.startswith(ENCRYPTED_PREFIX):
        return "****"
    if len(value) <= show_last:
        return "****"
    return "*" * (len(value) - show_last) + value[-show_last:]


def mask_profile_fields(profile_data: dict) -> dict:
    """Mask sensitive fields for export responses."""
    mask_map = {
        "guest_sitter_mode.wifi_password": 4,
        "guest_sitter_mode.garage_code": 0,  # fully mask
        "guest_sitter_mode.alarm_instructions": 0,
        "contacts_vendors.insurance.policy_number": 4,
    }
    for field_path, show_last in mask_map.items():
        val = _get_nested(profile_data, field_path)
        if val and isinstance(val, str) and val.strip():
            if show_last == 0:
                _set_nested(profile_data, field_path, "[REDACTED — included in binder]")
            else:
                _set_nested(profile_data, field_path, mask_value(val, show_last))
    return profile_data


def generate_encryption_key() -> str:
    """Generate a new Fernet key for .env configuration."""
    return Fernet.generate_key().decode()
