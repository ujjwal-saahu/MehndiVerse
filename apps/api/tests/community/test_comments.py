from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import DesignStatus
from app.db.models.engagement import Comment
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_comment,
    make_design,
    make_user,
    make_user_block,
)


def _published_design(db_session: Session):
    artist_profile = make_artist_profile(db_session)
    design = make_design(
        db_session, artist_profile=artist_profile, status=DesignStatus.PUBLISHED.value
    )
    db_session.commit()
    return artist_profile, design


def _token(db_session: Session, *, role: str = "customer") -> tuple:
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def test_create_comment_requires_authentication(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)

    response = client.post(f"/api/v1/designs/{design.id}/comments", json={"body": "Nice!"})

    assert response.status_code == 401


def test_create_and_list_top_level_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    user, token = _token(db_session)

    create_response = client.post(
        f"/api/v1/designs/{design.id}/comments",
        json={"body": "Beautiful design!"},
        headers=auth_headers(token),
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["body"] == "Beautiful design!"
    assert body["replies"] == []

    list_response = client.get(f"/api/v1/designs/{design.id}/comments", headers=auth_headers(token))
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


def test_cannot_comment_on_unpublished_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status=DesignStatus.DRAFT.value)
    db_session.commit()
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{design.id}/comments", json={"body": "Hi"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_html_is_stripped_from_comment_body(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{design.id}/comments",
        json={"body": "<script>alert(1)</script>Nice work"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["body"] == "alert(1)Nice work"


def test_reply_to_top_level_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, author_token = _token(db_session)
    top_level = make_comment(db_session, design=design, user=author)
    db_session.commit()
    _, replier_token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{design.id}/comments",
        json={"body": "I agree!", "parent_comment_id": str(top_level.id)},
        headers=auth_headers(replier_token),
    )

    assert response.status_code == 201

    list_response = client.get(
        f"/api/v1/designs/{design.id}/comments", headers=auth_headers(author_token)
    )
    items = list_response.json()["items"]
    assert len(items) == 1
    assert len(items[0]["replies"]) == 1
    assert items[0]["replies"][0]["body"] == "I agree!"
    assert items[0]["replies"][0]["parent_comment_id"] == str(top_level.id)


def test_replying_to_a_reply_is_rejected(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, _ = _token(db_session)
    top_level = make_comment(db_session, design=design, user=author)
    reply = make_comment(db_session, design=design, user=author, parent_comment_id=top_level.id)
    db_session.commit()
    _, token = _token(db_session)

    response = client.post(
        f"/api/v1/designs/{design.id}/comments",
        json={"body": "Nested reply", "parent_comment_id": str(reply.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_owner_can_edit_own_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, token = _token(db_session)
    comment = make_comment(db_session, design=design, user=author, body="Original")
    db_session.commit()

    response = client.patch(
        f"/api/v1/comments/{comment.id}", json={"body": "Edited"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["body"] == "Edited"


def test_non_owner_cannot_edit_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, _ = _token(db_session)
    comment = make_comment(db_session, design=design, user=author)
    db_session.commit()
    _, other_token = _token(db_session)

    response = client.patch(
        f"/api/v1/comments/{comment.id}",
        json={"body": "Hijacked"},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_owner_can_delete_own_comment_and_it_disappears_from_listing(
    client: TestClient, db_session: Session
) -> None:
    _, design = _published_design(db_session)
    author, token = _token(db_session)
    comment = make_comment(db_session, design=design, user=author)
    db_session.commit()

    delete_response = client.delete(f"/api/v1/comments/{comment.id}", headers=auth_headers(token))
    assert delete_response.status_code == 204

    list_response = client.get(f"/api/v1/designs/{design.id}/comments", headers=auth_headers(token))
    assert list_response.json()["items"] == []


def test_non_owner_cannot_delete_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, _ = _token(db_session)
    comment = make_comment(db_session, design=design, user=author)
    db_session.commit()
    _, other_token = _token(db_session)

    response = client.delete(f"/api/v1/comments/{comment.id}", headers=auth_headers(other_token))

    assert response.status_code == 403


def test_deleting_comment_preserves_body_for_moderation(
    client: TestClient, db_session: Session
) -> None:
    _, design = _published_design(db_session)
    author, token = _token(db_session)
    comment = make_comment(db_session, design=design, user=author, body="Rude comment")
    db_session.commit()

    client.delete(f"/api/v1/comments/{comment.id}", headers=auth_headers(token))

    db_session.expire_all()
    reloaded = db_session.get(Comment, comment.id)
    assert reloaded is not None
    assert reloaded.deleted_at is not None
    assert reloaded.body == "Rude comment"


def test_blocked_user_cannot_comment_on_artists_design(
    client: TestClient, db_session: Session
) -> None:
    artist_profile, design = _published_design(db_session)
    artist_user = db_session.get(User, artist_profile.user_id)
    assert artist_user is not None
    commenter, token = _token(db_session)
    make_user_block(db_session, blocker=artist_user, blocked=commenter)
    db_session.commit()

    response = client.post(
        f"/api/v1/designs/{design.id}/comments",
        json={"body": "Hi"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_comment_rate_limit_enforced(client: TestClient, db_session: Session) -> None:
    # Default comment_rate_limit is "20/minute" (app/core/config.py) — the
    # 21st request in a minute should be throttled.
    _, design = _published_design(db_session)
    _, token = _token(db_session)

    statuses = [
        client.post(
            f"/api/v1/designs/{design.id}/comments",
            json={"body": f"Comment {i}"},
            headers=auth_headers(token),
        ).status_code
        for i in range(21)
    ]

    assert statuses[:20] == [201] * 20
    assert statuses[20] == 429


def test_report_comment(client: TestClient, db_session: Session) -> None:
    _, design = _published_design(db_session)
    author, _ = _token(db_session)
    comment = make_comment(db_session, design=design, user=author)
    db_session.commit()
    _, reporter_token = _token(db_session)

    response = client.post(
        f"/api/v1/comments/{comment.id}/report",
        json={"reason": "Spam"},
        headers=auth_headers(reporter_token),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["reported_entity_type"] == "comment"


def test_reporting_same_comment_twice_while_pending_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    _, design = _published_design(db_session)
    author, _ = _token(db_session)
    comment = make_comment(db_session, design=design, user=author)
    db_session.commit()
    _, reporter_token = _token(db_session)

    first = client.post(
        f"/api/v1/comments/{comment.id}/report",
        json={"reason": "Spam"},
        headers=auth_headers(reporter_token),
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/comments/{comment.id}/report",
        json={"reason": "Spam again"},
        headers=auth_headers(reporter_token),
    )
    assert second.status_code == 409
