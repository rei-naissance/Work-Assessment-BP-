"""Simple in-memory rate limiting for auth endpoints."""

import time
import logging
from collections import defaultdict
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("home_binder.rate_limit")


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 10, burst: int = 15):
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.tokens = defaultdict(lambda: burst)
        self.last_update = defaultdict(float)

    def _get_key(self, request: Request) -> str:
        """Get rate limit key from request (IP address)."""
        # Get real IP from X-Forwarded-For header if behind proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def is_allowed(self, request: Request) -> bool:
        """Check if request is allowed under rate limit."""
        key = self._get_key(request)
        now = time.time()

        # Refill tokens based on time passed
        time_passed = now - self.last_update[key]
        self.tokens[key] = min(
            self.burst,
            self.tokens[key] + time_passed * (self.requests_per_minute / 60)
        )
        self.last_update[key] = now

        # Check if we have tokens
        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True

        logger.warning(f"Rate limit exceeded for {key}")
        return False

    def cleanup(self, max_age: int = 3600):
        """Remove old entries to prevent memory growth."""
        now = time.time()
        expired = [k for k, v in self.last_update.items() if now - v > max_age]
        for key in expired:
            del self.tokens[key]
            del self.last_update[key]


# Global rate limiters for different endpoint types
auth_limiter = RateLimiter(requests_per_minute=5, burst=10)  # Strict for auth
generation_limiter = RateLimiter(requests_per_minute=2, burst=3)  # Expensive operations
api_limiter = RateLimiter(requests_per_minute=60, burst=100)  # General API


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    # Paths that use the strict auth limiter
    AUTH_PATHS = {"/api/auth/request-otp", "/api/auth/verify-otp", "/api/auth/login-password"}
    # Paths that use the generation limiter (expensive operations)
    GENERATION_PATHS = {"/api/binders/generate"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path

        # Use strict limiter for auth endpoints
        if path in self.AUTH_PATHS:
            if not auth_limiter.is_allowed(request):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": True,
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please wait a moment before trying again.",
                        "detail": "Auth rate limit exceeded",
                    }
                )

        # Use generation limiter for expensive operations
        elif path in self.GENERATION_PATHS:
            if not generation_limiter.is_allowed(request):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": True,
                        "code": "RATE_LIMITED",
                        "message": "Please wait before generating another binder.",
                        "detail": "Generation rate limit exceeded",
                    }
                )

        # General API rate limiting (less strict)
        elif path.startswith("/api/"):
            if not api_limiter.is_allowed(request):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": True,
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down.",
                        "detail": "API rate limit exceeded",
                    }
                )

        return await call_next(request)
