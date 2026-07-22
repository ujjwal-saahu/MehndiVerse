"""Genuine cross-connection concurrency test for "prevent overlapping
confirmed bookings" — see docs/booking-lifecycle.md#6 and
tests/engagement/test_concurrency.py, whose module docstring explains why a
real multi-connection/multi-thread test is needed here rather than the
single-transaction `db_session` fixture every other booking test uses: only
two independent connections racing against not-yet-committed rows can
demonstrate that the FOR UPDATE lock in
app/services/booking.py::_lock_artist_calendar actually serializes
confirmation attempts, rather than both passing the overlap check before
either commits.
"""

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AppError
from app.db.enums import BookingStatus, QuoteStatus
from app.db.models.artist import ArtistAvailability, ArtistProfile, ArtistService
from app.db.models.booking import Booking, BookingQuote
from app.db.models.user import User
from app.services.booking import accept_quote

_MONDAY = date(2026, 3, 9)


def _run_concurrently_capturing_errors(
    engine: Engine, fns: list[Callable[[Session], None]]
) -> list[str]:
    def worker(fn: Callable[[Session], None]) -> str:
        connection = engine.connect()
        session = sessionmaker(bind=connection)()
        try:
            fn(session)
            session.commit()
            return "ok"
        except AppError as exc:
            session.rollback()
            return f"error:{exc.status_code}"
        finally:
            session.close()
            connection.close()

    with ThreadPoolExecutor(max_workers=len(fns)) as executor:
        futures = [executor.submit(worker, fn) for fn in fns]
        return [future.result() for future in futures]


def _committed_setup(
    engine: Engine,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """One artist (with Monday 09:00-17:00 hours and a 60-minute service),
    two customers, each with a `quotation_sent` booking for the exact same
    Monday 10:00 slot and a pending quote ready to accept. Returns
    (booking_a_id, quote_a_id, booking_b_id, quote_b_id)."""
    connection = engine.connect()
    session = sessionmaker(bind=connection)()
    try:
        artist_user = User(email=f"{uuid.uuid4()}@example.com", role="artist")
        session.add(artist_user)
        session.flush()
        artist_profile = ArtistProfile(user_id=artist_user.id, verification_status="approved")
        session.add(artist_profile)
        session.flush()
        session.add(
            ArtistAvailability(
                artist_profile_id=artist_profile.id,
                day_of_week=1,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )
        service = ArtistService(
            artist_profile_id=artist_profile.id,
            name="Bridal Henna",
            pricing_type="fixed",
            price_amount=5000,
            currency="INR",
            duration_minutes=60,
        )
        session.add(service)
        session.flush()

        booking_ids = []
        quote_ids = []
        for _ in range(2):
            customer = User(email=f"{uuid.uuid4()}@example.com", role="customer")
            session.add(customer)
            session.flush()
            booking = Booking(
                customer_id=customer.id,
                artist_profile_id=artist_profile.id,
                service_id=service.id,
                status=BookingStatus.QUOTATION_SENT.value,
                requested_date=_MONDAY,
                requested_time=time(10, 0),
                currency="INR",
            )
            session.add(booking)
            session.flush()
            quote = BookingQuote(
                booking_id=booking.id, amount=5000, currency="INR", status=QuoteStatus.PENDING.value
            )
            session.add(quote)
            session.flush()
            booking_ids.append(booking.id)
            quote_ids.append(quote.id)

        session.commit()
        return booking_ids[0], quote_ids[0], booking_ids[1], quote_ids[1]
    finally:
        session.close()
        connection.close()


def test_concurrent_quote_acceptance_only_confirms_one_booking(db_engine: Engine) -> None:
    booking_a_id, quote_a_id, booking_b_id, quote_b_id = _committed_setup(db_engine)

    def accept(booking_id: uuid.UUID, quote_id: uuid.UUID) -> Callable[[Session], None]:
        def _do(session: Session) -> None:
            booking = session.get(Booking, booking_id)
            quote = session.get(BookingQuote, quote_id)
            assert booking is not None and quote is not None
            accept_quote(session, booking, quote, changed_by=booking.customer_id)

        return _do

    try:
        results = _run_concurrently_capturing_errors(
            db_engine,
            [accept(booking_a_id, quote_a_id), accept(booking_b_id, quote_b_id)],
        )

        assert sorted(results) == ["error:409", "ok"]

        with db_engine.connect() as conn:
            statuses = conn.execute(
                text("SELECT id, status FROM bookings WHERE id IN (:a, :b)"),
                {"a": booking_a_id, "b": booking_b_id},
            ).all()
        statuses_by_id = {row.id: row.status for row in statuses}
        confirmed = [s for s in statuses_by_id.values() if s == BookingStatus.CONFIRMED.value]
        still_pending = [
            s for s in statuses_by_id.values() if s == BookingStatus.QUOTATION_SENT.value
        ]
        assert len(confirmed) == 1
        assert len(still_pending) == 1
    finally:
        with db_engine.connect() as conn:
            user_ids = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT customer_id FROM bookings WHERE id IN (:a, :b) "
                        "UNION SELECT user_id FROM artist_profiles WHERE id = "
                        "(SELECT artist_profile_id FROM bookings WHERE id = :a)"
                    ),
                    {"a": booking_a_id, "b": booking_b_id},
                )
            ]
        with db_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM booking_status_history WHERE booking_id IN (:a, :b)"),
                {"a": booking_a_id, "b": booking_b_id},
            )
            conn.execute(
                text("DELETE FROM booking_quotes WHERE booking_id IN (:a, :b)"),
                {"a": booking_a_id, "b": booking_b_id},
            )
            conn.execute(
                text("DELETE FROM bookings WHERE id IN (:a, :b)"),
                {"a": booking_a_id, "b": booking_b_id},
            )
            # Cascades to artist_profiles -> artist_services/artist_availability.
            for user_id in user_ids:
                conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
