from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_design, make_user


def test_like_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/like")

    assert response.status_code == 401


def test_like_increments_like_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"liked": True, "like_count": 1}


def test_liking_twice_does_not_double_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    first = client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))
    second = client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"liked": True, "like_count": 1}


def test_unlike_decrements_like_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)
    client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    response = client.delete(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"liked": False, "like_count": 0}


def test_unliking_when_not_liked_is_a_no_op(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.delete(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"liked": False, "like_count": 0}


def test_two_users_liking_the_same_design_both_count(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    alice = make_user(db_session)
    bob = make_user(db_session)
    db_session.commit()

    client.post(
        f"/api/v1/designs/{design.id}/like",
        headers=auth_headers(sign_token(alice.id, email=alice.email)),
    )
    response = client.post(
        f"/api/v1/designs/{design.id}/like",
        headers=auth_headers(sign_token(bob.id, email=bob.email)),
    )

    assert response.json() == {"liked": True, "like_count": 2}


def test_like_unpublished_design_returns_404(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="draft")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))

    assert response.status_code == 404


def test_like_nonexistent_design_returns_404(client: TestClient, db_session: Session) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(
        "/api/v1/designs/00000000-0000-0000-0000-000000000000/like",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_design_detail_reflects_like_state(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    before = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert before.json()["is_liked"] is False

    client.post(f"/api/v1/designs/{design.id}/like", headers=auth_headers(token))
    after = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert after.json()["is_liked"] is True
    assert after.json()["like_count"] == 1
