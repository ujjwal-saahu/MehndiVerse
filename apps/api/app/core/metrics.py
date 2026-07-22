"""Prometheus metrics — see docs/observability.md#dashboards-and-metrics
for what each metric backs and the exact queries to build a dashboard panel
from it. `/metrics` is registered in app/main.py and is *not* meant to be
public-internet-reachable in production — see that doc's note on putting it
behind the reverse proxy / internal network, same as any Prometheus target.
"""

from prometheus_client import Counter, Histogram

# --- HTTP (API latency / error rate / request volume) -----------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled.",
    ["method", "route", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "route"],
)


def observe_http_request(
    *, method: str, route: str, status_code: int, duration_seconds: float
) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(duration_seconds)


# --- Background jobs (failed jobs / queue depth) -----------------------------

BACKGROUND_JOB_RUNS_TOTAL = Counter(
    "background_job_runs_total",
    "Background CLI job runs, by job name and outcome.",
    ["job", "outcome"],  # outcome: success | failure
)

AI_JOB_QUEUE_DEPTH = Histogram(
    "ai_job_queue_depth",
    "Number of AI jobs still pending/processing at the end of a process_ai_jobs run.",
    buckets=(0, 1, 5, 10, 25, 50, 100, 250),
)


def observe_background_job(job: str, *, success: bool) -> None:
    BACKGROUND_JOB_RUNS_TOTAL.labels(job=job, outcome="success" if success else "failure").inc()


# --- Payments (payment failures) ---------------------------------------------

PAYMENT_WEBHOOK_EVENTS_TOTAL = Counter(
    "payment_webhook_events_total",
    "Payment provider webhook deliveries, by outcome.",
    ["outcome"],  # outcome: settled | signature_invalid | error
)


def observe_payment_webhook(outcome: str) -> None:
    PAYMENT_WEBHOOK_EVENTS_TOTAL.labels(outcome=outcome).inc()


# --- Third-party dependency health (AI-provider failure / storage-error) ----

DEPENDENCY_CALL_FAILURES_TOTAL = Counter(
    "dependency_call_failures_total",
    "Failed calls to a third-party dependency, by which one.",
    ["dependency"],  # supabase_auth | supabase_storage | razorpay | ai_provider
)


def observe_dependency_failure(dependency: str) -> None:
    DEPENDENCY_CALL_FAILURES_TOTAL.labels(dependency=dependency).inc()
