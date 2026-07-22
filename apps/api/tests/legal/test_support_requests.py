"""POST /support/requests — see docs/legal-and-support.md#report-a-problem-
and-contact-support."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.support import SupportRequest
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def test_guest_can_submit_a_support_request(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/v1/support/requests",
        json={
            "contact_email": "guest@example.com",
            "category": "bug_report",
            "subject": "Upload button does nothing",
            "message": "Tapping upload on the design form does nothing on Safari.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"

    row = db_session.get(SupportRequest, body["id"])
    assert row is not None
    assert row.user_id is None
    assert row.contact_email == "guest@example.com"


def test_signed_in_user_s_support_request_is_attributed_to_their_account(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/support/requests",
        json={
            "contact_email": user.email,
            "category": "account_issue",
            "subject": "Can't change my email",
            "message": "The settings page 404s when I try to update my email.",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    row = db_session.execute(
        select(SupportRequest).where(SupportRequest.id == response.json()["id"])
    ).scalar_one()
    assert row.user_id == user.id


def test_rejects_unknown_category(client: TestClient) -> None:
    response = client.post(
        "/api/v1/support/requests",
        json={
            "contact_email": "guest@example.com",
            "category": "not_a_real_category",
            "subject": "x",
            "message": "y",
        },
    )
    assert response.status_code == 422


def test_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/support/requests",
        json={
            "contact_email": "not-an-email",
            "category": "other",
            "subject": "x",
            "message": "y",
        },
    )
    assert response.status_code == 422


def test_support_requests_are_rate_limited(client: TestClient) -> None:
    statuses = [
        client.post(
            "/api/v1/support/requests",
            json={
                "contact_email": "spammer@example.com",
                "category": "other",
                "subject": "x",
                "message": "y",
            },
        ).status_code
        for _ in range(6)
    ]
    assert statuses[:5] == [201, 201, 201, 201, 201]
    assert statuses[5] == 429
