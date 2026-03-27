"""Redis-backed sliding-window rate limiting middleware."""

import time
import logging
from typing import Callable, Awaitable

import redis.asyncio as aioredis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("home_binder.rate_limit")

_redis: aioredis.Redis | None = None

# Evicts stale entries, then only records request if count is below limit.
# Returns: {allowed (1/0), current_count, oldest_score_or_0}
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, tostring(now))
    redis.call('EXPIRE', key, window)
    return {1, count + 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = 0
    if #oldest > 0 then
        oldest_score = tonumber(oldest[2])
    end
    return {0, count, oldest_score}
end
"""


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        from app.config import settings
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _check_rate(limiter: str, key: str, limit: int, window: int) -> tuple[bool, int]:
    """Atomic sliding-window rate limit using a Redis Lua script.

    Returns (allowed, retry_after_seconds).
    - allowed is True if the request is within the limit.
    - retry_after_seconds is the number of seconds until the window clears
      (only meaningful when allowed is False).

    Denied requests are never recorded in Redis, so the window cannot be
    extended indefinitely by a flood of rejected retries.
    """
    redis_key = f"rl:{limiter}:{key}"
    now = time.time()

    result = await _get_redis().eval(  # type: ignore[attr-defined]
        _RATE_LIMIT_SCRIPT, 1, redis_key, limit, window, now
    )

    allowed = bool(result[0])
    oldest_score = float(result[2])

    retry_after = window  # default fallback
    if not allowed and oldest_score:
        retry_after = max(1, int(oldest_score + window - now) + 1)

    return allowed, retry_after


def _get_trusted_proxies() -> set[str]:
    """Return the set of trusted proxy IPs from settings (cached per import)."""
    from app.config import settings
    raw = settings.trusted_proxies.strip()
    if not raw:
        return set()
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


def _get_client_ip(request: Request) -> str:
    """Return the real client IP.

    X-Forwarded-For is only trusted when the immediate peer (request.client.host)
    is in the TRUSTED_PROXIES list.  Without this guard an attacker can spoof the
    header to bypass per-IP rate limiting.  Deployments behind a reverse proxy
    must set TRUSTED_PROXIES to the proxy's IP(s).

    When trusted, the rightmost non-proxy IP in the XFF chain is used to avoid
    header-injection by earlier hops.
    """
    peer_ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")

    if forwarded and peer_ip and peer_ip in _get_trusted_proxies():
        # Use the rightmost entry — this is the last hop added by our trusted proxy
        # and cannot be forged by the original client.
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]

    return peer_ip or "unknown"


def _rate_limit_response(message: str, detail: str, retry_after: int) -> JSONResponse:
    """Build a 429 JSON response with a Retry-After header."""
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "code": "RATE_LIMITED",
            "message": message,
            "detail": detail,
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Route-aware rate limiting backed by Redis."""

    AUTH_PATHS = {
        "/api/auth/request-otp",
        "/api/auth/verify-otp",
        "/api/auth/login-password",
    }
    GENERATION_PATHS = {"/api/binders/generate"}
    ADMIN_PATH_PREFIX = "/api/admin"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        from app.config import settings
        if settings.environment not in ("production", "staging"):
            return await call_next(request)

        path = request.url.path
        ip = _get_client_ip(request)

        try:
            if path in self.AUTH_PATHS:
                allowed, retry_after = await _check_rate("auth", ip, limit=5, window=60)
                if not allowed:
                    logger.warning("Auth rate limit exceeded for %s", ip)
                    return _rate_limit_response(
                        "Too many requests. Please wait a moment before trying again.",
                        "Auth rate limit exceeded",
                        retry_after,
                    )

            elif path in self.GENERATION_PATHS:
                allowed, retry_after = await _check_rate("gen", ip, limit=2, window=60)
                if not allowed:
                    logger.warning("Generation rate limit exceeded for %s", ip)
                    return _rate_limit_response(
                        "Please wait before generating another binder.",
                        "Generation rate limit exceeded",
                        retry_after,
                    )

            elif path.startswith(self.ADMIN_PATH_PREFIX):
                allowed, retry_after = await _check_rate("admin", ip, limit=30, window=60)
                if not allowed:
                    logger.warning("Admin rate limit exceeded for %s", ip)
                    return _rate_limit_response(
                        "Too many requests. Please slow down.",
                        "Admin rate limit exceeded",
                        retry_after,
                    )

            elif path.startswith("/api/"):
                allowed, retry_after = await _check_rate("api", ip, limit=60, window=60)
                if not allowed:
                    logger.warning("API rate limit exceeded for %s", ip)
                    return _rate_limit_response(
                        "Too many requests. Please slow down.",
                        "API rate limit exceeded",
                        retry_after,
                    )

        except Exception as exc:
            # Open failure if Redis is unavailable, allow the request through
            # rather than blocking all traffic. Log so ops can respond.
            logger.error("Rate limiter Redis error (failing open): %s", exc)

        return await call_next(request)
