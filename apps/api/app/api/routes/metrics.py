"""GET /metrics — Prometheus scrape endpoint. See
docs/observability.md#dashboards-and-metrics.

Gated by a shared-secret `?token=` (or `X-Metrics-Token` header) query
param, checked with `hmac.compare_digest` — defense-in-depth on top of the
network-level restriction (reverse proxy / private network) that must also
be in place in staging/production; see app/core/config.py::metrics_token's
docstring for why the local-dev default is a fixed non-secret string.
"""

import hmac

from fastapi import APIRouter, Header, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def metrics(request: Request, x_metrics_token: str | None = Header(default=None)) -> Response:
    settings = get_settings()
    provided = x_metrics_token or request.query_params.get("token") or ""
    if not hmac.compare_digest(provided, settings.metrics_token):
        raise AuthenticationError("Invalid or missing metrics token.")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
