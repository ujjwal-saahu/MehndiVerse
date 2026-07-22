"""Request ID / correlation ID middleware — see docs/observability.md
#correlation-ids-and-request-ids.

`request_id` identifies *this* HTTP request/response pair (generated fresh
if the caller doesn't supply one). `correlation_id` identifies a logical
operation that may span multiple requests/services (e.g. apps/web's
server-side `backendFetch` forwarding a correlation id it received from the
browser, or a background job triggered by a request) — it defaults to the
request id when nothing upstream provided one, so every log line always has
both bound, and they're only ever different when something upstream chose
to link them into a wider chain deliberately.

Both are bound via `structlog.contextvars`, which the existing processor
chain (`app/core/logging.py::configure_logging`) already merges into every
log line for the lifetime of the request — no call site needs to pass
either explicitly.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

from app.core.logging import get_logger
from app.core.metrics import observe_http_request

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

logger = get_logger(__name__)


def add_request_context(app: FastAPI) -> None:
    @app.middleware("http")
    async def _request_context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        duration_seconds = time.perf_counter() - start

        # The one log line "performance monitoring" and "request volume"/
        # "error rate" dashboards are built from — see
        # docs/observability.md#api-latency and #error-rate. Uses the
        # route *template* (request.scope["route"].path_format, e.g.
        # "/designs/{id}") where available so metrics/log queries aren't
        # fragmented per unique UUID.
        route = request.scope.get("route")
        route_path = getattr(route, "path_format", request.url.path)
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=round(duration_seconds * 1000, 2),
            route=route_path,
        )
        observe_http_request(
            method=request.method,
            route=route_path,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
