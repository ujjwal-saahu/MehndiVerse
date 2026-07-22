from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus
from app.db.models.artist import ArtistProfile
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user, make_user_block


def _draft(db_session: Session) -> ArtistProfile:
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.DRAFT.value
    db_session.add(profile)
    return profile


def _viewer_token(db_session: Session) -> str:
    viewer = make_user(db_session, role="customer")
    db_session.commit()
    return sign_token(viewer.id, email=viewer.email)


def test_get_artist_requires_authentication(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()

    response = client.get(f"/api/v1/artists/{profile.id}")

    assert response.status_code == 401


def test_stranger_gets_404_for_a_draft_profile(client: TestClient, db_session: Session) -> None:
    profile = _draft(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token))

    assert response.status_code == 404


def test_owner_can_view_their_own_draft_profile(client: TestClient, db_session: Session) -> None:
    profile = _draft(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token))

    assert response.status_code == 200


def test_approved_profile_includes_services_portfolio_and_availability(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    profile.professional_name = "Priya Sharma"
    profile.bio = "Ten years of bridal henna."
    db_session.add(profile)
    make_design(db_session, artist_profile=profile, status="published")
    make_design(db_session, artist_profile=profile, status="draft")  # should not appear
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Priya Sharma"
    assert body["is_verified"] is True
    assert body["portfolio_count"] == 1
    assert len(body["portfolio_preview"]) == 1
    assert body["services"] == []
    assert body["availability_preview"] == []
    assert body["follower_count"] == 0
    assert body["is_followed"] is False


def test_full_portfolio_is_reachable_via_published_designs_filter(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    make_design(db_session, artist_profile=profile, status="published")
    other = make_artist_profile(db_session)
    make_design(db_session, artist_profile=other, status="published")
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        "/api/v1/designs/published",
        params={"artist_profile_id": str(profile.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["artist_profile_id"] == str(profile.id)


def test_follow_and_unfollow(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    follow_response = client.post(
        f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token)
    )
    assert follow_response.status_code == 204

    detail = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token)).json()
    assert detail["is_followed"] is True
    assert detail["follower_count"] == 1

    unfollow_response = client.delete(
        f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token)
    )
    assert unfollow_response.status_code == 204

    detail_after = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token)).json()
    assert detail_after["is_followed"] is False
    assert detail_after["follower_count"] == 0


def test_following_twice_is_idempotent(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    client.post(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))
    client.post(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))

    detail = client.get(f"/api/v1/artists/{profile.id}", headers=auth_headers(token)).json()
    assert detail["follower_count"] == 1


def test_unfollowing_when_not_following_is_a_no_op(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.delete(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))

    assert response.status_code == 204


def test_cannot_follow_yourself(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))

    assert response.status_code == 422


def test_blocked_user_cannot_follow_artist(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    viewer = make_user(db_session, role="customer")
    artist_user = db_session.get(User, profile.user_id)
    assert artist_user is not None
    make_user_block(db_session, blocker=artist_user, blocked=viewer)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))

    assert response.status_code == 403


def test_following_artist_who_blocked_you_the_other_direction_also_fails(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    viewer = make_user(db_session, role="customer")
    artist_user = db_session.get(User, profile.user_id)
    assert artist_user is not None
    make_user_block(db_session, blocker=viewer, blocked=artist_user)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/artists/{profile.id}/follow", headers=auth_headers(token))

    assert response.status_code == 403
