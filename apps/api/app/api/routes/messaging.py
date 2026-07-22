"""Booking-scoped messaging — see docs/booking-messaging.md.

Every endpoint here first resolves the booking and checks the caller is one
of its two parties (customer or the artist who owns it) — see
`_require_party` below, mirroring app/api/routes/bookings.py's identical
check. A third party gets a 403, never see anything about a conversation
they're not part of. Staff dispute-review access is a *separate* router
(app/api/routes/admin_messaging.py) — this router has no staff bypass.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError
from app.core.images import MAX_DESIGN_IMAGE_BYTES, InvalidImageError, process_image_upload
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.session import get_db_session
from app.integrations import supabase_storage
from app.integrations.supabase_storage import SupabaseStorageError
from app.schemas.design import PageInfo
from app.schemas.messaging import (
    ConversationDetailOut,
    ConversationSummaryOut,
    MessageListOut,
    MessageOut,
    ReportMessageRequest,
)
from app.schemas.moderation import ReportOut
from app.services.messaging import (
    get_or_create_booking_conversation,
    get_own_membership,
    list_conversations_for_user,
    mark_conversation_read,
    send_message,
)
from app.services.messaging_summaries import (
    conversation_detail_out,
    conversation_summaries,
    message_out,
)
from app.services.reports import create_report

router = APIRouter(tags=["messaging"])

_MESSAGES_SORT = "booking_messages"
_MESSAGES_PAGE_SIZE = 30


def _rate_limit() -> str:
    return get_settings().message_rate_limit


def _report_rate_limit() -> str:
    return get_settings().report_rate_limit


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


def _get_conversation_or_404(db: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise AppError("Conversation not found.", status_code=404)
    return conversation


def _member_last_read_by_user(
    db: Session, conversation_id: uuid.UUID
) -> dict[uuid.UUID, datetime | None]:
    members = (
        db.execute(
            select(ConversationMember).where(ConversationMember.conversation_id == conversation_id)
        )
        .scalars()
        .all()
    )
    return {m.user_id: m.last_read_at for m in members}


@router.get("/bookings/{booking_id}/conversation", response_model=ConversationDetailOut)
def get_booking_conversation(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ConversationDetailOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    conversation = get_or_create_booking_conversation(db, booking)
    db.commit()
    db.refresh(conversation)
    return conversation_detail_out(db, conversation, booking, viewer_id=current.user.id)


@router.get("/bookings/{booking_id}/conversation/messages", response_model=MessageListOut)
def list_booking_messages(
    booking_id: uuid.UUID,
    cursor: str | None = None,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> MessageListOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    conversation = get_or_create_booking_conversation(db, booking)
    db.commit()
    last_read_by_user = _member_last_read_by_user(db, conversation.id)

    stmt = select(Message).where(
        Message.conversation_id == conversation.id, Message.deleted_at.is_(None)
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_MESSAGES_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Message.created_at, Message.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(
        _MESSAGES_PAGE_SIZE + 1
    )

    messages = list(db.execute(stmt).scalars().all())
    has_more = len(messages) > _MESSAGES_PAGE_SIZE
    page = messages[:_MESSAGES_PAGE_SIZE]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_MESSAGES_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return MessageListOut(
        items=[message_out(m, member_last_read_by_user=last_read_by_user) for m in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.post(
    "/bookings/{booking_id}/conversation/messages", response_model=MessageOut, status_code=201
)
@limiter.limit(_rate_limit())
def send_booking_message(
    request: Request,
    booking_id: uuid.UUID,
    body: str | None = Form(default=None),
    file: UploadFile | None = None,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> MessageOut:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    conversation = get_or_create_booking_conversation(db, booking)

    attachment_url = None
    if file is not None:
        raw = file.file.read()
        try:
            processed = process_image_upload(raw, max_bytes=MAX_DESIGN_IMAGE_BYTES)
        except InvalidImageError as exc:
            raise AppError(str(exc), status_code=422) from exc
        path = f"messages/{conversation.id}/{uuid.uuid4()}.{processed.extension}"
        try:
            attachment_url = supabase_storage.upload_object(
                bucket="portfolio",
                path=path,
                data=processed.data,
                content_type=processed.content_type,
            )
        except SupabaseStorageError as exc:
            raise AppError("Failed to upload image. Please try again.", status_code=502) from exc

    message = send_message(
        db, conversation, sender_id=current.user.id, body=body, attachment_url=attachment_url
    )
    db.commit()
    db.refresh(message)

    last_read_by_user = _member_last_read_by_user(db, conversation.id)
    return message_out(message, member_last_read_by_user=last_read_by_user)


@router.post("/bookings/{booking_id}/conversation/read", status_code=204)
def mark_booking_conversation_read(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    booking = _get_booking_or_404(db, booking_id)
    _require_party(db, booking, current)
    conversation = get_or_create_booking_conversation(db, booking)
    membership = get_own_membership(db, conversation, current.user.id)
    mark_conversation_read(db, membership)
    db.commit()


@router.get("/conversations", response_model=list[ConversationSummaryOut])
def list_my_conversations(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ConversationSummaryOut]:
    conversations = list_conversations_for_user(db, current.user.id)
    return conversation_summaries(db, conversations, viewer_id=current.user.id)


@router.post("/messages/{message_id}/report", response_model=ReportOut, status_code=201)
@limiter.limit(_report_rate_limit())
def report_message(
    request: Request,
    message_id: uuid.UUID,
    payload: ReportMessageRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    message = db.get(Message, message_id)
    if message is None:
        raise AppError("Message not found.", status_code=404)
    conversation = _get_conversation_or_404(db, message.conversation_id)
    # Reusing membership as the visibility check: you can only report a
    # message you were actually allowed to see.
    get_own_membership(db, conversation, current.user.id)

    report = create_report(
        db,
        reporter_id=current.user.id,
        entity_type="message",
        entity_id=message.id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        reporter_id=report.reporter_id,
        reported_entity_type=report.reported_entity_type,
        reported_entity_id=report.reported_entity_id,
        status=report.status,
        reason=report.reason,
        resolution_notes=report.resolution_notes,
        resolved_by=report.resolved_by,
        resolved_at=report.resolved_at,
        created_at=report.created_at,
    )
