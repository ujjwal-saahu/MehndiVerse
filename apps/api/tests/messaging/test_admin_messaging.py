"""Staff-only conversation access for dispute review — see
docs/booking-messaging.md#7."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def _setup_conversation(db_session: Session, client: TestClient):
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)
    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "please help with a dispute"},
        headers=auth_headers(customer_token),
    )
    return profile, customer, booking


def test_customer_cannot_use_the_admin_endpoint(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_conversation(db_session, client)
    token = sign_token(customer.id, email=customer.email)

    response = client.get(
        f"/api/v1/admin/bookings/{booking.id}/conversation/messages", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_moderator_can_view_and_it_is_audited(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_conversation(db_session, client)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(
        f"/api/v1/admin/bookings/{booking.id}/conversation/messages", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["body"] == "please help with a dispute"

    audit_entries = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "conversation.admin_view"))
        .scalars()
        .all()
    )
    assert len(audit_entries) == 1
    assert audit_entries[0].actor_id == moderator.id


def test_admin_view_of_booking_with_no_conversation_is_404(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(
        f"/api/v1/admin/bookings/{booking.id}/conversation/messages", headers=auth_headers(token)
    )
    assert response.status_code == 404
