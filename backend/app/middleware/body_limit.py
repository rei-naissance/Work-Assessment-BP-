"""Middleware to reject requests whose Content-Length exceeds the configured limit.

Checked at the header level (fast path). A missing Content-Length header is
allowed through; the reverse proxy (Cloudflare / Nginx / Caddy) should enforce
a hard cap there.  This catches well-behaved clients that do declare a size.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Paths that legitimately carry larger payloads (PDF download, etc.)
_LARGE_BODY_PATHS: set[str] = set()

_DEFAULT_MAX_BYTES = 512 * 1024  # 512 KB — generous for JSON API payloads


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = _DEFAULT_MAX_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _LARGE_BODY_PATHS:
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": True,
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Request body exceeds the maximum allowed size.",
                },
            )
        return await call_next(request)
