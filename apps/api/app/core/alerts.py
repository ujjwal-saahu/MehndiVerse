"""Failed-job / dependency-health alerting — see docs/observability.md
#alerting. No paging/on-call tool (PagerDuty, Opsgenie) is wired up in this
environment, so this is deliberately a two-tier foundation:

1. Always logs at ERROR level — this alone makes the event visible to
   whatever log aggregation the deployment uses (CloudWatch/Datadog/etc.
   log-based alert rules — see docs/runbook.md for example queries), with
   zero external dependency.
2. Additionally POSTs a Slack-compatible incoming-webhook payload *if*
   `alert_webhook_url` is configured (empty by default — a real deployment
   sets it via the "staging"/"production" secrets, same pattern as every
   other environment-gated credential in this codebase).

Never raises: a broken alert channel must never take down the request/job
that triggered the alert.
"""

import time

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# A readiness probe alone can call this every few seconds under a load
# balancer's health check — without de-duplication, a sustained outage
# would fire a new webhook alert on every poll instead of once per
# incident. Per-process, in-memory (matches CircuitBreaker's own scope —
# see app/core/resilience.py); a multi-replica deployment gets one alert
# per replica, not one globally, which is an acceptable tradeoff for a
# foundation without a shared alert-dedup store.
_ALERT_COOLDOWN_SECONDS = 300.0
_last_sent_at: dict[str, float] = {}


def send_alert(event: str, *, severity: str = "error", **details: object) -> None:
    logger.error(f"alert.{event}", severity=severity, **details)

    webhook_url = get_settings().alert_webhook_url
    if not webhook_url:
        return

    now = time.monotonic()
    if now - _last_sent_at.get(event, 0.0) < _ALERT_COOLDOWN_SECONDS:
        return
    _last_sent_at[event] = now

    detail_lines = "\n".join(f"- {key}: {value}" for key, value in details.items())
    text = f":rotating_light: *{event}* ({severity})\n{detail_lines}"
    try:
        httpx.post(webhook_url, json={"text": text}, timeout=5.0)
    except httpx.HTTPError:
        logger.warning("alert_webhook_delivery_failed", alert_event=event)
