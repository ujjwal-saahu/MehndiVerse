"""Push-notification foundation — see docs/booking-messaging.md#4-push-and-
email-notification-foundations.

No real FCM/APNs integration exists in this environment (no push-provider
credentials, no client SDK wiring on the mobile app beyond device-token
*registration* — see `UserDevice`, Phase 5). This module is the single seam
a future phase swaps a real provider into: callers never talk to a push
provider directly, only to `send_push_notification()`, so nothing else needs
to change when that happens. For now it only logs the attempt.
"""

import uuid

from app.core.logging import get_logger

logger = get_logger(__name__)


def send_push_notification(
    *, device_tokens: list[str], title: str, body: str, user_id: uuid.UUID
) -> bool:
    """Returns True if there was at least one device to (notionally) deliver
    to. Foundation-level: does not actually call a push provider."""
    if not device_tokens:
        return False
    logger.info(
        "push_notification_dispatched",
        user_id=str(user_id),
        device_count=len(device_tokens),
        title=title,
        body_preview=body[:50],
    )
    return True
