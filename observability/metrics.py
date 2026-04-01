"""Prometheus metrics for the AgentForge API."""

from __future__ import annotations

import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ── Metric Definitions ──────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "agentforge_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "agentforge_http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_REQUESTS = Gauge(
    "agentforge_http_active_requests",
    "Currently active HTTP requests",
)

AGENT_RUNS_TOTAL = Counter(
    "agentforge_agent_runs_total",
    "Total agent runs",
    labelnames=["agent_id", "status"],
)

AGENT_RUN_LATENCY = Histogram(
    "agentforge_agent_run_duration_seconds",
    "Agent run latency in seconds",
    labelnames=["agent_id", "provider"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

TOKENS_USED = Counter(
    "agentforge_tokens_used_total",
    "Total tokens consumed",
    labelnames=["agent_id", "provider"],
)

DB_POOL_SIZE = Gauge(
    "agentforge_db_pool_size",
    "Current database connection pool size",
)


# ── Middleware ───────────────────────────────────────────────────────────────


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request count, latency, and active connections."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        ACTIVE_REQUESTS.dec()

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(duration)

        return response


# ── Endpoint ─────────────────────────────────────────────────────────────────


async def metrics_endpoint(request: Request) -> Response:
    """Return Prometheus metrics in text exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
