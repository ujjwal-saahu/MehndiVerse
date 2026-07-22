from datetime import date, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_availability_rule,
    make_user,
)


def _viewer_token(db_session: Session) -> str:
    viewer = make_user(db_session, role="customer")
    db_session.commit()
    return sign_token(viewer.id, email=viewer.email)


def test_slots_requires_authentication(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    db_session.commit()

    response = client.get(
        f"/api/v1/artists/{profile.id}/availability/slots",
        params={
            "service_id": str(service.id),
            "start_date": "2026-03-09",
            "end_date": "2026-03-09",
        },
    )

    assert response.status_code == 401


def test_slots_for_a_hidden_artist_is_404(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.DRAFT.value
    db_session.add(profile)
    service = make_artist_service(db_session, artist_profile=profile)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        f"/api/v1/artists/{profile.id}/availability/slots",
        params={
            "service_id": str(service.id),
            "start_date": "2026-03-09",
            "end_date": "2026-03-09",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_slots_for_a_service_belonging_to_another_artist_is_404(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    other_service = make_artist_service(db_session, artist_profile=other_profile)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        f"/api/v1/artists/{profile.id}/availability/slots",
        params={
            "service_id": str(other_service.id),
            "start_date": "2026-03-09",
            "end_date": "2026-03-09",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_slots_for_an_inactive_service_is_404(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile, is_active=False)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        f"/api/v1/artists/{profile.id}/availability/slots",
        params={
            "service_id": str(service.id),
            "start_date": "2026-03-09",
            "end_date": "2026-03-09",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def _next_monday_at_least_a_week_out() -> date:
    """A Monday safely in the future (this endpoint filters out past slots
    using the real wall clock, unlike the pure-function tests in
    tests/scheduling/test_slot_calculation.py, which pin `now_utc`)."""
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7  # next Monday, never today
    return today + timedelta(days=days_ahead + 7)  # and a week further, for safety


def test_slots_returns_computed_availability(client: TestClient, db_session: Session) -> None:
    monday = _next_monday_at_least_a_week_out()
    assert monday.weekday() == 0

    profile = make_artist_profile(db_session)
    profile.timezone = "Asia/Kolkata"
    db_session.add(profile)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=1,  # 0=Sunday..6=Saturday, so Monday == 1
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    db_session.commit()
    token = _viewer_token(db_session)

    response = client.get(
        f"/api/v1/artists/{profile.id}/availability/slots",
        params={
            "service_id": str(service.id),
            "start_date": monday.isoformat(),
            "end_date": monday.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["artist_timezone"] == "Asia/Kolkata"
    assert len(body["slots"]) == 2
    # 09:00 IST == 03:30 UTC.
    assert body["slots"][0]["start"] == f"{monday.isoformat()}T03:30:00Z"
