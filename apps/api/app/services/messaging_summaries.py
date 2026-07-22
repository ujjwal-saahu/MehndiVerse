"""DTO-building for conversation/message responses — see
docs/booking-messaging.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.artist import ArtistProfile, ArtistService
from app.db.models.booking import Booking
from app.db.models.messaging import Conversation, ConversationMember, Message
from app.db.models.user import Profile
from app.schemas.messaging import (
    ConversationBookingContextOut,
    ConversationDetailOut,
    ConversationSummaryOut,
    MessageOut,
)


def _other_party_display_name(db: Session, user_id: uuid.UUID) -> str | None:
    artist_profile = db.execute(
        select(ArtistProfile.professional_name, ArtistProfile.business_name).where(
            ArtistProfile.user_id == user_id
        )
    ).first()
    if artist_profile is not None:
        name: str | None = artist_profile.professional_name or artist_profile.business_name
        return name
    profile = db.execute(
        select(Profile.display_name).where(Profile.user_id == user_id)
    ).scalar_one_or_none()
    return profile


def _booking_context(db: Session, booking: Booking) -> ConversationBookingContextOut:
    service_name = None
    if booking.service_id is not None:
        service_name = db.execute(
            select(ArtistService.name).where(ArtistService.id == booking.service_id)
        ).scalar_one_or_none()
    return ConversationBookingContextOut(
        booking_id=booking.id,
        status=booking.status,
        requested_date=booking.requested_date,
        service_name=service_name,
        artist_profile_id=booking.artist_profile_id,
    )


def conversation_detail_out(
    db: Session, conversation: Conversation, booking: Booking, *, viewer_id: uuid.UUID
) -> ConversationDetailOut:
    other = db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id != viewer_id,
        )
    ).scalar_one_or_none()
    my_membership = db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id == viewer_id,
        )
    ).scalar_one_or_none()
    return ConversationDetailOut(
        id=conversation.id,
        booking=_booking_context(db, booking),
        other_party_display_name=(
            _other_party_display_name(db, other.user_id) if other is not None else None
        ),
        my_last_read_at=my_membership.last_read_at if my_membership is not None else None,
    )


def conversation_summaries(
    db: Session, conversations: list[Conversation], *, viewer_id: uuid.UUID
) -> list[ConversationSummaryOut]:
    if not conversations:
        return []
    conversation_ids = [c.id for c in conversations]

    bookings_by_id: dict[uuid.UUID, Booking] = {}
    booking_ids = [c.booking_id for c in conversations if c.booking_id is not None]
    if booking_ids:
        rows = db.execute(select(Booking).where(Booking.id.in_(booking_ids))).scalars().all()
        bookings_by_id = {b.id: b for b in rows}

    members = (
        db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id.in_(conversation_ids)
            )
        )
        .scalars()
        .all()
    )
    other_user_by_conversation: dict[uuid.UUID, uuid.UUID] = {}
    my_last_read_by_conversation: dict[uuid.UUID, datetime | None] = {}
    for member in members:
        if member.user_id == viewer_id:
            my_last_read_by_conversation[member.conversation_id] = member.last_read_at
        else:
            other_user_by_conversation[member.conversation_id] = member.user_id

    latest_rows = db.execute(
        select(Message.conversation_id, Message.body, Message.message_type, Message.created_at)
        .where(Message.conversation_id.in_(conversation_ids))
        .order_by(Message.conversation_id, Message.created_at.desc())
    ).all()
    last_message_body_by_conversation: dict[uuid.UUID, str | None] = {}
    seen: set[uuid.UUID] = set()
    for conv_id, body, message_type, _created_at in latest_rows:
        if conv_id in seen:
            continue
        seen.add(conv_id)
        last_message_body_by_conversation[conv_id] = body or (
            "Sent an image" if message_type == "image" else None
        )

    unread_counts: dict[uuid.UUID, int] = {}
    for conversation in conversations:
        last_read = my_last_read_by_conversation.get(conversation.id)
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation.id, Message.sender_id != viewer_id
        )
        if last_read is not None:
            stmt = stmt.where(Message.created_at > last_read)
        unread_counts[conversation.id] = db.execute(stmt).scalar_one()

    results: list[ConversationSummaryOut] = []
    for conversation in conversations:
        booking = bookings_by_id.get(conversation.booking_id) if conversation.booking_id else None
        if booking is None:
            continue
        other_user_id = other_user_by_conversation.get(conversation.id)
        results.append(
            ConversationSummaryOut(
                id=conversation.id,
                booking=_booking_context(db, booking),
                other_party_display_name=(
                    _other_party_display_name(db, other_user_id)
                    if other_user_id is not None
                    else None
                ),
                last_message_preview=last_message_body_by_conversation.get(conversation.id),
                last_message_at=conversation.last_message_at,
                unread_count=unread_counts.get(conversation.id, 0),
            )
        )
    return results


def message_out(
    message: Message, *, member_last_read_by_user: dict[uuid.UUID, datetime | None]
) -> MessageOut:
    """`is_read` is a property of the message alone (has its *recipient* —
    the member who isn't its sender — read up to this timestamp), not of
    whoever happens to be asking. `member_last_read_by_user` maps every
    conversation member's user_id to their own `last_read_at`."""
    recipient_last_read_at = next(
        (
            last_read
            for user_id, last_read in member_last_read_by_user.items()
            if user_id != message.sender_id
        ),
        None,
    )
    is_read = recipient_last_read_at is not None and message.created_at <= recipient_last_read_at
    return MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        body=message.body,
        attachment_url=message.attachment_url,
        message_type=message.message_type,
        is_read=is_read,
        created_at=message.created_at,
    )
