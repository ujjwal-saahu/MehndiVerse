"""Artist availability and scheduling — see docs/artist-scheduling.md.

Timezone strategy (docs/artist-scheduling.md#timezone-strategy): recurring
weekly rules and blocked-date rows store *local wall-clock* time
(`ArtistAvailability.start_time`/`end_time`, `ArtistBlockedDate.start_time`/
`end_time`) plus a separate IANA zone name
(`ArtistProfile.timezone`) — never a pre-computed UTC time. A concrete slot
instant, by contrast, IS a specific point in time, so
`compute_available_slots()` resolves each local wall-clock window against
its specific calendar date via `zoneinfo` (which is DST-aware for that
date) and returns UTC-aware datetimes. This is what makes DST transitions
transparent: "9am" always means 9am local, and the UTC instant it
corresponds to shifts automatically across a DST boundary.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import BOOKING_OCCUPYING_STATUS_VALUES
from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistProfile, ArtistService
from app.db.models.booking import Booking

MAX_QUERY_RANGE_DAYS = 60


def validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AppError(
            f"'{name}' is not a recognized IANA timezone name.", status_code=422
        ) from exc
    return name


def stored_weekday(day: date) -> int:
    """Converts Python's `date.weekday()` (0=Monday..6=Sunday) to this
    schema's convention (0=Sunday..6=Saturday, matching
    `ArtistAvailability.day_of_week`'s check constraint)."""
    return (day.weekday() + 1) % 7


def effective_buffer_minutes(profile: ArtistProfile, service: ArtistService) -> int:
    if service.buffer_minutes is not None:
        return service.buffer_minutes
    return profile.default_buffer_minutes


def effective_travel_buffer_minutes(profile: ArtistProfile, service: ArtistService) -> int:
    return (
        service.travel_buffer_minutes
        if service.travel_buffer_minutes is not None
        else profile.default_travel_buffer_minutes
    )


# --- Overlap prevention ------------------------------------------------------


