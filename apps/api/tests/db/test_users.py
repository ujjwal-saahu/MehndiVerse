import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import Profile, User

from .factories import make_user


def test_create_user_with_defaults(db_session: Session) -> None:
    user = make_user(db_session)

    assert user.id is not None
    assert user.status == "active"
    assert user.created_at is not None
    assert user.deleted_at is None


def test_email_uniqueness_is_case_insensitive(db_session: Session) -> None:
    make_user(db_session, email="Someone@Example.com")

    with pytest.raises(IntegrityError):
        make_user(db_session, email="someone@example.com")


def test_invalid_role_is_rejected_by_check_constraint(db_session: Session) -> None:
    user = User(email="bad-role@example.com", role="not_a_real_role")
    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_profile_is_one_to_one_and_cascades_with_user(db_session: Session) -> None:
    user = make_user(db_session)
    profile = Profile(user_id=user.id, display_name="Test User")
    db_session.add(profile)
    db_session.flush()

    profile_id = profile.id
    db_session.delete(user)
    db_session.flush()
    db_session.expunge_all()  # avoid the identity map masking the DB-side cascade delete

    remaining = db_session.execute(
        select(func.count()).select_from(Profile).where(Profile.id == profile_id)
    ).scalar_one()
    assert remaining == 0


def test_role_values_match_documented_enum() -> None:
    assert {r.value for r in UserRole} == {
        "customer",
        "artist",
        "moderator",
        "administrator",
        "super_administrator",
    }
