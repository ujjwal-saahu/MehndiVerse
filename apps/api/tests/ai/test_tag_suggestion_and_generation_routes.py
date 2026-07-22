"""GET .../ai/tag-suggestions, POST .../resolve, POST .../embeddings, and
POST .../moderation-check's success path — uncovered before Phase 26
(coverage audit). Denial-path tests for these already exist in
test_routes.py; these cover the success paths."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import AiGenerationStatus, TagSuggestionStatus
from app.db.models.ai import DesignTagSuggestion
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def _make_tag_suggestion(
    db: Session, *, design_id: uuid.UUID, tag_name: str = "bridal"
) -> DesignTagSuggestion:
    suggestion = DesignTagSuggestion(design_id=design_id, tag_name=tag_name, confidence=0.8)
    db.add(suggestion)
    db.flush()
    return suggestion


def test_list_tag_suggestions_visible_to_owner(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    _make_tag_suggestion(db_session, design_id=design.id)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["tag_name"] == "bridal"


def test_list_tag_suggestions_forbidden_for_non_owner(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_owner_can_accept_a_tag_suggestion(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    suggestion = _make_tag_suggestion(db_session, design_id=design.id)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions/{suggestion.id}/resolve",
        json={"accepted": True},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == TagSuggestionStatus.ACCEPTED.value


def test_resolving_an_already_resolved_suggestion_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    suggestion = _make_tag_suggestion(db_session, design_id=design.id)
    suggestion.status = TagSuggestionStatus.ACCEPTED.value
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions/{suggestion.id}/resolve",
        json={"accepted": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_resolve_returns_404_for_a_suggestion_belonging_to_a_different_design(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    other_design = make_design(db_session, artist_profile=artist_profile)
    suggestion = _make_tag_suggestion(db_session, design_id=other_design.id)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/tag-suggestions/{suggestion.id}/resolve",
        json={"accepted": True},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_owner_can_request_embedding_generation(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/embeddings", headers=auth_headers(token)
    )

    assert response.status_code == 202
    body = response.json()
    assert body["generation_type"] == "embedding_generation"
    assert body["status"] in {AiGenerationStatus.PENDING.value, AiGenerationStatus.PROCESSING.value}


def test_owner_can_request_a_moderation_check(client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/ai/moderation-check", headers=auth_headers(token)
    )

    assert response.status_code == 202
    body = response.json()
    assert body["generation_type"] == "moderation_check"
