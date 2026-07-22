import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import AnalyticsEventType, check_in
from app.db.mixins import UUIDPrimaryKeyMixin


class AnalyticsEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only product-analytics event log — see docs/analytics-and-
    recommendations.md#privacy-safe-analytics-event-schema. The direct
    successor to Phase 20's `RecommendationEvent` (see
    `AnalyticsEventType`'s docstring for why it was replaced rather than
    kept alongside this table).

    No soft delete, no `updated_at` — an event is an immutable fact about
    something that already happened; nothing about this table is ever
    edited after the row is written.

    `user_id` is nullable (`SET NULL` on delete) so a guest's activity
    (tracked only by `session_id`) and a deleted user's historical events
    both remain valid, non-identifying rows rather than being destroyed —
    aggregate analytics (trending designs, funnel conversion rates) should
    not silently lose data points because an account was later deleted.

    `entity_type`/`entity_id` is the same polymorphic-reference pattern
    `AiGeneration`/`Report` already use — one column pair covers every
    entity kind a product-analytics event might be about (design, artist
    profile, booking, subscription, payment, AI design request, preview)
    instead of a wide table of mostly-null foreign keys.

    `properties` is a JSONB bag for event-specific, privacy-safe
    supplementary data (e.g. a booking's event-type category, a payment's
    amount bucket, a search's result count) — see docs/analytics-and-
    recommendations.md#do-not-place-sensitive-personal-information-in-
    analytics-payloads for what must never appear here.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        CheckConstraint(check_in("event_type", AnalyticsEventType), name="event_type_valid"),
        Index("ix_analytics_events_event_type_created_at", "event_type", "created_at"),
        Index("ix_analytics_events_user_id_created_at", "user_id", "created_at"),
        Index("ix_analytics_events_entity", "entity_type", "entity_id"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    session_id: Mapped[str | None] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(30))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
