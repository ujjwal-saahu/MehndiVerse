# MehndiVerse — Observability (Phase 28)

## Structured logs

`app/core/logging.py` (structlog, JSON to stdout — already established since Phase 0/24). Every log line has, at minimum: `event`, `level`, `timestamp`, and — for anything logged during a request — `request_id`, `correlation_id`, `method`, `path` (bound automatically, see below; no call site passes these explicitly).

## Correlation IDs and request IDs

`app/core/request_context.py` — middleware on every request:

- **`request_id`** — identifies this one HTTP request/response. Uses the caller's `X-Request-ID` header if present, otherwise generates a UUID4.
- **`correlation_id`** — identifies a logical operation that may span multiple requests/services. Defaults to `request_id` when nothing upstream provides one; a future cross-service caller (e.g. `apps/web`'s `backendFetch`) can set `X-Correlation-ID` to link its own request to the backend calls it triggers.

Both are bound via `structlog.contextvars` (cleared at the start/end of each request — safe under concurrent requests, since Python's `contextvars` are per-`asyncio.Task`) and echoed back as response headers, so a client can correlate its own logs with the server's.

## Error tracking (Sentry)

`app/core/error_tracking.py`, initialized in `create_app()`. `sentry_sdk.init(dsn="")` is a documented no-op — nothing is sent anywhere until `SENTRY_DSN` is set to a real project DSN (staging/production secrets, see docs/environments.md). `send_default_pii=False` plus a `before_send` hook that redacts `Authorization`/`Cookie`/`X-Metrics-Token` headers from any captured event — belt-and-suspenders on top of Sentry's own PII controls, mirroring `app/core/logging.py`'s redaction list rather than trusting a third-party default alone.

## Health and readiness endpoints

Unchanged from Phase 25 (`GET /health/live` — pure liveness, no dependency checks; `GET /health` — readiness, checks DB + Redis). This phase adds a database-health alert on DB failure and a cache-unavailable alert on Redis failure (see [Alerting](#alerting)), and both endpoints are now recorded in the API latency/error-rate metrics like any other request (see [Dashboards and metrics](#dashboards-and-metrics)).

## Uptime monitoring foundation

`GET /health/live` is the target for an external uptime monitor (UptimeRobot, Pingdom, a status-page provider's synthetic check) — unauthenticated, no dependency checks, sub-millisecond. Point it at `https://<api-host>/health/live` on a 1-5 minute interval; alert on 2+ consecutive failures (a single missed check is noise on most networks). `GET /health` is *not* the right target for this — a downstream Postgres/Redis blip would trip an uptime alert for a condition the database-health alert (see [Alerting](#alerting)) already covers with more context.

## Dashboards and metrics

`GET /metrics` (Prometheus exposition format, `app/api/routes/metrics.py`), gated by a shared-secret token (`METRICS_TOKEN` — header `X-Metrics-Token` or `?token=`). **Must be network-restricted** in staging/production (reverse proxy / private network / Prometheus's own scrape-target allowlist) — the token is defense-in-depth, not the only control, same reasoning as every other network-facing secret in this codebase.

No live Grafana/Datadog instance exists to screenshot in this environment — each dashboard panel below is defined by its exact metric name and PromQL, ready to paste into whichever tool is provisioned.

| Dashboard panel | Metric / query |
|---|---|
| **API latency** | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))` (p95 per route) |
| **Error rate** | `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **Request volume** | `sum(rate(http_requests_total[5m])) by (route)` |
| **Database latency** | No dedicated histogram yet (see [What isn't instrumented yet](#what-isnt-instrumented-yet)) — proxy today: `/health` appearing in `http_request_duration_seconds` with an elevated value is the current signal. |
| **Queue depth** | `ai_job_queue_depth` (a `Histogram`, recorded once per `process_ai_jobs` run — see `count_pending_ai_jobs()`); graph the observed value over time, not a rate. |
| **Failed jobs** | `sum(rate(background_job_runs_total{outcome="failure"}[1h])) by (job)` |
| **Payment failures** | `sum(rate(payment_webhook_events_total{outcome="payment_failed"}[1h]))` |
| **Booking conversion** | Already computed, not a Prometheus metric — `app/services/analytics/booking_analytics.py::get_booking_conversion_funnel()` (Phase 22), surfaced via `GET /admin/analytics/booking-conversion`. Not duplicated here to avoid two disagreeing sources of truth for the same number. |
| **Active users** | Already computed via `AnalyticsEvent` (Phase 22, `app_opened`/session-level events) — `docs/analytics-and-recommendations.md`. Same reasoning as booking conversion: the analytics-event pipeline is the source of truth, not a new Prometheus counter. |
| **Crash-free mobile sessions** | **Not implemented** — requires a mobile crash reporter (Sentry Flutter or Firebase Crashlytics) integrated into `apps/mobile`. No Flutter/Dart toolchain exists in this environment to add and verify that dependency (same constraint noted in docs/test-matrix.md) — recommended follow-up: add `sentry_flutter` (consistent with this phase's backend choice) and initialize it in `apps/mobile/lib/main.dart`. |

## Background-worker monitoring

Every `app/cli/process_*.py` / `reconcile_payments.py` run records `background_job_runs_total{job=<name>, outcome="success"|"failure"}` and, on failure, calls [`send_alert`](#alerting). `process_ai_jobs` additionally records `ai_job_queue_depth` (pending-job count after the run) and alerts on **exhausted** AI jobs specifically (see below) — a job still retrying is not itself alert-worthy.

## Payment-webhook monitoring

`payment_webhook_events_total{outcome=...}` in `app/services/payments/service.py::handle_webhook` — outcomes: `settled`, `payment_failed`, `refund`, `duplicate` (idempotent replay, expected/benign), `signature_invalid`, `error` (unreferenceable event), `ignored` (an event type this app doesn't track). A signature-invalid spike triggers the same investigation as docs/incident-response.md#payment-webhook-anomaly.

## Alerting

`app/core/alerts.py::send_alert(event, severity="error", **details)` — a two-tier foundation (see that module's docstring): always logs at ERROR (zero external dependency), and additionally POSTs a Slack-compatible payload to `ALERT_WEBHOOK_URL` if one is configured (empty by default). A 5-minute per-event-name cooldown prevents a sustained outage from spamming the webhook on every poll/retry — the ERROR log itself is never cooled down, since log aggregators handle their own volume/dedup.

Wired into:

- **Database-health alerts** — `GET /health`'s DB-connect failure (`send_alert("database_unavailable", ...)`, `app/api/routes/health.py`). The same endpoint's Redis-ping failure sends `cache_unavailable` alongside it.
- **Storage-error alerts** — `CircuitBreaker` opening for `supabase_storage` (`send_alert("circuit_breaker_opened", service="supabase_storage", ...)`, `app/core/resilience.py`; the same mechanism also covers `supabase_auth`, though that's not literally "storage").
- **AI-provider failure alerts** — an `AiJob` reaching terminal `failed` status after exhausting `max_attempts` (`app/services/ai/jobs.py::fail_job`).
- **Failed-job alerts** — every background CLI's uncaught exception (see above).
- Razorpay's circuit breaker opening (payment-provider connectivity, distinct from the payment-webhook outcome metrics above).

## Log redaction

`app/core/logging.py::_redact_sensitive_fields` (extended this phase). Two mechanisms:

1. **Key-name matching** (case-insensitive): `password`, `access_token`, `refresh_token`, `token`, `authorization`, `secret`, `signature`, `jwt`, `client_secret`, `api_key`, and — new this phase — `email`/`to_email`/`contact_email`/`phone`/`to_phone`/`contact_phone` (sensitive user details). Fixed one real call site this caught: `app/integrations/email_notifications.py` was logging a raw email address under `to_email=`.
2. **Value-shape matching** (new this phase): any string value containing `/storage/v1/object/sign/` (a Supabase signed private-document URL — verification documents, hand/foot preview photos, AI generation results) has its query string redacted regardless of which kwarg it's logged under, since the query string *is* the bearer credential for that private file. No call site logs one today (audited every `logger.*()` call site in the codebase), but this protects a future one.

Tests: `tests/core/test_log_redaction.py`.

## What isn't instrumented yet

- No per-database-query latency histogram (only whole-request duration, which includes DB time as part of it). Adding one would mean instrumenting SQLAlchemy's event hooks (`before_cursor_execute`/`after_cursor_execute`) — not done this phase; the request-duration metric is a reasonable proxy until it is.
- No distributed tracing (OpenTelemetry spans) — request/correlation IDs give log-based correlation across services today; a real trace waterfall is a larger addition than this phase's scope.
- Crash-free mobile sessions (see the dashboard table above).

## Related documents

- [docs/runbook.md](runbook.md)
- [docs/incident-response.md](incident-response.md)
- [docs/performance-and-reliability.md](performance-and-reliability.md) — the circuit breakers/health endpoints this phase adds alerting on top of.
- [docs/security-review.md#sensitive-log-redaction](security-review.md#sensitive-log-redaction) — the original redaction work this phase extends.
