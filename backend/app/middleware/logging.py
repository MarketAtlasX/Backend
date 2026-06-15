"""Structured request/response logging middleware.

Logs every request with:
- Request ID (UUID) for tracing across services
- Method, path, status code, duration
- Client IP and user agent

Output is JSON-formatted for ingestion by log aggregators (ELK, Loki, etc.).
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("marketatlas.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs structured request/response data."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.monotonic()
        method = request.method
        path = request.url.path
        query = str(request.url.query)

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "query": query,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
            )
            raise

        duration_ms = (time.monotonic() - start_time) * 1000
        status_code = response.status_code

        if status_code < 400:
            log_fn = logger.info
        elif status_code < 500:
            log_fn = logger.warning
        else:
            log_fn = logger.error

        log_fn(
            "%s %s -> %d (%.1fms)",
            method,
            path,
            status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query": query,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response
