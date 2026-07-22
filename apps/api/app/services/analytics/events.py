"""Privacy-safe analytics event recording — see docs/analytics-and-
recommendations.md#privacy-safe-analytics-event-schema.

`record_event` is the *only* place `AnalyticsEvent` rows are ever created —
every route/service in this codebase that wants to track something calls
this function, never `db.add(AnalyticsEvent(...))` directly, so the
consent/flag gating and sanitization below can never be accidentally
bypassed.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.analytics import AnalyticsEvent
from app.db.models.user import UserPreference

from .flags import is_analytics_enabled

# Defense-in-depth against a caller accidentally passing something sensitive
# in `properties` — see docs/analytics-and-recommendations.md#do-not-place-
# sensitive-personal-information-in-analytics-payloads. The real guarantee
# is caller discipline (nothing in this codebase's call sites passes email/
# phone/name/address/payment-card/message-body data), but a key-name
# denylist catches an obvious mistake before it's ever persisted.
_DENYLISTED_PROPERTY_KEYS = frozenset(
    {
        "email",
        "phone",
        "phone_number",
        "password",
        "name",
        "full_name",
        "display_name",
        "address",
        "street_address",
        "card_number",
        "cvv",
        "card",
        "ssn",
        "message",
        "message_body",
        "body",
        "ip_address",
        "latitude",
        "longitude",
    }
)

# `properties` values are already coarse/short by construction at every call
# site (a category id, a result count, a status string) — this cap is a
# backstop against a caller accidentally dumping something large/freeform,
# not a expected-to-bind limit.
_MAX_PROPERTY_VALUE_LENGTH = 200


def _sanitize_properties(properties: dict[str, Any] | None) -> dict[str, Any] | None:
    if not properties:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in properties.items():
        if key.lower() in _DENYLISTED_PROPERTY_KEYS:
            continue
        if isinstance(value, str) and len(value) > _MAX_PROPERTY_VALUE_LENGTH:
            value = value[:_MAX_PROPERTY_VALUE_LENGTH]
        cleaned[key] = value
    return cleaned or None


def _user_has_consented(db: Session, user_id: uuid.UUID) -> bool:
    consent = db.execute(
        select(UserPreference.analytics_consent).where(UserPreference.user_id == user_id)
    ).scalar_one_or_none()
    return bool(consent)


def record_event(
    db: Session,
    *,
    event_type: str,
    user_id: uuid.UUID | None = None,
    session_id: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    properties: dict[str, Any] | None = None,
) -> AnalyticsEvent | None:
    """Returns `None` (recording nothing) if the operator-level flag is off
    — see `flags.py`. If a `user_id` is given but that user has not set
    `UserPreference.analytics_consent`, the event is still recorded (its
    aggregate signal — e.g. "a design was viewed" — still has analytical
    value) but *anonymized*: `user_id` is dropped, keeping only `session_id`
    if the caller supplied one. This is what "provide analytics consent
    where legally required" actually enforces: a non-consenting user's
    identity is never attached to a stored event, even though the anonymous
    fact of the event still is.

    Must run in the same transaction as the action being tracked — this
    function never commits."""
    if not is_analytics_enabled(db):
        return None

    effective_user_id = user_id
    if user_id is not None and not _user_has_consented(db, user_id):
        effective_user_id = None

    event = AnalyticsEvent(
        user_id=effective_user_id,
        session_id=session_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        properties=_sanitize_properties(properties),
    )
    db.add(event)
    db.flush()
    return event
