from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_category, make_user


def test_list_categories_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 401


def test_list_categories_returns_seeded_taxonomy(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/categories", headers=auth_headers(token))

    assert response.status_code == 200
    slugs = {c["slug"] for c in response.json()}
    assert "bridal" in slugs  # seeded in Phase 2, category_type=occasion
    assert "beginner-friendly" in slugs  # seeded in Phase 6, category_type=difficulty


def test_list_categories_sets_a_safe_public_cache_header(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/categories", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("public")


def test_list_categories_filters_by_category_type(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.get(
        "/api/v1/categories", params={"category_type": "region"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body  # at least the seeded region categories
    assert all(c["category_type"] == "region" for c in body)


def test_list_categories_rejects_unknown_category_type(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.get(
        "/api/v1/categories", params={"category_type": "flavor"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_customer_cannot_create_category(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Watercolor", "slug": "watercolor", "category_type": "style"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_admin_can_create_category(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Watercolor", "slug": "watercolor", "category_type": "style"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["category_type"] == "style"


def test_admin_cannot_create_category_with_invalid_type(
    client: TestClient, db_session: Session
) -> None:
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Watercolor", "slug": "watercolor", "category_type": "flavor"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_admin_cannot_create_duplicate_slug(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    make_category(db_session, name="Existing", category_type="style")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    existing_slug_response = client.get("/api/v1/categories", headers=auth_headers(token))
    slug = existing_slug_response.json()[0]["slug"]

    response = client.post(
        "/api/v1/categories",
        json={"name": "Another", "slug": slug, "category_type": "style"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_admin_can_update_category(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMINISTRATOR.value)
    category = make_category(db_session, name="Old Name", category_type="style")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/categories/{category.id}",
        json={"name": "New Name", "is_active": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["is_active"] is False


def test_moderator_cannot_manage_categories(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role=UserRole.MODERATOR.value)
    token = sign_token(moderator.id, email=moderator.email)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Watercolor", "slug": "watercolor-2", "category_type": "style"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403
