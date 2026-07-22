import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.engagement import Collection, Like

from .factories import make_design, make_user


def test_like_is_unique_per_user_and_design(db_session: Session) -> None:
    user = make_user(db_session)
    design = make_design(db_session)
    db_session.add(Like(user_id=user.id, design_id=design.id))
    db_session.flush()

    db_session.add(Like(user_id=user.id, design_id=design.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_collection_name_unique_per_user(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add(Collection(user_id=user.id, name="Favorites"))
    db_session.flush()

    db_session.add(Collection(user_id=user.id, name="Favorites"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_collection_name_allowed_for_different_users(db_session: Session) -> None:
    user_a = make_user(db_session)
    user_b = make_user(db_session)
    db_session.add(Collection(user_id=user_a.id, name="Favorites"))
    db_session.add(Collection(user_id=user_b.id, name="Favorites"))

    db_session.flush()  # should not raise


def test_design_defaults_to_draft_status(db_session: Session) -> None:
    design = make_design(db_session)

    assert design.status == "draft"
    assert design.view_count == 0
    assert design.like_count == 0
