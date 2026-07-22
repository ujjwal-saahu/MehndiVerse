"""Message reporting — see docs/booking-messaging.md#8. Reuses the generic
`reports` table (ReportEntityType.MESSAGE) from Phase 6/7 moderation."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.moderation import Report
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def _setup_message(db_session: Session, client: TestClient):
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)
    message = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "inappropriate content"},
        headers=auth_headers(customer_token),
    ).json()
    return profile, customer, booking, message


def test_conversation_member_can_report_a_message(client: TestClient, db_session: Session) -> None:
    profile, customer, booking, message = _setup_message(db_session, client)
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/messages/{message['id']}/report",
        json={"reason": "This is inappropriate."},
        headers=auth_headers(artist_token),
    )

    assert response.status_code == 201
    report = db_session.execute(select(Report)).scalars().first()
    assert report is not None
    assert report.reported_entity_type == "message"
    assert (
        report.reported_entity_id == message["id"]
        or str(report.reported_entity_id) == message["id"]
    )


def test_third_party_cannot_report_a_message_they_cannot_see(
    client: TestClient, db_session: Session
) -> None:
    profile, customer, booking, message = _setup_message(db_session, client)
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    third_party_token = sign_token(third_party.id, email=third_party.email)

    response = client.post(
        f"/api/v1/messages/{message['id']}/report",
        json={"reason": "spam"},
        headers=auth_headers(third_party_token),
    )
    assert response.status_code == 403


def test_report_unknown_message_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/messages/00000000-0000-0000-0000-000000000000/report",
        json={"reason": "spam"},
        headers=auth_headers(token),
    )
    assert response.status_code == 404
