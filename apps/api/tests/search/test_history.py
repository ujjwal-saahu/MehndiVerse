from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.search import SearchEvent
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_design, make_user


def test_history_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/search/history")
    assert response.status_code == 401


def test_history_returns_recent_distinct_queries_most_recent_first(
    client: TestClient, db_session: Session
) -> None:
    # Events are inserted directly (rather than via repeated calls to the
    # search endpoint) so each gets an explicit, distinct `created_at` —
    # `now()` is frozen for the life of a Postgres transaction, and this
    # test's whole HTTP session shares one, so back-to-back requests would
    # otherwise tie on timestamp.
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    base = datetime.now(UTC)
    for offset, q in enumerate(["bridal", "floral", "bridal", "mandala"]):
        db_session.add(
            SearchEvent(
                user_id=viewer.id,
                query=q,
                filters={},
                result_count=0,
                created_at=base + timedelta(seconds=offset),
            )
        )
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/search/history", headers=auth_headers(token))

    assert response.status_code == 200
    queries = [item["query"] for item in response.json()]
    assert queries == ["mandala", "bridal", "floral"]


def test_filters_only_search_does_not_appear_in_recent_searches(
    client: TestClient, db_session: Session
) -> None:
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/search", params={"is_premium": False}, headers=auth_headers(token)
    )
    assert response.status_code == 200

    history = client.get("/api/v1/designs/search/history", headers=auth_headers(token))
    assert history.status_code == 200
    assert history.json() == []


def test_history_is_scoped_per_user(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    viewer_a = make_user(db_session)
    viewer_b = make_user(db_session)
    db_session.commit()
    token_a = sign_token(viewer_a.id, email=viewer_a.email)
    token_b = sign_token(viewer_b.id, email=viewer_b.email)

    client.get("/api/v1/designs/search", params={"q": "only-a"}, headers=auth_headers(token_a))

    history_b = client.get("/api/v1/designs/search/history", headers=auth_headers(token_b))

    assert history_b.status_code == 200
    assert history_b.json() == []


def test_clear_search_history(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    client.get("/api/v1/designs/search", params={"q": "bridal"}, headers=auth_headers(token))
    assert (
        len(client.get("/api/v1/designs/search/history", headers=auth_headers(token)).json()) == 1
    )

    clear_response = client.delete("/api/v1/designs/search/history", headers=auth_headers(token))
    assert clear_response.status_code == 204

    after = client.get("/api/v1/designs/search/history", headers=auth_headers(token))
    assert after.json() == []
    assert db_session.query(SearchEvent).filter(SearchEvent.user_id == viewer.id).count() == 0
