from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.payment import Payment, Refund

from .factories import make_booking


def _make_payment(session: Session, **overrides: object) -> Payment:
    booking = overrides.pop("booking", None) or make_booking(session)
    payment = Payment(
        booking_id=booking.id,
        payer_id=booking.customer_id,
        amount=overrides.pop("amount", 50000),
        currency="INR",
        provider="test-provider",
        provider_order_id=overrides.pop("provider_order_id", f"order_{booking.id}"),
        provider_payment_id=overrides.pop("provider_payment_id", f"pay_{booking.id}"),
        payment_type="deposit",
        **overrides,
    )
    session.add(payment)
    session.flush()
    return payment


def test_payment_amount_must_be_positive(db_session: Session) -> None:
    booking = make_booking(db_session)
    payment = Payment(
        booking_id=booking.id,
        payer_id=booking.customer_id,
        amount=0,
        currency="INR",
        provider="test-provider",
        provider_order_id="order_zero",
        provider_payment_id="pay_zero",
        payment_type="deposit",
    )
    db_session.add(payment)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_provider_payment_id_is_unique(db_session: Session) -> None:
    booking = make_booking(db_session)
    _make_payment(db_session, booking=booking, provider_payment_id="pay_dup")

    with pytest.raises(IntegrityError):
        _make_payment(
            db_session,
            booking=booking,
            provider_order_id="order_dup_2",
            provider_payment_id="pay_dup",
        )


def test_provider_order_id_is_unique(db_session: Session) -> None:
    booking = make_booking(db_session)
    _make_payment(
        db_session, booking=booking, provider_order_id="order_dup", provider_payment_id="pay_a"
    )

    with pytest.raises(IntegrityError):
        _make_payment(
            db_session, booking=booking, provider_order_id="order_dup", provider_payment_id="pay_b"
        )


def test_booking_with_a_payment_cannot_be_hard_deleted(db_session: Session) -> None:
    """payments.booking_id uses ON DELETE RESTRICT — a booking with financial
    history can never be deleted out from under its payment record."""
    booking = make_booking(db_session)
    _make_payment(db_session, booking=booking)

    db_session.delete(booking)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_refund_amount_must_be_positive(db_session: Session) -> None:
    payment = _make_payment(db_session)
    refund = Refund(
        payment_id=payment.id,
        amount=-1,
        currency="INR",
        status="pending",
        requested_at=datetime.now(UTC),
    )
    db_session.add(refund)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_payment_with_a_refund_cannot_be_hard_deleted(db_session: Session) -> None:
    """refunds.payment_id uses ON DELETE RESTRICT — a payment with a refund
    record can never be deleted."""
    payment = _make_payment(db_session)
    db_session.add(
        Refund(
            payment_id=payment.id,
            amount=100,
            currency="INR",
            status="pending",
            requested_at=datetime.now(UTC),
        )
    )
    db_session.flush()

    db_session.delete(payment)
    with pytest.raises(IntegrityError):
        db_session.flush()
