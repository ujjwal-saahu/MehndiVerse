"""Account-deletion finalization — see docs/security-review.md#account-
deletion.

`POST /auth/account/deletion-request` (app/api/routes/auth.py) only ever
flagged the account (`status = pending_deletion`, `deletion_requested_at`
set) — nothing processed that flag into an actual deletion. `User.deleted_at`
(via `SoftDeleteMixin`) already existed and `get_current_user` already
rejects any account with `deleted_at` set, but nothing ever wrote to it.
This module is that missing processing step, run periodically via
app/cli/process_account_deletions.py, mirroring app/cli/process_
subscriptions.py's "no scheduler exists yet" standalone-script shape.

Scope: anonymizes PII in *our* database and marks the account gone locally.
It does not call Supabase's Admin API to delete the underlying `auth.users`
row — that needs a service-role-authenticated GoTrue Admin API integration
this codebase doesn't have yet (see docs/security-review.md's account-
deletion finding for the recommended follow-up). Dependent records
(bookings, reviews, messages) are deliberately left in place rather than
cascade-deleted: once the account's own PII is scrubbed, those rows no
longer identify the person, and removing them outright would break other
parties' own booking/review history.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import UserStatus
from app.db.models.system import AuditLog
from app.db.models.user import Profile, User, UserDevice


@dataclass(frozen=True)
class DeletionResult:
    user_id: uuid.UUID


def _anonymize(db: Session, user: User) -> None:
    now = datetime.now(UTC)
    user.email = f"deleted-{user.id}@deleted.mehndiverse.invalid"
    user.phone = None
    user.deleted_at = now
    db.add(user)

    profile = db.execute(select(Profile).where(Profile.user_id == user.id)).scalar_one_or_none()
    if profile is not None:
        profile.display_name = "Deleted user"
        profile.avatar_url = None
        profile.bio = None
        profile.city = None
        profile.country = None
        db.add(profile)

    for device in db.execute(select(UserDevice).where(UserDevice.user_id == user.id)).scalars():
        db.delete(device)

    db.add(
        AuditLog(
            actor_id=None,
            action="account.deletion_finalized",
            entity_type="user",
            entity_id=user.id,
        )
    )


def process_pending_deletions(
    db: Session, *, grace_period_days: int | None = None
) -> list[DeletionResult]:
    """Finalizes every account whose deletion grace period has elapsed.
    Does not commit — the CLI caller commits (or rolls back for
    `--dry-run`), matching every other app/cli/process_*.py script."""
    if grace_period_days is None:
        grace_period_days = get_settings().account_deletion_grace_period_days
    cutoff = datetime.now(UTC) - timedelta(days=grace_period_days)

    due = db.execute(
        select(User).where(
            User.status == UserStatus.PENDING_DELETION.value,
            User.deletion_requested_at.is_not(None),
            User.deletion_requested_at <= cutoff,
            User.deleted_at.is_(None),
        )
    ).scalars()

    results = []
    for user in due:
        _anonymize(db, user)
        results.append(DeletionResult(user_id=user.id))
    return results
