from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user


def test_list_blocks_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artist/availability/blocks")
    assert response.status_code == 401


def test_create_block_requires_an_artist_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-12", "block_type": "vacation"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_create_whole_day_block(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-12",
            "block_type": "vacation",
            "reason": "Family trip",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["block_type"] == "vacation"
    assert body["start_time"] is None
    assert body["reason"] == "Family trip"


def test_create_manual_time_scoped_block(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "block_type": "personal_leave",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["start_time"] == "14:00:00"
    assert body["end_time"] == "16:00:00"


def test_time_scoped_block_across_multiple_days_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-11",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_block_rejects_end_date_before_start_date(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-12", "end_date": "2026-03-10"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_block_rejects_end_time_before_start_time(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "16:00:00",
            "end_time": "14:00:00",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_block_rejects_unknown_block_type(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10", "block_type": "bogus"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_block_rejects_overlapping_whole_day_range(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-15", "block_type": "vacation"},
        headers=auth_headers(token),
    )

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-14", "end_date": "2026-03-20", "block_type": "vacation"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_whole_day_block_conflicts_with_an_existing_time_scoped_block_same_date(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        },
        headers=auth_headers(token),
    )

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10", "block_type": "holiday"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_two_non_overlapping_time_scoped_blocks_same_date_are_both_allowed(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        headers=auth_headers(token),
    )

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201


def test_overlapping_time_scoped_blocks_same_date_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
        },
        headers=auth_headers(token),
    )

    response = client.post(
        "/api/v1/artist/availability/blocks",
        json={
            "start_date": "2026-03-10",
            "end_date": "2026-03-10",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_list_blocks_filters_by_date_range(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-01-01", "end_date": "2026-01-02"},
        headers=auth_headers(token),
    )
    client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-06-01", "end_date": "2026-06-02"},
        headers=auth_headers(token),
    )

    response = client.get(
        "/api/v1/artist/availability/blocks",
        params={"start_date": "2026-05-01", "end_date": "2026-07-01"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["start_date"] == "2026-06-01"


def test_update_block(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10", "block_type": "other"},
        headers=auth_headers(token),
    ).json()

    response = client.patch(
        f"/api/v1/artist/availability/blocks/{created['id']}",
        json={"reason": "Updated reason"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "Updated reason"


def test_another_artist_cannot_delete_someone_elses_block(
    client: TestClient, db_session: Session
) -> None:
    owner = make_artist_profile(db_session)
    other = make_artist_profile(db_session)
    db_session.commit()
    owner_token = sign_token(owner.user_id, email="owner@example.com")
    other_token = sign_token(other.user_id, email="other@example.com")
    created = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10"},
        headers=auth_headers(owner_token),
    ).json()

    response = client.delete(
        f"/api/v1/artist/availability/blocks/{created['id']}", headers=auth_headers(other_token)
    )

    assert response.status_code == 403


def test_delete_block(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/availability/blocks",
        json={"start_date": "2026-03-10", "end_date": "2026-03-10"},
        headers=auth_headers(token),
    ).json()

    response = client.delete(
        f"/api/v1/artist/availability/blocks/{created['id']}", headers=auth_headers(token)
    )

    assert response.status_code == 204
