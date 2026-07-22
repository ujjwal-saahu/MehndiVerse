import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import Profile
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def test_get_profile_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me/profile")
    assert response.status_code == 401


def test_get_profile_returns_existing_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="withprofile@example.com")
    db_session.add(Profile(user_id=user.id, display_name="Existing Name", bio="Hello there"))
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/users/me/profile", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Existing Name"
    assert body["bio"] == "Hello there"


def test_get_profile_lazily_creates_one_if_missing(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="noprofile@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/users/me/profile", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["display_name"] == "noprofile"
    assert db_session.query(Profile).filter(Profile.user_id == user.id).count() == 1


def test_update_profile_applies_only_provided_fields(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="partial@example.com")
    db_session.add(
        Profile(user_id=user.id, display_name="Original", bio="Original bio", city="Mumbai")
    )
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"bio": "Updated bio"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Updated bio"
    assert body["display_name"] == "Original"
    assert body["city"] == "Mumbai"


def test_update_profile_rejects_blank_display_name(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="blank@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"display_name": "   "},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_update_profile_rejects_invalid_country_code(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="badcountry@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"country": "India"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_update_profile_normalizes_country_code_case(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="lowercountry@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"country": "in"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["country"] == "IN"


def test_update_profile_rejects_invalid_locale(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="badlocale@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"locale": "not-a-locale!"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_update_profile_has_no_route_to_target_another_user(
    client: TestClient, db_session: Session
) -> None:
    """The update endpoint takes no user id — it always operates on the
    authenticated caller, so there is no request shape that edits someone
    else's profile. Sending an extraneous user_id in the body is simply
    ignored (Pydantic drops unknown fields by default)."""
    victim = make_user(db_session, email="victim@example.com")
    db_session.add(Profile(user_id=victim.id, display_name="Victim"))
    attacker = make_user(db_session, email="attacker@example.com")
    db_session.commit()
    token = sign_token(attacker.id, email=attacker.email)

    response = client.patch(
        "/api/v1/users/me/profile",
        json={"user_id": str(victim.id), "display_name": "Hacked"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    db_session.refresh(victim)
    victim_profile = db_session.query(Profile).filter(Profile.user_id == victim.id).one()
    assert victim_profile.display_name == "Victim"


def test_get_public_profile_returns_404_for_unknown_user(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="viewer@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.get(f"/api/v1/users/{uuid.uuid4()}/profile", headers=auth_headers(token))

    assert response.status_code == 404
