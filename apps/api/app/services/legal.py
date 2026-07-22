"""Consent, support-request, and account-data-export services — see
docs/legal-and-support.md."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.booking import Booking
from app.db.models.payment import Payment
from app.db.models.review import Review
from app.db.models.subscription import Subscription
from app.db.models.support import ConsentRecord, DataExportRequest, SupportRequest
from app.db.models.user import Profile, User


def record_consent(
    db: Session, *, user_id: uuid.UUID, consent_type: str, version: str, granted: bool
) -> ConsentRecord:
    record = ConsentRecord(
        user_id=user_id, consent_type=consent_type, version=version, granted=granted
    )
    db.add(record)
    return record


def list_consent_records(db: Session, *, user_id: uuid.UUID) -> list[ConsentRecord]:
    return list(
        db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(ConsentRecord.created_at.desc())
        ).scalars()
    )


def create_support_request(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    contact_email: str,
    category: str,
    subject: str,
    message: str,
) -> SupportRequest:
    request = SupportRequest(
        user_id=user_id,
        contact_email=contact_email,
        category=category,
        subject=subject,
        message=message,
    )
    db.add(request)
    return request


def _payment_row(payment: Payment) -> dict[str, Any]:
    return {
        "id": str(payment.id),
        "booking_id": str(payment.booking_id) if payment.booking_id else None,
        "subscription_id": str(payment.subscription_id) if payment.subscription_id else None,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "created_at": payment.created_at.isoformat(),
    }


def build_account_data_export(db: Session, *, user: User) -> dict[str, Any]:
    """Gathers every record this user's own account is entitled to see about
    itself. Deliberately excludes other parties' data even where a shared
    row exists (e.g. an artist's own reviews of a booking aren't included in
    a customer's export) — see docs/legal-and-support.md#data-export-
    request for what's covered today vs. deferred."""
    profile = db.execute(select(Profile).where(Profile.user_id == user.id)).scalar_one_or_none()
    bookings = db.execute(select(Booking).where(Booking.customer_id == user.id)).scalars().all()
    booking_ids = [booking.id for booking in bookings]

    payments: list[Payment] = []
    if booking_ids:
        payments.extend(
            db.execute(select(Payment).where(Payment.booking_id.in_(booking_ids))).scalars()
        )
    subscription_rows = db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    ).scalars()
    subscription_ids = [row.id for row in subscription_rows]
    if subscription_ids:
        payments.extend(
            db.execute(
                select(Payment).where(Payment.subscription_id.in_(subscription_ids))
            ).scalars()
        )

    reviews = db.execute(select(Review).where(Review.customer_id == user.id)).scalars().all()
    consent_records = list_consent_records(db, user_id=user.id)
    support_requests = (
        db.execute(select(SupportRequest).where(SupportRequest.user_id == user.id)).scalars().all()
    )

    db.add(DataExportRequest(user_id=user.id))

    return {
        "generated_at": datetime.now(UTC),
        "profile": {
            "display_name": profile.display_name if profile else None,
            "bio": profile.bio if profile else None,
            "city": profile.city if profile else None,
            "country": profile.country if profile else None,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        },
        "bookings": [
            {
                "id": str(booking.id),
                "status": booking.status,
                "total_amount": float(booking.total_amount) if booking.total_amount else None,
                "created_at": booking.created_at.isoformat(),
            }
            for booking in bookings
        ],
        "payments": [_payment_row(payment) for payment in payments],
        "reviews": [
            {
                "id": str(review.id),
                "booking_id": str(review.booking_id),
                "rating": review.rating,
                "body": review.body,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ],
        "consent_records": [
            {
                "consent_type": record.consent_type,
                "version": record.version,
                "granted": record.granted,
                "created_at": record.created_at.isoformat(),
            }
            for record in consent_records
        ],
        "support_requests": [
            {
                "id": str(request.id),
                "category": request.category,
                "subject": request.subject,
                "status": request.status,
                "created_at": request.created_at.isoformat(),
            }
            for request in support_requests
        ],
    }
