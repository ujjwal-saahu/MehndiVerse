from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.artist import ArtistProfile
from app.services.reviews import recompute_artist_rating
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_review, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def _review(db_session: Session, *, rating: int = 4):
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(
        db_session, artist_profile=artist_profile, status=BookingStatus.COMPLETED.value
    )
    review = make_review(db_session, booking=booking, rating=rating)
    recompute_artist_rating(db_session, artist_profile.id)
    db_session.commit()
    return artist_profile, review


def test_list_reviews_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")
    response = client.get("/api/v1/admin/reviews", headers=auth_headers(token))
    assert response.status_code == 403


def test_moderator_can_view_but_not_moderate_a_review(
    client: TestClient, db_session: Session
) -> None:
    _, review = _review(db_session)
    _, moderator_token = _token(db_session, role="moderator")

    list_response = client.get("/api/v1/admin/reviews", headers=auth_headers(moderator_token))
    assert list_response.status_code == 200

    moderate_response = client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "remove", "reason": "Contains personal information"},
        headers=auth_headers(moderator_token),
    )
    assert moderate_response.status_code == 403


def test_admin_can_remove_a_review_and_rating_recomputes(
    client: TestClient, db_session: Session
) -> None:
    artist_profile, _kept_review = _review(db_session, rating=5)
    booking2 = make_booking(
        db_session, artist_profile=artist_profile, status=BookingStatus.COMPLETED.value
    )
    remove_me = make_review(db_session, booking=booking2, rating=1)
    recompute_artist_rating(db_session, artist_profile.id)
    db_session.commit()

    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/reviews/{remove_me.id}/moderate",
        json={"action": "remove", "reason": "Contains personal information"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["is_deleted"] is True

    db_session.expire_all()
    refreshed = db_session.get(ArtistProfile, artist_profile.id)
    assert refreshed is not None
    assert refreshed.rating_count == 1
    assert float(refreshed.rating_average) == 5.0


def test_moderate_without_reason_is_rejected(client: TestClient, db_session: Session) -> None:
    _, review = _review(db_session)
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "remove", "reason": ""},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_admin_can_restore_a_removed_review(client: TestClient, db_session: Session) -> None:
    artist_profile, review = _review(db_session)
    _, admin_token = _token(db_session, role="administrator")

    client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "remove", "reason": "Under investigation"},
        headers=auth_headers(admin_token),
    )
    response = client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "restore", "reason": "Investigation concluded, no issue found"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["is_deleted"] is False


def test_flag_and_unflag_a_review(client: TestClient, db_session: Session) -> None:
    _, review = _review(db_session)
    _, admin_token = _token(db_session, role="administrator")

    flag_response = client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "flag", "reason": "Reported by artist as unfair"},
        headers=auth_headers(admin_token),
    )
    assert flag_response.json()["is_flagged"] is True

    unflag_response = client.post(
        f"/api/v1/admin/reviews/{review.id}/moderate",
        json={"action": "unflag", "reason": "Reviewed, no policy violation"},
        headers=auth_headers(admin_token),
    )
    assert unflag_response.json()["is_flagged"] is False
