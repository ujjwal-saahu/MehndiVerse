"""Thin async client for Supabase's GoTrue (Auth) REST API.

FastAPI is the single integration point with Supabase Auth — see
docs/authentication.md#2-architecture-fastapi-as-the-single-supabase-integration-point.
No Supabase SDK is used here deliberately: these are five small, well-documented
REST calls, and a raw httpx client keeps the dependency surface minimal and the
HTTP layer trivially mockable in tests (see tests/auth/conftest.py).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.resilience import retry_connect_only, supabase_auth_breaker


class SupabaseAuthError(Exception):
    """Raised when Supabase's Auth API rejects a request. Carries the upstream
    HTTP status so routes can map it to an appropriate client-facing error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    email: str | None
    email_confirmed: bool


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        base_url=f"{settings.supabase_url}/auth/v1",
        headers={"apikey": settings.supabase_anon_key},
        timeout=10.0,
    )


def _call(fn: Callable[[], httpx.Response]) -> httpx.Response:
    """Every request in this module is a POST that creates/mutates
    server-side auth state, so only connection-establishment failures are
    retried — see app/core/resilience.py's module docstring."""
    return supabase_auth_breaker.call(lambda: retry_connect_only(fn))


def _raise_for_error(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        body = response.json()
        message = body.get("error_description") or body.get("msg") or body.get("error") or str(body)
    except ValueError:
        message = response.text
    raise SupabaseAuthError(response.status_code, message)


def _session_from_token_response(body: dict[str, Any]) -> SupabaseSession:
    user = body.get("user") or {}
    return SupabaseSession(
        access_token=body["access_token"],
        refresh_token=body["refresh_token"],
        expires_in=body.get("expires_in", 3600),
        user_id=user.get("id", ""),
        email=user.get("email"),
        email_confirmed=user.get("email_confirmed_at") is not None,
    )


@dataclass(frozen=True)
class SignUpResult:
    user_id: str
    email: str
    email_confirmation_required: bool
    session: SupabaseSession | None


def sign_up(email: str, password: str) -> SignUpResult:
    with _client() as client:
        response = _call(
            lambda: client.post("/signup", json={"email": email, "password": password})
        )
    _raise_for_error(response)
    body = response.json()

    # Supabase returns the created auth user either at the top level (when no
    # session is issued yet, pending email confirmation) or nested under
    # "user" alongside a session.
    user = body.get("user") or body
    session = _session_from_token_response(body) if body.get("access_token") else None

    return SignUpResult(
        user_id=user["id"],
        email=user["email"],
        email_confirmation_required=session is None,
        session=session,
    )


def sign_in_with_password(email: str, password: str) -> SupabaseSession:
    with _client() as client:
        response = _call(
            lambda: client.post(
                "/token",
                params={"grant_type": "password"},
                json={"email": email, "password": password},
            )
        )
    _raise_for_error(response)
    return _session_from_token_response(response.json())


def refresh_session(refresh_token: str) -> SupabaseSession:
    with _client() as client:
        response = _call(
            lambda: client.post(
                "/token",
                params={"grant_type": "refresh_token"},
                json={"refresh_token": refresh_token},
            )
        )
    _raise_for_error(response)
    return _session_from_token_response(response.json())


def sign_out(access_token: str, *, scope: str = "local") -> None:
    """`scope="local"` (default) revokes only the session tied to
    `access_token`, matching `POST /auth/logout`'s existing behavior.
    `scope="global"` revokes every session for the account — see
    `POST /auth/sessions/revoke-all` in app/api/routes/auth.py. Passed
    explicitly rather than relying on GoTrue's own default so this
    behavior doesn't silently change under us on a GoTrue upgrade."""
    with _client() as client:
        response = _call(
            lambda: client.post(
                "/logout",
                params={"scope": scope},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        )
    _raise_for_error(response)


def send_password_reset(email: str) -> None:
    with _client() as client:
        response = _call(lambda: client.post("/recover", json={"email": email}))
    _raise_for_error(response)


def resend_verification_email(email: str) -> None:
    with _client() as client:
        response = _call(lambda: client.post("/resend", json={"type": "signup", "email": email}))
    _raise_for_error(response)
