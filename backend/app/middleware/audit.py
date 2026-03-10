"""Audit logging middleware — logs sensitive data access to MongoDB."""

import logging
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths that access sensitive data and should be audit-logged
AUDITED_PATHS = {
    "/api/profile/export": "data_export",
    "/api/profile/": "profile_access",
}

# Patterns for dynamic paths (checked via startswith)
AUDITED_PATTERNS = [
    ("/api/binders/", "/download", "pdf_download"),
]


def _get_audit_action(path: str, method: str) -> str | None:
    """Determine audit action for a given path."""
    if method == "DELETE" and path == "/api/profile/":
        return "account_deletion"

    if method == "GET":
        # Exact matches
        action = AUDITED_PATHS.get(path)
        if action:
            return action

        # Pattern matches (download endpoints)
        for prefix, suffix, action in AUDITED_PATTERNS:
            if path.startswith(prefix) and suffix in path:
                return action

    return None


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Only log successful access to sensitive endpoints
        if response.status_code < 400:
            action = _get_audit_action(request.url.path, request.method)
            if action:
                await self._log_access(request, action, response.status_code)

        return response

    async def _log_access(self, request: Request, action: str, status_code: int):
        """Write audit entry to MongoDB."""
        try:
            # Extract user_id from JWT if present
            user_id = None
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                from jose import jwt as jose_jwt
                from app.config import settings
                try:
                    payload = jose_jwt.decode(auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
                    user_id = payload.get("sub")
                except Exception:
                    pass

            entry = {
                "action": action,
                "user_id": user_id,
                "path": str(request.url.path),
                "method": request.method,
                "status_code": status_code,
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "")[:200],
                "timestamp": datetime.utcnow(),
            }

            db = request.app.state.db
            await db.audit_log.insert_one(entry)
        except Exception as e:
            # Never let audit logging break the request
            logger.warning("Audit log write failed: %s", e)
