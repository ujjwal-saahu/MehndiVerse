"""Shared user-blocking check — see docs/community-and-trust.md#6-blocked-
users-cannot-directly-interact.

`UserBlock` (Phase 5) was a self-service foundation that nothing else
consulted at the time ("later phases that touch messaging, discovery, and
notifications are responsible for checking it" — see the model's own
docstring in app/db/models/user.py). Phase 14 was the first consumer
(messaging); this module extracts that check into one shared place so
every subsequent direct-interaction surface (comments, reviews, follows —
Phase 16) enforces the exact same rule rather than each re-implementing it.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import UserBlock


def is_blocked_either_direction(db: Session, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
    """True if either user has blocked the other, in either direction."""
    return (
        db.execute(
            select(UserBlock.id).where(
                ((UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b))
                | ((UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a))
            )
        ).first()
        is not None
    )
