"""Unit test for the structlog redaction processor — see
docs/observability.md#log-redaction and app/core/logging.py."""

from app.core.logging import _redact_sensitive_fields


def test_redacts_known_sensitive_keys() -> None:
    event_dict = {
        "event": "login_attempt",
        "password": "hunter2",
        "access_token": "eyJ...",
        "refresh_token": "abc123",
        "Authorization": "Bearer xyz",
        "signature": "deadbeef",
        "email": "user@example.com",
        "phone": "+911234567890",
    }

    result = _redact_sensitive_fields(None, "info", dict(event_dict))

    assert result["password"] == "[REDACTED]"
    assert result["access_token"] == "[REDACTED]"
    assert result["refresh_token"] == "[REDACTED]"
    assert result["Authorization"] == "[REDACTED]"
    assert result["signature"] == "[REDACTED]"
    assert result["email"] == "[REDACTED]"
    assert result["phone"] == "[REDACTED]"
    # Non-sensitive fields pass through untouched.
    assert result["event"] == "login_attempt"


def test_leaves_event_dict_without_sensitive_keys_unchanged() -> None:
    event_dict = {"event": "design_viewed", "design_id": "abc-123"}
    result = _redact_sensitive_fields(None, "info", dict(event_dict))
    assert result == event_dict


def test_redacts_a_signed_storage_url_s_query_string_regardless_of_key_name() -> None:
    """A signed URL's query string is itself a bearer credential — see
    app/integrations/supabase_storage.py::create_signed_url. Matched by
    shape, not key name, so a future call site logging one under any kwarg
    name is still caught."""
    signed_url = (
        "https://project.supabase.co/storage/v1/object/sign/"
        "verification-documents/abc/doc.png?token=eyJhbGciOi...&expires=3600"
    )
    event_dict = {"event": "document_uploaded", "some_url_field": signed_url}

    result = _redact_sensitive_fields(None, "info", dict(event_dict))

    assert result["some_url_field"] == (
        "https://project.supabase.co/storage/v1/object/sign/"
        "verification-documents/abc/doc.png?[REDACTED]"
    )


def test_leaves_a_public_url_unchanged() -> None:
    event_dict = {
        "event": "x",
        "image_url": "https://project.supabase.co/storage/v1/object/public/avatars/a.png",
    }
    result = _redact_sensitive_fields(None, "info", dict(event_dict))
    assert result == event_dict
