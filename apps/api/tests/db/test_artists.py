from datetime import date, time, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistService

from .factories import make_artist_profile


def test_artist_service_price_max_must_be_gte_price_min(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    service = ArtistService(
        artist_profile_id=artist_profile.id,
        name="Bridal Package",
        pricing_type="range",
        price_min=100,
        price_max=50,
        currency="INR",
    )
    db_session.add(service)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_artist_service_valid_range_is_accepted(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    service = ArtistService(
        artist_profile_id=artist_profile.id,
        name="Bridal Package",
        pricing_type="range",
        price_min=50,
        price_max=100,
        currency="INR",
    )
    db_session.add(service)
    db_session.flush()

    assert service.id is not None


def test_artist_availability_end_time_must_be_after_start_time(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    slot = ArtistAvailability(
        artist_profile_id=artist_profile.id,
        day_of_week=1,
        start_time=time(14, 0),
        end_time=time(10, 0),
    )
    db_session.add(slot)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_artist_availability_day_of_week_out_of_range_rejected(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    slot = ArtistAvailability(
        artist_profile_id=artist_profile.id,
        day_of_week=7,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    db_session.add(slot)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_artist_blocked_date_end_before_start_rejected(db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    blocked = ArtistBlockedDate(
        artist_profile_id=artist_profile.id,
        start_date=date.today(),
        end_date=date.today() - timedelta(days=1),
    )
    db_session.add(blocked)

    with pytest.raises(IntegrityError):
        db_session.flush()
