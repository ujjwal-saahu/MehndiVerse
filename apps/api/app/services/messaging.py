"""Booking-scoped messaging — see docs/booking-messaging.md.

One conversation per booking (`Conversation.booking_id` is unique — see the
Phase 14 migration), lazily created the first time either party needs it
rather than eagerly at booking-creation time, mirroring this codebase's
established lazy-provisioning pattern (draft artist profiles, placeholder
`User` rows, etc.).
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import (
    BookingStatus,
    ConversationMemberRole,
    ConversationType,
    MessageType,
)
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.services.blocking import is_blocked_either_direction
from app.services.notifications import notify_user

MAX_MESSAGE_BODY_LENGTH = 4000

# Plain text only — no rich text/markdown support. Any HTML-tag-looking
# sequence is stripped outright (rather than HTML-entity-escaped and stored
# escaped) so the stored body is always exactly what a plain-text renderer
# should show, with no double-escaping ambiguity between storage and
# display. See docs/booking-messaging.md#5-content-safety.
_HTML_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_message_body(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def get_or_create_booking_conversation(db: Session, booking: Booking) -> Conversation:
    if booking.status == BookingStatus.DRAFT.value:
        raise AppError(
            "Messaging isn't available until the booking has been submitted.", status_code=422
        )

    existing = db.execute(
        select(Conversation).where(Conversation.booking_id == booking.id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
    if artist_profile is None:
        raise AppError("Artist not found.", status_code=404)

    try:
        with db.begin_nested():
            conversation = Conversation(booking_id=booking.id, type=ConversationType.BOOKING.value)
            db.add(conversation)
            db.flush()
            db.add_all(
                [
                    ConversationMember(
                        conversation_id=conversation.id,
                        user_id=booking.customer_id,
                        role=ConversationMemberRole.CUSTOMER.value,
                    ),
                    ConversationMember(
                        conversation_id=conversation.id,
                        user_id=artist_profile.user_id,
                        role=ConversationMemberRole.ARTIST.value,
                    ),
                ]
            )
            db.flush()
            return conversation
    except IntegrityError:
        # Lost a race to create it (concurrent first-message from both
        # parties) — the unique constraint on booking_id guarantees a
        # winner already exists.
        winner = db.execute(
            select(Conversation).where(Conversation.booking_id == booking.id)
        ).scalar_one_or_none()
        if winner is not None:
            return winner
        raise


def get_own_membership(
    db: Session, conversation: Conversation, user_id: uuid.UUID
) -> ConversationMember:
    """Authorization gate: every conversation-scoped action goes through
    this — see docs/booking-messaging.md#2-authorization."""
    member = db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if member is None:
        raise AuthorizationError("You do not have access to this conversation.")
    return member


def _other_member(
    db: Session, conversation: Conversation, exclude_user_id: uuid.UUID
) -> ConversationMember | None:
    return db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id != exclude_user_id,
        )
    ).scalar_one_or_none()


def send_message(
    db: Session,
    conversation: Conversation,
    *,
    sender_id: uuid.UUID,
    body: str | None,
    attachment_url: str | None,
) -> Message:
    if not body and not attachment_url:
        raise AppError("A message needs text or an attachment.", status_code=422)

    clean_body = sanitize_message_body(body) if body else None
    if body and not clean_body and not attachment_url:
        raise AppError("A message needs text or an attachment.", status_code=422)
    if clean_body and len(clean_body) > MAX_MESSAGE_BODY_LENGTH:
        raise AppError(
            f"Messages cannot exceed {MAX_MESSAGE_BODY_LENGTH} characters.", status_code=422
        )

    other = _other_member(db, conversation, sender_id)
    if other is not None and is_blocked_either_direction(db, sender_id, other.user_id):
        raise AppError(
            "You can't message this user — one of you has blocked the other.", status_code=403
        )

    message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        body=clean_body,
        attachment_url=attachment_url,
        message_type=(MessageType.IMAGE.value if attachment_url else MessageType.TEXT.value),
    )
    db.add(message)
    conversation.last_message_at = datetime.now(UTC)
    db.add(conversation)
    db.flush()

    if other is not None:
        preview = clean_body or "Sent an image"
        notify_user(
            db,
            user_id=other.user_id,
            notification_type="message",
            title="New message",
            body=preview[:200],
            data={
                "conversation_id": str(conversation.id),
                "booking_id": str(conversation.booking_id),
            },
        )

    return message


def mark_conversation_read(db: Session, member: ConversationMember) -> None:
    member.last_read_at = datetime.now(UTC)
    db.add(member)


def list_conversations_for_user(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    return list(
        db.execute(
            select(Conversation)
            .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
            .where(ConversationMember.user_id == user_id)
            .order_by(
                Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc()
            )
        )
        .scalars()
        .all()
    )