def find_overlapping_rule(
    db: Session,
    *,
    artist_profile_id: uuid.UUID,
    day_of_week: int,
    start_time: time,
    end_time: time,
    exclude_id: uuid.UUID | None = None,
) -> ArtistAvailability | None:
    stmt = select(ArtistAvailability).where(
        ArtistAvailability.artist_profile_id == artist_profile_id,
        ArtistAvailability.day_of_week == day_of_week,
        ArtistAvailability.start_time < end_time,
        ArtistAvailability.end_time > start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(ArtistAvailability.id != exclude_id)
    return db.execute(stmt).scalars().first()


def _blocks_conflict(
    existing: ArtistBlockedDate,
    *,
    start_date: date,
    end_date: date,
    start_time: time | None,
    end_time: time | None,
) -> bool:
    """Called only for rows whose date ranges already overlap. Two
    single-day, time-scoped blocks on the exact same date only conflict if
    their time ranges also overlap (e.g. a 9-10am block and a 2-4pm block on
    the same day are both fine); any block touching a whole-day/multi-day
    range is always a conflict."""
    both_time_scoped = (
        existing.start_time is not None
        and start_time is not None
        and existing.start_date == existing.end_date == start_date == end_date
    )
    if both_time_scoped:
        assert existing.start_time is not None and start_time is not None
        assert existing.end_time is not None and end_time is not None
        return existing.start_time < end_time and existing.end_time > start_time
    return True


def find_overlapping_block(
    db: Session,
    *,
    artist_profile_id: uuid.UUID,
    start_date: date,
    end_date: date,
    start_time: time | None,
    end_time: time | None,
    exclude_id: uuid.UUID | None = None,
) -> ArtistBlockedDate | None:
    stmt = select(ArtistBlockedDate).where(
        ArtistBlockedDate.artist_profile_id == artist_profile_id,
        ArtistBlockedDate.start_date <= end_date,
        ArtistBlockedDate.end_date >= start_date,
    )
    if exclude_id is not None:
        stmt = stmt.where(ArtistBlockedDate.id != exclude_id)
    for candidate in db.execute(stmt).scalars().all():
        if _blocks_conflict(
            candidate,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
        ):
            return candidate
    return None


# --- Interval algebra ---------------------------------------------------------

Interval = tuple[datetime, datetime]


def _subtract_intervals(free: list[Interval], busy: list[Interval]) -> list[Interval]:
    """`free` minus `busy` — both lists of (start, end) aware datetimes.
    Assumes each `free` interval is independent (non-overlapping with other
    `free` intervals); `busy` may overlap arbitrarily."""
    if not busy:
        return sorted(free)
    busy_sorted = sorted(busy)
    result: list[Interval] = []
    for f_start, f_end in sorted(free):
        cursor = f_start
        for b_start, b_end in busy_sorted:
            if b_end <= cursor or b_start >= f_end:
                continue
            if b_start > cursor:
                result.append((cursor, min(b_start, f_end)))
            cursor = max(cursor, b_end)
            if cursor >= f_end:
                break
        if cursor < f_end:
            result.append((cursor, f_end))
    return result


# --- Slot calculation ----------------------------------------------------------


@dataclass(frozen=True)
class AvailableSlot:
    start_utc: datetime
    end_utc: datetime


def compute_available_slots(
    db: Session,
    artist_profile: ArtistProfile,
    service: ArtistService,
    *,
    start_date: date,
    end_date: date,
    now_utc: datetime | None = None,
) -> list[AvailableSlot]:
    if end_date < start_date:
        raise AppError("end_date must be on or after start_date.", status_code=422)
    if (end_date - start_date).days + 1 > MAX_QUERY_RANGE_DAYS:
        raise AppError(f"Date range cannot exceed {MAX_QUERY_RANGE_DAYS} days.", status_code=422)
    if service.duration_minutes is None:
        raise AppError(
            "This service has no fixed duration, so slots can't be calculated for it.",
            status_code=422,
        )
    if service.artist_profile_id != artist_profile.id:
        raise AppError("This service does not belong to this artist.", status_code=422)

    tz = ZoneInfo(validate_timezone(artist_profile.timezone))
    duration = timedelta(minutes=service.duration_minutes)
    gap = timedelta(
        minutes=effective_buffer_minutes(artist_profile, service)
        + effective_travel_buffer_minutes(artist_profile, service)
    )
    step = duration + gap
    now_utc = now_utc or datetime.now(UTC)

    rules = (
        db.execute(
            select(ArtistAvailability).where(
                ArtistAvailability.artist_profile_id == artist_profile.id,
                ArtistAvailability.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    rules_by_weekday: dict[int, list[ArtistAvailability]] = {}
    for rule in rules:
        rules_by_weekday.setdefault(rule.day_of_week, []).append(rule)

    blocks = (
        db.execute(
            select(ArtistBlockedDate).where(
                ArtistBlockedDate.artist_profile_id == artist_profile.id,
                ArtistBlockedDate.start_date <= end_date,
                ArtistBlockedDate.end_date >= start_date,
            )
        )
        .scalars()
        .all()
    )

    bookings = (
        db.execute(
            select(Booking).where(
                Booking.artist_profile_id == artist_profile.id,
                Booking.requested_date >= start_date,
                Booking.requested_date <= end_date,
                Booking.requested_time.is_not(None),
                Booking.status.in_(BOOKING_OCCUPYING_STATUS_VALUES),
            )
        )
        .scalars()
        .all()
    )
    booking_durations = _service_durations(
        db, [b.service_id for b in bookings if b.service_id is not None]
    )

    slots: list[AvailableSlot] = []
    day = start_date
    while day <= end_date:
        weekday = stored_weekday(day)
        free: list[Interval] = [
            (
                datetime.combine(day, rule.start_time, tzinfo=tz),
                datetime.combine(day, rule.end_time, tzinfo=tz),
            )
            for rule in rules_by_weekday.get(weekday, [])
        ]
        if free:
            busy: list[Interval] = []
            for block in blocks:
                if not (block.start_date <= day <= block.end_date):
                    continue
                if block.start_time is None:
                    busy.append(
                        (
                            datetime.combine(day, time.min, tzinfo=tz),
                            datetime.combine(day, time.max, tzinfo=tz),
                        )
                    )
                else:
                    assert block.end_time is not None
                    busy.append(
                        (
                            datetime.combine(day, block.start_time, tzinfo=tz),
                            datetime.combine(day, block.end_time, tzinfo=tz),
                        )
                    )
            for booking in bookings:
                if booking.requested_date != day or booking.requested_time is None:
                    continue
                booking_duration = (
                    booking_durations.get(booking.service_id) if booking.service_id else None
                ) or duration
                booking_start = datetime.combine(day, booking.requested_time, tzinfo=tz)
                busy.append((booking_start, booking_start + booking_duration))

            free = _subtract_intervals(free, busy)

            for window_start, window_end in free:
                cursor = window_start
                while cursor + duration <= window_end:
                    slot_start_utc = cursor.astimezone(UTC)
                    slot_end_utc = (cursor + duration).astimezone(UTC)
                    if slot_start_utc > now_utc:
                        slots.append(AvailableSlot(start_utc=slot_start_utc, end_utc=slot_end_utc))
                    cursor += step

        day += timedelta(days=1)

    slots.sort(key=lambda s: s.start_utc)
    return slots


def _service_durations(db: Session, service_ids: list[uuid.UUID]) -> dict[uuid.UUID, timedelta]:
    if not service_ids:
        return {}
    rows = db.execute(
        select(ArtistService.id, ArtistService.duration_minutes).where(
            ArtistService.id.in_(set(service_ids))
        )
    ).all()
    return {
        service_id: timedelta(minutes=minutes)
        for service_id, minutes in rows
        if minutes is not None
    }
