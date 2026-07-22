"""GET/POST /legal/consent — see docs/legal-and-support.md#consent-records."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def test_create_consent_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/legal/consent",
        json={"consent_type": "cookies_analytics", "version": "2026-07-21", "granted": True},
    )
    assert response.status_code == 401


def test_create_consent_records_a_row(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/legal/consent",
        json={"consent_type": "cookies_analytics", "version": "2026-07-21", "granted": True},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["consent_type"] == "cookies_analytics"
    assert body["granted"] is True


def test_create_consent_rejects_unknown_type(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/legal/consent",
        json={"consent_type": "something_made_up", "version": "1", "granted": True},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_get_my_consent_returns_only_the_caller_s_own_records(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    other = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    other_token = sign_token(other.id, email=other.email)

    client.post(
        "/api/v1/legal/consent",
        json={"consent_type": "cookies_analytics", "version": "1", "granted": True},
        headers=auth_headers(token),
    )
    client.post(
        "/api/v1/legal/consent",
        json={"consent_type": "cookies_analytics", "version": "1", "granted": False},
        headers=auth_headers(other_token),
    )

    response = client.get("/api/v1/legal/consent", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["granted"] is True
