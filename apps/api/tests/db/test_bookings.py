import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.booking import BookingStatusHistory

from .factories import make_booking


def test_booking_status_check_constraint_rejects_unknown_value(db_session: Session) -> None:
    booking = make_booking(db_session)
    booking.status = "not_a_real_status"

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_booking_deposit_amount_cannot_be_negative(db_session: Session) -> None:
    booking = make_booking(db_session)
    booking.deposit_amount = -10

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_booking_status_history_records_initial_transition(db_session: Session) -> None:
    booking = make_booking(db_session)
    history = BookingStatusHistory(booking_id=booking.id, from_status=None, to_status="requested")
    db_session.add(history)
    db_session.flush()

    assert history.id is not None
    assert history.from_status is None


def test_booking_status_history_rejects_invalid_to_status(db_session: Session) -> None:
    booking = make_booking(db_session)
    history = BookingStatusHistory(booking_id=booking.id, from_status=None, to_status="bogus")
    db_session.add(history)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_booking_is_never_hard_deletable_once_it_has_status_history(db_session: Session) -> None:
    """booking_status_history.booking_id uses ON DELETE RESTRICT: a booking
    with recorded history can never be deleted, protecting the audit trail."""
    booking = make_booking(db_session)
    db_session.add(
        BookingStatusHistory(booking_id=booking.id, from_status=None, to_status="requested")
    )
    db_session.flush()

    db_session.delete(booking)
    with pytest.raises(IntegrityError):
        db_session.flush()
