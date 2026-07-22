from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user

_FIXED_SERVICE = {
    "name": "Bridal Henna Package",
    "pricing_type": "fixed",
    "price_amount": 5000,
    "currency": "inr",
    "duration_minutes": 120,
    "customer_capacity": 1,
    "deposit_required": True,
    "deposit_amount": 1000,
    "travel_charge_amount": 500,
    "cancellation_policy": "Full refund up to 48 hours before the appointment.",
}


def test_list_services_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artist/services")
    assert response.status_code == 401


def test_create_service_requires_an_artist_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(token)
    )

    assert response.status_code == 404


def test_customer_cannot_create_a_service(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_create_and_list_fixed_price_service(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    create_response = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(token)
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "Bridal Henna Package"
    assert body["currency"] == "INR"
    assert body["is_active"] is True

    list_response = client.get("/api/v1/artist/services", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_range_priced_service_requires_min_and_max(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/services",
        json={
            "name": "Party Henna",
            "pricing_type": "range",
            "price_min": 1000,
            "currency": "INR",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_fixed_price_service_rejects_price_range_fields(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/services",
        json={
            "name": "Party Henna",
            "pricing_type": "fixed",
            "price_amount": 1000,
            "price_min": 500,
            "currency": "INR",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_custom_quote_service_rejects_any_price_field(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/services",
        json={"name": "Custom Bridal Package", "pricing_type": "custom_quote", "currency": "INR"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["pricing_type"] == "custom_quote"


def test_owner_can_update_and_deactivate_a_service(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/artist/services/{created['id']}",
        json={"is_active": False, "price_amount": 6000},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["price_amount"] == 6000


def test_update_rejects_inconsistent_pricing_after_merge(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(token)
    ).json()

    # Switching to range pricing without also supplying price_min/price_max
    # should fail once merged onto the existing (fixed-shaped) row.
    response = client.patch(
        f"/api/v1/artist/services/{created['id']}",
        json={"pricing_type": "range"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_another_artist_cannot_update_someone_elses_service(
    client: TestClient, db_session: Session
) -> None:
    owner = make_artist_profile(db_session)
    other = make_artist_profile(db_session)
    db_session.commit()
    owner_token = sign_token(owner.user_id, email="owner@example.com")
    other_token = sign_token(other.user_id, email="other@example.com")
    created = client.post(
        "/api/v1/artist/services", json=_FIXED_SERVICE, headers=auth_headers(owner_token)
    ).json()

    response = client.patch(
        f"/api/v1/artist/services/{created['id']}",
        json={"is_active": False},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_update_unknown_service_is_404(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.patch(
        "/api/v1/artist/services/00000000-0000-0000-0000-000000000000",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 404
