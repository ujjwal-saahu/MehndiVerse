import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import DevicePlatform, ProfileVisibility, UserRole, UserStatus, check_in
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Base account row. `id` is expected to equal the Supabase Auth `auth.users.id`
    once the auth integration phase wires accounts up — see docs/database-schema.md.
    Supabase Auth owns credentials; no password hash is stored here.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(check_in("role", UserRole), name="role_valid"),
        CheckConstraint(check_in("status", UserStatus), name="status_valid"),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE.value)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # passive_deletes=True: these children use ON DELETE CASCADE at the DB
    # level, so the ORM should not try to load and null out their FK on
    # parent delete — let Postgres cascade the delete directly.
    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, passive_deletes=True
    )
    preferences: Mapped["UserPreference | None"] = relationship(
        back_populates="user", uselist=False, passive_deletes=True
    )
    devices: Mapped[list["UserDevice"]] = relationship(back_populates="user", passive_deletes=True)


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Public-facing profile fields, kept separate from the auth-critical `users` row."""

    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_profiles_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    bio: Mapped[str | None] = mapped_column(String(1000))
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(2))
    locale: Mapped[str | None] = mapped_column(String(10))
    timezone: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship(back_populates="profile")


class UserPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """1:1 notification/marketing/privacy preferences. No soft delete — deleted
    with the user. Privacy fields (`profile_visibility`, `show_location`,
    `allow_messages_from_strangers`) added in Phase 5 — see
    docs/profile-and-privacy.md. `analytics_consent` added in Phase 22 — see
    docs/analytics-and-recommendations.md#provide-analytics-consent-where-
    legally-required. Defaults `False`, mirroring `marketing_opt_in`'s
    established opt-in-required precedent for legally-sensitive consent
    flags in this table, rather than assuming consent."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
        CheckConstraint(
            check_in("profile_visibility", ProfileVisibility), name="profile_visibility_valid"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email_notifications: Mapped[bool] = mapped_column(default=True, nullable=False)
    push_notifications: Mapped[bool] = mapped_column(default=True, nullable=False)
    sms_notifications: Mapped[bool] = mapped_column(default=False, nullable=False)
    marketing_opt_in: Mapped[bool] = mapped_column(default=False, nullable=False)
    profile_visibility: Mapped[str] = mapped_column(
        String(20), default=ProfileVisibility.PUBLIC.value, nullable=False
    )
    show_location: Mapped[bool] = mapped_column(default=True, nullable=False)
    allow_messages_from_strangers: Mapped[bool] = mapped_column(default=True, nullable=False)
    analytics_consent: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="preferences")


class UserDevice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Push-notification device registrations (FCM). No soft delete — a device
    row is either active or removed outright when the token is revoked."""

    __tablename__ = "user_devices"
    __table_args__ = (
        CheckConstraint(check_in("platform", DevicePlatform), name="platform_valid"),
        UniqueConstraint("device_token", name="uq_user_devices_device_token"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_token: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="devices")


class UserBlock(UUIDPrimaryKeyMixin, Base):
    """Directed user-to-user block, self-service (Phase 5 foundation). No
    soft delete — unblocking removes the row outright, same as `Like`/`Follow`.

    This only stores the relationship; it is not yet enforced anywhere else
    (messaging, discovery, notifications) — later phases that touch those
    surfaces are responsible for checking it. See docs/profile-and-privacy.md.
    """

    __tablename__ = "user_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_blocker_blocked"),
        CheckConstraint("blocker_id != blocked_id", name="blocker_not_blocked"),
    )

    blocker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
