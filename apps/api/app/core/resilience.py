"""Retry + circuit-breaker helpers for outbound HTTP calls to third-party
providers (Supabase Auth, Supabase Storage, Razorpay) — see
docs/performance-and-reliability.md#retry-strategy and
#circuit-breaker-considerations.

No new dependency: this is deliberately small enough to hand-write rather
than add `tenacity`/`pybreaker` for three call sites, per this project's
"no dependency added for later" rule.

Retry policy is deliberately narrow: `retry_connect_only` only retries
`ConnectError`/`ConnectTimeout`/`PoolTimeout` — failures where the request
was never transmitted, so retrying can't double-submit a non-idempotent
POST (e.g. Supabase signup, Razorpay order creation). It never retries on
`ReadTimeout` or a 5xx response for a mutating call, because the provider
may have already processed the request and retrying could duplicate it.
`retry_idempotent` is for GET/read-only calls, where a slow-but-successful
attempt being retried has no side effect, so it's safe to also retry on
`ReadTimeout`/5xx.
"""

import time
from collections.abc import Callable

import httpx

from app.core.alerts import send_alert
from app.core.logging import get_logger
from app.core.metrics import observe_dependency_failure

logger = get_logger(__name__)

_CONNECT_EXCEPTIONS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
_RETRYABLE_READ_EXCEPTIONS = (*_CONNECT_EXCEPTIONS, httpx.ReadTimeout)


def _run_with_retry(
    fn: Callable[[], httpx.Response],
    *,
    exceptions: tuple[type[Exception], ...],
    retry_5xx: bool,
    max_attempts: int,
    base_delay_seconds: float,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = fn()
        except exceptions as exc:
            last_exc = exc
        else:
            if retry_5xx and response.status_code >= 500 and attempt < max_attempts:
                logger.warning("http_retry_5xx", attempt=attempt, status_code=response.status_code)
                time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
                continue
            return response

        if attempt == max_attempts:
            raise last_exc
        logger.warning("http_retry_transport_error", attempt=attempt, error=str(last_exc))
        time.sleep(base_delay_seconds * (2 ** (attempt - 1)))

    # Unreachable (the loop always returns or raises), but keeps mypy happy.
    raise last_exc  # type: ignore[misc]


def retry_connect_only(
    fn: Callable[[], httpx.Response], *, max_attempts: int = 3, base_delay_seconds: float = 0.2
) -> httpx.Response:
    """Safe for POST/PUT/DELETE — only retries failures where nothing was
    ever sent to the server."""
    return _run_with_retry(
        fn,
        exceptions=_CONNECT_EXCEPTIONS,
        retry_5xx=False,
        max_attempts=max_attempts,
        base_delay_seconds=base_delay_seconds,
    )


def retry_idempotent(
    fn: Callable[[], httpx.Response], *, max_attempts: int = 3, base_delay_seconds: float = 0.2
) -> httpx.Response:
    """For GET/read-only calls — also retries a slow response or a 5xx,
    since re-issuing a read has no side effect."""
    return _run_with_retry(
        fn,
        exceptions=_RETRYABLE_READ_EXCEPTIONS,
        retry_5xx=True,
        max_attempts=max_attempts,
        base_delay_seconds=base_delay_seconds,
    )


class CircuitOpenError(Exception):
    """Raised instead of even attempting a call while a breaker is open."""

    def __init__(self, service: str) -> None:
        self.service = service
        super().__init__(f"Circuit breaker open for '{service}' — refusing to call it right now.")


class CircuitBreaker:
    """Per-process, in-memory breaker — one instance per external service
    (see the module-level instances below). Not shared across worker
    processes/machines; that would need a Redis-backed counter, which isn't
    justified yet at this app's traffic volume. Documented as the concrete
    "circuit-breaker considerations" for this phase: trips after
    `failure_threshold` consecutive failures, refuses calls for
    `reset_timeout_seconds`, then allows one trial call (half-open) to
    decide whether to close again."""

    def __init__(
        self, name: str, *, failure_threshold: int = 5, reset_timeout_seconds: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_timeout_seconds:
            return False  # half-open: allow the next call through as a trial
        return True

    def call(self, fn: Callable[[], httpx.Response]) -> httpx.Response:
        if self._is_open():
            raise CircuitOpenError(self.name)
        try:
            response = fn()
        except Exception:
            self._record_failure()
            raise
        if response.status_code >= 500:
            self._record_failure()
        else:
            self._reset()
        return response

    def _record_failure(self) -> None:
        observe_dependency_failure(self.name)
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            if self._opened_at is None:
                # Storage-error / AI-provider / payment-provider alerts —
                # see docs/observability.md#alerting. Fires once per open,
                # not on every failure once already open, so a sustained
                # outage pages once, not on every retry.
                send_alert(
                    "circuit_breaker_opened",
                    service=self.name,
                    consecutive_failures=self._consecutive_failures,
                )
            self._opened_at = time.monotonic()

    def _reset(self) -> None:
        if self._opened_at is not None:
            logger.info("circuit_breaker_closed", service=self.name)
        self._consecutive_failures = 0
        self._opened_at = None


supabase_auth_breaker = CircuitBreaker("supabase_auth")
supabase_storage_breaker = CircuitBreaker("supabase_storage")
razorpay_breaker = CircuitBreaker("razorpay")
