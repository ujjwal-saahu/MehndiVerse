import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import NotificationChannel, NotificationType, check_in
from app.db.mixins import SoftDeleteMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, SoftDeleteMixin, Base):
    """No updated_at: a notification is written once and only ever gains a
    read/delete timestamp, never edited."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(check_in("type", NotificationType), name="type_valid"),
        CheckConstraint(check_in("channel", NotificationChannel), name="channel_valid"),
        # Backs GET /notifications' user_id filter + created_at DESC sort —
        # see migrations/versions/8f509ffde693.
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
