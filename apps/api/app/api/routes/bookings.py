"""Customer-facing booking endpoints — draft, submission, detail, quote
decisions, cancellation, reschedule, inspiration images. See
docs/booking-lifecycle.md. The artist-side inbox/review/quote-sending/
calendar endpoints live in app/api/routes/artist_bookings.py.

`GET /bookings/{id}` (and the shared actions below it) are reachable by
*either* party on the booking — the customer who made the request or the
artist it was made to — not just the customer, since both sides need to see
status history/quotes and both may cancel or propose a reschedule.

Route order matters: `/bookings/mine` is a literal path segment that must be
registered before `/bookings/{booking_id}` or FastAPI would try (and fail) to
parse "mine" as a UUID — see app/api/routes/designs.py's `/designs/mine` for
the precedent this mirrors.
"""

import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.exceptions import AppError, AuthorizationError
from app.core.images import MAX_DESIGN_IMAGE_BYTES, InvalidImageError, process_image_upload
from app.db.enums import AttachmentFileType, BookingStatus
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking, BookingAttachment
from app.db.session import get_db_session
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.schemas.booking import (
    BookingAttachmentOut,
    BookingDetailOut,
    BookingDraftCreateRequest,
    BookingDraftUpdateRequest,
    BookingImageUploadResponse,
    BookingSummaryOut,
    CancelBookingRequest,
    QuoteRejectRequest,
    RescheduleRequest,
)
from app.services.booking import (
    accept_quote,
    cancel_booking,
    create_draft_booking,
    get_active_quote_or_404,
    reject_quote,
    request_reschedule,
    submit_booking,
    update_draft_booking,
)
from app.services.booking_summaries import booking_detail, booking_summaries

router = APIRouter(prefix="/bookings", tags=["bookings"])


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


def _require_customer_owner(booking: Booking, current: AuthenticatedUser) -> None:
    if booking.customer_id != current.user.id:
        raise AuthorizationError("You do not have access to this booking.")


@router.post("", response_model=BookingDetailOut, status_code=201)
def create_booking_draft(
    payload: BookingDraftCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = create_draft_booking(
        db, customer_id=current.user.id, artist_profile_id=payload.artist_profile_id
    )
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.get("/mine", response_model=list[BookingSummaryOut])
def list_my_bookings(
    status_filter: str | None = None,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[BookingSummaryOut]:
    stmt = select(Booking).where(Booking.customer_id == current.user.id)
    if status_filter is not None:
        valid_statuses = {member.value for member in BookingStatus}
        if status_filter not in valid_statuses:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Booking.status == status_filter)
    stmt = stmt.order_by(Booking.created_at.desc()).limit(200)
    bookings = list(db.execute(stmt).scalars().all())
    return booking_summaries(db, bookings)


@router.get("/{booking_id}", response_model=BookingDetailOut)
def get_booking(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    return booking_detail(db, booking)


@router.patch("/{booking_id}", response_model=BookingDetailOut)
def update_booking_draft(
    booking_id: uuid.UUID,
    payload: BookingDraftUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_customer_owner(booking, current)
    update_draft_booking(db, booking, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/submit", response_model=BookingDetailOut)
def submit_booking_request(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_customer_owner(booking, current)
    submit_booking(db, booking, changed_by=current.user.id)
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/quotes/{quote_id}/accept", response_model=BookingDetailOut)
def accept_booking_quote(
    booking_id: uuid.UUID,
    quote_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_customer_owner(booking, current)
    quote = get_active_quote_or_404(db, booking, quote_id)
    accept_quote(db, booking, quote, changed_by=current.user.id)
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/quotes/{quote_id}/reject", response_model=BookingDetailOut)
def reject_booking_quote(
    booking_id: uuid.UUID,
    quote_id: uuid.UUID,
    payload: QuoteRejectRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_customer_owner(booking, current)
    quote = get_active_quote_or_404(db, booking, quote_id)
    reject_quote(db, booking, quote, changed_by=current.user.id, reason=payload.reason)
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/cancel", response_model=BookingDetailOut)
def cancel_my_booking(
    booking_id: uuid.UUID,
    payload: CancelBookingRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    cancel_booking(db, booking, changed_by=current.user.id, reason=payload.reason)
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/reschedule", response_model=BookingDetailOut)
def reschedule_my_booking(
    booking_id: uuid.UUID,
    payload: RescheduleRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    request_reschedule(
        db,
        booking,
        new_date=payload.new_date,
        new_time=payload.new_time,
        changed_by=current.user.id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post(
    "/{booking_id}/attachments", response_model=BookingImageUploadResponse, status_code=201
)
def upload_booking_inspiration_image(
    booking_id: uuid.UUID,
    file: UploadFile,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> BookingImageUploadResponse:
    booking = _get_booking_or_404(db, booking_id)
    _require_customer_owner(booking, current)

    raw = file.file.read()
    try:
        processed = process_image_upload(raw, max_bytes=MAX_DESIGN_IMAGE_BYTES)
    except InvalidImageError as exc:
        raise AppError(str(exc), status_code=422) from exc

    attachment_id = uuid.uuid4()
    path = f"bookings/{booking.id}/{attachment_id}.{processed.extension}"
    try:
        file_url = supabase_storage.upload_object(
            bucket="portfolio", path=path, data=processed.data, content_type=processed.content_type
        )
    except SupabaseStorageError as exc:
        raise AppError("Failed to upload image. Please try again.", status_code=502) from exc

    attachment = BookingAttachment(
        id=attachment_id,
        booking_id=booking.id,
        uploaded_by=current.user.id,
        file_url=file_url,
        file_type=AttachmentFileType.IMAGE.value,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return BookingImageUploadResponse(
        attachment=BookingAttachmentOut(
            id=attachment.id,
            file_url=attachment.file_url,
            file_type=attachment.file_type,
            caption=attachment.caption,
            uploaded_by=attachment.uploaded_by,
            created_at=attachment.created_at,
        )
    )
