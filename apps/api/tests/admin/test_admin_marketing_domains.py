from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_design, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


# --- Promotional banners ------------------------------------------------------


def test_moderator_cannot_create_a_banner(client: TestClient, db_session: Session) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        "/api/v1/admin/banners",
        json={"title": "Diwali Sale", "image_url": "https://cdn.example.com/banner.jpg"},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 403


def test_admin_can_create_list_update_and_delete_a_banner(
    client: TestClient, db_session: Session
) -> None:
    _, admin_token = _token(db_session, role="administrator")

    create_response = client.post(
        "/api/v1/admin/banners",
        json={"title": "Diwali Sale", "image_url": "https://cdn.example.com/banner.jpg"},
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    banner_id = create_response.json()["id"]
    assert create_response.json()["is_active"] is True

    list_response = client.get(
        "/api/v1/admin/banners", params={"is_active": True}, headers=auth_headers(admin_token)
    )
    assert any(b["id"] == banner_id for b in list_response.json()["items"])

    update_response = client.patch(
        f"/api/v1/admin/banners/{banner_id}",
        json={"is_active": False},
        headers=auth_headers(admin_token),
    )
    assert update_response.json()["is_active"] is False

    delete_response = client.delete(
        f"/api/v1/admin/banners/{banner_id}", headers=auth_headers(admin_token)
    )
    assert delete_response.status_code == 204


# --- Featured collections ------------------------------------------------------


def test_moderator_cannot_create_a_featured_collection(
    client: TestClient, db_session: Session
) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        "/api/v1/admin/featured-collections",
        json={"title": "Bridal Favorites"},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 403


def test_admin_can_create_a_collection_and_manage_its_items(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    create_response = client.post(
        "/api/v1/admin/featured-collections",
        json={"title": "Bridal Favorites"},
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    collection_id = create_response.json()["id"]
    assert create_response.json()["items"] == []

    add_response = client.post(
        f"/api/v1/admin/featured-collections/{collection_id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(admin_token),
    )
    assert add_response.status_code == 201
    items = add_response.json()["items"]
    assert len(items) == 1
    item_id = items[0]["id"]

    duplicate_response = client.post(
        f"/api/v1/admin/featured-collections/{collection_id}/items",
        json={"design_id": str(design.id)},
        headers=auth_headers(admin_token),
    )
    assert duplicate_response.status_code == 409

    remove_response = client.delete(
        f"/api/v1/admin/featured-collections/{collection_id}/items/{item_id}",
        headers=auth_headers(admin_token),
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["items"] == []


# --- Notification campaigns ------------------------------------------------------


def test_moderator_cannot_create_a_campaign(client: TestClient, db_session: Session) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        "/api/v1/admin/notification-campaigns",
        json={"title": "New Year Sale", "body": "20% off all bookings this week!"},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 403


def test_admin_can_create_and_send_a_campaign_to_targeted_role(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, role="customer")
    make_user(db_session, role="customer")
    make_user(db_session, role="artist")
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    create_response = client.post(
        "/api/v1/admin/notification-campaigns",
        json={
            "title": "New Year Sale",
            "body": "20% off all bookings this week!",
            "target_role": "customer",
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "draft"
    campaign_id = create_response.json()["id"]

    send_response = client.post(
        f"/api/v1/admin/notification-campaigns/{campaign_id}/send",
        headers=auth_headers(admin_token),
    )

    assert send_response.status_code == 200
    body = send_response.json()
    assert body["status"] == "sent"
    # At least the two customers created above (there may be more from
    # other fixtures/migrations, so assert a lower bound, not an exact count).
    assert body["recipient_count"] >= 2


def test_cannot_send_a_campaign_twice(client: TestClient, db_session: Session) -> None:
    _, admin_token = _token(db_session, role="administrator")
    campaign_id = client.post(
        "/api/v1/admin/notification-campaigns",
        json={"title": "Test", "body": "Test body"},
        headers=auth_headers(admin_token),
    ).json()["id"]

    client.post(
        f"/api/v1/admin/notification-campaigns/{campaign_id}/send",
        headers=auth_headers(admin_token),
    )
    second_send = client.post(
        f"/api/v1/admin/notification-campaigns/{campaign_id}/send",
        headers=auth_headers(admin_token),
    )

    assert second_send.status_code == 422
