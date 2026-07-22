"""Booking-scoped payments — see docs/payments.md.

Every endpoint resolves the booking and checks the caller is one of its two
parties (customer or the artist who owns it) — same 403-for-third-parties
check duplicated from app/api/routes/bookings.py/messaging.py, consistent
with this codebase's small-per-route-file-helper precedent.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError
from app.db.models.artist import ArtistProfile, ArtistService
from app.db.models.booking import Booking
from app.db.models.payment import Payment, Refund
from app.db.session import get_db_session
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    PaymentOrderOut,
    PaymentOut,
    PaymentReceiptOut,
    RefundOut,
    RefundRequestRequest,
)
from app.services.payments.service import create_payment_order, request_refund

router = APIRouter(prefix="/bookings/{booking_id}/payments", tags=["payments"])


def _rate_limit() -> str:
    return get_settings().payment_rate_limit


def _get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    return booking


def _require_party(db: Session, booking: Booking, current: AuthenticatedUser) -> None:
    if booking.customer_id == current.user.id:
        return
    artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
    if artist_profile is not None and artist_profile.user_id == current.user.id:
        return
    raise AuthorizationError("You do not have access to this booking.")


def _get_payment_or_404(db: Session, booking_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None or payment.booking_id != booking_id:
        raise AppError("Payment not found.", status_code=404)
    return payment


def _payment_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        booking_id=payment.booking_id,
        payer_id=payment.payer_id,
        amount=payment.amount,
        currency=payment.currency,
        provider=payment.provider,
        payment_type=payment.payment_type,
        status=payment.status,
        failure_reason=payment.failure_reason,
        commission_amount=payment.commission_amount,
        net_amount=payment.net_amount,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


def _refund_out(refund: Refund) -> RefundOut:
    return RefundOut(
        id=refund.id,
        payment_id=refund.payment_id,
        amount=refund.amount,
        currency=refund.currency,
        reason=refund.reason,
        status=refund.status,
        requested_at=refund.requested_at,
        processed_at=refund.processed_at,
    )


@router.post("", response_model=PaymentOrderOut, status_code=201)
@limiter.limit(_rate_limit())
def create_booking_payment_order(
    request: Request,
    booking_id: uuid.UUID,
    payload: CreatePaymentOrderRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PaymentOrderOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)

    payment, provider_key_id = create_payment_order(
        db,
        booking,
        payment_type=payload.payment_type,
        payer_id=current.user.id,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    db.refresh(payment)
    return PaymentOrderOut(
        payment_id=payment.id,
        provider=payment.provider,
        provider_order_id=payment.provider_order_id,
        provider_key_id=provider_key_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
    )


@router.get("", response_model=list[PaymentOut])
def list_booking_payments(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[PaymentOut]:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    payments = (
        db.execute(
            select(Payment)
            .where(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [_payment_out(p) for p in payments]


@router.get("/{payment_id}", response_model=PaymentOut)
def get_booking_payment(
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PaymentOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    payment = _get_payment_or_404(db, booking_id, payment_id)
    return _payment_out(payment)


@router.get("/{payment_id}/receipt", response_model=PaymentReceiptOut)
def get_booking_payment_receipt(
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PaymentReceiptOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    payment = _get_payment_or_404(db, booking_id, payment_id)
    if payment.status != "succeeded":
        raise AppError("A receipt is only available for a successful payment.", status_code=422)

    artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
    artist_display_name = None
    if artist_profile is not None:
        artist_display_name = artist_profile.professional_name or artist_profile.business_name
    service_name = None
    if booking.service_id is not None:
        service_name = db.execute(
            select(ArtistService.name).where(ArtistService.id == booking.service_id)
        ).scalar_one_or_none()

    return PaymentReceiptOut(
        payment_id=payment.id,
        booking_id=booking.id,
        payment_type=payment.payment_type,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        paid_at=payment.paid_at,
        provider=payment.provider,
        provider_payment_id=payment.provider_payment_id,
        artist_display_name=artist_display_name,
        service_name=service_name,
    )


@router.post("/{payment_id}/refund", response_model=RefundOut, status_code=201)
def request_booking_payment_refund(
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: RefundRequestRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RefundOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    payment = _get_payment_or_404(db, booking_id, payment_id)

    refund = request_refund(db, payment, requested_by=current.user.id, reason=payload.reason)
    db.commit()
    db.refresh(refund)
    return _refund_out(refund)
