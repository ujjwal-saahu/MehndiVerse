import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ReportEntityType, ReportStatus, check_in
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`reported_entity_id` is a polymorphic reference (no DB foreign key,
    since the referenced table depends on `reported_entity_type`); integrity
    for it is validated at the application layer. See
    docs/database-relationships.md#reports-polymorphic-reference.

    The partial unique index below is the abuse-prevention guard from
    docs/community-and-trust.md#7-abuse-prevention: the same reporter can't
    open a second *pending* report against the same target, but may report
    it again once the earlier report is resolved/dismissed."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            check_in("reported_entity_type", ReportEntityType), name="entity_type_valid"
        ),
        CheckConstraint(check_in("status", ReportStatus), name="status_valid"),
        Index(
            "uq_reports_one_pending_per_reporter_and_target",
            "reporter_id",
            "reported_entity_type",
            "reported_entity_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reported_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reported_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReportStatus.PENDING.value, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
