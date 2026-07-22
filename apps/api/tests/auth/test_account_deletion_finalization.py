"""app/services/account_deletion.py — see docs/security-review.md#account-
deletion."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import UserRole, UserStatus
from app.db.models.system import AuditLog
from app.db.models.user import Profile, User
from app.services.account_deletion import process_pending_deletions


def _make_pending_deletion_user(
    db: Session, *, requested_at: datetime, email: str = "pending@example.com"
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        role=UserRole.CUSTOMER.value,
        status=UserStatus.PENDING_DELETION.value,
        deletion_requested_at=requested_at,
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, display_name="Original Name", bio="hello", city="Mumbai"))
    return user


def test_leaves_a_user_inside_the_grace_period_untouched(db_session: Session) -> None:
    user = _make_pending_deletion_user(
        db_session, requested_at=datetime.now(UTC) - timedelta(days=1)
    )
    db_session.commit()

    results = process_pending_deletions(db_session, grace_period_days=14)

    assert results == []
    db_session.refresh(user)
    assert user.deleted_at is None
    assert user.email == "pending@example.com"


def test_anonymizes_a_user_past_the_grace_period(db_session: Session) -> None:
    user = _make_pending_deletion_user(
        db_session, requested_at=datetime.now(UTC) - timedelta(days=20)
    )
    db_session.commit()

    results = process_pending_deletions(db_session, grace_period_days=14)
    db_session.commit()

    assert [r.user_id for r in results] == [user.id]
    db_session.refresh(user)
    assert user.deleted_at is not None
    assert user.email == f"deleted-{user.id}@deleted.mehndiverse.invalid"

    profile = db_session.execute(select(Profile).where(Profile.user_id == user.id)).scalar_one()
    assert profile.display_name == "Deleted user"
    assert profile.bio is None
    assert profile.city is None


def test_finalization_is_audit_logged(db_session: Session) -> None:
    user = _make_pending_deletion_user(
        db_session,
        requested_at=datetime.now(UTC) - timedelta(days=20),
        email="audited@example.com",
    )
    db_session.commit()

    process_pending_deletions(db_session, grace_period_days=14)
    db_session.commit()

    events = (
        db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "account.deletion_finalized",
                AuditLog.entity_id == user.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


def test_an_already_finalized_user_is_not_processed_twice(db_session: Session) -> None:
    _make_pending_deletion_user(db_session, requested_at=datetime.now(UTC) - timedelta(days=20))
    db_session.commit()

    process_pending_deletions(db_session, grace_period_days=14)
    db_session.commit()

    second_pass = process_pending_deletions(db_session, grace_period_days=14)
    assert second_pass == []
