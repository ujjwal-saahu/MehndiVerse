"""Backend localization foundation — see
docs/localization-and-accessibility.md#backend-message-localization.

This is a small, additive foundation: a fixed catalog of *system-level*
message keys (auth/authorization/validation/internal-error), resolved from
the client's `Accept-Language` header. It deliberately does not attempt to
localize the ~200+ individual `AppError("...")` call sites scattered across
the codebase — those keep their existing English literals unchanged (see
`AppError.__init__` in app/core/exceptions.py). Only messages that opt in
via a `code` (the two base classes' *default* messages, and the handlers'
own generic messages) are looked up here. apps/web owns localization of
everything else — page copy, form labels, Zod validation messages — via its
own translation catalog under apps/web/src/i18n/.
"""

from __future__ import annotations

SUPPORTED_LOCALES: tuple[str, ...] = ("en", "hi", "ur", "ar")
DEFAULT_LOCALE = "en"

_CATALOG: dict[str, dict[str, str]] = {
    "auth.required": {
        "en": "Authentication required.",
        "hi": "प्रमाणीकरण आवश्यक है।",
        "ur": "توثیق درکار ہے۔",
        "ar": "المصادقة مطلوبة.",
    },
    "auth.forbidden": {
        "en": "You do not have permission to perform this action.",
        "hi": "आपको यह कार्रवाई करने की अनुमति नहीं है।",
        "ur": "آپ کو یہ کارروائی کرنے کی اجازت نہیں ہے۔",
        "ar": "ليس لديك إذن للقيام بهذا الإجراء.",
    },
    "validation.failed": {
        "en": "Request validation failed.",
        "hi": "अनुरोध सत्यापन विफल रहा।",
        "ur": "درخواست کی توثیق ناکام ہو گئی۔",
        "ar": "فشل التحقق من صحة الطلب.",
    },
    "error.internal": {
        "en": "An unexpected error occurred.",
        "hi": "एक अनपेक्षित त्रुटि हुई।",
        "ur": "ایک غیر متوقع خرابی پیش آگئی۔",
        "ar": "حدث خطأ غير متوقع.",
    },
}


def resolve_locale(accept_language: str | None) -> str:
    """Picks the best-supported locale from an `Accept-Language` header —
    a simple pass over its comma-separated tags in the order the client
    listed them (not a full `q=`-weighted negotiation), falling back to
    `DEFAULT_LOCALE` when the header is absent or names nothing we
    support."""
    if not accept_language:
        return DEFAULT_LOCALE
    for part in accept_language.split(","):
        tag = part.split(";")[0].strip().lower()
        primary = tag.split("-")[0]
        if primary in SUPPORTED_LOCALES:
            return primary
    return DEFAULT_LOCALE


def translate(code: str, locale: str) -> str | None:
    """Looks up `code` in the catalog for `locale`, falling back to
    `DEFAULT_LOCALE`. Returns `None` if `code` isn't a catalog entry at all
    so the caller can fall back to its own message."""
    entry = _CATALOG.get(code)
    if entry is None:
        return None
    return entry.get(locale, entry[DEFAULT_LOCALE])
