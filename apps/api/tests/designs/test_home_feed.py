from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_design, make_user


def test_home_feed_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/home-feed")
    assert response.status_code == 401


def test_home_feed_returns_the_three_sections(client: TestClient, db_session: Session) -> None:
    latest = make_design(db_session, status="published")
    featured = make_design(db_session, status="published")
    featured.is_featured = True
    trending = make_design(db_session, status="published")
    trending.view_count = 500
    db_session.add_all([latest, featured, trending])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/home-feed", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert {"latest", "featured", "trending"} <= body.keys()

    latest_ids = [item["id"] for item in body["latest"]]
    featured_ids = [item["id"] for item in body["featured"]]
    trending_ids = [item["id"] for item in body["trending"]]

    assert str(latest.id) in latest_ids
    assert str(featured.id) in featured_ids
    assert str(latest.id) not in featured_ids  # not featured, shouldn't appear there
    assert trending_ids[0] == str(trending.id)  # highest view_count first


def test_home_feed_excludes_drafts_from_every_section(
    client: TestClient, db_session: Session
) -> None:
    draft = make_design(db_session, status="draft")
    draft.is_featured = True
    draft.view_count = 999999
    db_session.add(draft)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/home-feed", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    all_ids = {item["id"] for section in body.values() for item in section}
    assert str(draft.id) not in all_ids


def test_home_feed_sets_a_safe_public_cache_header(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/home-feed", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("public")


def test_home_feed_query_count_does_not_scale_with_design_count(
    client: TestClient, db_session: Session
) -> None:
    """Query-optimization regression guard — see
    docs/design-gallery.md#query-optimization. A naive per-design lookup for
    primary images/artist info would issue O(n) extra queries; the batched
    implementation issues a small, constant number regardless of how many
    designs are in the feed."""
    for _ in range(15):
        make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    statement_count = 0

    def _count_statements(*args: object, **kwargs: object) -> None:
        nonlocal statement_count
        statement_count += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _count_statements)
    try:
        response = client.get("/api/v1/designs/home-feed", headers=auth_headers(token))
    finally:
        event.remove(engine, "before_cursor_execute", _count_statements)

    assert response.status_code == 200
    # 3 section queries + at most 2 batch queries (images, artists) + a
    # handful of auth/session bookkeeping queries — nowhere near the 15+
    # per-design queries a naive N+1 implementation would issue.
    assert statement_count < 15
