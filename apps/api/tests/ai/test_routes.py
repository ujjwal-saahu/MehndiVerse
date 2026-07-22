"""HTTP-level tests for `app/api/routes/ai.py` — design-scoped AI
capability endpoints and generation status polling. Authorization is
exercised here (route layer); provider/job mechanics are covered in
test_capabilities.py and test_jobs_queue.py. The client-reported analytics-
events endpoint moved to `/analytics/events` in Phase 22 — see
tests/analytics/test_analytics_routes.py."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import AiGenerationStatus, AiReviewStatus
from app.db.models.system import SystemSetting
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_ai_generation, make_artist_profile, make_design, make_user


def test_request_tag_suggestions_requires_authentication(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session)
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/ai/tag-suggestions")
    assert response.status_code == 401


def test_request_tag_suggestions_forbidden_for_non_owner(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    other_user = make_user(db_session)
    db_session.commit()
    token = sign_token(other_user.id, email=other_user.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_request_tag_suggestions_succeeds_for_owner(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions", headers=auth_headers(token)
    )
    assert response.status_code == 202
    body = response.json()
    assert body["generation_type"] == "tag_suggestion"
    assert body["status"] in {AiGenerationStatus.PENDING.value, AiGenerationStatus.PROCESSING.value}


def test_request_tag_suggestions_returns_503_when_feature_disabled(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.add(SystemSetting(key="ai.tag_suggestions.enabled", value={"enabled": False}))
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions", headers=auth_headers(token)
    )
    assert response.status_code == 503


def test_get_generation_status_forbidden_for_a_different_user(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    generation = make_ai_generation(db_session, user=owner)
    other_user = make_user(db_session)
    db_session.commit()
    token = sign_token(other_user.id, email=other_user.email)

    response = client.get(f"/api/v1/ai/generations/{generation.id}", headers=auth_headers(token))
    assert response.status_code == 403


def test_get_generation_status_visible_to_staff(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    generation = make_ai_generation(db_session, user=owner)
    staff = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(staff.id, email=staff.email)

    response = client.get(f"/api/v1/ai/generations/{generation.id}", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["review_status"] == AiReviewStatus.NOT_REQUIRED.value


def test_similar_designs_endpoint_requires_authentication(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.get(f"/api/v1/designs/{design.id}/ai/similar")
    assert response.status_code == 401


def test_similar_designs_endpoint_open_to_any_authenticated_user_for_a_published_design(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{design.id}/ai/similar", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []


def test_similar_designs_endpoint_404s_for_a_missing_design(
    client: TestClient, db_session: Session
) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{uuid.uuid4()}/ai/similar", headers=auth_headers(token))
    assert response.status_code == 404


def test_similar_designs_endpoint_404s_for_an_unpublished_design_to_a_stranger(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="draft")
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/designs/{design.id}/ai/similar", headers=auth_headers(token))
    assert response.status_code == 404


def test_moderation_check_route_requires_permission(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/moderation-check", headers=auth_headers(token)
    )
    assert response.status_code == 403
