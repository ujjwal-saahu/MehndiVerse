"""Authorization on booking conversations — see docs/booking-messaging.md#2.
Every endpoint requires the caller to be one of the booking's two parties;
a third party (and staff, via the ordinary member-facing router) gets 403."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def test_get_conversation_requires_authentication(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()

    response = client.get(f"/api/v1/bookings/{booking.id}/conversation")
    assert response.status_code == 401


def test_third_party_cannot_view_conversation(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.get(
        f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_unknown_booking_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get(
        "/api/v1/bookings/00000000-0000-0000-0000-000000000000/conversation",
        headers=auth_headers(token),
    )
    assert response.status_code == 404


def test_draft_booking_has_no_conversation_yet(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.DRAFT.value
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(
        f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(token)
    )
    assert response.status_code == 422


def test_customer_and_artist_can_both_view_the_conversation(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    customer_response = client.get(
        f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(customer_token)
    )
    artist_response = client.get(
        f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(artist_token)
    )

    assert customer_response.status_code == 200
    assert artist_response.status_code == 200
    assert customer_response.json()["id"] == artist_response.json()["id"]


def test_conversation_is_created_lazily_and_only_once(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    first = client.get(f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(token))
    second = client.get(f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(token))

    assert first.json()["id"] == second.json()["id"]


def test_third_party_cannot_send_a_message(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "hi"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_third_party_cannot_list_messages(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.get(
        f"/api/v1/bookings/{booking.id}/conversation/messages", headers=auth_headers(token)
    )
    assert response.status_code == 403
