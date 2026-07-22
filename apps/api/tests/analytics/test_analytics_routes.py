"""HTTP-level tests for `app/api/routes/analytics.py` — client-reported
events and the personalized recommendation endpoints. Also covers the
`analytics_consent` preferences toggle (`app/api/routes/profile.py`),
since it's this phase's addition to that existing endpoint."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.analytics import AnalyticsEvent
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_consenting_user, make_design, make_user


def test_report_event_requires_authentication(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/analytics/events", json={"event_type": "app_opened"})
    assert response.status_code == 401


def test_report_event_rejects_a_server_only_event_type(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/analytics/events",
        json={"event_type": "design_viewed"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_report_event_accepts_app_opened(client: TestClient, db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/analytics/events",
        json={"event_type": "app_opened"},
        headers=auth_headers(token),
    )
    assert response.status_code == 204

    stored = (
        db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.user_id == user.id, AnalyticsEvent.event_type == "app_opened"
            )
        )
        .scalars()
        .all()
    )
    assert len(stored) == 1


def test_report_event_accepts_design_shared(client: TestClient, db_session: Session) -> None:
    user = make_consenting_user(db_session)
    design = make_design(db_session, status="published")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/analytics/events",
        json={
            "event_type": "design_shared",
            "entity_type": "design",
            "entity_id": str(design.id),
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 204


def test_recently_viewed_requires_authentication(client: TestClient, db_session: Session) -> None:
    response = client.get("/api/v1/analytics/recently-viewed")
    assert response.status_code == 401


def test_recently_viewed_returns_empty_list_for_new_user(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/analytics/recently-viewed", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_recommended_returns_not_personalized_for_new_user(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/analytics/recommended", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["is_personalized"] is False
    assert body["items"] == []


def test_home_feed_always_returns_a_response_shape(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/analytics/home-feed", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert "recently_viewed" in body
    assert "recommended_for_you" in body
    assert "trending" in body
    assert "is_personalized" in body


def test_preferences_expose_and_update_analytics_consent(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    get_response = client.get("/api/v1/users/me/preferences", headers=auth_headers(token))
    assert get_response.status_code == 200
    assert get_response.json()["analytics_consent"] is False

    patch_response = client.patch(
        "/api/v1/users/me/preferences",
        json={"analytics_consent": True},
        headers=auth_headers(token),
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["analytics_consent"] is True
