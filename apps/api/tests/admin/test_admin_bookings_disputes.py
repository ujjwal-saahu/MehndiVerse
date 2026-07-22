from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def test_list_bookings_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")
    response = client.get("/api/v1/admin/bookings", headers=auth_headers(token))
    assert response.status_code == 403


def test_moderator_can_view_but_not_open_a_dispute(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session, status=BookingStatus.CONFIRMED.value)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    list_response = client.get("/api/v1/admin/bookings", headers=auth_headers(moderator_token))
    assert list_response.status_code == 200

    dispute_response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/dispute",
        json={"reason": "Customer complaint about service quality"},
        headers=auth_headers(moderator_token),
    )
    assert dispute_response.status_code == 403


def test_admin_can_open_a_dispute_with_reason(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session, status=BookingStatus.CONFIRMED.value)
    db_session.commit()
    admin, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/dispute",
        json={"reason": "Customer complaint about service quality"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disputed"

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "bookings", AuditLog.action == "booking.dispute.open")
        .one()
    )
    assert entry.actor_id == admin.id


def test_dispute_without_reason_is_rejected(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session, status=BookingStatus.CONFIRMED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/dispute",
        json={"reason": ""},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_cannot_dispute_a_booking_that_is_not_in_a_disputable_status(
    client: TestClient, db_session: Session
) -> None:
    booking = make_booking(db_session, status=BookingStatus.DRAFT.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/dispute",
        json={"reason": "Testing"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_admin_can_resolve_a_dispute(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session, status=BookingStatus.DISPUTED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/resolve-dispute",
        json={"to_status": "completed", "reason": "Resolved in favor of the artist"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_resolve_dispute_requires_valid_target_status(
    client: TestClient, db_session: Session
) -> None:
    booking = make_booking(db_session, status=BookingStatus.DISPUTED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/resolve-dispute",
        json={"to_status": "confirmed", "reason": "Testing"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_cannot_resolve_a_dispute_on_a_non_disputed_booking(
    client: TestClient, db_session: Session
) -> None:
    booking = make_booking(db_session, status=BookingStatus.CONFIRMED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/bookings/{booking.id}/resolve-dispute",
        json={"to_status": "completed", "reason": "Testing"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_filter_bookings_by_artist(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    mine = make_booking(db_session, artist_profile=artist_profile)
    make_booking(db_session)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/bookings",
        params={"artist_profile_id": str(artist_profile.id)},
        headers=auth_headers(admin_token),
    )

    ids = {b["id"] for b in response.json()["items"]}
    assert ids == {str(mine.id)}
