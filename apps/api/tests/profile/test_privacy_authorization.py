from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import Profile, UserPreference
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def _make_profile(db_session: Session, *, email: str, role: str = UserRole.CUSTOMER.value):
    user = make_user(db_session, email=email, role=role)
    db_session.add(
        Profile(user_id=user.id, display_name="Target User", city="Mumbai", country="IN")
    )
    db_session.commit()
    return user


def test_public_profile_is_visible_to_anyone(client: TestClient, db_session: Session) -> None:
    target = _make_profile(db_session, email="public-target@example.com")
    stranger = make_user(db_session, email="stranger@example.com")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["display_name"] == "Target User"


def test_private_profile_is_hidden_from_strangers(client: TestClient, db_session: Session) -> None:
    target = _make_profile(db_session, email="private-target@example.com")
    db_session.add(UserPreference(user_id=target.id, profile_visibility="private"))
    stranger = make_user(db_session, email="stranger2@example.com")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 404


def test_private_profile_is_visible_to_its_owner(client: TestClient, db_session: Session) -> None:
    target = _make_profile(db_session, email="private-owner@example.com")
    db_session.add(UserPreference(user_id=target.id, profile_visibility="private"))
    db_session.commit()
    token = sign_token(target.id, email=target.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 200


def test_private_profile_is_visible_to_staff(client: TestClient, db_session: Session) -> None:
    target = _make_profile(db_session, email="private-vs-staff@example.com")
    db_session.add(UserPreference(user_id=target.id, profile_visibility="private"))
    moderator = make_user(db_session, email="mod@example.com", role=UserRole.MODERATOR.value)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 200


def test_show_location_false_hides_city_and_country_from_others(
    client: TestClient, db_session: Session
) -> None:
    target = _make_profile(db_session, email="hide-location@example.com")
    db_session.add(UserPreference(user_id=target.id, show_location=False))
    stranger = make_user(db_session, email="stranger3@example.com")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["city"] is None
    assert body["country"] is None


def test_show_location_false_does_not_hide_from_owner(
    client: TestClient, db_session: Session
) -> None:
    target = _make_profile(db_session, email="owner-sees-own-location@example.com")
    db_session.add(UserPreference(user_id=target.id, show_location=False))
    db_session.commit()
    token = sign_token(target.id, email=target.email)

    response = client.get(f"/api/v1/users/{target.id}/profile", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["city"] == "Mumbai"
