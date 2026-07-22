from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user

_RULE = {"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00"}


def test_list_rules_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artist/availability/rules")
    assert response.status_code == 401


def test_create_rule_requires_an_artist_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token)
    )

    assert response.status_code == 404


def test_customer_cannot_create_a_rule(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_create_and_list_rule(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    create_response = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token)
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["day_of_week"] == 1
    assert body["start_time"] == "09:00:00"
    assert body["is_active"] is True

    list_response = client.get("/api/v1/artist/availability/rules", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_rule_rejects_invalid_range(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "17:00:00", "end_time": "09:00:00"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_create_rule_rejects_out_of_range_day_of_week(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 7, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_create_rule_rejects_overlap_with_existing_rule_same_day(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post("/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token))

    response = client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "16:00:00", "end_time": "20:00:00"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_create_rule_allows_non_overlapping_same_day(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "12:00:00"},
        headers=auth_headers(token),
    )

    response = client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "13:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201


def test_create_rule_allows_same_hours_on_a_different_day(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post("/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token))

    response = client.post(
        "/api/v1/artist/availability/rules",
        json={**_RULE, "day_of_week": 2},
        headers=auth_headers(token),
    )

    assert response.status_code == 201


def test_update_rule(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/v1/artist/availability/rules/{created['id']}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_update_rule_rejects_overlap_with_another_rule(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "12:00:00"},
        headers=auth_headers(token),
    )
    second = client.post(
        "/api/v1/artist/availability/rules",
        json={"day_of_week": 1, "start_time": "13:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    ).json()

    response = client.patch(
        f"/api/v1/artist/availability/rules/{second['id']}",
        json={"start_time": "11:00:00"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_another_artist_cannot_update_someone_elses_rule(
    client: TestClient, db_session: Session
) -> None:
    owner = make_artist_profile(db_session)
    other = make_artist_profile(db_session)
    db_session.commit()
    owner_token = sign_token(owner.user_id, email="owner@example.com")
    other_token = sign_token(other.user_id, email="other@example.com")
    created = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(owner_token)
    ).json()

    response = client.patch(
        f"/api/v1/artist/availability/rules/{created['id']}",
        json={"is_active": False},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_delete_rule(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")
    created = client.post(
        "/api/v1/artist/availability/rules", json=_RULE, headers=auth_headers(token)
    ).json()

    response = client.delete(
        f"/api/v1/artist/availability/rules/{created['id']}", headers=auth_headers(token)
    )
    assert response.status_code == 204

    list_response = client.get("/api/v1/artist/availability/rules", headers=auth_headers(token))
    assert list_response.json() == []


def test_delete_unknown_rule_is_404(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.delete(
        "/api/v1/artist/availability/rules/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
