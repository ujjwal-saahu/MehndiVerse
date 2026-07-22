from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.artist import ArtistProfile
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_review,
    make_user,
    make_user_block,
)


def _completed_booking(db_session: Session):
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.COMPLETED.value,
    )
    db_session.commit()
    return artist_profile, customer, booking


def test_review_requires_authentication(client: TestClient, db_session: Session) -> None:
    _, _, booking = _completed_booking(db_session)

    response = client.post(f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 5})

    assert response.status_code == 401


def test_customer_can_review_completed_booking(client: TestClient, db_session: Session) -> None:
    artist_profile, customer, booking = _completed_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews",
        json={"rating": 5, "body": "Fantastic henna artist!"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 5
    assert body["booking_id"] == str(booking.id)


def test_non_customer_cannot_review_booking(client: TestClient, db_session: Session) -> None:
    _, _, booking = _completed_booking(db_session)
    other = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(other.id, email=other.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 4}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_artist_cannot_review_own_booking(client: TestClient, db_session: Session) -> None:
    artist_profile, _, booking = _completed_booking(db_session)
    token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 4}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_cannot_review_non_completed_booking(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 5}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_one_review_per_booking(client: TestClient, db_session: Session) -> None:
    artist_profile, customer, booking = _completed_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    first = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 5}, headers=auth_headers(token)
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 3}, headers=auth_headers(token)
    )
    assert second.status_code == 409


def test_rating_out_of_range_is_rejected_by_schema(client: TestClient, db_session: Session) -> None:
    _, customer, booking = _completed_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 6}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_rating_zero_is_rejected(client: TestClient, db_session: Session) -> None:
    _, customer, booking = _completed_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 0}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_blocked_customer_cannot_review_artist(client: TestClient, db_session: Session) -> None:
    artist_profile, customer, booking = _completed_booking(db_session)
    artist_user = db_session.get(User, artist_profile.user_id)
    assert artist_user is not None
    make_user_block(db_session, blocker=artist_user, blocked=customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reviews", json={"rating": 5}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_rating_aggregation_recomputes_average_and_count(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)

    def _review(rating: int) -> None:
        customer = make_user(db_session, role="customer")
        booking = make_booking(
            db_session,
            customer=customer,
            artist_profile=artist_profile,
            status=BookingStatus.COMPLETED.value,
        )
        db_session.commit()
        token = sign_token(customer.id, email=customer.email)
        response = client.post(
            f"/api/v1/bookings/{booking.id}/reviews",
            json={"rating": rating},
            headers=auth_headers(token),
        )
        assert response.status_code == 201

    _review(5)
    _review(3)
    _review(4)

    db_session.expire_all()
    refreshed = db_session.get(ArtistProfile, artist_profile.id)
    assert refreshed is not None
    assert refreshed.rating_count == 3
    assert float(refreshed.rating_average) == 4.0


def test_list_artist_reviews_includes_rating_summary(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.COMPLETED.value,
    )
    make_review(db_session, booking=booking, rating=4)
    artist_profile.rating_average = 4
    artist_profile.rating_count = 1
    db_session.add(artist_profile)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(
        f"/api/v1/artists/{artist_profile.id}/reviews", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["rating_average"] == 4.0
    assert body["rating_count"] == 1
