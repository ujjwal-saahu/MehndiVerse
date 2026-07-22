"""Pure unit tests for app/services/scheduling.py::compute_available_slots —
no HTTP layer, so failures point directly at the algorithm. See
docs/artist-scheduling.md#available-slot-calculation.

Every call pins `now_utc` to a fixed instant safely before any date used in
these tests, so the "exclude past slots" behavior (tested explicitly below)
never accidentally swallows other tests' fixture dates depending on when the
suite happens to run in real wall-clock time.
"""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import BookingStatus
from app.services.scheduling import compute_available_slots
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_availability_rule,
    make_blocked_date,
    make_booking,
)

# 2026-01-05 is a Monday.
_MONDAY = date(2026, 1, 5)
_FAR_PAST = datetime(2000, 1, 1, tzinfo=UTC)


def _stored_dow(d: date) -> int:
    return (d.weekday() + 1) % 7  # 0=Sunday..6=Saturday


def test_basic_slot_generation_fills_the_whole_window(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert [s.start_utc.hour for s in slots] == [9, 10, 11]
    assert all(s.end_utc - s.start_utc == timedelta(minutes=60) for s in slots)


def test_buffer_minutes_spaces_out_slots(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    service = make_artist_service(
        db_session, artist_profile=profile, duration_minutes=30, buffer_minutes=15
    )
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    # step = 30 + 15 = 45 minutes: 9:00, 9:45, 10:30 fit; 11:15 would not.
    starts = [s.start_utc.strftime("%H:%M") for s in slots]
    assert starts == ["09:00", "09:45", "10:30"]


def test_travel_buffer_falls_back_to_profile_default(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    profile.default_travel_buffer_minutes = 20
    db_session.add(profile)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    # travel_buffer_minutes left unset on the service -> falls back to the
    # profile default of 20.
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=30)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    # step = 30 + 20 = 50 minutes: only 9:00 fits inside a 60-minute window.
    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["09:00"]


def test_service_level_travel_buffer_overrides_profile_default(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    profile.default_travel_buffer_minutes = 20
    db_session.add(profile)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    service = make_artist_service(
        db_session, artist_profile=profile, duration_minutes=30, travel_buffer_minutes=0
    )
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    # step = 30 + 0 = 30 minutes: both 9:00 and 9:30 fit.
    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["09:00", "09:30"]


def test_service_without_duration_is_rejected(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=None)
    db_session.commit()

    with pytest.raises(AppError):
        compute_available_slots(
            db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
        )


def test_service_from_another_artist_is_rejected(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=other_profile)
    db_session.commit()

    with pytest.raises(AppError):
        compute_available_slots(
            db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
        )


def test_end_date_before_start_date_is_rejected(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    db_session.commit()

    with pytest.raises(AppError):
        compute_available_slots(
            db_session,
            profile,
            service,
            start_date=_MONDAY,
            end_date=_MONDAY - timedelta(days=1),
            now_utc=_FAR_PAST,
        )


def test_query_range_over_max_is_rejected(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    db_session.commit()

    with pytest.raises(AppError):
        compute_available_slots(
            db_session,
            profile,
            service,
            start_date=_MONDAY,
            end_date=_MONDAY + timedelta(days=61),
            now_utc=_FAR_PAST,
        )


def test_whole_day_block_removes_all_slots(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    make_blocked_date(db_session, artist_profile=profile, start_date=_MONDAY, block_type="holiday")
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert slots == []


def test_manual_time_scoped_block_removes_only_that_window(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(13, 0),
    )
    # A dentist appointment 10:00-11:00.
    make_blocked_date(
        db_session,
        artist_profile=profile,
        start_date=_MONDAY,
        block_type="personal_leave",
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["09:00", "11:00", "12:00"]


def test_existing_booking_removes_its_slot(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.flush()
    make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
        service_id=service.id,
    )
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["09:00", "11:00"]


def test_cancelled_booking_does_not_remove_its_slot(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.flush()
    make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.CANCELLED.value,
        requested_date=_MONDAY,
        requested_time=time(9, 0),
        service_id=service.id,
    )
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["09:00", "10:00"]


def test_inactive_rule_produces_no_slots(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(12, 0),
        is_active=False,
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert slots == []


def test_no_slots_on_a_day_without_a_rule(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    tuesday = _MONDAY + timedelta(days=1)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=tuesday, end_date=tuesday, now_utc=_FAR_PAST
    )

    assert slots == []


# --- Boundary tests -----------------------------------------------------------


def test_window_exactly_one_slot_long_yields_exactly_one_slot(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert len(slots) == 1
    assert slots[0].start_utc.strftime("%H:%M") == "09:00"
    assert slots[0].end_utc.strftime("%H:%M") == "10:00"


def test_window_one_minute_short_yields_no_slots(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(9, 59),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert slots == []


def test_slot_starting_exactly_at_now_is_excluded_but_the_next_is_kept(
    db_session: Session,
) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    now_utc = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=now_utc
    )

    assert [s.start_utc.strftime("%H:%M") for s in slots] == ["10:00"]


# --- Timezone / DST tests -------------------------------------------------------


def test_non_utc_timezone_converts_local_hours_to_the_correct_utc_offset(
    db_session: Session,
) -> None:
    profile = make_artist_profile(db_session)
    profile.timezone = "Asia/Kolkata"  # UTC+5:30, no DST
    db_session.add(profile)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert len(slots) == 1
    # 09:00 IST == 03:30 UTC (UTC+5:30).
    assert slots[0].start_utc == datetime(2026, 1, 5, 3, 30, tzinfo=UTC)


def test_dst_spring_forward_shifts_the_utc_offset(db_session: Session) -> None:
    """2026-03-08 is when America/New_York springs forward (2am -> 3am).
    Both dates below are Sundays, so a single recurring Sunday 9-10am rule
    covers both — the UTC instant it resolves to differs across the DST
    boundary even though the local wall-clock time (and the rule row) never
    changes, which is exactly the point of storing local time + zone name
    rather than a pre-computed UTC time (see
    docs/artist-scheduling.md#timezone-strategy)."""
    profile = make_artist_profile(db_session)
    profile.timezone = "America/New_York"
    db_session.add(profile)
    before_dst = date(2026, 3, 1)  # a Sunday, EST (UTC-5)
    after_dst = date(2026, 3, 8)  # a Sunday, EDT (UTC-4)
    assert _stored_dow(before_dst) == _stored_dow(after_dst)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(before_dst),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    before_slots = compute_available_slots(
        db_session, profile, service, start_date=before_dst, end_date=before_dst, now_utc=_FAR_PAST
    )
    after_slots = compute_available_slots(
        db_session, profile, service, start_date=after_dst, end_date=after_dst, now_utc=_FAR_PAST
    )

    # 9am EST (UTC-5) = 14:00 UTC; 9am EDT (UTC-4, after springing forward) = 13:00 UTC.
    assert before_slots[0].start_utc == datetime(2026, 3, 1, 14, 0, tzinfo=UTC)
    assert after_slots[0].start_utc == datetime(2026, 3, 8, 13, 0, tzinfo=UTC)


def test_dst_fall_back_still_produces_exactly_one_slot_per_local_hour(
    db_session: Session,
) -> None:
    """2026-11-01 is when America/New_York falls back (2am -> 1am) — the
    2:00-2:59am wall-clock hour occurs twice that day, but this rule's
    window (9-10am) is unaffected; this test guards against the calculator
    crashing or double-counting around a fold date."""
    profile = make_artist_profile(db_session)
    profile.timezone = "America/New_York"
    db_session.add(profile)
    fall_back_date = date(2026, 11, 1)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(fall_back_date),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session,
        profile,
        service,
        start_date=fall_back_date,
        end_date=fall_back_date,
        now_utc=_FAR_PAST,
    )

    assert len(slots) == 1
    # 9am EST (already back from DST by 9am) = 14:00 UTC.
    assert slots[0].start_utc == datetime(2026, 11, 1, 14, 0, tzinfo=UTC)


def test_local_midnight_crossing_maps_to_the_correct_utc_date(db_session: Session) -> None:
    """An artist far east of UTC with early-morning local hours should
    produce slots dated the *previous* UTC day."""
    profile = make_artist_profile(db_session)
    profile.timezone = "Pacific/Auckland"  # UTC+13 in NZ summer (Jan)
    db_session.add(profile)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=_stored_dow(_MONDAY),
        start_time=time(1, 0),
        end_time=time(2, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    slots = compute_available_slots(
        db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
    )

    assert len(slots) == 1
    # 2026-01-05 01:00 NZDT (UTC+13) == 2026-01-04 12:00 UTC.
    assert slots[0].start_utc == datetime(2026, 1, 4, 12, 0, tzinfo=UTC)


def test_invalid_timezone_on_the_profile_is_rejected(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    profile.timezone = "Not/AZone"
    db_session.add(profile)
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()

    with pytest.raises(AppError):
        compute_available_slots(
            db_session, profile, service, start_date=_MONDAY, end_date=_MONDAY, now_utc=_FAR_PAST
        )
