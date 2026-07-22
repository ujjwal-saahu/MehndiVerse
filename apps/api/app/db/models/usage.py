import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import UsageType, check_in
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per (user, usage_type, billing period) — see
    docs/subscriptions-and-entitlements.md#usage-quotas. `count` is
    incremented atomically each time the user consumes one unit (a design
    download, an AI generation); entitlement checks compare it against the
    limit in the user's current plan's `features` JSON before allowing the
    action, so the limit is enforced at the point of use rather than trusted
    from the client."""

    __tablename__ = "usage_records"
    __table_args__ = (
        CheckConstraint(check_in("usage_type", UsageType), name="usage_type_valid"),
        CheckConstraint("count >= 0", name="count_non_negative"),
        UniqueConstraint(
            "user_id", "usage_type", "period_start", name="uq_usage_records_user_type_period"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
