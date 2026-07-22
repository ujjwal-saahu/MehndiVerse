"""Booking-conversion analytics — see docs/analytics-and-recommendations.md
#booking-conversion-analytics.

A simple event-count funnel over `AnalyticsEvent`: booking_started ->
booking_submitted -> quote_accepted -> payment_completed. This deliberately
counts *events*, not distinct bookings that made it through every stage in
order — a lightweight foundation metric ("how many of each thing happened
this window, and what fraction of the stage before it"), not a full
per-booking cohort/attribution analysis.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType
from app.db.models.analytics import AnalyticsEvent

DEFAULT_WINDOW_DAYS = 30

_FUNNEL_STAGES: tuple[str, ...] = (
    AnalyticsEventType.BOOKING_STARTED.value,
    AnalyticsEventType.BOOKING_SUBMITTED.value,
    AnalyticsEventType.QUOTE_ACCEPTED.value,
    AnalyticsEventType.PAYMENT_COMPLETED.value,
)


class BookingConversionFunnel:
    def __init__(self, *, stage_counts: dict[str, int]) -> None:
        # Preserve funnel order (dict insertion order), not whatever the
        # SQL GROUP BY happened to return.
        self.stage_counts = {stage: stage_counts.get(stage, 0) for stage in _FUNNEL_STAGES}

    @property
    def stage_conversion_rates(self) -> dict[str, float | None]:
        """Each stage's count divided by the *previous* stage's count — the
        first stage has no "previous" and is always `None`."""
        rates: dict[str, float | None] = {}
        previous_count: int | None = None
        for stage in _FUNNEL_STAGES:
            count = self.stage_counts[stage]
            if previous_count is None or previous_count == 0:
                rates[stage] = None
            else:
                rates[stage] = count / previous_count
            previous_count = count
        return rates

    @property
    def overall_conversion_rate(self) -> float | None:
        """`payment_completed` count divided by `booking_started` count —
        the single top-line "does a started booking end in a paid
        booking" number."""
        started = self.stage_counts[AnalyticsEventType.BOOKING_STARTED.value]
        completed = self.stage_counts[AnalyticsEventType.PAYMENT_COMPLETED.value]
        if started == 0:
            return None
        return completed / started


def get_booking_conversion_funnel(
    db: Session, *, window_days: int = DEFAULT_WINDOW_DAYS
) -> BookingConversionFunnel:
    since = datetime.now(UTC) - timedelta(days=window_days)
    rows = db.execute(
        select(AnalyticsEvent.event_type, func.count())
        .where(AnalyticsEvent.event_type.in_(_FUNNEL_STAGES), AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.event_type)
    ).all()
    return BookingConversionFunnel(stage_counts={row[0]: row[1] for row in rows})
