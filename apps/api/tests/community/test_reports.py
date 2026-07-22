import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus, DesignStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_conversation,
    make_design,
    make_message,
    make_user,
)


def _token(db_session: Session, *, role: str = "customer"):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def test_report_design_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/report", json={"reason": "Stolen art"})

    assert response.status_code == 401


def test_report_design_success(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{design.id}/report",
        json={"reason": "This looks stolen"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["reported_entity_type"] == "design"
    assert body["reported_entity_id"] == str(design.id)


def test_report_nonexistent_design_404s(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{uuid.uuid4()}/report",
        json={"reason": "Missing"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_report_user_success(client: TestClient, db_session: Session) -> None:
    target = make_user(db_session, role="customer")
    db_session.commit()
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/users/{target.id}/report",
        json={"reason": "Harassment"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["reported_entity_type"] == "user"


def test_cannot_report_yourself(client: TestClient, db_session: Session) -> None:
    user, token = _token(db_session)

    response = client.post(
        f"/api/v1/users/{user.id}/report",
        json={"reason": "self report"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_duplicate_pending_report_against_same_target_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    _, token = _token(db_session)

    first = client.post(
        f"/api/v1/designs/{design.id}/report",
        json={"reason": "Copy"},
        headers=auth_headers(token),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/designs/{design.id}/report",
        json={"reason": "Copy again"},
        headers=auth_headers(token),
    )
    assert second.status_code == 409


def test_report_message_success(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.CONFIRMED.value,
    )
    conversation = make_conversation(db_session, booking=booking)
    message = make_message(db_session, conversation=conversation, sender=customer, body="rude text")
    db_session.commit()
    artist_token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/messages/{message.id}/report",
        json={"reason": "Abusive"},
        headers=auth_headers(artist_token),
    )

    assert response.status_code == 201
    assert response.json()["reported_entity_type"] == "message"


def test_reporting_same_message_twice_while_pending_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.CONFIRMED.value,
    )
    conversation = make_conversation(db_session, booking=booking)
    message = make_message(db_session, conversation=conversation, sender=customer, body="rude text")
    db_session.commit()
    artist_token = sign_token(artist_profile.user_id, email="artist@example.com")

    first = client.post(
        f"/api/v1/messages/{message.id}/report",
        json={"reason": "Abusive"},
        headers=auth_headers(artist_token),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/messages/{message.id}/report",
        json={"reason": "Still abusive"},
        headers=auth_headers(artist_token),
    )
    assert second.status_code == 409


def test_non_member_cannot_report_message(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=artist_profile,
        status=BookingStatus.CONFIRMED.value,
    )
    conversation = make_conversation(db_session, booking=booking)
    message = make_message(db_session, conversation=conversation, sender=customer, body="hi")
    db_session.commit()
    _, outsider_token = _token(db_session)

    response = client.post(
        f"/api/v1/messages/{message.id}/report",
        json={"reason": "Abusive"},
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 403
