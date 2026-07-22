"""Staff-only conversation access for dispute review — see
docs/booking-messaging.md#7-admin-access-for-dispute-review.

Deliberately a separate router from app/api/routes/messaging.py, not a
staff-bypass branch inside it: viewing someone else's private conversation
is a distinct, audited action (`audit_logs`), not a normal part of the
member-facing messaging surface. Every view is logged with the viewing
staff member's identity, mirroring
app/api/routes/admin_artist_verification.py's audit-log precedent.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.models.booking import Booking
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.session import get_db_session
from app.schemas.design import PageInfo
from app.schemas.messaging import MessageListOut
from app.services.audit import record_audit_log
from app.services.messaging_summaries import message_out

router = APIRouter(prefix="/admin/bookings", tags=["admin-messaging"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_SORT = "admin_booking_messages"
_PAGE_SIZE = 50


@router.get("/{booking_id}/conversation/messages", response_model=MessageListOut)
def admin_view_booking_conversation(
    booking_id: uuid.UUID,
    request: Request,
    cursor: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> MessageListOut:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise AppError("Booking not found.", status_code=404)
    conversation = db.execute(
        select(Conversation).where(Conversation.booking_id == booking_id)
    ).scalar_one_or_none()
    if conversation is None:
        raise AppError("This booking has no conversation yet.", status_code=404)

    stmt = select(Message).where(Message.conversation_id == conversation.id)
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Message.created_at, Message.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(_PAGE_SIZE + 1)

    messages = list(db.execute(stmt).scalars().all())
    has_more = len(messages) > _PAGE_SIZE
    page = messages[:_PAGE_SIZE]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(sort=_SORT, sort_value=last.created_at.isoformat(), id_=last.id)

    record_audit_log(
        db,
        request=request,
        actor_id=current.user.id,
        action="conversation.admin_view",
        entity_type="conversations",
        entity_id=conversation.id,
        after_state={"booking_id": str(booking_id), "messages_returned": len(page)},
    )
    db.commit()

    members = (
        db.execute(
            select(ConversationMember).where(ConversationMember.conversation_id == conversation.id)
        )
        .scalars()
        .all()
    )
    last_read_by_user = {m.user_id: m.last_read_at for m in members}

    return MessageListOut(
        items=[message_out(m, member_last_read_by_user=last_read_by_user) for m in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )
