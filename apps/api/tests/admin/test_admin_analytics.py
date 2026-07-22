"""Admin analytics views — see docs/analytics-and-recommendations.md#admin-
analytics-views. Role-gated the same way every other admin-reporting route
in this codebase is (`moderator`/`admin`/`super_admin` may view; nothing
here mutates, so there is no edit-role split)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_trending_designs_requires_staff_role(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/analytics/trending-designs", headers=auth_headers(token))
    assert response.status_code == 403


def test_trending_designs_visible_to_moderator(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    make_design(db_session, status="published")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/analytics/trending-designs", headers=auth_headers(token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_popular_artists_visible_to_admin(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = "approved"
    db_session.add(artist_profile)
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.get("/api/v1/admin/analytics/popular-artists", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {item["artist_profile_id"] for item in response.json()}
    assert str(artist_profile.id) in ids


def test_search_analytics_requires_staff_role(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/analytics/search", headers=auth_headers(token))
    assert response.status_code == 403


def test_search_analytics_returns_a_summary_for_staff(
    client: TestClient, db_session: Session
) -> None:
    staff = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(staff.id, email=staff.email)

    response = client.get("/api/v1/admin/analytics/search", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert "total_searches" in body
    assert "zero_result_rate" in body
    assert "top_queries" in body


def test_booking_conversion_requires_staff_role(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/analytics/booking-conversion", headers=auth_headers(token))
    assert response.status_code == 403


def test_booking_conversion_returns_a_funnel_for_staff(
    client: TestClient, db_session: Session
) -> None:
    staff = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(staff.id, email=staff.email)

    response = client.get("/api/v1/admin/analytics/booking-conversion", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert "stage_counts" in body
    assert "stage_conversion_rates" in body
    assert "overall_conversion_rate" in body
