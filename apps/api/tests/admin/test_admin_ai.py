"""Staff-side AI operations surface — see
docs/ai-foundation.md#human-review. Mirrors admin_moderation.py's
`_VIEW_ROLES`/`_EDIT_ROLES` authorization split."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import AiJobStatus, AiReviewStatus, DuplicateMatchStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_ai_generation,
    make_ai_job,
    make_design,
    make_duplicate_match,
    make_user,
)


def test_jobs_list_requires_staff_role(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/ai/jobs", headers=auth_headers(token))
    assert response.status_code == 403


def test_jobs_list_visible_to_moderator(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    make_ai_job(db_session, status=AiJobStatus.PENDING.value)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/ai/jobs", headers=auth_headers(token))
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_jobs_list_filters_by_status(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    make_ai_job(db_session, status=AiJobStatus.FAILED.value)
    make_ai_job(db_session, status=AiJobStatus.PENDING.value)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(
        "/api/v1/admin/ai/jobs", params={"status": "failed"}, headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert all(job["status"] == "failed" for job in response.json())


def test_review_queue_lists_pending_generations(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    pending = make_ai_generation(db_session)
    pending.requires_human_review = True
    pending.review_status = AiReviewStatus.PENDING.value
    not_pending = make_ai_generation(db_session)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/ai/review-queue", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(pending.id) in ids
    assert str(not_pending.id) not in ids


def test_resolve_review_item_requires_edit_role(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    generation = make_ai_generation(db_session)
    generation.requires_human_review = True
    generation.review_status = AiReviewStatus.PENDING.value
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.post(
        f"/api/v1/admin/ai/review-queue/{generation.id}/resolve",
        json={"approved": True},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_resolve_review_item_succeeds_for_admin(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    generation = make_ai_generation(db_session)
    generation.requires_human_review = True
    generation.review_status = AiReviewStatus.PENDING.value
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/ai/review-queue/{generation.id}/resolve",
        json={"approved": True, "notes": "Confirmed fine."},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == AiReviewStatus.APPROVED.value


def test_resolve_review_item_rejects_double_resolution(
    client: TestClient, db_session: Session
) -> None:
    admin = make_user(db_session, role="administrator")
    generation = make_ai_generation(db_session)
    generation.review_status = AiReviewStatus.APPROVED.value
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/ai/review-queue/{generation.id}/resolve",
        json={"approved": True},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_duplicate_matches_list_and_resolve(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    design_a = make_design(db_session)
    design_b = make_design(db_session)
    match = make_duplicate_match(db_session, design=design_a, matched_design=design_b)
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    list_response = client.get("/api/v1/admin/ai/duplicate-matches", headers=auth_headers(token))
    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json()["items"]}
    assert str(match.id) in ids

    resolve_response = client.post(
        f"/api/v1/admin/ai/duplicate-matches/{match.id}/resolve",
        json={"approved": True},
        headers=auth_headers(token),
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == DuplicateMatchStatus.CONFIRMED.value
