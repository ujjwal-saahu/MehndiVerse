"""Builds the self-service calendar view — see
docs/artist-scheduling.md#calendar-view. Deliberately separate from
scheduling.py's slot-calculation (which needs a specific service to compute
bookable durations); this shows raw weekly-rule windows and blocks per day,
for the artist to review their own setup."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistProfile
from app.schemas.scheduling import (
    BlockedDateOut,
    CalendarDayOut,
    CalendarViewOut,
    CalendarWindowOut,
)
from app.services.scheduling import stored_weekday


def build_calendar_view(
    db: Session, artist_profile: ArtistProfile, *, start_date: date, end_date: date
) -> CalendarViewOut:
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

    days: list[CalendarDayOut] = []
    day = start_date
    while day <= end_date:
        weekday = stored_weekday(day)
        day_rules = sorted(rules_by_weekday.get(weekday, []), key=lambda r: r.start_time)
        day_blocks = [b for b in blocks if b.start_date <= day <= b.end_date]
        is_whole_day_blocked = any(b.start_time is None for b in day_blocks)

        days.append(
            CalendarDayOut(
                date=day,
                day_of_week=weekday,
                windows=[
                    CalendarWindowOut(start_time=r.start_time, end_time=r.end_time)
                    for r in day_rules
                ],
                blocks=[
                    BlockedDateOut(
                        id=b.id,
                        start_date=b.start_date,
                        end_date=b.end_date,
                        block_type=b.block_type,
                        start_time=b.start_time,
                        end_time=b.end_time,
                        reason=b.reason,
                    )
                    for b in day_blocks
                ],
                is_available=bool(day_rules) and not is_whole_day_blocked,
            )
        )
        day += timedelta(days=1)

    return CalendarViewOut(timezone=artist_profile.timezone, days=days)
