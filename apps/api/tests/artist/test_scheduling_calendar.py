from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile


def test_calendar_requires_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/artist/availability/calendar",
        params={"start_date": "2026-03-09", "end_date": "2026-03-15"},
    )
    assert response.status_code == 401


def test_calendar_rejects_end_before_start(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/artist/availability/calendar",
        params={"start_date": "2026-03-15", "end_date": "2026-03-09"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_calendar_rejects_range_over_60_days(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/artist/availability/calendar",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_calendar_shows_windows_and_blocks_per_day(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    # 2026-03-09 is a Monday.
    client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )
    client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10", "block_type": "holiday"},
        headers=auth_headers(token),
    )

    response = client.get(
        "/api/v1/artist/availability/calendar",
        params={"start_date": "2026-03-09", "end_date": "2026-03-10"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "UTC"
    days = {d["date"]: d for d in body["days"]}

    monday = days["2026-03-09"]
    assert monday["is_available"] is True
    assert len(monday["windows"]) == 1
    assert monday["blocks"] == []

    tuesday = days["2026-03-10"]
    assert tuesday["is_available"] is False
    assert len(tuesday["blocks"]) == 1
