"""Staff-side booking oversight and dispute management — see
docs/admin-dashboard.md#booking-management and #dispute-management.

No customer/artist-facing "raise a dispute" action exists anywhere in this
codebase (a booking only ever reaches `disputed` today via this router) —
see docs/admin-dashboard.md#dispute-management for why marking *and*
resolving a dispute are both staff-only actions here, rather than adding a
new customer-facing flow that's out of scope for an "admin dashboard" phase.
"""

import uuid
from collections.abc import Mapping

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import (
    normalize_pagination,
    paginate,
    resolve_sort_column,
    resolve_sort_direction,
)
from app.core.exceptions import AppError
from app.db.enums import BookingStatus
from app.db.models.booking import Booking
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminBookingListItemOut,
    AdminBookingListOut,
    AdminPageInfo,
    BookingDisputeRequest,
    BookingDisputeResolveRequest,
)
from app.services.audit import record_audit_log
from app.services.booking import transition_booking
from app.services.design_summaries import batch_artist_summaries

router = APIRouter(prefix="/admin/bookings", tags=["admin-bookings"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_DISPUTABLE_STATUSES = frozenset(
    {
        BookingStatus.CONFIRMED.value,
        BookingStatus.DEPOSIT_PENDING.value,
        BookingStatus.DEPOSIT_PAID.value,
        BookingStatus.IN_PROGRESS.value,
    }
)
_DISPUTE_RESOLUTION_STATUSES = frozenset(
    {BookingStatus.COMPLETED.value, BookingStatus.CANCELLED.value, BookingStatus.REFUNDED.value}
)

_SORT_COLUMNS = {
    "created_at": Booking.created_at,
    "requested_date": Booking.requested_date,
    "status": Booking.status,
    "total_amount": Booking.total_amount,
}


def _get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    return booking


def _customer_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(user_ids)))
    ).all()
    return {row.user_id: row.display_name for row in rows}


def _booking_item_out(
    booking: Booking,
    *,
    customer_names: Mapping[uuid.UUID, str | None],
    artist_names: Mapping[uuid.UUID, str | None],
) -> AdminBookingListItemOut:
    return AdminBookingListItemOut(
        id=booking.id,
        customer_id=booking.customer_id,
        customer_display_name=customer_names.get(booking.customer_id),
        artist_profile_id=booking.artist_profile_id,
        artist_display_name=artist_names.get(booking.artist_profile_id),
        status=booking.status,
        requested_date=booking.requested_date,
        total_amount=booking.total_amount,
        currency=booking.currency,
        created_at=booking.created_at,
    )


@router.get("", response_model=AdminBookingListOut)
def list_bookings(
    status_filter: str | None = None,
    customer_id: uuid.UUID | None = None,
    artist_profile_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminBookingListOut:
    page, page_size = normalize_pagination(page, page_size)
    sort_key, sort_column = resolve_sort_column(
        sort_by, columns=_SORT_COLUMNS, default_key="created_at"
    )
    direction = resolve_sort_direction(sort_dir)

    stmt = select(Booking)
    if status_filter is not None:
        if status_filter not in {s.value for s in BookingStatus}:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Booking.status == status_filter)
    if customer_id is not None:
        stmt = stmt.where(Booking.customer_id == customer_id)
    if artist_profile_id is not None:
        stmt = stmt.where(Booking.artist_profile_id == artist_profile_id)

    ordered = stmt.order_by(
        sort_column.desc() if direction == "desc" else sort_column.asc(), Booking.id
    )
    result = paginate(db, ordered, page=page, page_size=page_size)

    customer_names = _customer_names(db, [b.customer_id for b in result.items])
    artist_summaries = batch_artist_summaries(db, [b.artist_profile_id for b in result.items])
    artist_names = {k: v.display_name for k, v in artist_summaries.items()}

    return AdminBookingListOut(
        items=[
            _booking_item_out(b, customer_names=customer_names, artist_names=artist_names)
            for b in result.items
        ],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("/{booking_id}/dispute", response_model=AdminBookingListItemOut)
def mark_booking_disputed(
    booking_id: uuid.UUID,
    payload: BookingDisputeRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminBookingListItemOut:
    booking = _get_booking_or_404(db, booking_id)
    if booking.status not in _DISPUTABLE_STATUSES:
        raise AppError(
            f"Cannot open a dispute on a booking in '{booking.status}' status.", status_code=422
        )

    transition_booking(
        db,
        booking,
        to_status=BookingStatus.DISPUTED.value,
        changed_by=current.user.id,
        reason=payload.reason,
    )
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="booking.dispute.open",
        entity_type="bookings",
        entity_id=booking.id,
        after_state={"reason": payload.reason},
    )
    db.commit()
    db.refresh(booking)

    customer_names = _customer_names(db, [booking.customer_id])
    artist_summaries = batch_artist_summaries(db, [booking.artist_profile_id])
    artist_names = {k: v.display_name for k, v in artist_summaries.items()}
    return _booking_item_out(booking, customer_names=customer_names, artist_names=artist_names)


@router.post("/{booking_id}/resolve-dispute", response_model=AdminBookingListItemOut)
def resolve_booking_dispute(
    booking_id: uuid.UUID,
    payload: BookingDisputeResolveRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AdminBookingListItemOut:
    booking = _get_booking_or_404(db, booking_id)
    if booking.status != BookingStatus.DISPUTED.value:
        raise AppError("This booking is not currently disputed.", status_code=422)
    if payload.to_status not in _DISPUTE_RESOLUTION_STATUSES:
        raise AppError(
            f"to_status must be one of: {', '.join(sorted(_DISPUTE_RESOLUTION_STATUSES))}.",
            status_code=422,
        )

    transition_booking(
        db, booking, to_status=payload.to_status, changed_by=current.user.id, reason=payload.reason
    )
    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="booking.dispute.resolve",
        entity_type="bookings",
        entity_id=booking.id,
        after_state={"to_status": payload.to_status, "reason": payload.reason},
    )
    db.commit()
    db.refresh(booking)

    customer_names = _customer_names(db, [booking.customer_id])
    artist_summaries = batch_artist_summaries(db, [booking.artist_profile_id])
    artist_names = {k: v.display_name for k, v in artist_summaries.items()}
    return _booking_item_out(booking, customer_names=customer_names, artist_names=artist_names)
