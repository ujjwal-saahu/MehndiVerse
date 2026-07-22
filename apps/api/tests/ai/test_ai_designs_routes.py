"""HTTP-level tests for `app/api/routes/ai_designs.py` — see
docs/ai-design-assistant.md. Authorization, validation, and the full
create -> background-process -> read lifecycle (via the `mock_ai_provider`
fake, never a real network call) are exercised here; prompt/service-level
behavior is covered in test_design_generation_service.py."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.ai.design_generation import AI_GENERATED_LABEL
from app.services.ai.jobs import process_due_jobs
from tests.ai.conftest import FakeProvider, mock_design_sign, mock_design_upload
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_ai_design_request,
    make_artist_profile,
    make_booking,
    make_subscription,
    make_subscription_plan,
    make_user,
)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "style": "Arabic",
        "occasion": "wedding",
        "body_placement": "hand",
        "difficulty_level": "intermediate",
        "density": "bold",
        "is_symmetric": True,
        "pattern_elements": ["peacock", "paisley"],
        "theme": "royal",
        "personalization_text": "R+K",
        "additional_instructions": "Leave space for a bracelet.",
    }
    payload.update(overrides)
    return payload


def test_create_requires_authentication(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/ai/designs", json=_valid_payload())
    assert response.status_code == 401


def test_create_rejects_an_invalid_occasion(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/ai/designs",
        json=_valid_payload(occasion="not-a-real-occasion"),
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_create_rejects_disallowed_prompt_content(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/ai/designs",
        json=_valid_payload(theme="weapon collection"),
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_create_response_includes_the_ai_generated_label(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post("/api/v1/ai/designs", json=_valid_payload(), headers=auth_headers(token))
    assert response.status_code == 202
    body = response.json()
    assert body["is_ai_generated"] is True
    assert body["ai_generated_label"] == AI_GENERATED_LABEL
    assert body["status"] == "pending"
    assert body["retry_count"] == 0
    assert body["max_retries"] == 3


def test_create_is_blocked_once_quota_is_exhausted(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"ai_credits_per_month": 1}
    )
    make_subscription(db_session, user=user, plan=plan, status="active")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    first = client.post("/api/v1/ai/designs", json=_valid_payload(), headers=auth_headers(token))
    assert first.status_code == 202

    second = client.post("/api/v1/ai/designs", json=_valid_payload(), headers=auth_headers(token))
    assert second.status_code == 403


def test_full_lifecycle_create_process_and_read(
    client: TestClient, db_session: Session, mock_ai_provider: FakeProvider, storage_mock
) -> None:
    mock_design_upload(storage_mock)
    mock_design_sign(storage_mock)
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    create_response = client.post(
        "/api/v1/ai/designs", json=_valid_payload(), headers=auth_headers(token)
    )
    assert create_response.status_code == 202
    request_id = create_response.json()["id"]

    process_due_jobs(db_session, limit=10)
    db_session.commit()

    get_response = client.get(f"/api/v1/ai/designs/{request_id}", headers=auth_headers(token))
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "completed"
    assert body["result_image_url"] is not None
    assert body["provider"] == "fake"


def test_get_forbidden_for_a_stranger(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/ai/designs/{request.id}", headers=auth_headers(token))
    assert response.status_code == 403


def test_list_only_returns_the_caller_s_own_requests(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    mine = make_ai_design_request(db_session, user=owner)
    make_ai_design_request(db_session, user=other)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get("/api/v1/ai/designs", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(mine.id) in ids
    assert len(ids) == 1


def test_retry_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner, status="failed")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.post(f"/api/v1/ai/designs/{request.id}/retry", headers=auth_headers(token))
    assert response.status_code == 403


def test_retry_rejects_a_non_failed_request(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner, status="completed")
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(f"/api/v1/ai/designs/{request.id}/retry", headers=auth_headers(token))
    assert response.status_code == 422


def test_retry_is_blocked_once_max_retries_reached(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(
        db_session, user=owner, status="failed", retry_count=3, max_retries=3
    )
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(f"/api/v1/ai/designs/{request.id}/retry", headers=auth_headers(token))
    assert response.status_code == 429


def test_retry_succeeds_and_increments_retry_count(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner, status="failed")
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(f"/api/v1/ai/designs/{request.id}/retry", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["retry_count"] == 1
    assert body["status"] == "pending"


def test_save_and_unsave(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    save_response = client.post(
        f"/api/v1/ai/designs/{request.id}/save", headers=auth_headers(token)
    )
    assert save_response.status_code == 200
    assert save_response.json()["is_saved"] is True

    unsave_response = client.delete(
        f"/api/v1/ai/designs/{request.id}/save", headers=auth_headers(token)
    )
    assert unsave_response.status_code == 200
    assert unsave_response.json()["is_saved"] is False


def test_share_requires_a_ready_result(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner, result_storage_path=None)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get(f"/api/v1/ai/designs/{request.id}/share", headers=auth_headers(token))
    assert response.status_code == 422


def test_share_returns_a_signed_url(client: TestClient, db_session: Session, storage_mock) -> None:
    mock_design_sign(storage_mock)
    owner = make_user(db_session)
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get(f"/api/v1/ai/designs/{request.id}/share", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["url"]


def test_send_to_artist_requires_ownership_of_the_booking(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    artist_profile = make_artist_profile(db_session)
    other_customer = make_user(db_session)
    booking = make_booking(db_session, customer=other_customer, artist_profile=artist_profile)
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/ai/designs/{request.id}/send-to-artist",
        json={"booking_id": str(booking.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_send_to_artist_succeeds(client: TestClient, db_session: Session, storage_mock) -> None:
    mock_design_sign(storage_mock)
    owner = make_user(db_session)
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(
        db_session, customer=owner, artist_profile=artist_profile, status="confirmed"
    )
    request = make_ai_design_request(
        db_session, user=owner, result_storage_path="u/req/result_0.png"
    )
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/ai/designs/{request.id}/send-to-artist",
        json={"booking_id": str(booking.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["shared_with_booking_id"] == str(booking.id)


def test_delete_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    stranger = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.delete(f"/api/v1/ai/designs/{request.id}", headers=auth_headers(token))
    assert response.status_code == 403


def test_delete_succeeds_for_owner(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    request = make_ai_design_request(db_session, user=owner)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.delete(f"/api/v1/ai/designs/{request.id}", headers=auth_headers(token))
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/ai/designs/{request.id}", headers=auth_headers(token))
    assert get_response.status_code == 404
