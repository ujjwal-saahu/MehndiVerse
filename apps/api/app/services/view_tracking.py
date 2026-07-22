"""View-count event handling foundation — see
docs/design-gallery.md#view-count-event-handling.

Every view increments `designs.view_count` atomically (a single `UPDATE ...
SET view_count = view_count + 1`, never read-modify-write in Python, so
concurrent viewers never lose an increment). A short-lived Redis key
deduplicates rapid repeat views from the same signed-in viewer — e.g.
reopening the same design a few times in one sitting — so a single visit
doesn't inflate the count. This is intentionally simple: no anonymous/IP
based dedup, no sliding analytics window. It's a foundation a later
analytics-focused phase can replace without changing the increment contract.

If Redis is unavailable, the dedup check is skipped (fails open) rather than
blocking the view-count increment on a non-critical dependency — a missed
dedup just means one extra count, not a broken feature.
"""

import uuid

from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.db.enums import AnalyticsEventType, DesignStatus
from app.db.models.design import Design
from app.services.analytics.events import record_event

logger = get_logger(__name__)

_DEDUP_TTL_SECONDS = 30 * 60


def _recently_counted(design_id: uuid.UUID, viewer_id: uuid.UUID) -> bool:
    key = f"design_view:{design_id}:{viewer_id}"
    try:
        # SET ... NX returns None/False if the key already existed, i.e. this
        # viewer was already counted within the window.
        was_new = get_redis_client().set(key, "1", nx=True, ex=_DEDUP_TTL_SECONDS)
        return not was_new
    except (RedisError, OSError):
        logger.warning("view_dedup_unavailable", design_id=str(design_id))
        return False


def record_design_view(db: Session, *, design_id: uuid.UUID, viewer_id: uuid.UUID) -> None:
    if _recently_counted(design_id, viewer_id):
        return

    db.execute(
        update(Design)
        .where(Design.id == design_id, Design.status == DesignStatus.PUBLISHED.value)
        .values(view_count=Design.view_count + 1)
    )
    record_event(
        db,
        event_type=AnalyticsEventType.DESIGN_VIEWED.value,
        user_id=viewer_id,
        entity_type="design",
        entity_id=design_id,
    )
    db.commit()
