"""Booking draft creation/editing and submission — see
docs/booking-lifecycle.md#3-booking-draft-and-submission."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_artist_service, make_user

_VALID_UPDATE = {
    "service_id": None,
    "requested_date": "2026-03-09",
    "requested_time": "10:00:00",
    "location_type": "artist_studio",
    "contact_name": "Priya Sharma",
    "contact_email": "priya@example.com",
    "contact_phone": "+911234567890",
}


def test_create_draft_requires_authentication(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    response = client.post("/api/v1/bookings", json={"artist_profile_id": str(profile.id)})
    assert response.status_code == 401


def test_create_draft_for_unknown_artist_is_404(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/bookings",
        json={"artist_profile_id": str(uuid.uuid4())},
        headers=auth_headers(token),
    )
    assert response.status_code == 404


def test_create_draft_when_artist_not_accepting_bookings_is_409(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    profile.is_accepting_bookings = False
    db_session.add(profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/bookings",
        json={"artist_profile_id": str(profile.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 409


def test_create_draft_succeeds(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/bookings",
        json={"artist_profile_id": str(profile.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert len(body["status_history"]) == 1
    assert body["status_history"][0]["from_status"] is None
    assert body["status_history"][0]["to_status"] == "draft"


def test_update_draft_by_non_owner_is_403(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    other = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    other_token = sign_token(other.id, email=other.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={"notes": "hi"},
        headers=auth_headers(other_token),
    )
    assert response.status_code == 403


def test_update_draft_rejects_service_from_another_artist(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    other_service = make_artist_service(db_session, artist_profile=other_profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={"service_id": str(other_service.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 404


def test_update_draft_rejects_invalid_budget_range(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={"budget_min": 5000, "budget_max": 1000},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_update_draft_rejects_invalid_location_type(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={"location_type": "on_the_moon"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_cannot_edit_a_booking_that_is_no_longer_a_draft(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()
    client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={**_VALID_UPDATE, "service_id": str(service.id)},
        headers=auth_headers(token),
    )
    client.post(f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(token))

    response = client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={"notes": "too late"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_submit_rejects_missing_required_fields(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.post(f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(token))
    assert response.status_code == 422
    assert "service_id" in response.json()["error"]["message"]


def test_submit_requires_location_address_for_customer_location(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()
    client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={**_VALID_UPDATE, "service_id": str(service.id), "location_type": "customer_location"},
        headers=auth_headers(token),
    )

    response = client.post(f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(token))
    assert response.status_code == 422
    assert "location_address" in response.json()["error"]["message"]


def test_submit_succeeds(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()
    client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={**_VALID_UPDATE, "service_id": str(service.id)},
        headers=auth_headers(token),
    )

    response = client.post(f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "requested"
    assert len(body["status_history"]) == 2


def test_submit_by_non_owner_is_403(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    other = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    other_token = sign_token(other.id, email=other.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.post(
        f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(other_token)
    )
    assert response.status_code == 403


def test_get_booking_unknown_id_is_404(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(f"/api/v1/bookings/{uuid.uuid4()}", headers=auth_headers(token))
    assert response.status_code == 404


def test_get_booking_by_third_party_is_403(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    third_party_token = sign_token(third_party.id, email=third_party.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.get(
        f"/api/v1/bookings/{created['id']}", headers=auth_headers(third_party_token)
    )
    assert response.status_code == 403


def test_get_booking_by_the_artist_succeeds(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()

    response = client.get(f"/api/v1/bookings/{created['id']}", headers=auth_headers(artist_token))
    assert response.status_code == 200
