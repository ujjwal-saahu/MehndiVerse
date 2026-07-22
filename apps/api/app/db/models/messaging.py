import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ConversationMemberRole, ConversationType, MessageType, check_in
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`booking_id` is unique (NULLs excepted) — see
    docs/booking-messaging.md#1-one-conversation-per-booking. Lazily created
    by app/services/messaging.py::get_or_create_booking_conversation() the
    first time either party needs to message about a booking, not eagerly at
    booking-creation time."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(check_in("type", ConversationType), name="type_valid"),
        UniqueConstraint("booking_id", name="uq_conversations_booking_id"),
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    members: Mapped[list["ConversationMember"]] = relationship(back_populates="conversation")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conversation_members_conv_user"),
        CheckConstraint(check_in("role", ConversationMemberRole), name="role_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="members")


class Message(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(check_in("message_type", MessageType), name="message_type_valid"),
        CheckConstraint(
            "body IS NOT NULL OR attachment_url IS NOT NULL", name="body_or_attachment_present"
        ),
        # Backs the message-list endpoint's conversation_id filter +
        # created_at DESC sort — see migrations/versions/8f509ffde693.
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str | None] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(2048))
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MessageType.TEXT.value
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
