"""app/core/resilience.py — see docs/performance-and-reliability.md
#retry-strategy and #circuit-breaker-considerations."""

import httpx
import pytest

from app.core.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    retry_connect_only,
    retry_idempotent,
)


def _response(status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code)


class TestRetryConnectOnly:
    def test_returns_immediately_on_success(self) -> None:
        calls = []

        def fn() -> httpx.Response:
            calls.append(1)
            return _response(200)

        result = retry_connect_only(fn, max_attempts=3, base_delay_seconds=0)
        assert result.status_code == 200
        assert len(calls) == 1

    def test_retries_on_connect_error_then_succeeds(self) -> None:
        attempts = {"n": 0}

        def fn() -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise httpx.ConnectError("boom")
            return _response(200)

        result = retry_connect_only(fn, max_attempts=3, base_delay_seconds=0)
        assert result.status_code == 200
        assert attempts["n"] == 2

    def test_exhausts_attempts_and_raises(self) -> None:
        def fn() -> httpx.Response:
            raise httpx.ConnectError("always fails")

        with pytest.raises(httpx.ConnectError):
            retry_connect_only(fn, max_attempts=2, base_delay_seconds=0)

    def test_never_retries_a_5xx_response(self) -> None:
        """A response was received — the request may already have been
        processed server-side, so retrying could double-submit."""
        calls = []

        def fn() -> httpx.Response:
            calls.append(1)
            return _response(500)

        result = retry_connect_only(fn, max_attempts=3, base_delay_seconds=0)
        assert result.status_code == 500
        assert len(calls) == 1

    def test_never_retries_a_read_timeout(self) -> None:
        def fn() -> httpx.Response:
            raise httpx.ReadTimeout("slow")

        with pytest.raises(httpx.ReadTimeout):
            retry_connect_only(fn, max_attempts=3, base_delay_seconds=0)


class TestRetryIdempotent:
    def test_retries_on_5xx_then_succeeds(self) -> None:
        attempts = {"n": 0}

        def fn() -> httpx.Response:
            attempts["n"] += 1
            return _response(503 if attempts["n"] < 2 else 200)

        result = retry_idempotent(fn, max_attempts=3, base_delay_seconds=0)
        assert result.status_code == 200
        assert attempts["n"] == 2

    def test_retries_on_read_timeout(self) -> None:
        attempts = {"n": 0}

        def fn() -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise httpx.ReadTimeout("slow")
            return _response(200)

        result = retry_idempotent(fn, max_attempts=3, base_delay_seconds=0)
        assert result.status_code == 200


class TestCircuitBreaker:
    def test_opens_after_consecutive_failures(self) -> None:
        breaker = CircuitBreaker("test-service", failure_threshold=2, reset_timeout_seconds=60)

        def failing() -> httpx.Response:
            return _response(500)

        breaker.call(failing)
        breaker.call(failing)

        with pytest.raises(CircuitOpenError):
            breaker.call(failing)

    def test_success_resets_failure_count(self) -> None:
        breaker = CircuitBreaker("test-service-2", failure_threshold=2, reset_timeout_seconds=60)
        breaker.call(lambda: _response(500))
        breaker.call(lambda: _response(200))  # resets the counter
        breaker.call(lambda: _response(500))
        # Only one consecutive failure since the reset — breaker stays closed.
        result = breaker.call(lambda: _response(200))
        assert result.status_code == 200

    def test_exception_counts_as_a_failure(self) -> None:
        breaker = CircuitBreaker("test-service-3", failure_threshold=1, reset_timeout_seconds=60)

        def raises() -> httpx.Response:
            raise httpx.ConnectError("down")

        with pytest.raises(httpx.ConnectError):
            breaker.call(raises)

        with pytest.raises(CircuitOpenError):
            breaker.call(lambda: _response(200))

    def test_half_opens_after_reset_timeout(self) -> None:
        breaker = CircuitBreaker("test-service-4", failure_threshold=1, reset_timeout_seconds=0)
        breaker.call(lambda: _response(500))
        # reset_timeout_seconds=0 means the very next call is treated as a
        # half-open trial rather than being rejected outright.
        result = breaker.call(lambda: _response(200))
        assert result.status_code == 200
