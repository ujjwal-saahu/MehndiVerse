from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus, UserRole
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_user


def test_create_design_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/designs", json={"title": "Untitled"})
    assert response.status_code == 401


def test_customer_cannot_create_design(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/designs", json={"title": "Bridal Special"}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_artist_without_artist_profile_cannot_create_design(
    client: TestClient, db_session: Session
) -> None:
    artist_user = make_user(db_session, role=UserRole.ARTIST.value)
    token = sign_token(artist_user.id, email=artist_user.email)

    response = client.post(
        "/api/v1/designs", json={"title": "Bridal Special"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_verified_artist_can_create_design_defaulting_to_draft(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/designs",
        json={"title": "Bridal Special", "difficulty_level": "advanced", "body_placement": "hand"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["artist_profile_id"] == str(artist_profile.id)
    assert body["is_premium"] is False
    assert body["is_featured"] is False


def test_verified_artist_can_create_a_premium_design(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/designs",
        json={"title": "Bridal Special", "is_premium": True},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["is_premium"] is True


def test_unverified_artist_cannot_create_a_premium_design(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = ArtistVerificationStatus.SUBMITTED.value
    db_session.add(artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/designs",
        json={"title": "Bridal Special", "is_premium": True},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_create_design_attaches_categories_and_tags(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    category = make_category(db_session, name="Bridal Style", category_type="occasion")
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist2@example.com")

    response = client.post(
        "/api/v1/designs",
        json={
            "title": "Bridal Special",
            "category_ids": [str(category.id)],
            "tag_names": ["Wedding", "  Bold  "],
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert [c["id"] for c in body["categories"]] == [str(category.id)]
    assert body["tags"] == ["bold", "wedding"]


def test_create_design_rejects_unknown_category_id(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist3@example.com")

    response = client.post(
        "/api/v1/designs",
        json={"title": "Bridal Special", "category_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_create_design_rejects_invalid_difficulty(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist4@example.com")

    response = client.post(
        "/api/v1/designs",
        json={"title": "Bridal Special", "difficulty_level": "expert"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_admin_can_create_platform_curated_design(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        "/api/v1/designs", json={"title": "Platform Pick"}, headers=auth_headers(token)
    )

    assert response.status_code == 201
    assert response.json()["artist_profile_id"] is None


def test_moderator_cannot_create_design(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role=UserRole.MODERATOR.value)
    token = sign_token(moderator.id, email=moderator.email)

    response = client.post(
        "/api/v1/designs", json={"title": "Bridal Special"}, headers=auth_headers(token)
    )

    assert response.status_code == 403
