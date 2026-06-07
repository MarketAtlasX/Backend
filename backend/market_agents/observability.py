"""Observability, logging, rate limiting, and metrics helpers."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI, Response
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from market_agents.contracts import HealthResponse

_TRACING_CONFIGURED = False

REQUEST_COUNT = Counter(
    "marketatlas_http_requests_total",
    "HTTP requests processed by MarketAtlas services.",
    ["service", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "marketatlas_http_request_duration_seconds",
    "HTTP request latency for MarketAtlas services.",
    ["service", "method", "path"],
)
CODE_PATH_LATENCY = Histogram(
    "marketatlas_code_path_duration_seconds",
    "Critical code path latency for MarketAtlas services.",
    ["service", "path"],
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("service", "request_id", "path", "method", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(service_name: str) -> logging.Logger:
    logger = logging.getLogger("marketatlas")
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logging.LoggerAdapter(logger, {"service": service_name})


def configure_tracing(service_name: str) -> None:
    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED:
        return
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
        except Exception:
            logging.getLogger("marketatlas").exception("otel_exporter_setup_failed")
    trace.set_tracer_provider(provider)
    _TRACING_CONFIGURED = True


def instrument_app(app: FastAPI, service_name: str) -> None:
    configure_tracing(service_name)
    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def metrics_and_logs(request, call_next):
        start = time.perf_counter()
        status_code = 500
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            path = request.scope.get("route").path if request.scope.get("route") else request.url.path
            REQUEST_COUNT.labels(service_name, request.method, path, str(status_code)).inc()
            REQUEST_LATENCY.labels(service_name, request.method, path).observe(duration)
            logging.getLogger("marketatlas").info(
                "request_complete",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@contextmanager
def traced_path(service_name: str, path_name: str) -> Iterator[None]:
    tracer = trace.get_tracer(service_name)
    start = time.perf_counter()
    with tracer.start_as_current_span(path_name):
        try:
            yield
        finally:
            CODE_PATH_LATENCY.labels(service_name, path_name).observe(time.perf_counter() - start)
