"""Thin server-side client for Supabase Storage's object API.

Mirrors app/integrations/supabase_auth.py's pattern: a small, mockable httpx
wrapper rather than the Supabase SDK, so the HTTP boundary stays trivial to
test (see tests/profile/conftest.py). This is the ONLY place that holds the
Supabase service-role key — clients never receive it and never talk to
Storage directly, which is what makes this a "secure" upload path (see
docs/profile-and-privacy.md#avatar-uploads): the browser/app only ever calls
our own authenticated API, and we re-validate + re-encode the image before
forwarding it upstream.
"""

from collections.abc import Callable

import httpx

from app.core.config import get_settings
from app.core.resilience import retry_idempotent, supabase_storage_breaker


class SupabaseStorageError(Exception):
    """Raised when Supabase Storage rejects an upload."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        base_url=f"{settings.supabase_url}/storage/v1",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        timeout=15.0,
    )


def _call(fn: Callable[[], httpx.Response]) -> httpx.Response:
    """Every operation in this module (upsert-write, delete, sign) is
    idempotent — retrying a slow-but-maybe-successful attempt has no
    duplication risk, so the fuller `retry_idempotent` policy applies."""
    return supabase_storage_breaker.call(lambda: retry_idempotent(fn))


def _raise_for_error(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        body = response.json()
        message = body.get("message") or body.get("error") or str(body)
    except ValueError:
        message = response.text
    raise SupabaseStorageError(response.status_code, message)


def upload_object(*, bucket: str, path: str, data: bytes, content_type: str) -> str:
    """Uploads (upserting) `data` to `bucket/path` and returns its public URL.

    Only used for buckets configured as public (e.g. `avatars` — see
    infrastructure/supabase/storage_policies.sql); private buckets (e.g.
    `verification-documents`) use `upload_private_object` + `create_signed_url`
    instead, and are never given a durable public-style URL at all.
    """
    settings = get_settings()
    with _client() as client:
        response = _call(
            lambda: client.post(
                f"/object/{bucket}/{path}",
                content=data,
                headers={"Content-Type": content_type, "x-upsert": "true"},
            )
        )
    _raise_for_error(response)
    return f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{path}"


def upload_private_object(*, bucket: str, path: str, data: bytes, content_type: str) -> None:
    """Same upload as `upload_object`, but for a private bucket — deliberately
    returns nothing, since a private object has no durable public URL to hand
    back. Callers persist `(bucket, path)`, not a URL, and mint a short-lived
    signed URL on demand via `create_signed_url` whenever the object actually
    needs to be viewed. See docs/artist-verification.md#document-privacy."""
    with _client() as client:
        response = _call(
            lambda: client.post(
                f"/object/{bucket}/{path}",
                content=data,
                headers={"Content-Type": content_type, "x-upsert": "true"},
            )
        )
    _raise_for_error(response)


def delete_object(*, bucket: str, path: str) -> None:
    """Best-effort by convention at call sites (see
    app/services/previews.py::delete_preview) — the database row's
    soft-delete is the authoritative "this is gone" signal; storage cleanup
    reduces retention of sensitive photos but a failure here shouldn't block
    the delete itself."""
    with _client() as client:
        response = _call(lambda: client.delete(f"/object/{bucket}/{path}"))
    _raise_for_error(response)


def create_signed_url(*, bucket: str, path: str, expires_in_seconds: int) -> str:
    """Mints a time-limited signed URL for a private-bucket object — the only
    way to view something in a private bucket, since it has no public URL.
    Never persist the result: callers should call this fresh on every read,
    right before returning it to an authorized caller (see
    docs/artist-verification.md#short-lived-signed-urls)."""
    settings = get_settings()
    with _client() as client:
        response = _call(
            lambda: client.post(
                f"/object/sign/{bucket}/{path}",
                json={"expiresIn": expires_in_seconds},
            )
        )
    _raise_for_error(response)
    signed_path = response.json()["signedURL"]
    return f"{settings.supabase_url}/storage/v1{signed_path}"
