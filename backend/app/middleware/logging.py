"""Request logging middleware with request IDs for tracing."""

import uuid
import time
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("home_binder.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that adds request IDs and logs requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        logger.info(
            "[%s] %s %s",
            request_id,
            request.method,
            request.url.path,
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            "[%s] %s %s -> %d (%.1fms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id

        return response
