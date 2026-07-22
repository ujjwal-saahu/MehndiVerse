import logging
import re
import sys

import structlog
from structlog.typing import EventDict, WrappedLogger

# Log keys that must never reach stdout in cleartext — see
# docs/security-review.md#sensitive-log-redaction. Matched by exact key
# name (case-insensitive) rather than value-content sniffing, since every
# call site in this codebase already uses consistent, predictable kwarg
# names (`get_logger(__name__).info("event", token=..., password=...)`) —
# a substring/regex value scan would be slower and easier to bypass by
# accident (e.g. nesting the secret one level deeper in a dict).
_REDACTED_KEYS = {
    "password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "secret",
    "signature",
    "jwt",
    "client_secret",
    "api_key",
    # Sensitive user details — see docs/observability.md#log-redaction.
    "email",
    "to_email",
    "contact_email",
    "phone",
    "to_phone",
    "contact_phone",
}
_REDACTED_VALUE = "[REDACTED]"

# Supabase Storage signs private-bucket URLs (verification documents, hand/
# foot preview photos, AI generation results — see app/integrations/
# supabase_storage.py::create_signed_url) by appending a bearer-equivalent
# token as a query string: anyone holding the full URL can fetch the file,
# no further auth required. No call site logs one of these today (grepped
# every `logger.*(` call site in this codebase), but a key-name allowlist
# alone wouldn't protect a future one — this catches it by *shape*
# regardless of what kwarg name it's logged under.
_SIGNED_URL_PATTERN = re.compile(r"(/storage/v1/object/sign/[^\s?]+)\?[^\s\"]*")
_SIGNED_URL_REPLACEMENT = r"\1?[REDACTED]"


def _redact_sensitive_fields(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    for key, value in event_dict.items():
        if key.lower() in _REDACTED_KEYS:
            event_dict[key] = _REDACTED_VALUE
        elif isinstance(value, str) and "/storage/v1/object/sign/" in value:
            event_dict[key] = _SIGNED_URL_PATTERN.sub(_SIGNED_URL_REPLACEMENT, value)
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _redact_sensitive_fields,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(name)
    return logger
