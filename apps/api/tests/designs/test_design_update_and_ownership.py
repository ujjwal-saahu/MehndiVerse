from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus, UserRole
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_design, make_user


def test_update_design_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session)
    db_session.commit()

    response = client.patch(f"/api/v1/designs/{design.id}", json={"title": "New Title"})

    assert response.status_code == 401


def test_owner_can_update_their_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="owner@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}",
        json={"title": "Updated Title", "description": "A lovely pattern."},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_another_artist_cannot_update_someone_elses_design(
    client: TestClient, db_session: Session
) -> None:
    owner_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=owner_profile)
    other_profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(other_profile.user_id, email="other@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"title": "Hijacked"}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_customer_cannot_update_any_design(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session)
    customer = make_user(db_session)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"title": "Hijacked"}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_admin_can_update_any_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"title": "Admin Edit"}, headers=auth_headers(token)
    )

    assert response.status_code == 200


def test_moderator_cannot_edit_designs(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session)
    moderator = make_user(db_session, role=UserRole.MODERATOR.value)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"title": "Mod Edit"}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_owner_can_publish_a_draft_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="publisher@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"status": "published"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_owner_can_unpublish_back_to_draft(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="unpublisher@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"status": "draft"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_owner_cannot_set_status_to_archived_via_update(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="archiver@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"status": "archived"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_owner_cannot_set_status_to_flagged(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="flagger@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"status": "flagged"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_owner_can_toggle_is_premium(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="premium@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"is_premium": True}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["is_premium"] is True


def test_unverified_artist_cannot_toggle_is_premium(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = ArtistVerificationStatus.UNDER_REVIEW.value
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.add(artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="pending@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"is_premium": True}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_unverified_artist_can_turn_off_premium(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    design.is_premium = True
    artist_profile.verification_status = ArtistVerificationStatus.UNDER_REVIEW.value
    db_session.add_all([artist_profile, design])
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="pending@example.com")

    response = client.patch(
        f"/api/v1/designs/{design.id}", json={"is_premium": False}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["is_premium"] is False


def test_update_design_replaces_categories_when_provided(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    old_category = make_category(db_session, category_type="style")
    new_category = make_category(db_session, category_type="occasion")
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="categorizer@example.com")

    client.patch(
        f"/api/v1/designs/{design.id}",
        json={"category_ids": [str(old_category.id)]},
        headers=auth_headers(token),
    )
    response = client.patch(
        f"/api/v1/designs/{design.id}",
        json={"category_ids": [str(new_category.id)]},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert [c["id"] for c in response.json()["categories"]] == [str(new_category.id)]
