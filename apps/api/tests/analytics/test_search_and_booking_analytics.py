"""`app/services/analytics/search_analytics.py` and
`app/services/analytics/booking_analytics.py` — see docs/analytics-and-
recommendations.md#search-analytics and #booking-conversion-analytics."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.enums import AnalyticsEventType
from app.services.analytics.booking_analytics import (
    BookingConversionFunnel,
    get_booking_conversion_funnel,
)
from app.services.analytics.search_analytics import get_search_analytics_summary
from tests.db.factories import make_analytics_event, make_search_event


def test_search_analytics_counts_totals_and_zero_result_rate(db_session: Session) -> None:
    make_search_event(db_session, query="bridal", result_count=5)
    make_search_event(db_session, query="minimalist", result_count=0)
    make_search_event(db_session, query="floral", result_count=0)
    db_session.commit()

    summary = get_search_analytics_summary(db_session)

    assert summary.total_searches >= 3
    assert summary.zero_result_searches >= 2
    assert summary.zero_result_rate > 0


def test_search_analytics_top_queries_ranks_by_frequency(db_session: Session) -> None:
    unique_query = f"unique-{uuid.uuid4().hex[:8]}"
    for _ in range(3):
        make_search_event(db_session, query=unique_query, result_count=5)
    make_search_event(db_session, query=f"other-{uuid.uuid4().hex[:8]}", result_count=5)
    db_session.commit()

    summary = get_search_analytics_summary(db_session, top_query_limit=50)

    top_query_counts = dict(summary.top_queries)
    assert top_query_counts[unique_query] == 3


def test_search_analytics_ignores_blank_queries_in_top_queries(db_session: Session) -> None:
    make_search_event(db_session, query=None, result_count=3)
    db_session.commit()

    summary = get_search_analytics_summary(db_session, top_query_limit=50)

    assert None not in dict(summary.top_queries)


def test_search_analytics_respects_the_window(db_session: Session) -> None:
    unique_query = f"stale-{uuid.uuid4().hex[:8]}"
    make_search_event(
        db_session,
        query=unique_query,
        result_count=5,
        created_at=datetime.now(UTC) - timedelta(days=90),
    )
    db_session.commit()

    summary = get_search_analytics_summary(db_session, window_days=7, top_query_limit=50)

    assert unique_query not in dict(summary.top_queries)


def test_booking_funnel_counts_each_stage(db_session: Session) -> None:
    for _ in range(4):
        make_analytics_event(db_session, event_type=AnalyticsEventType.BOOKING_STARTED.value)
    for _ in range(3):
        make_analytics_event(db_session, event_type=AnalyticsEventType.BOOKING_SUBMITTED.value)
    for _ in range(2):
        make_analytics_event(db_session, event_type=AnalyticsEventType.QUOTE_ACCEPTED.value)
    make_analytics_event(db_session, event_type=AnalyticsEventType.PAYMENT_COMPLETED.value)
    db_session.commit()

    funnel = get_booking_conversion_funnel(db_session)

    assert funnel.stage_counts[AnalyticsEventType.BOOKING_STARTED.value] >= 4
    assert funnel.stage_counts[AnalyticsEventType.BOOKING_SUBMITTED.value] >= 3
    assert funnel.stage_counts[AnalyticsEventType.QUOTE_ACCEPTED.value] >= 2
    assert funnel.stage_counts[AnalyticsEventType.PAYMENT_COMPLETED.value] >= 1


def test_booking_funnel_conversion_rates_are_relative_to_the_previous_stage() -> None:
    funnel = BookingConversionFunnel(
        stage_counts={
            AnalyticsEventType.BOOKING_STARTED.value: 10,
            AnalyticsEventType.BOOKING_SUBMITTED.value: 5,
            AnalyticsEventType.QUOTE_ACCEPTED.value: 4,
            AnalyticsEventType.PAYMENT_COMPLETED.value: 2,
        }
    )
    rates = funnel.stage_conversion_rates

    assert rates[AnalyticsEventType.BOOKING_STARTED.value] is None
    assert rates[AnalyticsEventType.BOOKING_SUBMITTED.value] == 0.5
    assert rates[AnalyticsEventType.QUOTE_ACCEPTED.value] == 0.8
    assert rates[AnalyticsEventType.PAYMENT_COMPLETED.value] == 0.5
    assert funnel.overall_conversion_rate == 0.2


def test_booking_funnel_handles_a_stage_with_zero_events() -> None:
    funnel = BookingConversionFunnel(stage_counts={})

    assert funnel.overall_conversion_rate is None
    assert all(rate is None for rate in funnel.stage_conversion_rates.values())
