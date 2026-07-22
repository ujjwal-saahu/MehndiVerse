import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class SearchEvent(UUIDPrimaryKeyMixin, Base):
    """One row per search request — the combined foundation for "recent
    searches" (per-user, read back by query text) and search analytics (the
    event log itself: filters used, result count, when). No soft delete —
    clearing history is a real delete (see docs/design-search.md
    #search-history-and-analytics-are-one-table). No `updated_at`: an event
    log entry is immutable once written.
    """

    __tablename__ = "search_events"
    __table_args__ = (
        Index("ix_search_events_user_id_created_at", "user_id", "created_at"),
        CheckConstraint("result_count >= 0", name="result_count_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Blank when a search was filters-only (no keyword) — still worth logging
    # for analytics, just never surfaced in the "recent searches" list (see
    # app/api/routes/search.py).
    query: Mapped[str | None] = mapped_column(String(200))
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
