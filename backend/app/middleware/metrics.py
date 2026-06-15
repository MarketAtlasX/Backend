"""Prometheus metrics middleware for MarketAtlas.

Exposes:

- ``marketatlas_http_requests_total`` — counter by method, path, status
- ``marketatlas_http_request_duration_seconds`` — histogram
- ``marketatlas_db_pool_size`` — gauge (current DB pool size)
- ``marketatlas_cache_hits_total`` / ``marketatlas_cache_misses_total``

Metrics are exposed at ``GET /metrics`` via a Prometheus client.
"""

import time

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

http_requests_total = Counter(
    "marketatlas_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration = Histogram(
    "marketatlas_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

cache_hits = Counter("marketatlas_cache_hits_total", "Cache hit count")
cache_misses = Counter("marketatlas_cache_misses_total", "Cache miss count")

db_pool_size = Gauge("marketatlas_db_pool_size", "Current DB connection pool size")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records Prometheus metrics for each request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return Response(
                content=generate_latest(),
                headers={"Content-Type": CONTENT_TYPE_LATEST},
            )

        method = request.method
        path = request.url.path
        start_time = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            http_requests_total.labels(method=method, path=path, status="500").inc()
            raise

        duration = time.monotonic() - start_time
        status_group = f"{response.status_code // 100}xx"

        http_requests_total.labels(method=method, path=path, status=status_group).inc()
        http_request_duration.labels(method=method, path=path).observe(duration)

        return response
