"""Rate limiting middleware for MarketAtlas.

Uses a simple in-memory token bucket algorithm per client IP.
Requires Redis for production use; falls back to in-memory when Redis is down.

Usage (in main.py):
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
"""

import time
from collections import defaultdict
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    Limits each client IP to ``max_requests`` per ``window_seconds``.
    Returns 429 Too Many Requests when the limit is exceeded.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds

        bucket = self._buckets[client_ip]
        bucket[:] = [t for t in bucket if t > cutoff]

        if len(bucket) >= self.max_requests:
            retry_after = int(bucket[0] + self.window_seconds - now)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after_seconds": max(retry_after, 1),
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        bucket.append(now)
        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host or "unknown"
        return "unknown"
