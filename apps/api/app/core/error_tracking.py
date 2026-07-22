"""Sentry error tracking — see docs/observability.md#error-tracking-
sentry. `sentry_sdk.init(dsn="")` is a documented no-op (the SDK disables
itself), so this is always called; nothing is sent anywhere until a real
project DSN is configured (staging/production secrets — see
docs/environments.md).
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.types import Event, Hint

from app.core.config import get_settings

_SCRUBBED_HEADERS = {"authorization", "cookie", "x-metrics-token"}


def _before_send(event: Event, _hint: Hint) -> Event | None:
    """Extra scrub on top of `send_default_pii=False` — Sentry's FastAPI
    integration can still attach request headers to an event; this drops
    exactly the ones that double as bearer credentials, mirroring
    app/core/logging.py's redaction list rather than trusting Sentry's own
    defaults alone."""
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            for header_name in list(headers):
                if header_name.lower() in _SCRUBBED_HEADERS:
                    headers[header_name] = "[REDACTED]"
    return event


def configure_error_tracking() -> None:
    settings = get_settings()
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        before_send=_before_send,
    )
