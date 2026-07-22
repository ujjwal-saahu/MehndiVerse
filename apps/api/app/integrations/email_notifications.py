"""Email-notification foundation — see docs/booking-messaging.md#4-push-and-
email-notification-foundations.

No SMTP/transactional-email provider is configured in this environment
(Supabase Auth sends its own verification/reset emails directly — see
docs/authentication.md — this module is unrelated to those). This is the
single seam a future phase swaps a real provider into. `render_email_body()`
is where any user-generated text (e.g. a message excerpt) gets HTML-escaped
before being embedded in an HTML email — the concrete place "escape unsafe
message content" (see docs/booking-messaging.md#5) applies, since a stored
message body is intentionally kept as raw plain text (see
app/services/messaging.py::sanitize_message_body) and only needs
HTML-encoding at the point something builds actual HTML out of it.
"""

import html

from app.core.logging import get_logger

logger = get_logger(__name__)


def render_email_body(*, greeting: str, message_excerpt: str | None = None) -> str:
    """Builds a minimal HTML email body. Any `message_excerpt` (user-generated
    text, e.g. quoted from a chat message) is HTML-escaped here — this is the
    point where plain-text-safe content must become HTML-safe content."""
    safe_greeting = html.escape(greeting)
    body = f"<p>{safe_greeting}</p>"
    if message_excerpt:
        body += f"<blockquote>{html.escape(message_excerpt)}</blockquote>"
    return body


def send_notification_email(*, to_email: str, subject: str, html_body: str) -> bool:
    """Foundation-level: does not actually call an email provider."""
    logger.info("notification_email_dispatched", to_email=to_email, subject=subject)
    return True
